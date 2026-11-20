"""
Экспорт в PDF (reportlab). Модуль не зависит от tkinter и базы данных: получает готовые данные,
поэтому его можно проверять отдельно.

Шрифт с кириллицей берётся из системы (Segoe UI / Arial в Windows, DejaVu / Liberation в Linux),
отдельный файл шрифта в проект добавлять не нужно.
"""
import math
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from utils.dates import iso_to_display

# Кандидаты на шрифт: (обычный, жирный). Берётся первая пара, где найдены оба файла.
_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]
FONT, FONT_BOLD = "WT-Regular", "WT-Bold"

# Цвета — из палитры приложения (светлая тема)
ACCENT = colors.HexColor("#4F46E5")
ACCENT_SOFT = colors.HexColor("#E0E7FF")
TEXT = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
STRIPE = colors.HexColor("#F8FAFC")
LOW_BG = colors.HexColor("#FEE2E2")
LOW_FG = colors.HexColor("#991B1B")


def _register_fonts():
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(FONT, regular))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold))
            pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD,
                                          italic=FONT, boldItalic=FONT_BOLD)
            return
    raise RuntimeError("Не найден шрифт с поддержкой кириллицы (Segoe UI или Arial). "
                       "Установите один из них в систему.")


def fmt_number(value, empty="—"):
    return empty if value is None else f"{value:g}"


def _lesson_name(name):
    return f"Урок {name}" if str(name).isdigit() else str(name)


def _esc(text):
    """Экранирует служебные символы разметки Paragraph."""
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _styles():
    base = dict(fontName=FONT, textColor=TEXT, leading=13)
    return {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=9, textColor=MUTED, leading=12),
        "name": ParagraphStyle("name", fontName=FONT_BOLD, fontSize=20, textColor=TEXT, leading=24),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=10, textColor=MUTED, leading=14),
        "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=12, textColor=TEXT, leading=16),
        "hint": ParagraphStyle("hint", fontName=FONT, fontSize=8.5, textColor=MUTED, leading=11),
        "cell": ParagraphStyle("cell", fontSize=9, **base),
        "cell_c": ParagraphStyle("cell_c", fontSize=9, alignment=TA_CENTER, **base),
        "head": ParagraphStyle("head", fontName=FONT_BOLD, fontSize=9, textColor=MUTED,
                               leading=12, alignment=TA_CENTER),
        "head_l": ParagraphStyle("head_l", fontName=FONT_BOLD, fontSize=9, textColor=MUTED, leading=12),
        "tile_v": ParagraphStyle("tile_v", fontName=FONT_BOLD, fontSize=20, textColor=ACCENT,
                                 leading=24, alignment=TA_CENTER),
        "tile_c": ParagraphStyle("tile_c", fontName=FONT, fontSize=8.5, textColor=MUTED,
                                 leading=11, alignment=TA_CENTER),
    }


def _stat_tiles(st, items, width):
    """Строка плиток «значение + подпись»."""
    lines = max(c.count("\n") for _, c in items)  # подписи выравниваем по числу строк
    items = [(v, c + "\n\u00a0" * (lines - c.count("\n"))) for v, c in items]
    cells = [[Paragraph(_esc(v), st["tile_v"]), Paragraph(_esc(c).replace("\n", "<br/>"), st["tile_c"])]
             for v, c in items]
    # Каждая плитка — своя маленькая таблица, чтобы у неё была рамка
    tiles = []
    for value, caption in cells:
        t = Table([[value], [caption]], colWidths=[width / len(items) - 6])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
            ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ]))
        tiles.append(t)
    row = Table([tiles], colWidths=[width / len(items)] * len(items))
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return row


def _data_table(header, rows, col_widths, align_left_cols, st, extra_styles=()):
    """Таблица с повторяющейся шапкой, чередованием строк и тонкими линиями."""
    head = [Paragraph(_esc(h), st["head_l"] if i in align_left_cols else st["head"])
            for i, h in enumerate(header)]
    table = Table([head] + rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT_SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(rows) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), STRIPE))
    table.setStyle(TableStyle(style + list(extra_styles)))
    return table


PAGE_W, PAGE_H = A4
MARGIN = 16 * mm


