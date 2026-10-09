from tkinter import *

from styles import set_styles

class AppWorkTracer:
    def __init__(self, root):
        self.root = root
        self.root.title("Work Tracking")
        self.root.geometry("1440x800")
        self.root.resizable(False, False)

        self.icon = PhotoImage(file='images/app_ico.png')
        self.header_logo = None
        root.iconphoto(True, self.icon)

        self.main_frame = Frame(root, background="#ffffff")
        self.main_frame.pack(fill="both", expand=True)

        set_styles(self.root)

        self.pages = {}

        self.current_window = None


    def register_page(self, name, page_class):
        self.pages[name] = page_class


    def show_window(self, name, *args, **kwargs):
        if name not in self.pages:
            print(f"Ошибка: Страница {name} не зарегистрирована!")
            return

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        page_class = self.pages[name]
        self.current_window = page_class(self.main_frame, self, *args, **kwargs)
