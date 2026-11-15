from tkinter import ttk

from config import FONT_FAMILY

# ----------------------------------------------------------------------
# Палитры.
# Светлая: индиго + голубовато-лавандовый фон, цветные карточки и насыщенная шапка.
# Тёмная: нейтральный графит/чёрный без зелёных и синих оттенков, один холодный акцент.
# Все прежние ключи сохранены, поэтому остальной код менять не нужно.
# ----------------------------------------------------------------------
PALETTES = {
    "light": {
        "bg": "#D9E0F5",           # фон окна — насыщенный лавандово-голубой
        "surface": "#F4F6FF",      # карточки — слегка подкрашенные, не чисто белые
        "surface_alt": "#E6EBFC",  # полосатые строки, шапка таблицы
        "header": "#312E81",       # шапка — глубокий индиго
        "header_fg": "#FFFFFF",
        "header_hover": "#4338CA",
        "header_press": "#4F46E5",
        "header_tab": "#27256B",   # «дорожка» вкладок в шапке
        "header_tab_fg": "#C7D2FE",
        "border": "#AEB9E6",
        "text": "#14183B",
        "muted": "#5B6490",
        "accent": "#4F46E5",
        "accent_hover": "#4338CA",
        "accent_active": "#312E81",
        "on_accent": "#FFFFFF",
        "accent_soft": "#C7D2FE",
        "mint": "#0D9488",
        "input_bg": "#FFFFFF",
        "btn2": "#CBD5F3",
        "btn2_hover": "#B9C5EC",
        "btn2_active": "#A5B3E4",
        "disabled_bg": "#C3CBE6",
        "disabled_fg": "#EEF1FC",
        "scroll": "#A5B3E4",
        "scroll_hover": "#7F8FD3",
        "select_bg": "#C7D2FE",
        "select_fg": "#1E1B4B",
        "low_bg": "#FECACA",       # красная подсветка
        "low_fg": "#991B1B",
        "warn_bg": "#FDE68A",      # янтарная подсветка
        "warn_fg": "#78350F",
        "worst_bg": "#FBCFE8",     # розовая подсветка
        "worst_fg": "#9D174D",
        "deco1": "#C3CDF2",
        "deco2": "#F0CFF5",
    },
    "dark": {
        "bg": "#121214",
        "surface": "#1C1C1F",
        "surface_alt": "#232327",
        "header": "#09090B",
        "header_fg": "#F2F2F4",
        "header_hover": "#222226",
        "header_press": "#2E2E33",
        "header_tab": "#1A1A1D",
        "header_tab_fg": "#9A9AA3",
        "border": "#303035",
        "text": "#ECECEF",
        "muted": "#9A9AA3",
        "accent": "#7C86FF",
        "accent_hover": "#939BFF",
        "accent_active": "#6670F0",
        "on_accent": "#0B0B10",
        "accent_soft": "#2D2F45",
        "mint": "#A3A3AD",
        "input_bg": "#141416",
        "btn2": "#2A2A2F",
        "btn2_hover": "#34343A",
        "btn2_active": "#40404A",
        "disabled_bg": "#26262A",
        "disabled_fg": "#5E5E67",
        "scroll": "#3D3D44",
        "scroll_hover": "#55555E",
        "select_bg": "#33364F",
        "select_fg": "#FFFFFF",
        "low_bg": "#3D1F24",
        "low_fg": "#FCA5A5",
        "warn_bg": "#3A301A",
        "warn_fg": "#FCD34D",
        "worst_bg": "#47202F",
        "worst_fg": "#FDA4AF",
        "deco1": "#18181B",
        "deco2": "#1F1F23",
    },
}

ROW_HEIGHT = 30  # высота строки таблиц (было 38) — компактнее, влезает больше студентов


def configure_tree_tags(tree, p):
    """Цвета строк таблицы: чередование и подсветка. Вызывать при смене темы."""
    tree.tag_configure("odd", background=p["surface"])
    tree.tag_configure("even", background=p["surface_alt"])
    tree.tag_configure("low_score", background=p["low_bg"], foreground=p["low_fg"])
    tree.tag_configure("many_absences", background=p["warn_bg"], foreground=p["warn_fg"])
    # 5 худших по баллу — всегда, жирным и отдельным цветом
    tree.tag_configure("worst_five", background=p["worst_bg"], foreground=p["worst_fg"],
                       font=(FONT_FAMILY, 10, "bold"))


