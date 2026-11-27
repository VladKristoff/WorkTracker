"""Общие элементы интерфейса: из них собраны все страницы."""
import tkinter as tk
from tkinter import ttk

from styles import configure_tree_tags
from utils.settings import save_setting
from view.insights import fmt_number


class Debouncer:
    """Откладывает вызов; при уничтожении виджета отменяет его."""

    def __init__(self, widget, delay_ms, callback):
        self.widget, self.delay, self.callback = widget, delay_ms, callback
        self.job = None
        widget.bind("<Destroy>", self._on_destroy, add="+")

    def __call__(self, *_):
        self.cancel()
        self.job = self.widget.after(self.delay, self._run)

    def _run(self):
        self.job = None
        self.callback()

    def cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _on_destroy(self, event):
        if event.widget is self.widget:
            self.cancel()


def bind_wheel(widget, canvas):
    """Прокрутка canvas колесом мыши, пока курсор над widget (Windows, macOS и Linux)."""

    def scroll(step):
        first, last = canvas.yview()
        if last - first < 1:  # всё помещается — прокручивать нечего
            canvas.yview_scroll(step, "units")

    def enter(_event):
        widget.bind_all("<MouseWheel>", lambda e: scroll(-1 if e.delta > 0 else 1))
        widget.bind_all("<Button-4>", lambda _e: scroll(-1))
        widget.bind_all("<Button-5>", lambda _e: scroll(1))

    def leave(_event=None):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.unbind_all(sequence)

    widget.bind("<Enter>", enter, add="+")
    widget.bind("<Leave>", leave, add="+")
    widget.bind("<Destroy>", leave, add="+")


def page_header(parent, title, subtitle="", back=None):
    """Заголовок страницы. Возвращает рамку для кнопок справа и надпись подзаголовка."""
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 16))
    if back:
        text, command = back
        ttk.Button(header, text=f"←  {text}", style="Quiet.TButton", cursor="hand2",
                   command=command).pack(anchor="w", pady=(0, 4))
    actions = ttk.Frame(header)
    actions.pack(side="right", anchor="s")
    ttk.Label(header, text=title, style="Title.TLabel").pack(anchor="w")
    sub = ttk.Label(header, text=subtitle, style="Muted.TLabel")
    sub.pack(anchor="w", pady=(2, 0))
    return actions, sub


def card(parent, title=None, padding=16):
    """Карточка с рамкой. Размещает её вызывающий код."""
    frame = ttk.Frame(parent, style="Card.TFrame", padding=padding)
    if title:
        frame.title_label = ttk.Label(frame, text=title, style="CardTitle.TLabel")
        frame.title_label.pack(anchor="w", pady=(0, 12))
    return frame


def stat_row(parent, captions):
    """Ряд карточек с крупными числами. Возвращает список (значение, подпись)."""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(0, 16))
    result = []
    for i, caption in enumerate(captions):
        row.columnconfigure(i, weight=1, uniform="stats")
        box = card(row, padding=(16, 12))
        box.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
        cap = ttk.Label(box, text=caption, style="CardMuted.TLabel")
        cap.pack(anchor="w")
        value = ttk.Label(box, text="—", style="Value.TLabel")
        value.pack(anchor="w", pady=(2, 0))
        result.append((value, cap))
    return result


class Segmented(ttk.Frame):
    """Переключатель из кнопок: один выбранный вариант."""

    def __init__(self, parent, options, value, command):
        super().__init__(parent)
        self.value, self.command = value, command
        self.buttons = {}
        for key, text in options:
            button = ttk.Button(self, text=text, cursor="hand2",
                                command=lambda k=key: self.select(k))
            button.pack(side="left", padx=(0, 4))
            self.buttons[key] = button
        self._paint()

    def select(self, key):
        self.value = key
        self._paint()
        self.command(key)

    def set_text(self, key, text):
        self.buttons[key].config(text=text)

    def _paint(self):
        for key, button in self.buttons.items():
            button.config(style="ChipActive.TButton" if key == self.value else "Chip.TButton")


