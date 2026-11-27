import os
import tkinter as tk
from tkinter import ttk

from config import APP_TITLE, ICON_PATH, WINDOW_SIZE, MIN_WINDOW_SIZE
from database.repository import database_has_data
from styles import set_styles, PALETTES
from utils.settings import load_settings, load_thresholds, save_setting
from view.loader import FileLoader
from view.sidebar import build_sidebar


class AppWorkTracker:
    """Окно приложения: тема, переходы между страницами и общее состояние."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)

        # Размер не больше экрана (ноутбуки 1366x768), окно можно менять и разворачивать
        width = min(WINDOW_SIZE[0], root.winfo_screenwidth() - 40)
        height = min(WINDOW_SIZE[1], root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(MIN_WINDOW_SIZE[0], width), min(MIN_WINDOW_SIZE[1], height))

        try:
            self.icon = tk.PhotoImage(file=ICON_PATH)
            root.iconphoto(True, self.icon)
        except tk.TclError:
            self.icon = None  # без иконки приложение работает

        settings = load_settings()
        theme = settings.get("theme", "light")
        self.theme = theme if theme in PALETTES else "light"
        self.palette = set_styles(self.root, self.theme)
        self.root.configure(background=self.palette["bg"])

        self.low_score, self.high_absences = load_thresholds()
        self.filepath = None
        self.warnings = []
        if settings.get("last_file") and database_has_data():
            self.filepath = settings["last_file"]
            self.warnings = settings.get("last_warnings") or []

        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.pages = {}
        self.state = {}  # поиск, фильтры и сортировка страниц сохраняются между переходами
        self.current_window = None
        self.current_page = ("main_menu", {})
        self.loader = FileLoader(self)

        root.bind("<Control-o>", lambda _e: self.open_file())
        root.bind("<Control-f>", lambda _e: self._call_page("focus_search"))
        root.bind("<Escape>", lambda _e: self._call_page("go_back"))

    # ------------------------------------------------------------------

    @property
    def theme_button_text(self):
        """На что переключим по клику."""
        return "Светлая тема" if self.theme == "dark" else "Тёмная тема"

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.palette = set_styles(self.root, self.theme)
        self.root.configure(background=self.palette["bg"])
        save_setting("theme", self.theme)
        # страница строится заново — не нужно перекрашивать каждый виджет вручную
        self.show_window(self.current_page[0], **self.current_page[1])

    def open_file(self):
        self.loader.open()

    def file_loaded(self, path, warnings):
        self.filepath, self.warnings = path, warnings
        self.state.clear()
        self.show_window("overview_page")

    def _call_page(self, method):
        handler = getattr(self.current_window, method, None)
        if handler and not self.loader.busy:
            handler()

    @property
    def file_name(self):
        return os.path.basename(self.filepath or "")

    # ------------------------------------------------------------------

    def register_page(self, name, page_class):
        self.pages[name] = page_class

    def show_window(self, name, **kwargs):
        if name not in self.pages:
            raise KeyError(f"Страница «{name}» не зарегистрирована")

        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.current_page = (name, kwargs)

        if name != "main_menu" and self.filepath:
            # карточка студента подсвечивает раздел, из которого её открыли
            build_sidebar(self.main_frame, self, kwargs.get("back", name))
        content = ttk.Frame(self.main_frame, padding=(24, 20, 24, 16))
        content.pack(side="left", fill="both", expand=True)
        self.current_window = self.pages[name](content, self, **kwargs)