def _button(style, name, *, bg, hover, pressed, fg, fg_pressed=None,
            disabled_bg, disabled_fg, font, padding, width=0):
    flat = dict(borderwidth=0, relief="flat")
    style.configure(name, font=font, padding=padding, anchor="center", width=width,
                    background=bg, foreground=fg, focuscolor=bg,
                    bordercolor=bg, lightcolor=bg, darkcolor=bg, **flat)
    # «pressed» должен стоять раньше «active», иначе нажатие не будет видно
    states = [("disabled", disabled_bg), ("pressed", pressed), ("active", hover)]
    style.map(name,
              background=states, bordercolor=states, lightcolor=states, darkcolor=states,
              foreground=[("disabled", disabled_fg), ("pressed", fg_pressed or fg),
                          ("active", fg)],
              relief=[("pressed", "flat")])


def set_styles(root, theme="light"):
    """Применяет тему ко всем ttk-стилям и возвращает палитру (dict)."""
    p = PALETTES[theme]
    F = FONT_FAMILY
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=p["bg"], foreground=p["text"], font=(F, 10),
                    troughcolor=p["border"], focuscolor=p["accent"])

    # --- Фреймы ---
    style.configure("TFrame", background=p["bg"])
    style.configure("Surface.TFrame", background=p["surface"])
    style.configure("Card.TFrame", background=p["surface"], relief="solid", borderwidth=1,
                    bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"])
    style.configure("Header.TFrame", background=p["header"])
    style.configure("Line.TFrame", background=p["border"])
    style.configure("TLabelframe", background=p["surface"], bordercolor=p["border"],
                    lightcolor=p["border"], darkcolor=p["border"])
    style.configure("TLabelframe.Label", background=p["surface"], foreground=p["text"],
                    font=(F, 10, "bold"))

    # --- Надписи ---
    style.configure("TLabel", background=p["bg"], foreground=p["text"])
    style.configure("Card.TLabel", background=p["surface"])
    style.configure("CardTitle.TLabel", background=p["surface"], font=(F, 10, "bold"))
    style.configure("CardHint.TLabel", background=p["surface"], foreground=p["muted"],
                    font=(F, 9))
    style.configure("Value.TLabel", background=p["surface"], foreground=p["accent"],
                    font=(F, 18, "bold"))
    style.configure("Name.TLabel", background=p["surface"], font=(F, 15, "bold"))
    style.configure("Subtitle.TLabel", background=p["surface"], foreground=p["muted"],
                    font=(F, 10))
    style.configure("Header.TLabel", background=p["header"], foreground=p["header_fg"],
                    font=(F, 12, "bold"))
    style.configure("BigLabel.TLabel", background=p["surface"], foreground=p["accent"],
                    font=(F, 30, "bold"))
    style.configure("SmallLabel.TLabel", background=p["bg"], font=(F, 11, "bold"))
    style.configure("Hint.TLabel", background=p["bg"], foreground=p["muted"], font=(F, 9))

    # --- Поля ввода ---
    focus = [("focus", p["accent"])]
    style.configure("TEntry", fieldbackground=p["input_bg"], foreground=p["text"],
                    insertcolor=p["text"], padding=(8, 5), borderwidth=1,
                    bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"])
    style.map("TEntry", bordercolor=focus, lightcolor=focus, darkcolor=focus)

    style.configure("TCombobox", fieldbackground=p["input_bg"], background=p["btn2"],
                    foreground=p["text"], arrowcolor=p["muted"], insertcolor=p["text"],
                    padding=(8, 5), borderwidth=1, bordercolor=p["border"],
                    lightcolor=p["border"], darkcolor=p["border"])
    style.map("TCombobox",
              fieldbackground=[("readonly", p["input_bg"])],
              foreground=[("readonly", p["text"])],
              background=[("active", p["btn2_hover"]), ("readonly", p["btn2"])],
              bordercolor=focus, lightcolor=focus, darkcolor=focus,
              arrowcolor=[("active", p["accent"])])
    # Выпадающий список комбобокса — обычный tk.Listbox, красим через option database
    root.option_add("*TCombobox*Listbox.background", p["input_bg"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["on_accent"])
    root.option_add("*TCombobox*Listbox.font", (F, 10))

    # --- Флажки на карточках ---
    style.configure("Card.TCheckbutton", background=p["surface"], foreground=p["text"],
                    focuscolor=p["surface"], indicatorbackground=p["input_bg"],
                    indicatorforeground=p["accent"], font=(F, 10))
    style.map("Card.TCheckbutton", background=[("active", p["surface"])],
              indicatorbackground=[("selected", p["accent"]), ("active", p["accent_soft"])],
              indicatorforeground=[("selected", p["on_accent"])])

    # --- Таблицы ---
    style.configure("Treeview", background=p["surface"], fieldbackground=p["surface"],
                    foreground=p["text"], rowheight=ROW_HEIGHT, borderwidth=0, relief="flat",
                    font=(F, 10))
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # без рамки
    style.map("Treeview", background=[("selected", p["select_bg"])],
              foreground=[("selected", p["select_fg"])])
    style.configure("Treeview.Heading", background=p["accent_soft"], foreground=p["text"],
                    font=(F, 10, "bold"), relief="flat", padding=(10, 7), borderwidth=1,
                    bordercolor=p["border"], lightcolor=p["accent_soft"],
                    darkcolor=p["accent_soft"])
    style.map("Treeview.Heading", background=[("active", p["accent"])],
              foreground=[("active", p["on_accent"])])

    # --- Полоса прокрутки: тонкая, без стрелок ---
    style.layout("Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Vertical.TScrollbar", background=p["scroll"], troughcolor=p["surface"],
                    bordercolor=p["surface"], lightcolor=p["scroll"], darkcolor=p["scroll"],
                    arrowsize=12, relief="flat", borderwidth=0, gripcount=0)
    hover = [("active", p["scroll_hover"])]
    style.map("Vertical.TScrollbar", background=hover, lightcolor=hover, darkcolor=hover)

    # --- Индикатор загрузки ---
    style.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["border"],
                    bordercolor=p["border"], lightcolor=p["accent"], darkcolor=p["accent"],
                    thickness=6)

    # --- Кнопки ---
    primary = dict(bg=p["accent"], hover=p["accent_hover"], pressed=p["accent_active"],
                   fg=p["on_accent"], disabled_bg=p["disabled_bg"], disabled_fg=p["disabled_fg"])
    _button(style, "BlueButton.TButton", font=(F, 11, "bold"), padding=(24, 11), width=22, **primary)
    _button(style, "MainButton.TButton", font=(F, 10, "bold"), padding=(14, 8), **primary)

    secondary = dict(bg=p["btn2"], hover=p["btn2_hover"], pressed=p["btn2_active"],
                     fg=p["text"], disabled_bg=p["btn2"], disabled_fg=p["disabled_fg"])
    _button(style, "Secondary.TButton", font=(F, 10, "bold"), padding=(12, 7), **secondary)
    _button(style, "TButton", font=(F, 10), padding=(12, 7), **secondary)

    # «Призрачные» кнопки: на фоне окна и на фоне цветной шапки
    _button(style, "Ghost.TButton", bg=p["bg"], hover=p["btn2_hover"], pressed=p["btn2_active"],
            fg=p["text"], disabled_bg=p["bg"], disabled_fg=p["disabled_fg"],
            font=(F, 10, "bold"), padding=(10, 6))
    _button(style, "HeaderGhost.TButton", bg=p["header"], hover=p["header_hover"],
            pressed=p["header_press"], fg=p["header_fg"], disabled_bg=p["header"],
            disabled_fg=p["header_tab_fg"], font=(F, 10, "bold"), padding=(10, 6))
    style.configure("ArrowButton.TButton", font=(F, 12, "bold"))  # совместимость со старым кодом

    # --- Вкладки в шапке: сегментированный переключатель ---
    style.configure("TabsBar.TFrame", background=p["header_tab"], relief="flat", borderwidth=0)
    _button(style, "TabActive.TButton", bg=p["surface"], hover=p["surface"], pressed=p["surface"],
            fg=p["accent"], disabled_bg=p["surface"], disabled_fg=p["disabled_fg"],
            font=(F, 10, "bold"), padding=(16, 6))
    _button(style, "Tab.TButton", bg=p["header_tab"], hover=p["header_hover"],
            pressed=p["header_press"], fg=p["header_tab_fg"], fg_pressed=p["header_fg"],
            disabled_bg=p["header_tab"], disabled_fg=p["disabled_fg"],
            font=(F, 10, "bold"), padding=(16, 6))
    style.map("Tab.TButton", foreground=[("active", p["header_fg"])])

    # --- Пункты списка диаграмм (боковая панель) ---
    _button(style, "ChartItemActive.TButton", bg=p["accent_soft"], hover=p["accent_soft"],
            pressed=p["accent_soft"], fg=p["accent"], disabled_bg=p["accent_soft"],
            disabled_fg=p["disabled_fg"], font=(F, 10, "bold"), padding=(10, 8))
    _button(style, "ChartItem.TButton", bg=p["surface"], hover=p["surface_alt"],
            pressed=p["surface_alt"], fg=p["text"], disabled_bg=p["surface"],
            disabled_fg=p["disabled_fg"], font=(F, 10), padding=(10, 8))

    return p