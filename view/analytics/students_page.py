import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import FONT_FAMILY, LOW_SCORE_THRESHOLD, HIGH_ABSENCES_THRESHOLD
from database import repository
from utils.dates import iso_to_display, display_to_iso


def fmt_number(value, empty="—"):
    """7.5 -> '7.5', 8.0 -> '8', None -> '—'."""
    return empty if value is None else f"{value:g}"


class StudentsPage:
    SEARCH_DELAY_MS = 250  # задержка перед поиском, чтобы не запрашивать БД на каждую букву

    # столбец таблицы -> столбец БД
    SORTABLE = {"fio": "fio", "score": "itog_ball", "absences": "kol_propuskov"}
    HEADINGS = {"id": "№", "fio": "ФИО", "score": "Итоговый балл", "absences": "Количество пропусков"}

    def __init__(self, main_frame, app, filepath):
        self.main_frame = main_frame
        self.app = app
        self.filepath = filepath

        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value="Без сортировки")
        self.sort_column = None   # столбец БД
        self.sort_dir = "ASC"
        self.current_rows = []
        self._search_job = None

        self.create_widgets()
        self.refresh_table()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def create_widgets(self):
        header_frame = ttk.Frame(self.main_frame, style="Header.TFrame")
        header_frame.pack(fill="x", side="top")

        ttk.Button(header_frame, text="🡸", cursor="hand2", style="ArrowButton.TButton",
                   command=self.back_to_main_menu).pack(pady=10, padx=15, anchor="w", side="left")

        ttk.Label(self.main_frame, text=self.filepath, style="Hint.TLabel").pack(side="bottom", pady=8)

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self._build_left_panel(content_frame)
        self._build_table(content_frame)

    def _build_left_panel(self, parent):
        panel = ttk.Frame(parent, width=280)
        panel.pack(side="left", fill="y", padx=(0, 15), anchor="n")

        ttk.Label(panel, text="Поиск:", style="SmallLabel.TLabel").pack(padx=5, pady=5, fill="x")
        self.search_entry = ttk.Entry(panel, textvariable=self.search_var)
        self.search_entry.pack(padx=5, pady=5, fill="x")
        self.search_var.trace_add("write", self.on_search_changed)

        info = ttk.LabelFrame(panel, text="Общая информация", padding=10)
        info.pack(padx=5, pady=(20, 5), fill="x")
        self.total_students_label = ttk.Label(info, text="Всего студентов: 0")
        self.total_students_label.pack(anchor="w", pady=2)
        self.shown_label = ttk.Label(info, text="Показано: 0")
        self.shown_label.pack(anchor="w", pady=2)
        self.avg_score_label = ttk.Label(info, text="Средний балл: —")
        self.avg_score_label.pack(anchor="w", pady=2)
        self.avg_absences_label = ttk.Label(info, text="Среднее пропусков: —")
        self.avg_absences_label.pack(anchor="w", pady=2)

        legend = ttk.LabelFrame(panel, text="Подсветка", padding=10)
        legend.pack(padx=5, pady=(10, 5), fill="x")
        for color, text in (("#FEE2E2", f"балл ниже {fmt_number(LOW_SCORE_THRESHOLD)}"),
                            ("#FEF3C7", f"пропусков больше {HIGH_ABSENCES_THRESHOLD}")):
            row = ttk.Frame(legend)
            row.pack(anchor="w", pady=2)
            tk.Label(row, background=color, width=2, relief="flat").pack(side="left", padx=(0, 8))
            ttk.Label(row, text=text, style="Hint.TLabel").pack(side="left")

        self.moreinfo_btn = ttk.Button(panel, text="Подробнее", cursor="hand2",
                                       style="MainButton.TButton", state=tk.DISABLED,
                                       command=self.open_student_window)
        self.moreinfo_btn.pack(pady=(25, 0), padx=5, fill="x")

    def _build_table(self, parent):
        table_frame = ttk.Frame(parent)
        table_frame.pack(side="right", fill="both", expand=True)

        columns = ("id", "fio", "score", "absences")
        self.student_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                                          selectmode="browse")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.student_table.yview)
        self.student_table.configure(yscrollcommand=scrollbar.set)

        widths = {"id": (50, "w"), "fio": (300, "w"), "score": (140, "center"), "absences": (200, "center")}
        for col in columns:
            self.student_table.heading(col, text=self.HEADINGS[col])
            if col in self.SORTABLE:
                # команду задаём отдельно: command=None в новых версиях Python вызывает TclError
                self.student_table.heading(col, command=lambda c=col: self.on_heading_click(c))
            self.student_table.column(col, width=widths[col][0], anchor=widths[col][1])

        self.student_table.tag_configure("low_score", background="#FEE2E2")
        self.student_table.tag_configure("many_absences", background="#FEF3C7")

        scrollbar.pack(side="right", fill="y")
        self.student_table.pack(side="left", fill="both", expand=True)

        self.student_table.bind("<Double-1>", self.open_student_window)
        self.student_table.bind("<Return>", self.open_student_window)
        self.student_table.bind("<<TreeviewSelect>>", self.on_table_select)

    # ------------------------------------------------------------------
    # Поиск, сортировка, таблица
    # ------------------------------------------------------------------

    def on_search_changed(self, *_):
        if self._search_job:
            self.main_frame.after_cancel(self._search_job)
        self._search_job = self.main_frame.after(self.SEARCH_DELAY_MS, self.refresh_table)

    def on_sort_selected(self, _event=None):
        option = repository.SORT_OPTIONS.get(self.sort_var.get())
        self.sort_column, self.sort_dir = option if option else (None, "ASC")
        self.refresh_table()

    def on_heading_click(self, table_column):
        db_column = self.SORTABLE[table_column]
        if self.sort_column == db_column:
            self.sort_dir = "DESC" if self.sort_dir == "ASC" else "ASC"
        else:
            self.sort_column, self.sort_dir = db_column, "ASC"
        self.sort_var.set("Без сортировки")  # сортировка теперь задаётся заголовком
        self.refresh_table()

    def _update_heading_arrows(self):
        for table_column, db_column in self.SORTABLE.items():
            arrow = ""
            if self.sort_column == db_column:
                arrow = " ▲" if self.sort_dir == "ASC" else " ▼"
            self.student_table.heading(table_column, text=self.HEADINGS[table_column] + arrow)

    def refresh_table(self, *_):
        self._search_job = None
        try:
            rows = repository.get_students(self.search_var.get(), self.sort_var.get(),
                                           self.sort_column, self.sort_dir)
            stats = repository.get_stats()
        except Exception as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось получить данные:\n{e}")
            return

        self.current_rows = rows
        self.student_table.delete(*self.student_table.get_children())
        for row in rows:
            tags = []
            if row["itog_ball"] is not None and row["itog_ball"] < LOW_SCORE_THRESHOLD:
                tags.append("low_score")
            if row["kol_propuskov"] is not None and row["kol_propuskov"] > HIGH_ABSENCES_THRESHOLD:
                tags.append("many_absences")
            self.student_table.insert(
                "", "end", iid=str(row["id"]), tags=tags,
                values=(row["id"], row["fio"], fmt_number(row["itog_ball"]),
                        fmt_number(row["kol_propuskov"])))

        self._update_heading_arrows()
        self.on_table_select()

        self.total_students_label.config(text=f"Всего студентов: {stats.total}")
        self.shown_label.config(text=f"Показано: {len(rows)}")
        self.avg_score_label.config(text=f"Средний балл: {fmt_number(round(stats.avg_score, 2) if stats.avg_score is not None else None)}")
        self.avg_absences_label.config(text=f"Среднее пропусков: {fmt_number(round(stats.avg_absences, 2) if stats.avg_absences is not None else None)}")

    def on_table_select(self, _event=None):
        state = tk.NORMAL if self.student_table.selection() else tk.DISABLED
        self.moreinfo_btn.config(state=state)

    # ------------------------------------------------------------------
    # Действия
    # ------------------------------------------------------------------

    def back_to_main_menu(self):
        if messagebox.askyesno("Внимание!", "Вы уверены, что хотите выйти в главное меню?"):
            self.app.show_window("main_menu")

    def open_student_window(self, _event=None):
        selection = self.student_table.selection()
        if selection:
            self.create_moreinfo_window(int(selection[0]))

    # ------------------------------------------------------------------
    # Окно «Подробнее»
    # ------------------------------------------------------------------

    def create_moreinfo_window(self, student_id):
        student = repository.get_student(student_id)
        if student is None:
            messagebox.showerror("Ошибка", "Студент не найден в базе данных.")
            return

        win = tk.Toplevel(self.main_frame)
        win.title(f"Подробная информация ({student['fio']})")
        win.geometry("900x680")
        win.transient(self.main_frame.winfo_toplevel())
        win.grab_set()
        win.bind("<Escape>", lambda _e: win.destroy())

        container = ttk.Frame(win, padding=20)
        container.pack(fill="both", expand=True)

        # --- Основная информация ---
        rank = repository.get_rank(student_id)
        total = repository.get_stats().total
        info = ttk.LabelFrame(container, text="Основная информация", padding=15)
        info.pack(fill="x", pady=(0, 10))
        ttk.Label(info, text=f"ФИО: {student['fio']}", font=(FONT_FAMILY, 11, "bold")).pack(anchor="w", pady=2)
        ttk.Label(info, text=f"Итоговый балл: {fmt_number(student['itog_ball'])}").pack(anchor="w", pady=2)
        ttk.Label(info, text=f"Количество пропусков: {fmt_number(student['kol_propuskov'])}").pack(anchor="w", pady=2)
        place = f"{rank} из {total}" if rank else "нет итогового балла"
        ttk.Label(info, text=f"Место в группе: {place}", font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=5)

        # --- Дата, до которой учитываем занятия ---
        last_date = repository.get_last_graded_date()
        date_var = tk.StringVar(value=iso_to_display(last_date))
        date_row = ttk.Frame(container)
        date_row.pack(fill="x", pady=(0, 10))
        ttk.Label(date_row, text="Учитывать занятия до:").pack(side="left")
        date_entry = ttk.Entry(date_row, textvariable=date_var, width=12)
        date_entry.pack(side="left", padx=8)
        ttk.Label(date_row, text="(дд.мм.гггг; по умолчанию — дата последнего оценённого занятия)",
                  style="Hint.TLabel").pack(side="left")

        # --- Таблицы ---
        lessons_frame = ttk.LabelFrame(container, text="Пропущенные занятия", padding=10)
        lessons_frame.pack(fill="both", expand=True, pady=(0, 10))
        lessons_table = self._build_activity_table(
            lessons_frame, (("date", "Дата", 90, "center"), ("name", "Занятие", 90, "center"),
                            ("topic", "Тема", 600, "w")))

        works_frame = ttk.LabelFrame(container, text="Работы без оценки", padding=10)
        works_frame.pack(fill="both", expand=True)
        works_table = self._build_activity_table(
            works_frame, (("date", "Дата", 90, "center"), ("name", "Название", 200, "w"),
                          ("type", "Тип", 90, "center"), ("topic", "Тема", 400, "w")))

        def fill(_event=None):
            try:
                up_to = display_to_iso(date_var.get())
            except ValueError:
                messagebox.showerror("Неверная дата", "Введите дату в формате дд.мм.гггг, "
                                     "например 06.10.2025.", parent=win)
                return
            rows = repository.get_empty_activities(student_id, up_to)
            lessons = [r for r in rows if r["tip"] in repository.LESSON_TYPES]
            works = [r for r in rows if r["tip"] not in repository.LESSON_TYPES]

            lessons_table.delete(*lessons_table.get_children())
            works_table.delete(*works_table.get_children())
            for r in lessons:
                name = f"Урок {r['nazvanie']}" if r["nazvanie"].isdigit() else r["nazvanie"]
                lessons_table.insert("", "end", values=(iso_to_display(r["data"]), name, r["tema"] or ""))
            for r in works:
                works_table.insert("", "end", values=(iso_to_display(r["data"]), r["nazvanie"],
                                                      r["tip"], r["tema"] or ""))
            lessons_frame.config(text=f"Пропущенные занятия ({len(lessons)})")
            works_frame.config(text=f"Работы без оценки ({len(works)})")

        ttk.Button(date_row, text="Применить", style="Secondary.TButton", command=fill).pack(side="left")
        date_entry.bind("<Return>", fill)

        ttk.Button(container, text="Закрыть", style="Secondary.TButton",
                   command=win.destroy).pack(pady=(12, 0))
        fill()

    @staticmethod
    def _build_activity_table(parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        ids = [c[0] for c in columns]
        table = ttk.Treeview(frame, columns=ids, show="headings", height=5)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        for col_id, title, width, anchor in columns:
            table.heading(col_id, text=title)
            table.column(col_id, width=width, anchor=anchor)
        scroll.pack(side="right", fill="y")
        table.pack(side="left", fill="both", expand=True)
        return table