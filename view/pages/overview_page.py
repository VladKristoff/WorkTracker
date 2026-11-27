"""«Обзор»: главные числа группы и список тех, кому нужно внимание."""
import tkinter as tk
from tkinter import ttk, messagebox

from database import repository
from styles import font
from utils.dates import iso_to_display
from view import insights
from view.insights import fmt_number, fmt_average
from view.widgets import DataTable, ThresholdFields, Debouncer, card, page_header, stat_row


class OverviewPage:
    def __init__(self, content, app):
        self.app = app
        self.bins = []

        actions, self.subtitle = page_header(content, "Обзор группы")
        ThresholdFields(actions, app, self.refresh).pack(side="left")

        self.stats = stat_row(content, ("Студентов", "Средний балл",
                                        "Среднее пропусков", "Проведено занятий"))

        body = ttk.Frame(content)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3, uniform="body")
        body.columnconfigure(1, weight=2, uniform="body")
        body.rowconfigure(0, weight=1)

        # --- Кому нужно внимание ---
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.attention_title = ttk.Label(left, text="Требуют внимания", font=font(12, True))
        self.attention_title.pack(anchor="w")
        ttk.Label(left, text="Двойной щелчок или Enter открывает карточку студента",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 8))
        self.table = DataTable(
            left, app.palette,
            [("fio", "ФИО", 180, "w", True), ("score", "Балл", 60, "center", False),
             ("missed", "Пропуски", 80, "center", False), ("notes", "Почему", 240, "w", True)],
            on_open=self.open_student, empty_text="По текущим порогам все в порядке")
        self.table.pack(fill="both", expand=True)

        # --- Распределение баллов и замечания к файлу ---
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        if app.warnings:  # упаковывается первым, чтобы не обрезаться на низком экране
            self._build_warnings(right)
        chart = card(right, "Распределение итоговых баллов")
        chart.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(chart, height=120, width=200, bg=app.palette["surface"], bd=0,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        redraw = Debouncer(self.canvas, 60, self.draw_histogram)
        self.canvas.bind("<Configure>", redraw, add="+")

        self.refresh()

    def _build_warnings(self, parent):
        box = card(parent, f"Что проверить в файле ({len(self.app.warnings)})")
        box.pack(side="bottom", fill="x", pady=(16, 0))
        p = self.app.palette
        area = ttk.Frame(box, style="Surface.TFrame")
        area.pack(fill="x")
        text = tk.Text(area, height=6, width=20, wrap="word", bd=0, highlightthickness=0, font=font(9),
                       bg=p["surface"], fg=p["text2"], cursor="arrow", spacing3=6)
        scroll = ttk.Scrollbar(area, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="x", expand=True)
        text.insert("1.0", "\n".join(f"• {w}" for w in self.app.warnings))
        text.configure(state="disabled")

    def refresh(self):
        try:
            rows = insights.students(self.app.low_score, self.app.high_absences)
            stats = repository.get_stats()
            lessons = repository.get_lesson_overview()
            self.bins = repository.get_score_distribution()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            return

        cutoff = iso_to_display(lessons["cutoff"]) or "—"
        self.subtitle.config(text=f"Занятия учтены до {cutoff} — это дата последней оценки")
        values = (str(stats.total), fmt_average(stats.avg_score), fmt_average(stats.avg_missed),
                  f"{lessons['total'] - lessons['remaining']} из {lessons['total']}")
        for (value, _), text in zip(self.stats, values):
            value.config(text=text)

        # Сначала те, у кого причин больше, затем с меньшим баллом
        attention = sorted(
            (s for s in rows if insights.needs_attention(s)),
            key=lambda s: (-(s["low"] + s["many"] + bool(s["control_periods"])),
                           s["score"] if s["score"] is not None else float("inf")))
        self.attention_title.config(text=f"Требуют внимания: {len(attention)} из {len(rows)}")
        self.table.set_rows([(s["id"], (s["fio"], fmt_number(s["score"]),
                                        fmt_number(s["missed"]), insights.notes(s, rank=False)),
                              insights.row_tag(s, i)) for i, s in enumerate(attention)])
        self.draw_histogram()

    def draw_histogram(self):
        c, p = self.canvas, self.app.palette
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60:
            return
        if not self.bins:
            c.create_text(w / 2, h / 2, text="Нет итоговых баллов", fill=p["muted"], font=font(10))
            return
        top, bottom = 20, 36
        slot = w / len(self.bins)
        peak = max(count for _, count in self.bins) or 1
        for i, (start, count) in enumerate(self.bins):
            x0, x1 = i * slot + 2, (i + 1) * slot - 2
            y = h - bottom - (h - top - bottom) * count / peak
            if count:
                # красный — только если весь интервал ниже порога
                color = p["danger"] if start + 1 <= self.app.low_score else p["accent"]
                c.create_rectangle(x0, y, x1, h - bottom, fill=color, outline="")
                c.create_text((x0 + x1) / 2, y - 4, anchor="s", text=str(count),
                              fill=p["text"], font=font(9, True))
            c.create_text((x0 + x1) / 2, h - bottom + 6, anchor="n", text=str(start),
                          fill=p["muted"], font=font(8))
        c.create_line(0, h - bottom, w, h - bottom, fill=p["border"])
        c.create_text(w / 2, h - 2, anchor="s", fill=p["muted"], font=font(8),
                      text="по оси — балл, над столбцом — число студентов")

    def open_student(self, iid):
        self.app.show_window("student_page", student_id=int(iid),
                             ids=[int(i) for i in self.table.ids()], back="overview_page")
