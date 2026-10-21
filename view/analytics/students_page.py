from tkinter import *
from tkinter import ttk, messagebox
from database.database_manager import db_connection


class StudentsPage:
    def __init__(self, main_frame, app, filepath):
        self.main_frame = main_frame
        self.app = app
        self.filepath = filepath

        self.create_widgets()

    def create_widgets(self):
        header_frame = ttk.Frame(self.main_frame, style="Header.TFrame")
        header_frame.pack(fill="x", side="top")

        back_btn = ttk.Button(header_frame, text="🡸", cursor='hand2', style="ArrowButton.TButton",
                              command=self.back_to_main_menu)
        back_btn.pack(pady=10, padx=15, anchor="w", side="left")

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        left_panel = ttk.Frame(content_frame)
        left_panel.pack(side="left", fill="y", padx=(0, 15), pady=0, anchor="n")

        self.moreinfo_btn = ttk.Button(left_panel, text="Подробнее", cursor='hand2', style="MainButton.TButton",
                                       state=DISABLED)
        self.moreinfo_btn.pack(pady=0, padx=0, fill="x")

        columns = ("id", "fio", "score", "absences")
        self.student_table = ttk.Treeview(content_frame, columns=columns, show="headings")

        self.student_table.heading("id", text="id")
        self.student_table.heading("fio", text="ФИО")
        self.student_table.heading("score", text="Итоговый балл")
        self.student_table.heading("absences", text="Количество пропусков")

        self.student_table.column("id", width=5, anchor="w")
        self.student_table.column("fio", width=300, anchor="w")
        self.student_table.column("score", width=130, anchor="center")
        self.student_table.column("absences", width=180, anchor="center")

        self.student_table.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        self.student_table.bind("<Double-1>", self.open_student_window)

        ttk.Label(self.main_frame, text=f"{self.filepath}", font=("Inter", 9), foreground="#8E8E93").pack(side="bottom",
                                                                                                          pady=10)

        self.get_students_data()

    def back_to_main_menu(self):
        isTrue = messagebox.askyesno("Внимание!", "Вы уверены, что хотите выйти в главное меню?")
        if isTrue:
            self.app.show_window("main_menu")
        else:
            return

    def check_db_status(self):
        conn = db_connection()
        if conn:
            messagebox.showinfo("Успешно", "База данных подключена")
            print("connected")
            return
        else:
            messagebox.showerror("Ошибка", "Не удалось подключиться к базе")
            return

    def get_students_data(self):
        for child in self.student_table.get_children():
            self.student_table.delete(child)

        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Students")

        items = cursor.fetchall()

        for row in items:
            self.student_table.insert("", 'end', values=tuple(row))

        cursor.close()
        conn.close()

    def open_student_window(self, event=None):
        selection = self.student_table.selection()
        if selection:
            item = self.student_table.item(selection[0])
            student_id = item['values'][0]
            student_name = item['values'][1]

            self.create_moreinfo_window(student_id, student_name)

    def create_moreinfo_window(self, student_id, student_name):
        self.moreinfo_window = Toplevel(self.main_frame)
        self.moreinfo_window.geometry("900x600")
        self.moreinfo_window.title(f"Подробная информация ({student_name})")
        self.moreinfo_window.grab_set()

        # Создаем основной контейнер
        main_container = ttk.Frame(self.moreinfo_window, padding="20")
        main_container.pack(fill="both", expand=True)

        # Получаем данные о студенте
        conn = db_connection()
        cursor = conn.cursor()

        # Получаем информацию о студенте
        cursor.execute("SELECT itog_ball, kol_propuskov FROM Students WHERE id = ?", (student_id,))
        student_data = cursor.fetchone()
        final_score = student_data[0] if student_data else 0
        absences = student_data[1] if student_data else 0

        # Вычисляем место в группе
        cursor.execute("""
            SELECT COUNT(*) + 1 as rank 
            FROM Students 
            WHERE itog_ball > ? 
            OR (itog_ball = ? AND id < ?)
        """, (final_score, final_score, student_id))
        rank = cursor.fetchone()[0]

        # Получаем общее количество студентов
        cursor.execute("SELECT COUNT(*) FROM Students")
        total_students = cursor.fetchone()[0]

        # Секция с основной информацией
        info_frame = ttk.LabelFrame(main_container, text="Основная информация", padding="15")
        info_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(info_frame, text=f"ФИО: {student_name}", font=("Inter", 11, "bold")).pack(anchor="w", pady=2)
        ttk.Label(info_frame, text=f"Итоговый балл: {final_score}", font=("Inter", 10)).pack(anchor="w", pady=2)
        ttk.Label(info_frame, text=f"Количество пропусков: {absences}", font=("Inter", 10)).pack(anchor="w", pady=2)
        ttk.Label(info_frame, text=f"Место в группе: {rank} из {total_students}", font=("Inter", 10, "bold")).pack(
            anchor="w", pady=5)

        # Секция с пропущенными занятиями
        activities_frame = ttk.LabelFrame(main_container, text="Пропущенные занятия", padding="15")
        activities_frame.pack(fill="both", expand=True)

        # Получаем пропущенные занятия
        cursor.execute("""
    SELECT a.data, a.tema, a.nazvanie
    FROM Activities a
    LEFT JOIN Grades g
           ON g.activity_id = a.id AND g.student_id = ?
    WHERE g.poluchenny_ball IS NULL
    ORDER BY a.data
""", (student_id,))
        missed_activities = cursor.fetchall()
        print(missed_activities)

        # Фильтруем будущие даты (без года)
        from datetime import datetime
        import re

        # ВРЕМЕННО ДЛЯ ТЕСТА:
        current_date = datetime(2025, 10, 6)

        filtered_activities = []
        for activity in missed_activities:
            date_str = activity[0]
            if not date_str:
                continue

            date_str = date_str.strip()
            parsed_date = None

            # 1. Парсим формат ГГГГ-ММ-ДД (например, 2025-11-16)
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

            # 2. Парсим формат ДД.ММ/ДД.ММ (например, 12.10/15.10)
            if not parsed_date:
                first_part = date_str.split('/')[0]
                match = re.match(r'(\d{1,2})\.(\d{1,2})', first_part)
                if match:
                    act_day = int(match.group(1))
                    act_month = int(match.group(2))
                    # Для дат без года используем год из current_date
                    parsed_date = datetime(current_date.year, act_month, act_day)

            # 3. Сравниваем
            if parsed_date and parsed_date <= current_date:
                filtered_activities.append(activity)

        # Создаем таблицу с пропущенными занятиями
        if filtered_activities:
            columns = ("date", "name", "topic")
            activities_table = ttk.Treeview(activities_frame, columns=columns, show="headings",
                                            height=min(len(filtered_activities), 10))

            activities_table.heading("date", text="Дата")
            activities_table.heading("name", text="Урок")
            activities_table.heading("topic", text="Тема")

            activities_table.column("date", width=80, anchor="center")
            activities_table.column("name", width=200, anchor="w")
            activities_table.column("topic", width=400, anchor="w")

            for activity in filtered_activities:
                activities_table.insert("", "end", values=(activity[0], activity[2], activity[1]))

            activities_table.pack(fill="both", expand=True)
        else:
            ttk.Label(activities_frame, text="Нет пропущенных занятий", font=("Inter", 10), foreground="#8E8E93").pack(
                pady=20)

        # Кнопка закрытия
        close_btn = ttk.Button(main_container, text="Закрыть", command=self.moreinfo_window.destroy)
        close_btn.pack(pady=(15, 0))

        cursor.close()
        conn.close()

