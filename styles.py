"""
Тема приложения: палитры и все ttk-стили.

Принцип: спокойный нейтральный фон и один акцент — «чернильный синий».
Красный и янтарный только означают проблему и нигде не используются для украшения.
"""
from tkinter import ttk

from config import FONT_FAMILY

PALETTES = {
    "light": {
        "bg": "#F6F6F7", "surface": "#FFFFFF", "surface_alt": "#F1F1F3",
        "sidebar": "#ECECEE", "border": "#E0E0E4",
        "text": "#18181B", "text2": "#45474E", "muted": "#66686F",
        "accent": "#24509F", "accent_hover": "#1D4388", "accent_soft": "#E5EBF7",
        "on_accent": "#FFFFFF",
        "danger": "#AE2418", "danger_soft": "#FCECEA",
        "warn": "#7F4E00", "warn_soft": "#FCF1DA",
        "disabled_bg": "#E6E6E9", "disabled_fg": "#98999F",
        "scroll": "#C9CAD0", "scroll_hover": "#A9AAB2",
    },
    "dark": {
        "bg": "#141415", "surface": "#1B1B1D", "surface_alt": "#232326",
        "sidebar": "#0F0F10", "border": "#2D2D31",
        "text": "#EDEDEE", "text2": "#BCBDC2", "muted": "#909198",
        "accent": "#8DADF5", "accent_hover": "#A5BFFA", "accent_soft": "#232C42",
        "on_accent": "#0D1424",
        "danger": "#FF958C", "danger_soft": "#38201F",
        "warn": "#EDBB62", "warn_soft": "#332916",
        "disabled_bg": "#26262A", "disabled_fg": "#66676E",
        "scroll": "#3C3C42", "scroll_hover": "#56565E",
    },
}

ROW_HEIGHT = 32


def font(size=10, bold=False):
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def configure_tree_tags(tree, p):
    """Цвета строк таблиц. Проблемные строки подсвечиваются, остальные чередуются."""
    tree.tag_configure("odd", background=p["surface"], foreground=p["text"])
    tree.tag_configure("even", background=p["surface_alt"], foreground=p["text"])
    tree.tag_configure("empty", background=p["surface"], foreground=p["muted"])
    tree.tag_configure("danger", background=p["danger_soft"], foreground=p["danger"])
    tree.tag_configure("warn", background=p["warn_soft"], foreground=p["warn"])
    tree.tag_configure("total", background=p["accent_soft"], foreground=p["text"],
                       font=font(10, True))
    tree.tag_configure("total_danger", background=p["danger_soft"], foreground=p["danger"],
                       font=font(10, True))


def _button(style, name, *, bg, hover, fg, p, border=None, padding=(14, 7),
            bold=False, anchor="center"):
    edge = border or bg
    style.configure(name, font=font(10, bold), padding=padding, anchor=anchor, width=0,
                    background=bg, foreground=fg, borderwidth=1, relief="flat",
                    bordercolor=edge, lightcolor=bg, darkcolor=bg, focuscolor=fg)
    states = [("disabled", p["disabled_bg"]), ("pressed", hover), ("active", hover)]
    style.map(name, background=states, lightcolor=states, darkcolor=states,
              # рамка акцентного цвета показывает фокус при управлении с клавиатуры
              bordercolor=[("disabled", p["disabled_bg"]), ("focus", p["accent"]),
                           ("active", border or hover)],
              foreground=[("disabled", p["disabled_fg"])],
              relief=[("pressed", "flat")])