def _build_doc(path, title, story):
    """Собирает документ A4 с общим колонтитулом (дата формирования и номер страницы)."""
    generated = datetime.now().strftime("%d.%m.%Y %H:%M")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 10 * mm, f"Work Tracking · сформировано {generated}")
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Стр. {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=16 * mm, bottomMargin=20 * mm,
                            title=title, author="Work Tracking")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_student_card_pdf(path, student, rank, total_students, up_to_iso, missed, grades):
    """
    Карточка студента: шапка с ключевыми цифрами, пропущенные занятия и оценки.

    student — dict/Row с ключами fio, itog_ball;  rank — место в группе или None;
    up_to_iso — дата, до которой считались пропуски;
    missed — строки repository.get_missed_lessons (data, nazvanie, tema);
    grades — строки repository.get_student_grades (work/period).
    """
    _register_fonts()
    st = _styles()
    width = PAGE_W - 2 * MARGIN
    fio = student["fio"]

    story = [Paragraph("КАРТОЧКА СТУДЕНТА", st["title"]), Spacer(1, 2),
             Paragraph(_esc(fio), st["name"]), Spacer(1, 2),
             Paragraph(f"Пропуски учтены до {iso_to_display(up_to_iso) or '—'}", st["sub"]),
             Spacer(1, 12)]

    place = f"{rank} из {total_students}" if rank else "—"
    story += [_stat_tiles(st, [(fmt_number(student["itog_ball"]), "Итоговый балл"),
                               (place, "Место в группе"),
                               (str(len(missed)), "Пропущено занятий")], width),
              Spacer(1, 18)]

    # --- Пропущенные занятия ---
    story.append(Paragraph(f"Пропущенные занятия ({len(missed)})", st["h2"]))
    story.append(Spacer(1, 6))
    if missed:
        rows = [[Paragraph(iso_to_display(r["data"]), st["cell_c"]),
                 Paragraph(_esc(_lesson_name(r["nazvanie"])), st["cell_c"]),
                 Paragraph(_esc(r["tema"]), st["cell"])] for r in missed]
        story.append(_data_table(("Дата", "Занятие", "Тема"), rows,
                                 [26 * mm, 28 * mm, width - 54 * mm], {2}, st))
    else:
        story.append(Paragraph("Пропусков нет.", st["sub"]))
    story.append(Spacer(1, 20))

    # --- Оценки: только выставленные + итоги периодов (как на вкладке по умолчанию) ---
    rows, extra, n = [], [], 0
    graded = 0
    for r in grades:
        if r["kind"] == "period":
            n += 1
            held = r["held"]
            low = r["grade"] == 2
            rows.append([Paragraph(iso_to_display(r["date"]), st["cell_c"]),
                         Paragraph(f"<b>Итог периода {r['period']}</b>", st["cell_c"]),
                         Paragraph("<b>Сумма баллов за период</b>" if held
                                   else "Контрольную ещё никто не писал", st["cell"]),
                         Paragraph(f"<b>{fmt_number(r['total']) if held else '—'}</b>", st["cell_c"]),
                         Paragraph(f"<b>{r['grade'] if r['grade'] is not None else '—'}</b>",
                                   st["cell_c"])])
            extra += [("BACKGROUND", (0, n), (-1, n), LOW_BG if low else ACCENT_SOFT)]
            continue
        if r["ball"] is None and r["raw"] is None:
            continue
        n += 1
        graded += 1
        value = fmt_number(r["ball"]) if r["ball"] is not None else (r["raw"] or "—")
        rows.append([Paragraph(iso_to_display(r["date"]), st["cell_c"]),
                     Paragraph(_esc(_lesson_name(r["name"])), st["cell_c"]),
                     Paragraph(_esc(r["tema"]), st["cell"]),
                     Paragraph(_esc(value), st["cell_c"]), Paragraph("", st["cell_c"])])

    story.append(Paragraph(f"Оценки (выставлено: {graded})", st["h2"]))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Оценка за период считается по сумме баллов за занятия периода.", st["hint"]))
    story.append(Spacer(1, 6))
    if rows:
        story.append(_data_table(("Дата", "Занятие", "Тема", "Балл", "Оценка"), rows,
                                 [26 * mm, 28 * mm, width - 26 * mm - 28 * mm - 17 * mm - 19 * mm,
                                  17 * mm, 19 * mm], {2}, st, extra))
    else:
        story.append(Paragraph("Оценок пока нет.", st["sub"]))

    _build_doc(path, f"Карточка студента — {fio}", story)


