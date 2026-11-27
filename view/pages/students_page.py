"""Список группы: поиск, быстрые фильтры, сортировка по заголовкам."""
import tkinter as tk
from tkinter import ttk, messagebox

from view import insights
from view.insights import fmt_number
from view.widgets import (DataTable, Debouncer, SearchBox, Segmented, ThresholdFields,
                          page_header)

FILTERS = {
    "all": ("Все", lambda s: True),
    "low": ("Низкий балл", lambda s: s["low"]),
    "many": ("Много пропусков", lambda s: s["many"]),
    "control": ("Контрольные", lambda s: bool(s["control_periods"])),
}
# столбец таблицы -> столбец/алиас БД
SORTABLE = {"fio": "fio", "score": "itog_ball", "missed": "missed"}


class StudentsPage:
    def __init__(self, content, app):
        self.app = app
        self.state = app.state.setdefault(
            "students", {"search": "", "filter": "all", "sort": None, "dir": "ASC",
                         "selected": None})

        actions, self.subtitle = page_header(content, "Студенты")
        self.open_button = ttk.Button(actions, text="Открыть карточку", style="Primary.TButton",
                                      cursor="hand2", command=self.open_selected)
        self.open_button.pack()

        toolbar = ttk.Frame(content)
        toolbar.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar(value=self.state["search"])
        self.search = SearchBox(toolbar, self.search_var)
        self.search.pack(side="left")
        ThresholdFields(toolbar, app, self.refresh).pack(side="right")

        self.chips = Segmented(content, [(k, v[0]) for k, v in FILTERS.items()],
                               self.state["filter"], self.set_filter)
        self.chips.pack(anchor="w", pady=(0, 12))

        ttk.Label(content, style="Muted.TLabel",
                  text="Красная строка — балл ниже порога · жёлтая — пропусков больше порога · "
                       "причины подписаны в «Заметках»").pack(side="bottom", anchor="w",
                                                              pady=(8, 0))
        self.table = DataTable(
            content, app.palette,
            [("id", "№", 48, "center", False), ("fio", "ФИО", 220, "w", True),
             ("score", "Балл", 80, "center", False),
             ("missed", "Пропущено", 100, "center", False),
             ("notes", "Заметки", 300, "w", True)],
            sortable=SORTABLE, on_sort=self.sort_by, on_open=lambda _i: self.open_selected(),
            on_select=self.on_select)
        self.table.pack(fill="both", expand=True)

        # поиск запускается не на каждую букву
        self.search_var.trace_add("write", Debouncer(self.table, 250, self.refresh))
        self.refresh()
        if self.state["selected"] is not None:
            self.table.select(self.state["selected"])
        self.on_select()

    def focus_search(self):
        self.search.focus()

    def go_back(self):
        self.search_var.set("")

    def set_filter(self, key):
        self.state["filter"] = key
        self.refresh()

    def sort_by(self, column):
        """Щелчок по заголовку: по возрастанию → по убыванию → порядок файла."""
        db_column = SORTABLE[column]
        if self.state["sort"] != db_column:
            self.state["sort"], self.state["dir"] = db_column, "ASC"
        elif self.state["dir"] == "ASC":
            self.state["dir"] = "DESC"
        else:
            self.state["sort"], self.state["dir"] = None, "ASC"
        self.refresh()

    def refresh(self):
        self.state["search"] = self.search_var.get()
        try:
            everyone = insights.students(self.app.low_score, self.app.high_absences)
            found = insights.students(self.app.low_score, self.app.high_absences,
                                      self.state["search"], self.state["sort"],
                                      self.state["dir"])
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            return
        for key, (title, match) in FILTERS.items():
            self.chips.set_text(key, f"{title}  {sum(map(match, everyone))}")
        rows = [s for s in found if FILTERS[self.state["filter"]][1](s)]
        self.table.set_rows([
            (s["id"], (s["id"], s["fio"], fmt_number(s["score"]), fmt_number(s["missed"]),
                       insights.notes(s)), insights.row_tag(s, i))
            for i, s in enumerate(rows)])
        arrow = next((k for k, v in SORTABLE.items() if v == self.state["sort"]), None)
        self.table.set_arrow(arrow, self.state["dir"] == "DESC")
        self.subtitle.config(text=f"Показано {len(rows)} из {len(everyone)}")
        self.on_select()

    def on_select(self):
        self.state["selected"] = self.table.selected() or self.state["selected"]
        self.open_button.state(["!disabled"] if self.table.selected() else ["disabled"])

    def open_selected(self):
        if self.table.selected():
            self.app.show_window("student_page", student_id=int(self.table.selected()),
                                 ids=[int(i) for i in self.table.ids()], back="students_page")
