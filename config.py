import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# База данных хранится рядом с программой, независимо от текущей папки запуска
DB_PATH = os.path.join(BASE_DIR, "university.db")
ICON_PATH = os.path.join(BASE_DIR, "images", "app_ico.png")
# Файл с настройками (путь к последнему открытому xlsx)
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")

APP_TITLE = "Work Tracking"
WINDOW_SIZE = (1440, 800)
MIN_WINDOW_SIZE = (1100, 650)

# Шрифты с запасным вариантом, если Inter не установлен
FONT_FAMILY = "Inter" if sys.platform != "win32" else "Segoe UI"

# Пороги подсветки в таблице студентов
LOW_SCORE_THRESHOLD = 5.0    # балл ниже — красная подсветка
# Пропусков больше — жёлтая подсветка. Считаются только реально прошедшие уроки без оценки
# (будущие занятия в это число не попадают), поэтому порог ощутимо ниже, чем для старого счётчика.
HIGH_ABSENCES_THRESHOLD = 5


# Контрольные: каждое 4-е занятие периода — контрольная, по итогам периода ставится оценка
LESSONS_PER_PERIOD = 4
# Балл за контрольную, который считается «не писал» (пустая ячейка — тоже не писал)
NO_CONTROL_SCORE = 0.5