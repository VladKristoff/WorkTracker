"""
«Журнал студента» — все его работы клетками, как в бумажном журнале.
Пропуск отмечен красной буквой «н».
"""
import re
import tkinter as tk
from tkinter import ttk

from styles import font
from utils.dates import iso_to_display
from view.insights import fmt_number
from view.widgets import Debouncer, card

CELL_W, CELL_H, GAP, LABEL_W = 34, 36, 4, 64


def work_title(name):
    return f"Урок {name}" if str(name).isdigit() else str(name)


def short_label(name):
    """«ПР1_ур.17» -> «ПР1», «ДЗ_БД Успев» -> «ДЗ», «Диф. зачет_33» -> «зач»."""
    if str(name).isdigit():
        return str(name)
    match = re.match(r"^\s*(пр|лр|дз)\s*(\d*)", name, re.IGNORECASE)
    if match:
        return match.group(1).upper() + match.group(2)
    return "зач" if re.search(r"зач[её]т", name, re.IGNORECASE) else name[:4]


def journal_lanes(grades, up_to_iso):
    """
    Раскладывает строки repository.get_student_grades по дорожкам журнала.
    Пропуском («н») считается только урок: прошедший до up_to_iso и без оценки —
    то же правило, что в repository.get_missed_lessons.
    """
    lessons, works = [], []
    for r in grades:
        if r["kind"] == "period":
            mark = str(r["grade"]) if r["grade"] is not None else "—"
            tip = (f"Итог периода {r['period']}: сумма {fmt_number(r['total'])}, оценка {mark}"
                   if r["held"] else f"Период {r['period']}: контрольную ещё никто не писал")
            lessons.append({"label": f"П{r['period']}", "value": mark,
                            "state": "total_danger" if r["grade"] == 2 else "total", "tip": tip})
            continue
        missed = False
        if r["ball"] is not None:
            value, state = fmt_number(r["ball"]), "graded"
        elif r["raw"] is not None:
            value, state = str(r["raw"])[:4], "graded"
        elif r["tip"] == "Урок" and r["date"] and r["date"] <= up_to_iso:
            value, state, missed = "н", "missed", True
        else:
            value, state = "", "empty"
        status = ("пропуск" if missed else "оценки нет" if state == "empty"
                  else f"балл {r['raw'] if r['ball'] is None else value}")
        tip = " · ".join(x for x in (iso_to_display(r["date"]), work_title(r["name"]),
                                     status, r["tema"]) if x)
        item = {"label": short_label(r["name"]), "value": value, "state": state, "tip": tip}
        (lessons if r["tip"] == "Урок" else works).append(item)
    return [(title, items) for title, items in (("Уроки", lessons), ("Работы", works)) if items]


class Journal:
    HINT = "Наведите на клетку, чтобы увидеть дату и тему · «н» — пропуск, П — итог периода"

    def __init__(self, parent, palette):
        self.palette = palette
        self.lanes = []
        self.frame = card(parent, padding=(16, 12))
        self.canvas = tk.Canvas(self.frame, height=2 * (CELL_H + GAP), bd=0,
                                bg=palette["surface"], highlightthickness=0)
        self.canvas.pack(fill="x")
        self.info = ttk.Label(self.frame, text=self.HINT, style="CardMuted.TLabel")
        self.info.pack(anchor="w", pady=(8, 0))
        self.canvas.bind("<Configure>", Debouncer(self.canvas, 40, self.draw), add="+")

    def show(self, lanes):
        self.lanes = lanes
        self.draw()

    def draw(self):
        c, p = self.canvas, self.palette
        c.delete("all")
        width = c.winfo_width()
        if width < LABEL_W + CELL_W:
            return
        per_line = max(1, (width - LABEL_W + GAP) // (CELL_W + GAP))
        colors = {  # состояние: (фон, рамка, цвет значения)
            "graded": (p["surface"], p["border"], p["text"]),
            "missed": (p["danger_soft"], p["danger"], p["danger"]),
            "empty": (p["surface_alt"], p["surface_alt"], p["muted"]),
            "total": (p["accent_soft"], p["accent"], p["accent"]),
            "total_danger": (p["danger_soft"], p["danger"], p["danger"]),
        }
        y = 0
        for title, items in self.lanes:
            c.create_text(0, y + CELL_H / 2, anchor="w", text=title, fill=p["muted"],
                          font=font(9))
            for i, item in enumerate(items):
                line, column = divmod(i, per_line)
                x = LABEL_W + column * (CELL_W + GAP)
                top = y + line * (CELL_H + GAP)
                fill, outline, ink = colors[item["state"]]
                tag = f"cell{id(item)}"
                c.create_rectangle(x, top, x + CELL_W, top + CELL_H, fill=fill,
                                   outline=outline, tags=tag)
                c.create_text(x + CELL_W / 2, top + 9, text=item["label"], fill=p["muted"],
                              font=font(7), tags=tag)
                c.create_text(x + CELL_W / 2, top + 25, text=item["value"], fill=ink,
                              font=font(10, True), tags=tag)
                c.tag_bind(tag, "<Enter>",
                           lambda _e, text=item["tip"]: self.info.config(text=text[:150]))
                c.tag_bind(tag, "<Leave>", lambda _e: self.info.config(text=self.HINT))
            y += ((len(items) - 1) // per_line + 1) * (CELL_H + GAP) + GAP
        c.configure(height=max(CELL_H, y - GAP))
