from tkinter import *
from tkinter import ttk


def set_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # --- ПАЛИТРА С АКЦЕНТАМИ (Indigo & Mint) ---
    bg_color = "#FFFFFF"  # Нейтральный фон контента
    header_color = "#EBF5F0"  # Пастельный мятный фон для шапки (Второстепенный акцент)
    text_color = "#1E293B"  # Темно-грифельный текст

    # Главный акцент (Яркий Индиго)
    accent_color = "#4F46E5"
    accent_hover = "#4338CA"  # Цвет при наведении
    accent_active = "#312E81"  # Цвет при нажатии

    # Базовые стили Tkinter-компонентов
    style.configure(".", background=bg_color, foreground=text_color)
    style.configure("TFrame", background=bg_color)
    style.configure("Header.TFrame", background=header_color)

    # --- СТИЛИ ДЛЯ ТАБЛИЦЫ TREEVIEW ---
    style.configure("Treeview",
                    background=bg_color,
                    fieldbackground=bg_color,
                    foreground=text_color,
                    rowheight=32,
                    font=("Inter", 10))

    style.configure("Treeview.Heading",
                    background=header_color,
                    foreground=text_color,
                    font=("Inter", 10, "bold"),
                    relief="flat",
                    padding=(10, 8))

    style.map("Treeview.Heading",
              background=[('active', '#D1FAE5')])  # Мятный чуть темнее при наведении

    # --- ВАШИ СУЩЕСТВУЮЩИЕ СТИЛИ (С акцентными цветами) ---
    style.configure("BigLabel.TLabel",
                    foreground=accent_color,  # Надпись теперь акцентная
                    font=("Arial Rounded MT Bold", 48),
                    background="#ffffff")

    # Большая кнопка (Яркий Индиго)
    style.configure("BlueButton.TButton",
                    font=("Inter", 12, "bold"),
                    padding=(30, 22),
                    anchor="center",
                    width=15,
                    background=accent_color,
                    foreground="#FFFFFF")

    style.map("BlueButton.TButton",
              background=[("active", accent_hover), ("pressed", accent_active)],
              foreground=[("active", "#FFFFFF"), ("pressed", "#E0E7FF")],
              relief=[("pressed", "flat")]
              )

    # Кнопка средних габаритов (Яркий Индиго)
    style.configure("MainButton.TButton",
                    font=("Inter", 12, "bold"),
                    padding=(20, 15),
                    anchor="center",
                    width=20,
                    background=accent_color,
                    foreground="#FFFFFF")

    style.map("MainButton.TButton",
              background=[("active", accent_hover), ("pressed", accent_active)],
              foreground=[("active", "#FFFFFF"), ("pressed", "#E0E7FF")],
              relief=[("pressed", "flat")]
              )

    # Кнопка-стрелка (Сдержанная, чтобы не отвлекать от главных кнопок)
    style.configure("ArrowButton.TButton",
                    font=("Inter", 12, "bold"),
                    padding=(5, 15),
                    anchor="center",
                    width=5,
                    background="#E2E8F0",
                    foreground=text_color)

    style.map("ArrowButton.TButton",
              background=[("active", "#CBD5E1"), ("pressed", "#94A3B8")],
              foreground=[("active", text_color), ("pressed", "#FFFFFF")],
              relief=[("pressed", "flat")]
              )