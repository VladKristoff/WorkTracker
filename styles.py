from tkinter import *
from tkinter import ttk

def set_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Большая надпись
    style.configure("BigLabel.TLabel",
                    foreground="Black",
                    font=("Arial Rounded MT Bold", 48),
                    background="#ffffff")

    # Большая кнопка
    style.configure("BlueButton.TButton",
                    font=("Inter", 12, "bold"),
                    padding=(30, 22),
                    anchor="center",
                    width=15,
                    cursor="hand2")

    # Эффект при наведении
    style.map("BlueButton.TButton",
              background=[("active", "#bababa"), ("pressed", "#212121")],
              foreground=[("active", "Black"), ("pressed", "#e0e0e0")],
              relief=[("pressed", "flat")]
              )
