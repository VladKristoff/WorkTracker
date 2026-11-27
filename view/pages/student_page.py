"""Карточка студента (раньше — отдельное всплывающее окно)."""
import os
import tkinter as tk
from datetime import date as date_cls
from tkinter import ttk, messagebox, filedialog

from tkcalendar import DateEntry

from database import repository
from utils.dates import iso_to_display, iso_to_date, date_to_iso
from utils.pdf_export import build_student_card_pdf
from utils.settings import load_settings, save_setting
from view import insights
from view.insights import fmt_number
from view.journal import Journal, journal_lanes, work_title
from view.widgets import DataTable, Segmented, page_header, stat_row

# Режимы вкладки «Оценки»
GRADE_FILTERS = ("Выставленные оценки", "Все занятия", "Только итоги периодов")
BACK_TITLES = {"overview_page": "К обзору", "students_page": "К списку студентов",
               "control_page": "К контрольным", "visualization_page": "К диаграммам"}


class StudentPage:
    def __init__(self, content, app, student_id, ids=(), back="students_page"):
        self.app, self.student_id, self.back = app, student_id, back
        self.ids = list(dict.fromkeys(ids))  # без повторов (в контрольных студент встречается дважды)
        self.state = app.state.setdefault("student", {"tab": "grades",
                                                      "filter": GRADE_FILTERS[0]})
        self.student = repository.get_student(student_id)
        if self.student is None:
            ttk.Label(content, text="Студент не найден в базе данных").pack(pady=40)
            return
        self.total = repository.get_stats().total
        self.rank = repository.get_rank(student_id)
        self.grades = repository.get_student_grades(student_id)

        me = next(s for s in insights.students(app.low_score, app.high_absences)
                  if s["id"] == student_id)
        actions, sub = page_header(content, self.student["fio"],
                                   back=(BACK_TITLES.get(back, "Назад"), self.go_back))
        sub.config(text=insights.notes(me) or "Замечаний по текущим порогам нет")
        self._neighbor_buttons(actions)
        ttk.Button(actions, text="Экспорт в PDF", style="Primary.TButton", cursor="hand2",
                   command=self.export_pdf).pack(side="left", padx=(12, 0))

        stats = stat_row(content, ("Итоговый балл", "Место в группе", "Пропущено занятий",
                                   "Пропуски считать до"))
        stats[0][0].config(text=fmt_number(self.student["itog_ball"]))
        stats[1][0].config(text=f"{self.rank} из {self.total}" if self.rank else "—")
        self.missed_value = stats[2][0]

        # Дата, до которой учитываем занятия, влияет на журнал, пропуски и PDF.
        # По умолчанию — дата последнего оценённого занятия
        date_card = stats[3][0].master
        stats[3][0].destroy()
        self.date_picker = self._date_picker(date_card)
        self.date_picker.pack(anchor="w", pady=(6, 0))
        for sequence in ("<<DateEntrySelected>>", "<Return>", "<FocusOut>"):
            self.date_picker.bind(sequence, self.refresh, add="+")

        self.journal = Journal(content, app.palette)
        self.journal.frame.pack(fill="x", pady=(0, 12))

        bar = ttk.Frame(content)
        bar.pack(fill="x", pady=(0, 8))
        self.tabs = Segmented(bar, [("grades", "Оценки"), ("missed", "Пропуски")],
                              self.state["tab"], self.show_tab)
        self.tabs.pack(side="left")
        self.filter_var = tk.StringVar(value=self.state["filter"])
        self.filter_box = ttk.Combobox(bar, textvariable=self.filter_var, values=GRADE_FILTERS,
                                       state="readonly", width=24)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.fill_grades())

        body = ttk.Frame(content)
        body.pack(fill="both", expand=True)
        self.grades_table = DataTable(
            body, app.palette,
            [("date", "Дата", 96, "center", False), ("name", "Занятие", 150, "w", False),
             ("topic", "Тема", 360, "w", True), ("ball", "Балл", 70, "center", False),
             ("mark", "Оценка", 80, "center", False)],
            empty_text="Оценок пока нет", height=3)
        self.missed_table = DataTable(
            body, app.palette,
            [("date", "Дата", 96, "center", False), ("name", "Занятие", 150, "w", False),
             ("topic", "Тема", 500, "w", True)], empty_text="Пропусков нет", height=3)
        self.fill_grades()
        self.refresh()
        self.show_tab(self.state["tab"])

    def _neighbor_buttons(self, parent):
        position = self.ids.index(self.student_id) if self.student_id in self.ids else None
        for text, step in (("‹ Предыдущий", -1), ("Следующий ›", 1)):
            button = ttk.Button(parent, text=text, cursor="hand2")
            button.pack(side="left", padx=(0, 4))
            if position is None or not 0 <= position + step < len(self.ids):
                button.state(["disabled"])
            else:
                button.config(command=lambda i=self.ids[position + step]: self.app.show_window(
                    "student_page", student_id=i, ids=self.ids, back=self.back))

    def _date_picker(self, parent):
        p = self.app.palette
        colors = dict(
            background=p["accent"], foreground=p["on_accent"],
            headersbackground=p["surface_alt"], headersforeground=p["text"],
            normalbackground=p["surface"], normalforeground=p["text"],
            weekendbackground=p["surface"], weekendforeground=p["text"],
            selectbackground=p["accent"], selectforeground=p["on_accent"],
            othermonthbackground=p["surface_alt"], othermonthforeground=p["muted"],
            othermonthwebackground=p["surface_alt"], othermonthweforeground=p["muted"],
            disabledbackground=p["disabled_bg"], disabledforeground=p["disabled_fg"],
            bordercolor=p["border"])
        picker = None
        # Разные версии tkcalendar иногда не принимают часть параметров —
        # пробуем от самого полного варианта к самому простому
        for kwargs in (dict(locale="ru_RU", **colors), colors, {}):
            try:
                picker = DateEntry(parent, width=11, date_pattern="dd.mm.yyyy", **kwargs)
                break
            except Exception:
                if not kwargs:
                    raise
        picker.set_date(iso_to_date(repository.get_last_graded_date()) or date_cls.today())
        return picker

    def selected_date(self):
        try:
            return date_to_iso(self.date_picker.get_date())
        except Exception:
            messagebox.showerror("Неверная дата", "Выберите дату в календаре.")
            return None

    def show_tab(self, key):
        self.state["tab"] = key
        self.grades_table.pack_forget()
        self.missed_table.pack_forget()
        self.filter_box.pack_forget()
        if key == "grades":
            self.filter_box.pack(side="right")
            self.grades_table.pack(fill="both", expand=True)
        else:
            self.missed_table.pack(fill="both", expand=True)

    def refresh(self, _event=None):
        if not hasattr(self, "journal") or not self.journal.canvas.winfo_exists():
            return  # FocusOut может прийти, пока страница строится или закрывается
        up_to = self.selected_date()
        if up_to is None:
            return
        lessons = repository.get_missed_lessons(self.student_id, up_to)
        self.missed_table.set_rows([
            (i, (iso_to_display(r["data"]), work_title(r["nazvanie"]), r["tema"] or ""),
             "even" if i % 2 else "odd") for i, r in enumerate(lessons)])
        self.missed_value.config(text=str(len(lessons)))
        self.tabs.set_text("missed", f"Пропуски  {len(lessons)}")
        self.journal.show(journal_lanes(self.grades, up_to))

    def fill_grades(self):
        mode = self.state["filter"] = self.filter_var.get()
        rows, graded = [], 0
        for number, r in enumerate(self.grades):
            if r["kind"] == "period":
                held = r["held"]
                rows.append((number, (
                    iso_to_display(r["date"]), f"Итог периода {r['period']}",
                    "Сумма баллов за период" if held else "Контрольную ещё никто не писал",
                    fmt_number(r["total"]) if held else "—",
                    r["grade"] if r["grade"] is not None else "—"),
                    "total_danger" if r["grade"] == 2 else "total"))
                continue
            has_grade = r["ball"] is not None or r["raw"] is not None
            graded += has_grade
            if mode == GRADE_FILTERS[2] or (mode == GRADE_FILTERS[0] and not has_grade):
                continue
            value = fmt_number(r["ball"]) if r["ball"] is not None else (r["raw"] or "—")
            tag = ("even" if len(rows) % 2 else "odd") if has_grade else "empty"
            rows.append((number, (iso_to_display(r["date"]), work_title(r["name"]),
                                  r["tema"] or "", value, ""), tag))
        self.grades_table.set_rows(rows)
        self.tabs.set_text("grades", f"Оценки  {graded}")

    def go_back(self):
        self.app.show_window(self.back)

    def export_pdf(self):
        """Сохраняет карточку студента в PDF: пропуски на выбранную дату и оценки."""
        up_to = self.selected_date()
        if up_to is None:
            return
        last_dir = load_settings().get("last_pdf_dir")
        name = "_".join(self.student["fio"].split()) + "_карточка.pdf"
        path = filedialog.asksaveasfilename(
            title="Сохранить карточку студента", defaultextension=".pdf",
            filetypes=[("PDF файлы", "*.pdf")], initialfile=name,
            initialdir=last_dir if last_dir and os.path.isdir(last_dir) else None)
        if not path:
            return
        try:
            build_student_card_pdf(
                path, self.student, self.rank, self.total, up_to,
                repository.get_missed_lessons(self.student_id, up_to), self.grades)
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
