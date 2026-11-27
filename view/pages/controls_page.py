"""«Контрольные»: кто не писал контрольную и у кого оценка 2 за период."""
import tkinter as tk
from tkinter import ttk, messagebox

from database import repository
from utils.dates import iso_to_display
from view.insights import fmt_number
from view.widgets import DataTable, Debouncer, SearchBox, Segmented, page_header

NO_CONTROL = "не писал контрольную"
TWO = "оценка 2"

FILTERS = {
    "all": ("Все", lambda r: True),
    "absent": ("Не писали контрольную", lambda r: NO_CONTROL in r["reasons"]),
    "two": ("Оценка 2", lambda r: TWO in r["reasons"]),
    "both": ("И то и другое", lambda r: NO_CONTROL in r["reasons"] and TWO in r["reasons"]),
}
ALL_PERIODS = "Все периоды"


class ControlPage:
    COLUMNS = [("fio", "ФИО", 170, "w", True), ("period", "Период", 64, "center", False),
               ("date", "Дата контрольной", 128, "center", False),
               ("control", "За контрольную", 112, "center", False),
               ("total", "Сумма за период", 116, "center", False),
               ("grade", "Оценка", 64, "center", False),
               ("reason", "Причина", 190, "w", True)]
    SORTABLE = ("fio", "period", "date", "control", "total", "grade")

    def __init__(self, content, app):
        self.app = app
        self.state = app.state.setdefault(
            "controls", {"search": "", "filter": "all", "period": ALL_PERIODS,
                         "sort": None, "desc": False})
        try:
            self.rows = repository.get_control_report()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            self.rows = []

        _, self.subtitle = page_header(content, "Контрольные")

        toolbar = ttk.Frame(content)
        toolbar.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar(value=self.state["search"])
        self.search = SearchBox(toolbar, self.search_var)
        self.search.pack(side="left")
        periods = [ALL_PERIODS] + [f"Период {p}" for p in sorted({r["period"] for r in self.rows})]
        if self.state["period"] not in periods:
            self.state["period"] = ALL_PERIODS
        self.period_var = tk.StringVar(value=self.state["period"])
        box = ttk.Combobox(toolbar, textvariable=self.period_var, values=periods,
                           state="readonly", width=16)
        box.pack(side="left", padx=(8, 0))
        box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        chips = Segmented(content, [(k, v[0]) for k, v in FILTERS.items()],
                          self.state["filter"], self.set_filter)
        chips.pack(anchor="w", pady=(0, 12))
        for key, (title, match) in FILTERS.items():
            chips.set_text(key, f"{title}  {sum(map(match, self.rows))}")

        ttk.Label(content, style="Muted.TLabel", wraplength=800, justify="left",
                  text="Красная строка — оценка 2 за период · жёлтая — не писал, но оценка выше 2."
                       "\nПериод учитывается, только если контрольную уже писал кто-то из группы. "
                       "Оценка считается по сумме баллов за период."
                  ).pack(side="bottom", anchor="w", pady=(8, 0))

        self.table = DataTable(
            content, app.palette, self.COLUMNS, sortable=self.SORTABLE, on_sort=self.sort_by,
            on_open=self.open_student,
            empty_text="Нет студентов с такими условиями" if self.rows
            else "Нет проведённых контрольных или нет отстающих по ним")
        self.table.pack(fill="both", expand=True)
        self.search_var.trace_add("write", Debouncer(self.table, 250, self.refresh))
        self.refresh()

    def focus_search(self):
        self.search.focus()

    def go_back(self):
        self.search_var.set("")

    def set_filter(self, key):
        self.state["filter"] = key
        self.refresh()

    def sort_by(self, column):
        if self.state["sort"] == column:
            self.state["desc"] = not self.state["desc"]
        else:
            self.state["sort"], self.state["desc"] = column, False
        self.refresh()

    def visible_rows(self):
        needle = self.state["search"].strip().casefold()
        match = FILTERS[self.state["filter"]][1]
        period = self.state["period"]
        rows = [r for r in self.rows
                if match(r)
                and (period == ALL_PERIODS or period == f"Период {r['period']}")
                and (not needle or needle in r["fio"].casefold())]
        key = self.state["sort"]
        if key:
            # пустые значения (например, нет балла за контрольную) всегда в конце
            filled = sorted((r for r in rows if r[key] is not None), key=lambda r: r[key],
                            reverse=self.state["desc"])
            rows = filled + [r for r in rows if r[key] is None]
        return rows

    def refresh(self):
        self.state["search"] = self.search_var.get()
        self.state["period"] = self.period_var.get()
        rows = self.visible_rows()
        self.shown = rows
        self.table.set_rows([
            (index, (r["fio"], r["period"], iso_to_display(r["date"]) or "—",
                     fmt_number(r["control"]), fmt_number(r["total"]), r["grade"],
                     ", ".join(r["reasons"])),
             "danger" if r["grade"] == 2 else "warn")
            for index, r in enumerate(rows)])
        # номера строк при фильтрации меняют смысл — старое выделение не переносим
        self.table.tree.selection_set(())
        self.table.set_arrow(self.state["sort"], self.state["desc"])
        self.subtitle.config(
            text=f"Показано записей: {len(rows)} · студентов: "
                 f"{len({r['student_id'] for r in rows})} · двойной щелчок открывает карточку")

    def open_student(self, iid):
        self.app.show_window("student_page", student_id=self.shown[int(iid)]["student_id"],
                             ids=[r["student_id"] for r in self.shown], back="control_page")
