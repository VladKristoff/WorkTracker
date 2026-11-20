"""
Экспорт в PDF (reportlab). Модуль не зависит от tkinter и базы данных: получает готовые данные,
поэтому его можно проверять отдельно.

Шрифт с кириллицей берётся из системы (Segoe UI / Arial в Windows, DejaVu / Liberation в Linux),
отдельный файл шрифта в проект добавлять не нужно.
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

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
    cells = [[Paragraph(_esc(v), st["tile_v"]), Paragraph(_esc(c), st["tile_c"])] for v, c in items]
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
    page_w, _ = A4
    margin = 16 * mm
    width = page_w - 2 * margin
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

    generated = datetime.now().strftime("%d.%m.%Y %H:%M")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin, 10 * mm, f"Work Tracking · сформировано {generated}")
        canvas.drawRightString(page_w - margin, 10 * mm, f"Стр. {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.line(margin, 14 * mm, page_w - margin, 14 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=16 * mm, bottomMargin=20 * mm,
                            title=f"Карточка студента — {fio}", author="Work Tracking")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
