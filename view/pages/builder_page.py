import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from utils.excel_template import TemplateConfig, validate, save_template
from utils.settings import load_settings, save_setting
from view.widgets import ScrollArea, card, page_header


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

    def __init__(self, content, app):
        self.app = app
        # введённые значения сохраняются при переходах между разделами и смене темы
        saved = app.state.setdefault("builder", {})
        defaults = TemplateConfig()
        self.vars = {}
        for name, _ in self.TEXTS:
            self.vars[name] = tk.StringVar(value=saved.get(name, getattr(defaults, name)))
        for name, _ in self.COUNTS + self.SCALES:
            self.vars[name] = tk.StringVar(value=saved.get(name, f"{getattr(defaults, name):g}"))
        for name, _ in self.CHECKS:
            self.vars[name] = tk.BooleanVar(value=saved.get(name, getattr(defaults, name)))
        for name, var in self.vars.items():
            var.trace_add("write", lambda *_, n=name: self.on_change(n))

        self.create_widgets(content)
        self.update_summary()

    def on_change(self, name):
        self.app.state["builder"][name] = self.vars[name].get()
        self.update_summary()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def create_widgets(self, content):
        back = None if self.app.filepath else ("На главный экран", self.go_back)
        page_header(content, "Новый журнал Excel",
                    "Задайте размеры — получится пустой файл с формулами, "
                    "останется вписать данные", back=back)

        # Итог и кнопка создаются раньше формы, чтобы всегда оставаться на экране
        bottom = card(content, padding=(16, 12))
        bottom.pack(fill="x", side="bottom", pady=(12, 0))
        self.create_btn = ttk.Button(bottom, text="Создать файл…", cursor="hand2",
                                     style="Primary.TButton", command=self.create_file)
        self.create_btn.pack(side="right", padx=(16, 0))
        self.summary_label = ttk.Label(bottom, style="Card.TLabel", justify="left",
                                       wraplength=560)
        self.summary_label.pack(anchor="w")
        self.error_label = ttk.Label(bottom, style="CardError.TLabel", justify="left",
                                     wraplength=560)
        self.error_label.pack(anchor="w")

        area = ScrollArea(content, self.app.palette)
        area.pack(fill="both", expand=True)
        for column in range(2):
            area.body.columnconfigure(column, weight=1, uniform="cards")

        about = self._section(area.body, 0, 0, "1. О дисциплине")
        for name, title in self.TEXTS:
            ttk.Label(about, text=title, style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))
            ttk.Entry(about, textvariable=self.vars[name]).pack(fill="x", pady=(4, 4))

        lessons = self._section(area.body, 0, 1, "2. Состав занятий")
        for name, title in self.COUNTS:
            row = ttk.Frame(lessons, style="Surface.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=title, style="Card.TLabel").pack(side="left")
            ttk.Entry(row, textvariable=self.vars[name], width=6,
                      justify="center").pack(side="right")

        extra = self._section(area.body, 1, 0, "3. Дополнительно")
        for name, title in self.CHECKS:
            ttk.Checkbutton(extra, text=title, variable=self.vars[name],
                            style="Card.TCheckbutton", cursor="hand2").pack(anchor="w", pady=4)

        scale = self._section(area.body, 1, 1, "4. Шкала оценок в формулах Excel")
        grid = ttk.Frame(scale, style="Surface.TFrame")
        grid.pack(fill="x")
        for column, heading in enumerate(("За период", "Итоговая")):
            ttk.Label(grid, text=heading, style="CardMuted.TLabel").grid(
                row=0, column=column * 2, columnspan=2, sticky="w", padx=(0, 24))
        for k, (name, title) in enumerate(self.SCALES):
            row, column = k % 3 + 1, (k // 3) * 2
            ttk.Label(grid, text=title, style="Card.TLabel").grid(row=row, column=column,
                                                                   sticky="w", pady=4)
            ttk.Entry(grid, textvariable=self.vars[name], width=5, justify="center").grid(
                row=row, column=column + 1, sticky="w", padx=(8, 24), pady=4)

    @staticmethod
    def _section(parent, row, column, title):
        box = card(parent, title)
        box.grid(row=row, column=column, sticky="nsew",
                 padx=(0, 6) if column == 0 else (6, 0), pady=(0, 12))
        return box

    def go_back(self):
        self.app.show_window("overview_page" if self.app.filepath else "main_menu")

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
            self.error_label.config(text=problem)
            self.create_btn.state(["disabled"])
            return
        errors = validate(cfg)
        if errors:
            self.summary_label.config(text="")
            self.error_label.config(text=errors[0])
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
        self.error_label.config(text="")
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
            f"баллы, сохраните — и откройте в программе (Ctrl+O).")
