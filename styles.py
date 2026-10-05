from tkinter import *
from tkinter import ttk

def set_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Большая синяя надпись
    style.configure("BigBlueLabel.TLabel",
                    foreground="#279ef9",
                    font=("Inter", 48, "bold"),
                    background="#ffffff")
