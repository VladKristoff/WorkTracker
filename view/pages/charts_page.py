"""«Диаграммы»: баллы и пропуски горизонтальными столбцами, экспорт обеих в PDF."""
import math
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog

from database import repository
from styles import font
from utils.pdf_export import build_visualization_pdf
from utils.settings import load_settings, save_setting
from view.insights import WORST_COUNT, short_name, worst_ids
from view.widgets import (Debouncer, Segmented, ThresholdFields, bind_wheel, card,
                          page_header, stat_row)

SORT_VALUES = ("По убыванию", "По возрастанию", "Как в списке")
# Цвета для PDF: он всегда на белой бумаге, независимо от темы
PDF_COLORS = {"scores": "#991B1B", "missed": "#D97706"}


def fmt_number(value):
    return f"{value:.2f}".rstrip("0").rstrip(".") if value is not None else "—"


class VisualizationPage:
    # Реестр диаграмм: ключ -> название кнопки
    CHARTS = {"scores": "Баллы", "missed": "Пропуски"}
    ROW_H, TOP, BOTTOM, LEFT, RIGHT = 24, 28, 52, 184, 56

    def __init__(self, content, app):
        self.app = app
        self.state = app.state.setdefault("charts", {"chart": "scores", "sort": SORT_VALUES[0]})
        self.rows, self.worst, self.row_ids = [], set(), []

        actions, _ = page_header(content, "Диаграммы",
                                 "Щелчок по строке открывает карточку студента")
        ttk.Button(actions, text="Экспорт в PDF", style="Primary.TButton", cursor="hand2",
                   command=self.export_pdf).pack()

        toolbar = ttk.Frame(content)
        toolbar.pack(fill="x", pady=(0, 12))
        Segmented(toolbar, list(self.CHARTS.items()), self.state["chart"],
                  self.select_chart).pack(side="left")
        ThresholdFields(toolbar, app, self.draw).pack(side="right")
        self.sort_var = tk.StringVar(value=self.state["sort"])
        order = ttk.Combobox(toolbar, textvariable=self.sort_var, state="readonly",
                             values=SORT_VALUES, width=16)
        order.pack(side="left", padx=(12, 0))
        order.bind("<<ComboboxSelected>>", lambda _e: self.draw())

        self.stats = stat_row(content, ("", "", ""))

        box = card(content, padding=1)
        box.pack(fill="both", expand=True)
        self.legend = tk.Canvas(box, height=32, bg=app.palette["surface"], bd=0,
                                highlightthickness=0)
        self.legend.pack(fill="x", padx=8, pady=(4, 0))
        scrollbar = ttk.Scrollbar(box, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.canvas = tk.Canvas(box, bg=app.palette["surface"], bd=0, highlightthickness=0,
                                yscrollcommand=scrollbar.set, yscrollincrement=self.ROW_H)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.canvas.yview)
        bind_wheel(self.canvas, self.canvas)
        self.canvas.bind("<Configure>", Debouncer(self.canvas, 60, self.draw), add="+")
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda _e: self.hover(None))
        self.canvas.bind("<Button-1>", self.on_click)

        self.load_data()
        self.draw()

    # ------------------------------------------------------------------
    # Данные
    # ------------------------------------------------------------------

    def load_data(self):
        try:
            rows = repository.get_students()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            return
        self.rows = [{"id": r["id"], "fio": r["fio"], "score": r["itog_ball"],
                      "missed": r["missed"]} for r in rows]
        # 5 худших по итоговому баллу выделяются на обеих диаграммах независимо от порогов
        self.worst = worst_ids(rows)

    def select_chart(self, key):
        self.state["chart"] = key
        self.draw()

    def _values(self, key):
        """[(строка, значение)] для диаграммы; студенты без значения не попадают."""
        field = "score" if key == "scores" else "missed"
        return [(r, r[field]) for r in self.rows if r[field] is not None]

    def _sorted_pairs(self, key):
        pairs = self._values(key)
        order = self.sort_var.get()
        if order == "По убыванию":
            pairs.sort(key=lambda d: -d[1])
        elif order == "По возрастанию":
            pairs.sort(key=lambda d: d[1])
        return pairs

    def _chart_spec(self, key):
        """Параметры диаграммы: общие для экрана и PDF."""
        if key == "scores":
            low = self.app.low_score
            return dict(
                title="Баллы студентов", subtitle="Итоговый балл каждого студента",
                is_flagged=lambda v: v < low, flag_text=f"ниже {fmt_number(low)}",
                flag_color=self.app.palette["danger"], avg_caption="средний балл",
                captions=("Лучший результат", "Средний балл", "Ниже порога"),
                empty_text="Нет итоговых баллов для диаграммы",
                missing_text="Студентов без итогового балла (не показаны)")
        high = self.app.high_absences
        return dict(
            title="Пропуски студентов",
            subtitle="Количество пропущенных занятий каждого студента",
            is_flagged=lambda v: v > high, flag_text=f"больше {fmt_number(high)}",
            flag_color=self.app.palette["warn"], avg_caption="в среднем",
            captions=("Больше всех пропусков", "Среднее пропусков", "Выше порога"),
            empty_text="Нет данных о пропусках для диаграммы",
            missing_text="Студентов без данных о пропусках (не показаны)")

    def _summary(self, key, spec):
        """[(значение, подпись)] — три числа над диаграммой и в PDF."""
        data = self._values(key)
        if not data:
            return []
        best_row, best = max(data, key=lambda d: d[1])
        average = sum(v for _, v in data) / len(data)
        flagged = sum(1 for _, v in data if spec["is_flagged"](v))
        return [(fmt_number(best), f"{spec['captions'][0]}\n{short_name(best_row['fio'])}"),
                (fmt_number(average), spec["captions"][1]),
                (f"{flagged} из {len(data)}", spec["captions"][2])]

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def draw(self):
        key = self.state["chart"]
        self.state["sort"] = self.sort_var.get()
        spec = self._chart_spec(key)
        summary = self._summary(key, spec)
        for i, (value, caption) in enumerate(self.stats):
            value.config(text=summary[i][0] if summary else "—")
            caption.config(text=summary[i][1].replace("\n", ": ") if summary
                           else spec["captions"][i])
        self._draw_legend(spec)
        self._draw_bars(key, spec)

    def _draw_legend(self, spec):
        c, p = self.legend, self.app.palette
        c.delete("all")
        measure = tkfont.Font(font=font(9)).measure
        x = 8
        for color, text in ((spec["flag_color"], spec["flag_text"]), (p["accent"], "остальные"),
                            (None, f"▼ {WORST_COUNT} худших по баллам"),
                            ("line", "пунктир — среднее")):
            if color == "line":
                c.create_line(x, 16, x + 16, 16, fill=p["text2"], dash=(4, 3), width=2)
                x += 24
            elif color:
                c.create_rectangle(x, 10, x + 12, 22, fill=color, outline="")
                x += 20
            c.create_text(x, 16, anchor="w", text=text, fill=p["text2"], font=font(9))
            x += measure(text) + 24

    def _draw_bars(self, key, spec):
        c, p = self.canvas, self.app.palette
        c.delete("all")
        self.row_ids = []
        w, view_h = c.winfo_width(), c.winfo_height()
        if w < 320 or view_h < 50:
            return
        pairs = self._sorted_pairs(key)
        if not pairs:
            c.create_text(w / 2, view_h / 2, text=spec["empty_text"], fill=p["muted"],
                          font=font(11))
            return

        n = len(pairs)
        base = self.TOP + n * self.ROW_H
        c.configure(scrollregion=(0, 0, w, max(base + self.BOTTOM, view_h)))
        c.yview_moveto(0)

        # Шкала: шаг подбираем так, чтобы было не больше ~10 делений
        peak = max(v for _, v in pairs)
        step = max(1, math.ceil(peak / 10))
        y_max = max(step, math.ceil(peak / step) * step)
        x0 = self.LEFT
        scale = (w - self.RIGHT - x0) / y_max

        # подложка строки под курсором — самый нижний слой
        self.hover_item = c.create_rectangle(0, 0, 0, 0, fill=p["surface_alt"], outline="")
        for i in range(y_max // step + 1):
            x = x0 + i * step * scale
            c.create_line(x, self.TOP - 4, x, base, fill=p["border"])
            c.create_text(x, self.TOP - 8, anchor="s", text=f"{i * step:g}", fill=p["muted"],
                          font=font(8))

        for i, (row, value) in enumerate(pairs):
            self.row_ids.append(row["id"])
            cy = self.TOP + self.ROW_H * (i + 0.5)
            worst = row["id"] in self.worst
            name = short_name(row["fio"])
            c.create_text(x0 - 12, cy, anchor="e", text=f"▼ {name}" if worst else name,
                          fill=p["text"], font=font(9, worst))
            end = x0 + value * scale
            c.create_rectangle(x0, cy - 7, max(x0 + 2, end), cy + 7, outline="",
                               fill=spec["flag_color"] if spec["is_flagged"](value)
                               else p["accent"])
            c.create_text(max(x0 + 2, end) + 8, cy, anchor="w", text=fmt_number(value),
                          fill=p["text"], font=font(9, True))

        average = sum(v for _, v in pairs) / n
        ax = x0 + average * scale
        c.create_line(ax, self.TOP - 4, ax, base, fill=p["text2"], dash=(4, 3), width=2)
        c.create_text(ax, base + 8, anchor="n", fill=p["muted"], font=font(9),
                      text=f"{spec['avg_caption']} {fmt_number(average)}")
        missing = len(self.rows) - n
        if missing:
            c.create_text(16, base + 28, anchor="nw", fill=p["muted"], font=font(9),
                          text=f"{spec['missing_text']}: {missing}")

    def _row_at(self, event):
        index = int((self.canvas.canvasy(event.y) - self.TOP) // self.ROW_H)
        return index if 0 <= index < len(self.row_ids) else None

    def hover(self, index):
        if not self.row_ids:
            return
        if index is None:
            self.canvas.coords(self.hover_item, 0, 0, 0, 0)
        else:
            top = self.TOP + index * self.ROW_H
            self.canvas.coords(self.hover_item, 0, top, self.canvas.winfo_width(),
                               top + self.ROW_H)
        self.canvas.configure(cursor="" if index is None else "hand2")

    def on_motion(self, event):
        self.hover(self._row_at(event))

    def on_click(self, event):
        index = self._row_at(event)
        if index is not None:
            self.app.show_window("student_page", student_id=self.row_ids[index],
                                 ids=list(self.row_ids), back="visualization_page")

    # ------------------------------------------------------------------
    # Экспорт в PDF
    # ------------------------------------------------------------------

    def _pdf_charts(self):
        """Данные обеих диаграмм для PDF — в том же порядке и с теми же порогами, что на экране."""
        charts = []
        for key in self.CHARTS:
            spec = self._chart_spec(key)
            pairs = self._sorted_pairs(key)
            missing = len(self.rows) - len(pairs)
            charts.append({
                "title": spec["title"], "subtitle": spec["subtitle"],
                "summary": self._summary(key, spec),
                "rows": [{"name": short_name(r["fio"]), "value": v,
                          "flagged": spec["is_flagged"](v), "worst": r["id"] in self.worst}
                         for r, v in pairs],
                "flag_text": spec["flag_text"], "flag_color": PDF_COLORS[key],
                "worst_text": f"{WORST_COUNT} худших по баллам",
                "avg_caption": spec["avg_caption"],
                "missing_note": f"{spec['missing_text']}: {missing}" if missing else ""})
        return charts

    def export_pdf(self):
        last_dir = load_settings().get("last_pdf_dir")
        path = filedialog.asksaveasfilename(
            title="Сохранить диаграммы", defaultextension=".pdf",
            filetypes=[("PDF файлы", "*.pdf")], initialfile="Визуализация_успеваемости.pdf",
            initialdir=last_dir if last_dir and os.path.isdir(last_dir) else None)
        if not path:
            return
        try:
            build_visualization_pdf(
                path, self._pdf_charts(),
                subtitle=f"Сортировка: {self.sort_var.get().lower()} · "
                         f"пороги: балл ниже {fmt_number(self.app.low_score)}, "
                         f"пропусков больше {fmt_number(self.app.high_absences)}")
        except PermissionError:
            messagebox.showerror("Не удалось сохранить",
                                 "Файл занят другой программой (возможно, открыт в просмотрщике "
                                 "PDF). Закройте его или выберите другое имя.")
            return
        except Exception as e:
            messagebox.showerror("Не удалось создать PDF", str(e))
            return
        save_setting("last_pdf_dir", os.path.dirname(path))
        if messagebox.askyesno("PDF создан", f"Файл сохранён:\n{path}\n\nОткрыть его сейчас?"):
            try:
                os.startfile(path)  # type: ignore[attr-defined]  # только Windows
            except (AttributeError, OSError):
                pass
