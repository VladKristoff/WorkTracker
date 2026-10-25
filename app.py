import tkinter as tk

from config import APP_TITLE, ICON_PATH, WINDOW_SIZE, MIN_WINDOW_SIZE
from styles import set_styles


class AppWorkTracker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)

        # Размер не больше экрана (ноутбуки 1366x768), окно можно менять
        width = min(WINDOW_SIZE[0], root.winfo_screenwidth() - 40)
        height = min(WINDOW_SIZE[1], root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(MIN_WINDOW_SIZE[0], width), min(MIN_WINDOW_SIZE[1], height))
        self.root.resizable(False, False)

        try:
            self.icon = tk.PhotoImage(file=ICON_PATH)
            root.iconphoto(True, self.icon)
        except tk.TclError:
            self.icon = None  # без иконки приложение работает

        self.main_frame = tk.Frame(root, background="#ffffff")
        self.main_frame.pack(fill="both", expand=True)

        set_styles(self.root)

        self.pages = {}
        self.current_window = None

    def register_page(self, name, page_class):
        self.pages[name] = page_class

    def show_window(self, name, *args, **kwargs):
        if name not in self.pages:
            raise KeyError(f"Страница «{name}» не зарегистрирована")

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.current_window = self.pages[name](self.main_frame, self, *args, **kwargs)
