from tkinter import *
from tkinter import ttk

def set_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Большая синяя надпись
    style.configure("BigBlueLabel.TLabel",
                    foreground="#279ef9",
                    font=("Arial Rounded MT Bold", 48),
                    background="#ffffff")

    # Большая синяя кнопка
    style.configure("BlueButton.TButton",
                    background="#1976D2",
                    foreground="#ffffff",
                    font=("Inter", 24, "bold"),
                    borderwidth=0,
                    focusthickness=0,
                    focuscolor="none",
                    relief="flat",
                    padding=(30, 22),  # внутренние отступы — кнопка становится крупнее
                    anchor="center",
                    width=15,
                    cursor="hand2"  # курсор-рука при наведении
                    )

    # Эффект при наведении
    style.map("BlueButton.TButton",
              background=[("active", "#1a8ae0"), ("pressed", "#1274c4")],
              foreground=[("active", "#ffffff"), ("pressed", "#e0e0e0")],
              relief=[("pressed", "flat")]
              )
