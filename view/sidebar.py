"""Боковое меню: разделы, текущий файл, загрузка другого файла и тема."""
import os
from tkinter import ttk

# (имя страницы в app.register_page, подпись)
SECTIONS = (
    ("overview_page", "Обзор"),
    ("students_page", "Студенты"),
    ("control_page", "Контрольные"),
    ("visualization_page", "Диаграммы"),
)
TOOLS = (("excel_builder_page", "Новый журнал Excel"),)
WIDTH = 224


def build_sidebar(parent, app, active):
    bar = ttk.Frame(parent, style="Sidebar.TFrame", width=WIDTH, padding=(12, 16))
    bar.pack(side="left", fill="y")
    bar.pack_propagate(False)
    ttk.Frame(parent, style="Line.TFrame", width=1).pack(side="left", fill="y")

    ttk.Label(bar, text="Work Tracker", style="Brand.TLabel").pack(anchor="w", padx=12,
                                                                    pady=(0, 20))

    def item(name, title):
        ttk.Button(bar, text=title, cursor="hand2", command=lambda: app.show_window(name),
                   style="NavActive.TButton" if name == active else "Nav.TButton"
                   ).pack(fill="x", pady=2)

    for name, title in SECTIONS:
        item(name, title)
    ttk.Frame(bar, style="Line.TFrame", height=1).pack(fill="x", pady=12)
    for name, title in TOOLS:
        item(name, title)

    # Низ меню упаковывается снизу вверх
    ttk.Button(bar, text=app.theme_button_text, style="Nav.TButton", cursor="hand2",
               command=app.toggle_theme).pack(side="bottom", fill="x", pady=(2, 0))
    ttk.Button(bar, text="Главный экран", style="Nav.TButton", cursor="hand2",
               command=lambda: app.show_window("main_menu")).pack(side="bottom", fill="x", pady=2)
    ttk.Button(bar, text="Открыть другой файл", cursor="hand2",
               command=app.open_file).pack(side="bottom", fill="x", pady=(8, 12))
    ttk.Label(bar, text=os.path.basename(app.filepath or ""), style="Side.TLabel",
              wraplength=WIDTH - 40, justify="left").pack(side="bottom", anchor="w", padx=12)
    ttk.Label(bar, text="Файл", style="SideMuted.TLabel").pack(side="bottom", anchor="w", padx=12)
