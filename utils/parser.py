import sqlite3
import os
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# === НАСТРОЙКИ ===
EXCEL_FILE = "ИСП.25_Основы проектирования баз данных.xlsx"
DB_FILE = "university.db"

# Удаляем старую базу, если она есть (чтобы не было дублей при повторном запуске)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Старая база {DB_FILE} удалена.")

# === СОЗДАНИЕ БАЗЫ ДАННЫХ ===
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Создаем 3 таблицы по нашей схеме
cursor.execute('''
CREATE TABLE IF NOT EXISTS Students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio TEXT NOT NULL,
    itog_ball REAL,
    kol_propuskov INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazvanie TEXT NOT NULL,
    tip TEXT NOT NULL,
    data TEXT,
    tema TEXT,
    max_ball REAL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Grades (
    student_id INTEGER,
    activity_id INTEGER,
    poluchenny_ball REAL,
    PRIMARY KEY (student_id, activity_id),
    FOREIGN KEY (student_id) REFERENCES Students(id),
    FOREIGN KEY (activity_id) REFERENCES Activities(id)
)
''')
conn.commit()
print("✅ Таблицы в БД созданы.")

# === ЗАГРУЗКА EXCEL ===
wb = load_workbook(EXCEL_FILE, data_only=True)

# --- ШАГ 1: Читаем лист "Даты_темы" ---
print("\n📖 Читаем лист 'Даты_темы'...")
sheet_dates = wb["Даты_темы"]

# Собираем словарь: {номер_урока: {"дата": ..., "тема": ...}}
lessons_info = {}
for row in sheet_dates.iter_rows(min_row=2, values_only=True):  # Пропускаем шапку
    if row[0] is None:
        continue
    try:
        lesson_num = int(row[0])
        date = str(row[1]) if row[1] else ""
        theme = str(row[2]) if row[2] else ""
        lessons_info[lesson_num] = {"дата": date, "тема": theme}
    except (ValueError, IndexError):
        continue

print(f"   Найдено {len(lessons_info)} уроков с темами.")

# --- ШАГ 2: Читаем лист "Баллы, оценки" ---
print("\n📖 Читаем лист 'Баллы, оценки'...")
sheet_grades = wb["Баллы, оценки"]

# Читаем шапку (строки 1 и 2) чтобы понять структуру столбцов
header_row1 = [cell.value for cell in sheet_grades[1]]
header_row2 = [cell.value for cell in sheet_grades[2]]

# Определяем, где заканчиваются столбцы с работами и начинаются итоговые
# Ищем столбцы с "итог", "кол-пропусков" — их пропускаем при создании Activities
activity_columns = []  # Список кортежей: (номер_столбца, название, дата)

for col_idx in range(len(header_row1)):
    col_letter = get_column_letter(col_idx + 1)
    name = header_row1[col_idx]
    date = header_row2[col_idx]

    # Пропускаем пустые столбцы и служебные (ФИО, итог, пропуски)
    if name is None:
        continue
    name_str = str(name).strip().lower()

    if any(x in name_str for x in ["итог", "кол-пропуск", "пропуск", "фио", "№"]):
        continue

    activity_columns.append((col_idx, str(name).strip(), str(date) if date else ""))

print(f"   Найдено {len(activity_columns)} видов работ для импорта.")

# --- ШАГ 3: Заполняем таблицу Activities ---
# Также создаем словарь для быстрого поиска activity_id по индексу столбца
col_to_activity_id = {}

