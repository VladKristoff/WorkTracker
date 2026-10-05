from tkinter import *
from app import AppWorkTracer

from view.main_menu import MainMenu

if __name__ == "__main__":
    root = Tk()
    app = AppWorkTracer(root)

    app.register_page("main_menu", MainMenu)

    app.show_window("main_menu")

    root.mainloop()