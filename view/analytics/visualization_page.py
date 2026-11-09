import math
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from config import FONT_FAMILY, LOW_SCORE_THRESHOLD, HIGH_ABSENCES_THRESHOLD
from database import repository
from view.tabs import build_tabs

WORST_COUNT = 5  # сколько худших по баллам выделяем всегда


def fmt_number(value):
    return f"{value:.2f}".rstrip("0").rstrip(".") if value is not None else "—"


def short_name(fio):
    """Иванов Иван Иванович -> Иванов И.И."""
    parts = fio.split()
    if len(parts) <= 1:
        return fio
    return f"{parts[0]} " + "".join(f"{w[0]}." for w in parts[1:3])


class VisualizationPage:
    SORT_VALUES = ("По убыванию", "По возрастанию", "Как в списке")
    # Яркий оранжевый для столбцов с большим числом пропусков: тёмно-коричневый warn_fg
    # на жёлтой плашке «худших» сливался, а красный занят баллами
    ABSENCE_COLORS = {"light": "#F97316", "dark": "#FB923C"}

    def __init__(self, main_frame, app, filepath):
        self.main_frame = main_frame
        self.app = app
        self.filepath = filepath

        # Реестр диаграмм: ключ -> название кнопки
        self.charts = {
            "scores": "Баллы студентов",
            "missed": "Пропуски студентов",
        }
        self.current_chart = "scores"
        self._chart_buttons = {}

        self.sort_var = tk.StringVar(value=self.SORT_VALUES[0])

        # Пороги подсветки: редактируются пользователем, начальные значения — из config
        self.low_score = float(LOW_SCORE_THRESHOLD)
        self.high_absences = float(HIGH_ABSENCES_THRESHOLD)
        self.low_score_var = tk.StringVar(value=fmt_number(self.low_score))
        self.high_absences_var = tk.StringVar(value=fmt_number(self.high_absences))
        self._threshold_job = None

        # Данные: [{"id", "fio", "score", "missed"}] — все студенты
        self._rows = []
        self._worst_ids = set()  # id пяти худших по баллам

        self.create_widgets()
        self.load_data()
        self.draw()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self.main_frame, style="Header.TFrame")
        header.pack(fill="x", side="top")
        ttk.Button(header, text="←  Назад", cursor="hand2", style="HeaderGhost.TButton",
                   command=self.back_to_main_menu).pack(side="left", padx=(14, 0), pady=10)
        build_tabs(header, self.app, "visualization_page", self.filepath).pack(side="left", padx=16)
        self.theme_btn = ttk.Button(header, text=self.app.theme_icon, width=3, cursor="hand2",
                                    style="HeaderGhost.TButton", command=self.app.toggle_theme)
        self.theme_btn.pack(side="right", padx=14)
        ttk.Frame(self.main_frame, style="Line.TFrame", height=1).pack(fill="x", side="top")

        ttk.Label(self.main_frame, text=f"Файл: {os.path.basename(self.filepath)}",
                  style="Hint.TLabel").pack(side="bottom", pady=8)

        content = ttk.Frame(self.main_frame)
        content.pack(fill="both", expand=True, padx=20, pady=(18, 4))

        self._build_left_panel(content)

        chart_card = ttk.Frame(content, style="Card.TFrame", padding=1)
        chart_card.pack(side="right", fill="both", expand=True)
        self.canvas = tk.Canvas(chart_card, bg=self.app.palette["surface"], bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw())
        # Прокрутка колесом мыши (если студентов много и диаграмма не помещается)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<Button-4>", lambda _e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda _e: self.canvas.yview_scroll(1, "units"))

    def _build_left_panel(self, parent):
        panel = ttk.Frame(parent, width=290)
        panel.pack(side="left", fill="y", padx=(0, 18), anchor="n")
        panel.pack_propagate(False)

        # --- Выбор диаграммы ---
        card = ttk.Frame(panel, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=(0, 14))
        ttk.Label(card, text="Диаграммы", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        for key, title in self.charts.items():
            btn = ttk.Button(card, text=title, cursor="hand2",
                             command=lambda k=key: self.select_chart(k))
            btn.pack(fill="x", pady=2)
            self._chart_buttons[key] = btn
        self._update_chart_buttons()

        # --- Сортировка ---
        sort_card = ttk.Frame(panel, style="Card.TFrame", padding=16)
        sort_card.pack(fill="x", pady=(0, 14))
        ttk.Label(sort_card, text="Сортировка", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        combo = ttk.Combobox(sort_card, textvariable=self.sort_var, state="readonly",
                             values=self.SORT_VALUES)
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", lambda _e: self.draw())

        # --- Пороги подсветки ---
        thr_card = ttk.Frame(panel, style="Card.TFrame", padding=16)
        thr_card.pack(fill="x", pady=(0, 14))
        ttk.Label(thr_card, text="Подсветка", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        for text, var in (("балл ниже", self.low_score_var),
                          ("пропусков больше", self.high_absences_var)):
            row = ttk.Frame(thr_card, style="Surface.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=text, style="CardHint.TLabel").pack(side="left")
            entry = ttk.Entry(row, textvariable=var, width=6, justify="center")
            entry.pack(side="right")
            var.trace_add("write", self.on_threshold_changed)
        ttk.Label(thr_card, text="Пороги можно менять (например, 7.5)",
                  style="CardHint.TLabel", wraplength=240, justify="left").pack(anchor="w", pady=(6, 0))

        # --- Сводка (зависит от выбранной диаграммы) ---
        stats = ttk.Frame(panel, style="Card.TFrame", padding=16)
        stats.pack(fill="x", pady=(0, 14))
        self.summary_title = ttk.Label(stats, text="Сводка", style="CardTitle.TLabel")
        self.summary_title.pack(anchor="w", pady=(0, 10))
        self.best_label, self.best_caption = self._stat(stats, "")
        self.avg_label, self.avg_caption = self._stat(stats, "")
        self.low_label, self.low_caption = self._stat(stats, "")

    @staticmethod
    def _stat(parent, caption):
        value = ttk.Label(parent, text="—", style="Value.TLabel", font=(FONT_FAMILY, 16, "bold"))
        value.pack(anchor="w")
        cap = ttk.Label(parent, text=caption, style="CardHint.TLabel")
        cap.pack(anchor="w", pady=(0, 6))
        return value, cap

    def _update_chart_buttons(self):
        for key, btn in self._chart_buttons.items():
            btn.config(style="MainButton.TButton" if key == self.current_chart
                       else "Secondary.TButton")

    # ------------------------------------------------------------------
    # Данные и действия
    # ------------------------------------------------------------------

    def load_data(self):
        try:
            rows = repository.get_students()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            return

        self._rows = [{"id": r["id"], "fio": r["fio"], "score": r["itog_ball"],
                       "missed": r["missed"]} for r in rows]

        # 5 худших по итоговому баллу — выделяются на обеих диаграммах всегда,
        # независимо от порогов
        scored = sorted((r for r in self._rows if r["score"] is not None),
                        key=lambda r: r["score"])
        self._worst_ids = {r["id"] for r in scored[:WORST_COUNT]}
        self._update_summary()

    def _values(self, key):
        """[(строка, значение)] для диаграммы; студенты без значения не попадают."""
        field = "score" if key == "scores" else "missed"
        return [(r, r[field]) for r in self._rows if r[field] is not None]

    def _update_summary(self):
        key = self.current_chart
        data = self._values(key)
        if key == "scores":
            self.summary_title.config(text="Сводка по баллам")
            captions = ("Лучший результат", "Средний балл", "Ниже порога")
        else:
            self.summary_title.config(text="Сводка по пропускам")
            captions = ("Больше всех пропусков", "Среднее пропусков", "Выше порога")
        self.best_caption.config(text=captions[0])
        self.avg_caption.config(text=captions[1])
        self.low_caption.config(text=captions[2])

        if not data:
            for lbl in (self.best_label, self.avg_label, self.low_label):
                lbl.config(text="—")
            return

        if key == "scores":
            best_row, best_val = max(data, key=lambda d: d[1])
            flagged = sum(1 for _, v in data if v < self.low_score)
        else:
            best_row, best_val = max(data, key=lambda d: d[1])
            flagged = sum(1 for _, v in data if v > self.high_absences)
        avg = sum(v for _, v in data) / len(data)
        self.best_label.config(text=f"{fmt_number(best_val)} · {short_name(best_row['fio'])}")
        self.avg_label.config(text=fmt_number(avg))
        self.low_label.config(text=f"{flagged} из {len(data)}")

    def select_chart(self, key):
        self.current_chart = key
        self._update_chart_buttons()
        self._update_summary()
        self.draw()

    def on_threshold_changed(self, *_):
        if self._threshold_job:
            self.main_frame.after_cancel(self._threshold_job)
        self._threshold_job = self.main_frame.after(400, self.apply_thresholds)

    def apply_thresholds(self):
        """Применяет введённые пороги; некорректный ввод игнорируется."""
        self._threshold_job = None
        changed = False
        for var, attr in ((self.low_score_var, "low_score"),
                          (self.high_absences_var, "high_absences")):
            try:
                value = float(var.get().strip().replace(",", "."))
            except ValueError:
                continue
            if value != getattr(self, attr):
                setattr(self, attr, value)
                changed = True
        if changed:
            self._update_summary()
            self.draw()

    def back_to_main_menu(self):
        if messagebox.askyesno("Внимание!", "Вы уверены, что хотите выйти в главное меню?"):
            self.app.show_window("main_menu")

    def on_theme_changed(self):
        self.canvas.configure(bg=self.app.palette["surface"])
        self.theme_btn.config(text=self.app.theme_icon)
        self.draw()

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        c.configure(scrollregion=(0, 0, w, h))
        c.yview_moveto(0)
        if self.current_chart == "scores":
            self.draw_bars(
                c, key="scores", title="Баллы студентов",
                subtitle="Итоговый балл каждого студента",
                threshold=self.low_score, is_flagged=lambda v: v < self.low_score,
                flag_text=f"ниже {fmt_number(self.low_score)}", avg_caption="средний балл",
                empty_text="Нет итоговых баллов для диаграммы",
                missing_text="Студентов без итогового балла (не показаны)",
                flag_color=self.app.palette["low_fg"])
        else:
            self.draw_bars(
                c, key="missed", title="Пропуски студентов",
                subtitle="Количество пропущенных занятий каждого студента",
                threshold=self.high_absences, is_flagged=lambda v: v > self.high_absences,
                flag_text=f"больше {fmt_number(self.high_absences)}", avg_caption="в среднем",
                empty_text="Нет данных о пропусках для диаграммы",
                missing_text="Студентов без данных о пропусках (не показаны)",
                flag_color=self.ABSENCE_COLORS[self.app.theme])

    def _title(self, c, title, subtitle):
        p = self.app.palette
        c.create_text(28, 26, anchor="nw", text=title, fill=p["text"], font=(FONT_FAMILY, 15, "bold"))
        c.create_text(28, 54, anchor="nw", text=subtitle, fill=p["muted"], font=(FONT_FAMILY, 10))

    def draw_bars(self, c, key, title, subtitle, threshold, is_flagged, flag_text,
                  avg_caption, empty_text, missing_text, flag_color):
        """Горизонтальные столбцы: студент — значение. Общий код для обеих диаграмм."""
        p, F = self.app.palette, FONT_FAMILY
        w, view_h = c.winfo_width(), c.winfo_height()
        if w < 50 or view_h < 50:
            return

        self._title(c, title, subtitle)

        # Легенда (справа налево): 5 худших, превышение порога, остальные
        legend = [(None, f"{WORST_COUNT} худших по баллам"),
                  (flag_color, flag_text),
                  (p["accent"], "остальные")]
        legend_font = tkfont.Font(family=F, size=10)  # точная ширина текста вместо оценки на глаз
        lx = w - 28
        for color, text in legend:
            tw = legend_font.measure(text)
            c.create_text(lx, 34, anchor="e", text=text, fill=p["muted"], font=(F, 10))
            sx = lx - tw - 10  # правый край образца
            if color is None:  # образец выделения: плашка с рамкой
                c.create_rectangle(sx - 16, 26, sx, 42,
                                   fill=p["warn_bg"], outline=p["warn_fg"], width=2)
            else:
                c.create_rectangle(sx - 16, 26, sx, 42, fill=color, outline="")
            lx = sx - 16 - 22

        pairs = self._values(key)
        missing = len(self._rows) - len(pairs)
        if not pairs:
            c.create_text(w / 2, view_h / 2, text=empty_text, fill=p["muted"], font=(F, 12))
            return

        order = self.sort_var.get()
        if order == "По убыванию":
            pairs.sort(key=lambda d: -d[1])
        elif order == "По возрастанию":
            pairs.sort(key=lambda d: d[1])

        n = len(pairs)
        top, bottom, left, right = 112, 56, 200, 70
        row_h = max(24, (view_h - top - bottom) / n)
        total_h = top + n * row_h + bottom
        c.configure(scrollregion=(0, 0, w, max(total_h, view_h)))

        # Шкала: шаг подбираем так, чтобы было не больше ~10 делений
        max_val = max(v for _, v in pairs)
        step = max(1, math.ceil(max_val / 10))
        y_max = max(step, math.ceil(max_val / step) * step)
        x0, x1 = left, w - right
        scale = (x1 - x0) / y_max
        base_y = top + n * row_h

        # Плашки под строками 5 худших (рисуем первыми, чтобы лежали под сеткой и столбцами)
        for i, (row, _v) in enumerate(pairs):
            if row["id"] in self._worst_ids:
                y_a, y_b = top + row_h * i + 1, top + row_h * (i + 1) - 1
                c.create_rectangle(16, y_a, w - 16, y_b, fill=p["warn_bg"],
                                   outline=p["warn_fg"], width=1)

        # Сетка и подписи шкалы сверху
        for i in range(y_max // step + 1):
            value = i * step
            x = x0 + value * scale
            c.create_line(x, top - 6, x, base_y, fill=p["border"])
            c.create_text(x, top - 12, anchor="s", text=f"{value:g}", fill=p["muted"], font=(F, 9))

        bar_h = row_h * 0.62
        for i, (row, value) in enumerate(pairs):
            cy = top + row_h * (i + 0.5)
            worst = row["id"] in self._worst_ids
            color = flag_color if is_flagged(value) else p["accent"]
            name = short_name(row["fio"])
            if worst:
                c.create_text(left - 12, cy, anchor="e", text=f"▼ {name}",
                              fill=p["warn_fg"], font=(F, 10, "bold"))
            else:
                c.create_text(left - 12, cy, anchor="e", text=name, fill=p["text"], font=(F, 10))
            c.create_rectangle(x0, cy - bar_h / 2, max(x0 + 2, x0 + value * scale), cy + bar_h / 2,
                               fill=color, outline=p["warn_fg"] if worst else "",
                               width=2 if worst else 1)
            c.create_text(x0 + value * scale + 8, cy, anchor="w", text=fmt_number(value),
                          fill=p["warn_fg"] if worst else p["text"], font=(F, 10, "bold"))

        # Линия среднего значения
        avg = sum(v for _, v in pairs) / n
        ax = x0 + avg * scale
        c.create_line(ax, top - 6, ax, base_y, fill=p["muted"], dash=(5, 4), width=2)
        c.create_text(ax, base_y + 10, anchor="n", text=f"{avg_caption} {fmt_number(avg)}",
                      fill=p["muted"], font=(F, 10, "bold"))
        c.create_line(x0, top - 6, x0, base_y, fill=p["muted"])
        c.create_line(left, base_y, w - right, base_y, fill=p["muted"])

        if missing:
            c.create_text(28, base_y + 32, anchor="nw", fill=p["muted"], font=(F, 9),
                          text=f"{missing_text}: {missing}")