for col_idx, name, date in activity_columns:
    # Определяем тип работы по названию
    name_lower = name.lower()
    if name_lower.startswith("пр"):
        tip = "ПР"
    elif name_lower.startswith("лр"):
        tip = "ЛР"
    elif name_lower.startswith("дз"):
        tip = "ДЗ"
    elif "оценка" in name_lower or "зачет" in name_lower:
        tip = "Зачет"
    else:
        tip = "Урок"

    # Пытаемся найти тему из листа Даты_темы
    tema = ""
    # Ищем номер урока в названии (например "ПР1_ур.17" -> 17)
    import re

    match = re.search(r'ур\.?\s*(\d+)', name, re.IGNORECASE)
    if match:
        lesson_num = int(match.group(1))
        if lesson_num in lessons_info:
            tema = lessons_info[lesson_num]["тема"]
            if not date:  # Если даты нет в шапке, берем из Даты_темы
                date = lessons_info[lesson_num]["дата"]

    # Определяем максимальный балл (по умолчанию)
    if tip == "Урок":
        max_ball = 2
    elif tip in ["ПР", "ЛР"]:
        max_ball = 5
    elif tip == "ДЗ":
        max_ball = 3
    elif tip == "Зачет":
        max_ball = 10
    else:
        max_ball = 5

    cursor.execute('''
        INSERT INTO Activities (nazvanie, tip, data, tema, max_ball)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, tip, date, tema, max_ball))
    col_to_activity_id[col_idx] = cursor.lastrowid

conn.commit()
print(f"✅ В таблицу Activities добавлено {len(activity_columns)} записей.")

# --- ШАГ 4: Читаем студентов и их оценки ---
print("\n👨‍🎓 Читаем студентов...")

# Ищем столбцы с ФИО, итоговым баллом и пропусками
fio_col = None
itog_col = None
propusk_col = None

for col_idx, val in enumerate(header_row1):
    if val is None:
        continue
    val_str = str(val).strip().lower()
    if "фио" in val_str or "ф.и.о" in val_str or "студент" in val_str:
        fio_col = col_idx
    elif "итог" in val_str:
        itog_col = col_idx
    elif "пропуск" in val_str:
        propusk_col = col_idx

# Если не нашли ФИО, предполагаем что это первый столбец (A)
if fio_col is None:
    fio_col = 0

print(
    f"   Столбец ФИО: {get_column_letter(fio_col + 1)}, Итог: {get_column_letter(itog_col + 1) if itog_col else 'не найден'}, Пропуски: {get_column_letter(propusk_col + 1) if propusk_col else 'не найден'}")

students_count = 0
grades_count = 0

# Читаем строки начиная с 3-й (строки 1 и 2 — шапка)
for row in sheet_grades.iter_rows(min_row=3, values_only=True):
    if row[fio_col] is None or str(row[fio_col]).strip() == "":
        continue

    fio = str(row[fio_col]).strip()

    # Пропускаем служебные строки типа "ОТЛИЧНО", "ХОРОШО", пустые разделители
    if fio.upper() in ["ОТЛИЧНО", "ХОРОШО", "УДОВЛЕТВОРИТЕЛЬНО", "НЕУДОВЛЕТВОРИТЕЛЬНО", "ИТОГ"]:
        continue

    # Получаем итоговый балл и пропуски
    itog = None
    if itog_col is not None and row[itog_col] is not None:
        try:
            itog = float(row[itog_col])
        except (ValueError, TypeError):
            itog = None

    propuski = None
    if propusk_col is not None and row[propusk_col] is not None:
        try:
            propuski = int(row[propusk_col])
        except (ValueError, TypeError):
            propuski = None

    # Вставляем студента
    cursor.execute('''
        INSERT INTO Students (fio, itog_ball, kol_propuskov)
        VALUES (?, ?, ?)
    ''', (fio, itog, propuski))
    student_id = cursor.lastrowid
    students_count += 1

    # Теперь проходим по всем столбцам с работами и добавляем оценки
    for col_idx, activity_id in col_to_activity_id.items():
        if col_idx >= len(row):
            continue

        cell_value = row[col_idx]

        # Обрабатываем значение ячейки
        if cell_value is None:
            ball = None  # Пропуск
        elif isinstance(cell_value, str):
            # Проверяем на ошибки Excel
            if cell_value.strip().startswith(("#", "ERROR", "#ИМЯ", "#ЗНАЧ")):
                ball = None
            else:
                # Пытаемся преобразовать строку в число
                try:
                    ball = float(cell_value.replace(",", "."))
                except ValueError:
                    ball = None
        elif isinstance(cell_value, (int, float)):
            ball = float(cell_value)
        else:
            ball = None

        # Вставляем оценку (даже если NULL — это пропуск, который мы хотим видеть!)
        cursor.execute('''
            INSERT INTO Grades (student_id, activity_id, poluchenny_ball)
            VALUES (?, ?, ?)
        ''', (student_id, activity_id, ball))
        grades_count += 1

conn.commit()
print(f"✅ Добавлено {students_count} студентов и {grades_count} оценок.")

# === ПРОВЕРКА ===
print("\n📊 Итоговая статистика базы данных:")
cursor.execute("SELECT COUNT(*) FROM Students")
print(f"   Студентов: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM Activities")
print(f"   Видов работ: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM Grades")
print(f"   Оценок (включая пропуски): {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM Grades WHERE poluchenny_ball IS NULL")
print(f"   Из них пропусков (NULL): {cursor.fetchone()[0]}")

# Показываем пример студента с пропусками
print("\n🔍 Пример: Пропущенные темы студента:")
cursor.execute('''
    SELECT s.fio, a.data, a.nazvanie, a.tema
    FROM Grades g
    JOIN Students s ON g.student_id = s.id
    JOIN Activities a ON g.activity_id = a.id
    WHERE g.poluchenny_ball IS NULL AND a.tema != ''
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f"   {row[0]} | {row[1]} | {row[2]} | {row[3]}")

conn.close()
wb.close()
print(f"\n🎉 Готово! База данных сохранена в файл: {DB_FILE}")
print("Откройте его через DB Browser for SQLite, чтобы посмотреть структуру.")