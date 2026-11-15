import os
import sys

if getattr(sys, "frozen", False):                     # запущено из .exe
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DATA_DIR = os.path.dirname(sys.executable)        # рядом с exe
else:
    RESOURCE_DIR = DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(DATA_DIR, "university.db")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
ICON_PATH = os.path.join(RESOURCE_DIR, "images", "app_ico.png")

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


# Контрольные: последнее занятие перед столбцом «оценка N» — контрольная периода
# Балл за контрольную, который считается «не писал» (пустая ячейка — тоже не писал)
NO_CONTROL_SCORE = 0.5