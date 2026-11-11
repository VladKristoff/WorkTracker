import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from utils.excel_template import TemplateConfig, validate, save_template
from utils.settings import load_settings, save_setting


class ExcelBuilderPage:
    """Конструктор: преподаватель задаёт размеры журнала, программа создаёт пустой xlsx."""

    # поле -> (подпись, значение по умолчанию, ширина поля)
    COUNTS = [
        ("students", "Студентов в группе"),
        ("total_lessons", "Всего занятий"),
        ("periods", "Периодов (столбцов «оценка N»)"),
        ("period_size", "Занятий в одном периоде"),
        ("practical", "Практических работ"),
        ("laboratory", "Лабораторных работ"),
        ("homework", "Столбцов «ДЗ»"),
        ("rows_per_lesson", "Строк на занятие в «Даты_темы»"),
    ]
    TEXTS = [("group", "Группа"), ("discipline", "Дисциплина"),
             ("teacher", "Преподаватель"), ("semester", "Семестр")]
    CHECKS = [("extra_tasks", "Блок «доп.задания» (STEPIC, доп.баллы)"),
              ("exam", "Столбец «Диф. зачет»"),
              ("legend", "Справочник баллов под таблицей"),
              ("subgroups", "Лабораторные в двух подгруппах")]
    SCALES = [("period_5", "5 при сумме ≥"), ("period_4", "4 при сумме >"), ("period_3", "3 при сумме >"),
              ("final_5", "5 при итоге ≥"), ("final_4", "4 при итоге ≥"), ("final_3", "3 при итоге ≥")]

    def __init__(self, main_frame, app):
        self.main_frame = main_frame
        self.app = app
        defaults = TemplateConfig()
        self.vars = {}
        for name, _ in self.TEXTS:
            self.vars[name] = tk.StringVar(value=getattr(defaults, name))
        for name, _ in self.COUNTS + self.SCALES:
            self.vars[name] = tk.StringVar(value=f"{getattr(defaults, name):g}")
        for name, _ in self.CHECKS:
            self.vars[name] = tk.BooleanVar(value=getattr(defaults, name))
        for var in self.vars.values():
            var.trace_add("write", lambda *_: self.update_summary())

        self.create_widgets()
        self.update_summary()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self.main_frame, style="Header.TFrame")
        header.pack(fill="x", side="top")
        ttk.Button(header, text="←  Назад", cursor="hand2", style="HeaderGhost.TButton",
                   command=lambda: self.app.show_window("main_menu")).pack(side="left", padx=(14, 0), pady=10)
        ttk.Label(header, text="Создание Excel-файла", style="Header.TLabel").pack(side="left", padx=16)
        self.theme_btn = ttk.Button(header, text=self.app.theme_icon, width=3, cursor="hand2",
                                    style="HeaderGhost.TButton", command=self.app.toggle_theme)
        self.theme_btn.pack(side="right", padx=14)
        ttk.Frame(self.main_frame, style="Line.TFrame", height=1).pack(fill="x", side="top")

        # Нижняя панель с итогом и кнопкой создаётся раньше контента, чтобы не уезжала за край окна
        bottom = ttk.Frame(self.main_frame, style="Surface.TFrame", padding=(20, 14))
        bottom.pack(fill="x", side="bottom")
        ttk.Frame(self.main_frame, style="Line.TFrame", height=1).pack(fill="x", side="bottom")
        self.create_btn = ttk.Button(bottom, text="Создать файл…", cursor="hand2",
                                     style="MainButton.TButton", command=self.create_file)
        self.create_btn.pack(side="right")
        texts = ttk.Frame(bottom, style="Surface.TFrame")
        texts.pack(side="left", fill="x", expand=True)
        self.summary_label = ttk.Label(texts, style="Card.TLabel", justify="left", wraplength=900)
        self.summary_label.pack(anchor="w")
        self.error_label = ttk.Label(texts, style="CardHint.TLabel", justify="left", wraplength=900)
        self.error_label.pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self.main_frame)
        content.pack(fill="both", expand=True, padx=20, pady=(18, 14))
        ttk.Label(content, style="Hint.TLabel", wraplength=1000, justify="left",
                  text="Укажите размеры журнала — программа создаст пустой файл с теми же листами, что в "
                       "примере: «Баллы, оценки», «Чек-лист» и «Даты_темы». Останется вписать данные."
                  ).pack(anchor="w", pady=(0, 12))

        columns = ttk.Frame(content)
        columns.pack(fill="both", expand=True)
        for c in range(3):
            columns.columnconfigure(c, weight=1, uniform="cards")
        columns.rowconfigure(0, weight=1)

        self._card(columns, 0, "О дисциплине", [(n, t, "text") for n, t in self.TEXTS[:4]]
                   + [("students", "Студентов в группе", "count")])
        self._card(columns, 1, "Состав занятий",
                   [(n, t, "count") for n, t in self.COUNTS[1:]])

        right = ttk.Frame(columns, style="Card.TFrame", padding=16)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        ttk.Label(right, text="Дополнительно", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        for name, text in self.CHECKS:
            ttk.Checkbutton(right, text=text, variable=self.vars[name], style="Card.TCheckbutton",
                            cursor="hand2").pack(anchor="w", pady=3)
        ttk.Label(right, text="Шкала оценок", style="CardTitle.TLabel").pack(anchor="w", pady=(14, 2))
        ttk.Label(right, style="CardHint.TLabel", justify="left", wraplength=300,
                  text="Пороги для формул: оценка периода (сумма баллов за период) и итоговая оценка."
                  ).pack(anchor="w", pady=(0, 6))
        grid = ttk.Frame(right, style="Surface.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)
        for k, (name, text) in enumerate(self.SCALES):
            col = 0 if k < 3 else 2
            row = k % 3
            ttk.Label(grid, text=text, style="Card.TLabel").grid(row=row, column=col, sticky="w",
                                                                  padx=(0 if col == 0 else 14, 6), pady=3)
            ttk.Entry(grid, textvariable=self.vars[name], width=6, justify="center"
                      ).grid(row=row, column=col + 1, sticky="e", pady=3)

    def _card(self, parent, column, title, fields):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 8))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        for name, text, kind in fields:
            if kind == "count":
                row = ttk.Frame(card, style="Surface.TFrame")
                row.pack(fill="x", pady=4)
                ttk.Label(row, text=text, style="Card.TLabel").pack(side="left")
                ttk.Entry(row, textvariable=self.vars[name], width=6, justify="center").pack(side="right")
            else:
                ttk.Label(card, text=text, style="CardHint.TLabel").pack(anchor="w", pady=(6, 0))
                ttk.Entry(card, textvariable=self.vars[name]).pack(fill="x", pady=(2, 0))

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------

    def read_config(self):
        """Собирает TemplateConfig из полей. Возвращает (config, ошибка_ввода)."""
        values = {}
        for name, title in self.COUNTS:
            raw = self.vars[name].get().strip()
            if not re.fullmatch(r"\d+", raw):
                return None, f"«{title}»: нужно целое неотрицательное число."
            values[name] = int(raw)
        for name, title in self.SCALES:
            raw = self.vars[name].get().strip().replace(",", ".")
            try:
                values[name] = float(raw)
            except ValueError:
                return None, f"Шкала оценок («{title}»): нужно число."
        for name, _ in self.TEXTS:
            values[name] = self.vars[name].get().strip()
        for name, _ in self.CHECKS:
            values[name] = bool(self.vars[name].get())
        return TemplateConfig(**values), None

    def update_summary(self):
        cfg, problem = self.read_config()
        if cfg is None:
            self.summary_label.config(text="")
            self.error_label.config(text=problem, foreground=self.app.palette["low_fg"])
            self.create_btn.state(["disabled"])
            return
        errors = validate(cfg)
        if errors:
            self.summary_label.config(text="")
            self.error_label.config(text=errors[0], foreground=self.app.palette["low_fg"])
            self.create_btn.state(["disabled"])
            return
        parts = [f"{cfg.period_lessons} занятий в {cfg.periods} периодах"] if cfg.periods else []
        if cfg.practical:
            parts.append(f"{cfg.practical} ПР")
        if cfg.laboratory:
            parts.append(f"{cfg.laboratory} ЛР")
        if cfg.rest_lessons:
            parts.append(f"{cfg.rest_lessons} прочих занятий")
        self.summary_label.config(
            text=f"Студентов: {cfg.students}. Занятия ({cfg.total_lessons}): " + " + ".join(parts) + ".")
        self.error_label.config(text="", foreground=self.app.palette["muted"])
        self.create_btn.state(["!disabled"])

    @staticmethod
    def _file_name(cfg):
        base = "_".join(x for x in (cfg.group, cfg.discipline) if x) or "Журнал успеваемости"
        return re.sub(r'[\\/:*?"<>|]+', "", base).strip() + ".xlsx"

    def create_file(self):
        cfg, problem = self.read_config()
        if cfg is None:
            messagebox.showerror("Проверьте поля", problem)
            return
        errors = validate(cfg)
        if errors:
            messagebox.showerror("Проверьте поля", "\n".join(errors))
            return

        last_dir = load_settings().get("last_template_dir")
        path = filedialog.asksaveasfilename(
            title="Сохранить файл", defaultextension=".xlsx", filetypes=[("Excel файлы", "*.xlsx")],
            initialfile=self._file_name(cfg),
            initialdir=last_dir if last_dir and os.path.isdir(last_dir) else None)
        if not path:
            return
        try:
            save_template(cfg, path)
        except (OSError, ValueError) as e:
            messagebox.showerror("Не удалось создать файл", str(e))
            return
        save_setting("last_template_dir", os.path.dirname(path))
        messagebox.showinfo(
            "Файл создан",
            f"Структура сохранена:\n{path}\n\nОткройте его в Excel, впишите студентов, даты, темы и "
            f"баллы, сохраните — и загрузите в программу кнопкой «Загрузить файл».")

    def on_theme_changed(self):
        self.theme_btn.config(text=self.app.theme_icon)
        self.update_summary()