class SearchBox(ttk.Frame):
    """Поле поиска с подсказкой и кнопкой очистки."""

    def __init__(self, parent, variable, placeholder="Поиск по ФИО", width=24):
        super().__init__(parent)
        self.variable = variable
        self.entry = ttk.Entry(self, textvariable=variable, width=width)
        self.entry.pack(side="left")
        self.hint = ttk.Label(self.entry, text=placeholder, style="CardMuted.TLabel",
                              cursor="xterm")
        self.clear = ttk.Button(self, text="✕", style="Quiet.TButton", cursor="hand2",
                                command=lambda: variable.set(""))
        self.hint.bind("<Button-1>", lambda _e: self.focus())
        self.entry.bind("<FocusIn>", lambda _e: self._update(True), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._update(False), add="+")
        self._trace = variable.trace_add("write", lambda *_: self._update())
        self.entry.bind("<Destroy>", lambda _e: variable.trace_remove("write", self._trace),
                        add="+")
        self._focused = False
        self._update()

    def focus(self):
        self.entry.focus_set()

    def _update(self, focused=None):
        if focused is not None:
            self._focused = focused
        filled = bool(self.variable.get())
        if filled or self._focused:
            self.hint.place_forget()
        else:
            self.hint.place(x=9, rely=0.5, anchor="w")
        if filled:
            self.clear.pack(side="left", padx=(4, 0))
        else:
            self.clear.pack_forget()


class DataTable(ttk.Frame):
    """Таблица в карточке: прокрутка, сортировка по заголовкам, открытие строки, пустое состояние."""

    def __init__(self, parent, palette, columns, sortable=(), on_sort=None, on_open=None,
                 on_select=None, empty_text="Ничего не найдено", height=5):
        """columns: [(id, заголовок, ширина, выравнивание, растягивается)]."""
        super().__init__(parent, style="Card.TFrame", padding=1)
        self.titles = {c[0]: c[1] for c in columns}
        self.on_open = on_open
        self.tree = ttk.Treeview(self, columns=list(self.titles), show="headings",
                                 selectmode="browse", height=height)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        for key, title, width, anchor, stretch in columns:
            self.tree.heading(key, text=title, anchor=anchor)
            if key in sortable and on_sort:
                # command задаём отдельно: command=None в новых версиях Python вызывает TclError
                self.tree.heading(key, command=lambda k=key: on_sort(k))
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=stretch)
        configure_tree_tags(self.tree, palette)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.empty = ttk.Label(self, text=empty_text, style="CardMuted.TLabel")
        if on_open:
            self.tree.bind("<Double-1>", self._open)
            self.tree.bind("<Return>", self._open)
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: on_select())

    def _open(self, event):
        # двойной щелчок по заголовку не должен открывать выбранную ранее строку
        if getattr(event, "num", None) == 1 and self.tree.identify_row(event.y) == "":
            return
        if self.selected() is not None:
            self.on_open(self.selected())

    def set_rows(self, rows):
        """rows: [(iid, значения, тег)]."""
        selected = self.selected()
        self.tree.delete(*self.tree.get_children())
        for iid, values, tag in rows:
            self.tree.insert("", "end", iid=str(iid), values=values, tags=(tag,))
        if selected is not None and self.tree.exists(selected):
            self.select(selected)
        if rows:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def selected(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def select(self, iid):
        if self.tree.exists(str(iid)):
            self.tree.selection_set(str(iid))
            self.tree.focus(str(iid))
            self.tree.see(str(iid))

    def ids(self):
        return list(self.tree.get_children())

    def set_arrow(self, column, descending):
        for key, title in self.titles.items():
            arrow = (" ▼" if descending else " ▲") if key == column else ""
            self.tree.heading(key, text=title + arrow)


class ThresholdFields(ttk.Frame):
    """Пороги подсветки. Общие для всех страниц и запоминаются в settings.json."""

    def __init__(self, parent, app, on_change):
        super().__init__(parent)
        self.app, self.on_change = app, on_change
        apply_later = Debouncer(self, 400, self.apply)
        self.fields = []
        for text, attr, key in (("Балл ниже", "low_score", "low_score_threshold"),
                                ("Пропусков больше", "high_absences", "high_absences_threshold")):
            ttk.Label(self, text=text, style="Muted.TLabel").pack(side="left", padx=(12, 6))
            variable = tk.StringVar(value=fmt_number(getattr(app, attr)))
            entry = ttk.Entry(self, textvariable=variable, width=5, justify="center")
            entry.pack(side="left")
            variable.trace_add("write", apply_later)
            self.fields.append((variable, entry, attr, key))

    def apply(self):
        """Некорректный ввод не применяется: поле получает красную рамку."""
        changed = False
        for variable, entry, attr, key in self.fields:
            try:
                value = float(variable.get().strip().replace(",", "."))
                if not 0 <= value < float("inf"):
                    raise ValueError
            except ValueError:
                entry.configure(style="Invalid.TEntry")
                continue
            entry.configure(style="TEntry")
            if value != getattr(self.app, attr):
                setattr(self.app, attr, value)
                save_setting(key, value)
                changed = True
        if changed:
            self.on_change()


class ScrollArea(ttk.Frame):
    """Область с вертикальной прокруткой; содержимое кладётся в .body."""

    def __init__(self, parent, palette):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=palette["bg"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = ttk.Frame(self.canvas)
        window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.body.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        bind_wheel(self, self.canvas)
