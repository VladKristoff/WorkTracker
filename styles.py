from tkinter import ttk

from config import FONT_FAMILY


def set_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # --- Палитра (Indigo & Mint) ---
    bg_color = "#FFFFFF"
    header_color = "#EBF5F0"
    text_color = "#1E293B"

    accent_color = "#4F46E5"
    accent_hover = "#4338CA"
    accent_active = "#312E81"

    style.configure(".", background=bg_color, foreground=text_color, font=(FONT_FAMILY, 10))
    style.configure("TFrame", background=bg_color)
    style.configure("TLabel", background=bg_color)
    style.configure("TLabelframe", background=bg_color)
    style.configure("TLabelframe.Label", background=bg_color, font=(FONT_FAMILY, 10, "bold"))
    style.configure("Header.TFrame", background=header_color)

    # --- Таблицы ---
    style.configure("Treeview", background=bg_color, fieldbackground=bg_color,
                    foreground=text_color, rowheight=32, font=(FONT_FAMILY, 10))
    style.map("Treeview", background=[("selected", "#C7D2FE")],
              foreground=[("selected", text_color)])
    style.configure("Treeview.Heading", background=header_color, foreground=text_color,
                    font=(FONT_FAMILY, 10, "bold"), relief="flat", padding=(10, 8))
    style.map("Treeview.Heading", background=[("active", "#D1FAE5")])

    # --- Надписи ---
    style.configure("BigLabel.TLabel", foreground=accent_color,
                    font=(FONT_FAMILY, 44, "bold"), background=bg_color)
    style.configure("SmallLabel.TLabel", background=bg_color, font=(FONT_FAMILY, 12, "bold"))
    style.configure("Hint.TLabel", background=bg_color, foreground="#8E8E93", font=(FONT_FAMILY, 9))

    # --- Кнопки ---
    for name, font_size, padding, width in (
        ("BlueButton.TButton", 12, (30, 22), 15),
        ("MainButton.TButton", 12, (20, 15), 20),
    ):
        style.configure(name, font=(FONT_FAMILY, font_size, "bold"), padding=padding,
                        anchor="center", width=width, background=accent_color, foreground="#FFFFFF")
        style.map(name,
                  background=[("disabled", "#C7C9D9"), ("active", accent_hover),
                              ("pressed", accent_active)],
                  foreground=[("disabled", "#F1F2F8"), ("active", "#FFFFFF"),
                              ("pressed", "#E0E7FF")],
                  relief=[("pressed", "flat")])

    # Второстепенные кнопки (серые)
    for name, font, padding, width in (
        ("ArrowButton.TButton", (FONT_FAMILY, 12, "bold"), (5, 15), 5),
        ("Secondary.TButton", (FONT_FAMILY, 10, "bold"), (12, 8), 0),
    ):
        style.configure(name, font=font, padding=padding, anchor="center", width=width,
                        background="#E2E8F0", foreground=text_color)
        style.map(name,
                  background=[("disabled", "#F1F5F9"), ("active", "#CBD5E1"), ("pressed", "#94A3B8")],
                  foreground=[("disabled", "#94A3B8"), ("active", text_color), ("pressed", "#FFFFFF")],
                  relief=[("pressed", "flat")])

    style.configure("Horizontal.TProgressbar", background=accent_color, troughcolor="#E2E8F0")
