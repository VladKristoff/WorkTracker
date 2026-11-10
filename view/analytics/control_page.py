import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Literal

from config import FONT_FAMILY
from database import repository
from styles import configure_tree_tags
from utils.dates import iso_to_display
from view.tabs import build_tabs

NO_CONTROL = "не писал контрольную"
TWO = "оценка 2"

FILTERS = {
    "Все": lambda r: True,
    "Не писали контрольную": lambda r: NO_CONTROL in r["reasons"],
    "Оценка 2": lambda r: TWO in r["reasons"],
    "И не писали, и оценка 2": lambda r: NO_CONTROL in r["reasons"] and TWO in r["reasons"],
}
ALL_PERIODS = "Все периоды"


def fmt_number(value, empty="—"):
    return empty if value is None else f"{value:g}"


class ControlPage:
    """Вкладка «Контрольные»: кто не писал контрольную и у кого оценка 2 за период."""

    SEARCH_DELAY_MS = 250
    HEADINGS = {"fio": "ФИО", "period": "Период", "date": "Дата контрольной",
                "control": "Балл за контрольную", "total": "Сумма за период",
                "grade": "Оценка", "reason": "Причина"}
    # столбец -> ключ в строке отчёта, по которому сортируем
    SORT_KEYS = {"fio": "fio", "period": "period", "date": "date",
                 "control": "control", "total": "total", "grade": "grade"}

    def __init__(self, main_frame, app, filepath):
        self.main_frame = main_frame
        self.app = app
        self.filepath = filepath

        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="Все")
        self.period_var = tk.StringVar(value=ALL_PERIODS)
        self.sort_column = None
        self.sort_desc = False
        self._rows = []
        self._search_job = None
        self._legend_swatches = []

        self.create_widgets()
        self.load_data()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self.main_frame, style="Header.TFrame")
        header.pack(fill="x", side="top")
        ttk.Button(header, text="←  Назад", cursor="hand2", style="HeaderGhost.TButton",
                   command=self.back_to_main_menu).pack(side="left", padx=(14, 0), pady=10)
        build_tabs(header, self.app, "control_page", self.filepath).pack(side="left", padx=16)
        self.theme_btn = ttk.Button(header, text=self.app.theme_icon, width=3, cursor="hand2",
                                    style="HeaderGhost.TButton", command=self.app.toggle_theme)
        self.theme_btn.pack(side="right", padx=14)
        ttk.Frame(self.main_frame, style="Line.TFrame", height=1).pack(fill="x", side="top")

        ttk.Label(self.main_frame, text=f"Файл: {os.path.basename(self.filepath)}",
                  style="Hint.TLabel").pack(side="bottom", pady=8)

        content = ttk.Frame(self.main_frame)
        content.pack(fill="both", expand=True, padx=20, pady=(18, 4))
        self._build_left_panel(content)
        self._build_table(content)

    @staticmethod
    def _card(parent, title, pady=(0, 14)):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=pady)
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        return card

    def _build_left_panel(self, parent):
        panel = ttk.Frame(parent, width=290)
        panel.pack(side="left", fill="y", padx=(0, 18), anchor="n")
        panel.pack_propagate(False)

        search = self._card(panel, "Поиск")
        ttk.Entry(search, textvariable=self.search_var).pack(fill="x")
        self.search_var.trace_add("write", self.on_search_changed)

        flt = self._card(panel, "Фильтр")
        ttk.Combobox(flt, textvariable=self.filter_var, values=list(FILTERS),
                     state="readonly").pack(fill="x")
        self.period_box = ttk.Combobox(flt, textvariable=self.period_var, state="readonly")
        self.period_box.pack(fill="x", pady=(8, 0))
        self.filter_var.trace_add("write", lambda *_: self.refresh_table())
        self.period_var.trace_add("write", lambda *_: self.refresh_table())

        stats = self._card(panel, "Сводка")
        grid = ttk.Frame(stats, style="Surface.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1, uniform="tiles")
        self.shown_label = self._tile(grid, 0, 0, "Показано строк")
        self.students_label = self._tile(grid, 0, 1, "Студентов")
        self.no_ctrl_label = self._tile(grid, 1, 0, "Не писали")
        self.two_label = self._tile(grid, 1, 1, "Оценка 2")

        legend = self._card(panel, "Подсветка")
        for bg_key, fg_key, text in (("low_bg", "low_fg", "оценка 2"),
                                     ("warn_bg", "warn_fg", "не писал, но оценка выше 2")):
            row = ttk.Frame(legend, style="Surface.TFrame")
            row.pack(fill="x", pady=3)
            swatch = tk.Frame(row, width=16, height=16, highlightthickness=1)
            swatch.pack(side="left", padx=(0, 10))
            self._legend_swatches.append((swatch, bg_key, fg_key))
            ttk.Label(row, text=text, style="CardHint.TLabel").pack(side="left")
        self.note_label = ttk.Label(legend, text="", style="CardHint.TLabel",
                                    wraplength=240, justify="left")
        self.note_label.pack(anchor="w", pady=(6, 0))
        self._recolor_legend()

    @staticmethod
    def _tile(parent, row, col, caption):
        tile = ttk.Frame(parent, style="Surface.TFrame")
        tile.grid(row=row, column=col, sticky="w", pady=6)
        value = ttk.Label(tile, text="—", style="Value.TLabel")
        value.pack(anchor="w")
        ttk.Label(tile, text=caption, style="CardHint.TLabel").pack(anchor="w")
        return value

    def _build_table(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=1)
        card.pack(side="right", fill="both", expand=True)

        columns = tuple(self.HEADINGS)
        self.table = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)

        layout: dict[str, tuple[int, Literal["w", "center"], bool]] = {"fio": (130, "w", True), "period": (80, "center", False),
                  "date": (150, "center", False), "control": (150, "center", False),
                  "total": (150, "center", False), "grade": (80, "center", False),
                  "reason": (220, "w", False)}
        for col in columns:
            width, anchor, stretch = layout[col]
            self.table.heading(col, text=self.HEADINGS[col], anchor=anchor)
            if col in self.SORT_KEYS:
                self.table.heading(col, command=lambda c=col: self.on_heading_click(c))
            self.table.column(col, width=width, anchor=anchor, stretch=stretch)
        self._configure_tags()

        scrollbar.pack(side="right", fill="y")
        self.table.pack(side="left", fill="both", expand=True)
        self.empty_label = ttk.Label(card, text="Нет студентов с такими условиями",
                                     style="CardHint.TLabel", font=(FONT_FAMILY, 12))

    # ------------------------------------------------------------------
    # Тема
    # ------------------------------------------------------------------

    def _recolor_legend(self):
        p = self.app.palette
        for swatch, bg_key, fg_key in self._legend_swatches:
            swatch.configure(bg=p[bg_key], highlightbackground=p[fg_key])

    def _configure_tags(self):
        configure_tree_tags(self.table, self.app.palette)

    def on_theme_changed(self):
        self._configure_tags()
        self._recolor_legend()
        self.theme_btn.config(text=self.app.theme_icon)

    # ------------------------------------------------------------------
    # Данные и таблица
    # ------------------------------------------------------------------

    def load_data(self):
        try:
            self._rows = repository.get_control_report()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            self._rows = []
        periods = sorted({r["period"] for r in self._rows})
        self.period_box.configure(values=[ALL_PERIODS] + [f"Период {p}" for p in periods])
        self.note_label.config(
            text="Период учитывается, только если контрольную уже писал кто-то из группы. "
                 "Оценка считается по сумме баллов за период." if self._rows else
                 "Нет проведённых контрольных или нет подходящих студентов.")
        self.refresh_table()

    def on_search_changed(self, *_):
        if self._search_job:
            self.main_frame.after_cancel(self._search_job)
        self._search_job = self.main_frame.after(self.SEARCH_DELAY_MS, self.refresh_table)

    def on_heading_click(self, column):
        if self.sort_column == column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column, self.sort_desc = column, False
        self.refresh_table()

    def _visible_rows(self):
        needle = self.search_var.get().strip().casefold()
        flt = FILTERS.get(self.filter_var.get(), FILTERS["Все"])
        period = self.period_var.get()
        rows = [r for r in self._rows
                if flt(r)
                and (period == ALL_PERIODS or period == f"Период {r['period']}")
                and (not needle or needle in r["fio"].casefold())]
        if self.sort_column:
            key = self.SORT_KEYS[self.sort_column]
            # пустые значения (например, нет балла за контрольную) всегда в конце
            rows.sort(key=lambda r: (r[key] is None, r[key] if r[key] is not None else 0),
                      reverse=False)
            if self.sort_desc:
                filled = [r for r in rows if r[key] is not None][::-1]
                rows = filled + [r for r in rows if r[key] is None]
        return rows

    def refresh_table(self, *_):
        self._search_job = None
        rows = self._visible_rows()
        self.table.delete(*self.table.get_children())
        for index, r in enumerate(rows):
            if r["grade"] == 2:
                tag = "low_score"
            else:
                tag = "many_absences"  # не писал контрольную, но оценка выше двойки
            self.table.insert("", "end", tags=(tag,), values=(
                r["fio"], r["period"], iso_to_display(r["date"]) or "—",
                fmt_number(r["control"]), fmt_number(r["total"]), r["grade"],
                ", ".join(r["reasons"])))

        self.shown_label.config(text=str(len(rows)))
        self.students_label.config(text=str(len({r["student_id"] for r in rows})))
        self.no_ctrl_label.config(text=str(sum(NO_CONTROL in r["reasons"] for r in rows)))
        self.two_label.config(text=str(sum(TWO in r["reasons"] for r in rows)))
        if rows:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        for col, key in self.SORT_KEYS.items():
            arrow = (" ▼" if self.sort_desc else " ▲") if self.sort_column == col else ""
            self.table.heading(col, text=self.HEADINGS[col] + arrow)

    def back_to_main_menu(self):
        if messagebox.askyesno("Внимание!", "Вы уверены, что хотите выйти в главное меню?"):
            self.app.show_window("main_menu")