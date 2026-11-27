"""Главный экран: продолжить работу, открыть журнал или создать новый."""
from tkinter import ttk

from view.widgets import card


class StartPage:
    def __init__(self, content, app):
        self.app = app

        ttk.Button(content, text=app.theme_button_text, style="Quiet.TButton", cursor="hand2",
                   command=app.toggle_theme).pack(anchor="ne")

        column = ttk.Frame(content)
        column.place(relx=0.5, rely=0.5, anchor="center", width=560)

        ttk.Label(column, text="Work Tracker", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(column, text="Успеваемость группы из вашего Excel-журнала: кто отстаёт, "
                               "кто пропускает и кто не писал контрольную",
                  style="Lead.TLabel", wraplength=540, justify="left"
                  ).pack(anchor="w", pady=(8, 24))

        if app.filepath:
            self._action(column, "Продолжить работу", app.file_name, "Открыть",
                         lambda: app.show_window("overview_page"), primary=True)
        self._action(column, "Открыть журнал", "Готовый файл .xlsx с оценками · Ctrl+O",
                     "Выбрать файл", app.open_file, primary=not app.filepath)
        self._action(column, "Создать новый журнал",
                     "Пустой Excel-файл нужной структуры с формулами", "Создать",
                     lambda: app.show_window("excel_builder_page"))

    @staticmethod
    def _action(parent, title, hint, button, command, primary=False):
        box = card(parent)
        box.pack(fill="x", pady=(0, 12))
        ttk.Button(box, text=button, cursor="hand2", command=command,
                   style="Primary.TButton" if primary else "TButton").pack(side="right",
                                                                           padx=(16, 0))
        ttk.Label(box, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(box, text=hint, style="CardMuted.TLabel", wraplength=360,
                  justify="left").pack(anchor="w", pady=(2, 0))