# ----------------------------------------------------------------------
# Диаграммы (страница «Визуализация»)
# ----------------------------------------------------------------------
WARN_BG = colors.HexColor("#FEF3C7")
WARN_FG = colors.HexColor("#92400E")
FIRST_CHUNK, NEXT_CHUNK = 30, 40      # сколько строк помещается на первой / следующих страницах диаграммы
ROW_H = 15.5                           # высота строки диаграммы, pt


class _Legend(Flowable):
    """Строка-легенда: образцы цветов столбцов."""

    def __init__(self, items, width):
        super().__init__()
        self.items, self.width, self.height = items, width, 16

    def wrap(self, avail_w, avail_h):
        return self.width, self.height

    def draw(self):
        c, x = self.canv, 0
        for kind, color, text in self.items:
            if kind == "worst":
                c.setFillColor(WARN_BG)
                c.setStrokeColor(WARN_FG)
                c.setLineWidth(1)
                c.rect(x, 3, 14, 10, fill=1, stroke=1)
            else:
                c.setFillColor(color)
                c.rect(x, 3, 14, 10, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.setFont(FONT, 8.5)
            c.drawString(x + 19, 5.5, text)
            x += 19 + pdfmetrics.stringWidth(text, FONT, 8.5) + 18


class _BarChunk(Flowable):
    """Горизонтальные столбцы для куска списка студентов; шкала общая для всех кусков."""

    NAME_W = 46 * mm
    VALUE_W = 14 * mm

    def __init__(self, rows, width, y_max, step, bar_color, flag_color, average, avg_caption,
                 first_index):
        super().__init__()
        self.rows, self.width = rows, width
        self.y_max, self.step = y_max, step
        self.bar_color, self.flag_color = bar_color, flag_color
        self.average, self.avg_caption = average, avg_caption
        self.first_index = first_index
        self.top, self.bottom = 18, 22
        self.height = self.top + len(rows) * ROW_H + self.bottom

    def wrap(self, avail_w, avail_h):
        return self.width, self.height

    def draw(self):
        c = self.canv
        x0 = self.NAME_W
        x1 = self.width - self.VALUE_W
        scale = (x1 - x0) / self.y_max
        base = self.bottom                       # y нижней границы области столбцов (ось y вверх)
        area_top = base + len(self.rows) * ROW_H

        # плашки «худших» под всем остальным
        for i, r in enumerate(self.rows):
            if r["worst"]:
                y = area_top - (i + 1) * ROW_H
                c.setFillColor(WARN_BG)
                c.setStrokeColor(WARN_FG)
                c.setLineWidth(0.8)
                c.rect(0, y + 0.5, self.width, ROW_H - 1, fill=1, stroke=1)

        # сетка и подписи шкалы сверху
        c.setLineWidth(0.5)
        for k in range(int(self.y_max // self.step) + 1):
            value = k * self.step
            x = x0 + value * scale
            c.setStrokeColor(BORDER)
            c.line(x, base, x, area_top + 3)
            c.setFillColor(MUTED)
            c.setFont(FONT, 7.5)
            c.drawCentredString(x, area_top + 7, f"{value:g}")

        # столбцы
        bar_h = ROW_H * 0.62
        for i, r in enumerate(self.rows):
            cy = area_top - (i + 0.5) * ROW_H
            worst = r["worst"]
            w = max(1.5, r["value"] * scale)
            c.setFillColor(self.flag_color if r["flagged"] else self.bar_color)
            if worst:
                c.setStrokeColor(WARN_FG)
                c.setLineWidth(1)
                c.rect(x0, cy - bar_h / 2, w, bar_h, fill=1, stroke=1)
            else:
                c.rect(x0, cy - bar_h / 2, w, bar_h, fill=1, stroke=0)

            c.setFillColor(WARN_FG if worst else TEXT)
            c.setFont(FONT_BOLD if worst else FONT, 8.5)
            name_right = x0 - 6
            c.drawRightString(name_right, cy - 3, r["name"])
            if worst:  # маркер «▼» рисуем фигурой: в шрифтах Windows этого символа может не быть
                tx = name_right - pdfmetrics.stringWidth(r["name"], FONT_BOLD, 8.5) - 9
                p = c.beginPath()
                p.moveTo(tx, cy + 2.5)
                p.lineTo(tx + 6, cy + 2.5)
                p.lineTo(tx + 3, cy - 2.5)
                p.close()
                c.setFillColor(WARN_FG)
                c.drawPath(p, fill=1, stroke=0)
            c.setFillColor(WARN_FG if worst else TEXT)
            c.setFont(FONT_BOLD, 8.5)
            c.drawString(x0 + r["value"] * scale + 4, cy - 3, f"{r['value']:g}")

        # оси и линия среднего
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.8)
        c.line(x0, base, x0, area_top + 3)
        c.line(x0, base, x1, base)
        ax = x0 + self.average * scale
        c.setDash(4, 3)
        c.setLineWidth(1.2)
        c.line(ax, base, ax, area_top + 3)
        c.setDash()
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 8.5)
        c.drawCentredString(ax, base - 12, f"{self.avg_caption} {round(self.average, 2):g}")


def _chunks(rows):
    """Делит строки на куски по страницам: первый короче (на странице есть шапка)."""
    out, i, size = [], 0, FIRST_CHUNK
    while i < len(rows):
        out.append((i, rows[i:i + size]))
        i += size
        size = NEXT_CHUNK
    return out


def build_visualization_pdf(path, charts, subtitle=""):
    """
    Диаграммы страницы «Визуализация»: каждая диаграмма начинается с новой страницы,
    длинный список студентов переносится на следующие страницы с той же шкалой.

    charts — список словарей:
      title, subtitle, summary [(значение, подпись)] (до 3 плиток),
      rows [{"name", "value", "flagged", "worst"}] (уже в нужном порядке),
      flag_text, flag_color (hex), worst_text, avg_caption, missing_note (или "").
    """
    _register_fonts()
    st = _styles()
    width = PAGE_W - 2 * MARGIN - 12   # минус внутренние отступы рамки страницы (по 6 pt)
    story = []

    for number, ch in enumerate(charts):
        if number:
            story.append(PageBreak())
        story += [Paragraph("ВИЗУАЛИЗАЦИЯ УСПЕВАЕМОСТИ", st["title"]), Spacer(1, 2),
                  Paragraph(_esc(ch["title"]), st["name"]), Spacer(1, 2),
                  Paragraph(_esc(ch["subtitle"]), st["sub"])]
        if subtitle:
            story.append(Paragraph(_esc(subtitle), st["hint"]))
        story.append(Spacer(1, 10))
        if ch.get("summary"):
            story += [_stat_tiles(st, ch["summary"], width), Spacer(1, 12)]

        flag_color = colors.HexColor(ch["flag_color"])
        story += [_Legend([("worst", None, ch["worst_text"]), ("bar", flag_color, ch["flag_text"]),
                           ("bar", ACCENT, "остальные")], width), Spacer(1, 6)]

        rows = ch["rows"]
        if not rows:
            story.append(Paragraph("Нет данных для диаграммы.", st["sub"]))
            continue
        max_val = max(r["value"] for r in rows)
        step = max(1, math.ceil(max_val / 10))
        y_max = max(step, math.ceil(max_val / step) * step)
        average = sum(r["value"] for r in rows) / len(rows)
        for first, part in _chunks(rows):
            chunk = _BarChunk(part, width, y_max, step, ACCENT, flag_color, average,
                              ch["avg_caption"], first)
            if first:
                story.append(KeepTogether([Paragraph(f"{_esc(ch['title'])} (продолжение)", st["h2"]),
                                           Spacer(1, 6), chunk]))
            else:
                story.append(chunk)
        if ch.get("missing_note"):
            story += [Spacer(1, 4), Paragraph(_esc(ch["missing_note"]), st["hint"])]

    _build_doc(path, "Визуализация успеваемости", story)