def set_styles(root, theme="light"):
    """Применяет тему ко всем ttk-стилям и возвращает палитру (dict)."""
    p = PALETTES[theme]
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=p["bg"], foreground=p["text"], font=font(),
                    troughcolor=p["border"], focuscolor=p["accent"])

    # --- Фреймы ---
    for name, color in (("TFrame", "bg"), ("Surface.TFrame", "surface"),
                        ("Sidebar.TFrame", "sidebar"), ("Line.TFrame", "border")):
        style.configure(name, background=p[color])
    style.configure("Card.TFrame", background=p["surface"], relief="solid", borderwidth=1,
                    bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"])

    # --- Надписи ---
    labels = {
        # имя: (фон, цвет текста, размер, жирный)
        "TLabel": ("bg", "text", 10, False),
        "Muted.TLabel": ("bg", "muted", 9, False),
        "Title.TLabel": ("bg", "text", 18, True),
        "Hero.TLabel": ("bg", "text", 28, True),
        "Lead.TLabel": ("bg", "text2", 12, False),
        "Card.TLabel": ("surface", "text", 10, False),
        "CardTitle.TLabel": ("surface", "text", 11, True),
        "CardMuted.TLabel": ("surface", "muted", 9, False),
        "CardError.TLabel": ("surface", "danger", 9, False),
        "Value.TLabel": ("surface", "text", 20, True),
        "Brand.TLabel": ("sidebar", "text", 13, True),
        "Side.TLabel": ("sidebar", "text2", 10, False),
        "SideMuted.TLabel": ("sidebar", "muted", 9, False),
    }
    for name, (bg, fg, size, bold) in labels.items():
        style.configure(name, background=p[bg], foreground=p[fg], font=font(size, bold))

    # --- Кнопки ---
    _button(style, "Primary.TButton", bg=p["accent"], hover=p["accent_hover"],
            fg=p["on_accent"], p=p, bold=True)
    _button(style, "TButton", bg=p["surface"], hover=p["surface_alt"], fg=p["text"],
            border=p["border"], p=p)
    _button(style, "Quiet.TButton", bg=p["bg"], hover=p["surface_alt"], fg=p["text2"],
            p=p, padding=(10, 6))
    _button(style, "Nav.TButton", bg=p["sidebar"], hover=p["surface_alt"], fg=p["text2"],
            p=p, padding=(12, 8), anchor="w")
    _button(style, "NavActive.TButton", bg=p["surface"], hover=p["surface"], fg=p["accent"],
            border=p["border"], p=p, padding=(12, 8), bold=True, anchor="w")
    _button(style, "Chip.TButton", bg=p["bg"], hover=p["surface_alt"], fg=p["text2"],
            border=p["border"], p=p, padding=(12, 6))
    _button(style, "ChipActive.TButton", bg=p["accent_soft"], hover=p["accent_soft"],
            fg=p["accent"], border=p["accent"], p=p, padding=(12, 6), bold=True)

    # --- Поля ввода ---
    edge = dict(bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"])
    focus = [("focus", p["accent"])]
    for name in ("TEntry", "Invalid.TEntry"):
        color = p["danger"] if name.startswith("Invalid") else p["border"]
        style.configure(name, fieldbackground=p["surface"], foreground=p["text"],
                        insertcolor=p["text"], padding=(8, 6), borderwidth=1,
                        bordercolor=color, lightcolor=p["surface"], darkcolor=p["surface"])
        style.map(name, bordercolor=focus)
    style.configure("TCombobox", fieldbackground=p["surface"], background=p["surface"],
                    foreground=p["text"], arrowcolor=p["text2"], insertcolor=p["text"],
                    padding=(8, 6), borderwidth=1, **edge)
    style.map("TCombobox", fieldbackground=[("readonly", p["surface"])],
              foreground=[("readonly", p["text"])],
              selectbackground=[("readonly", p["surface"])],
              selectforeground=[("readonly", p["text"])],
              bordercolor=focus)
    # Выпадающий список комбобокса — обычный tk.Listbox, красим через option database
    root.option_add("*TCombobox*Listbox.background", p["surface"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["on_accent"])
    root.option_add("*TCombobox*Listbox.font", font())

    style.configure("Card.TCheckbutton", background=p["surface"], foreground=p["text"],
                    focuscolor=p["accent"], indicatorbackground=p["surface"],
                    indicatorforeground=p["on_accent"])
    style.map("Card.TCheckbutton", background=[("active", p["surface"])],
              indicatorbackground=[("selected", p["accent"])])

    # --- Таблицы ---
    style.configure("Treeview", background=p["surface"], fieldbackground=p["surface"],
                    foreground=p["text"], rowheight=ROW_HEIGHT, borderwidth=0, relief="flat")
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.map("Treeview", background=[("selected", p["accent"])],
              foreground=[("selected", p["on_accent"])])
    style.configure("Treeview.Heading", background=p["surface"], foreground=p["muted"],
                    font=font(9, True), relief="flat", padding=(8, 8), borderwidth=1,
                    bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"])
    style.map("Treeview.Heading", background=[("active", p["surface_alt"])],
              foreground=[("active", p["text"])])

    # --- Прокрутка и индикатор загрузки ---
    style.layout("Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Vertical.TScrollbar", background=p["scroll"], troughcolor=p["surface"],
                    bordercolor=p["surface"], lightcolor=p["scroll"], darkcolor=p["scroll"],
                    arrowsize=12, relief="flat", borderwidth=0, gripcount=0)
    hover = [("active", p["scroll_hover"])]
    style.map("Vertical.TScrollbar", background=hover, lightcolor=hover, darkcolor=hover)
    style.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["border"],
                    bordercolor=p["border"], lightcolor=p["accent"], darkcolor=p["accent"],
                    thickness=4)
    return p
