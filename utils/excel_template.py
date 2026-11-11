"""
Генератор пустой структуры Excel-журнала в том формате, который читает UniversityParser.

Создаются те же три листа, что и в файле-примере:
  «Баллы, оценки» — журнал (ФИО, занятия по периодам, оценки периодов, ПР, ЛР, итог, пропуски, ДЗ, зачёт);
  «Чек-лист»      — вопросы/ДЗ по периодам и темы практических и лабораторных работ;
  «Даты_темы»     — даты и темы занятий + сводка по количеству работ.

Преподавателю остаётся только вписать данные. Формулы (оценка периода, итог, пропуски, зачёт)
заполнены сразу. Модуль не зависит от tkinter, поэтому его можно проверять отдельно.
"""
from dataclasses import dataclass

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from utils.parser import UniversityParser

SHEET_GRADES = UniversityParser.SHEET_GRADES
SHEET_CHECK = "Чек-лист"
SHEET_DATES = UniversityParser.SHEET_DATES

MAX_STUDENTS = 200
MAX_LESSONS = 200

# Цвета заголовков — как в файле-примере
YELLOW, GREEN, PINK = "FFFF00", "93C47D", "F4CCCC"
BLUE, LIGHT_BLUE, GREY, RED, ROYAL = "6FA8DC", "CFE2F3", "F6F8F9", "E06666", "4A86E8"
PERIOD_GRADE = "FFF2CC"

_thin = Side(style="thin", color="999999")
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
FONT = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
DATE_FMT = "dd.mm.yyyy"


@dataclass
class TemplateConfig:
    # --- шапка листа «Даты_темы» ---
    group: str = ""
    discipline: str = ""
    teacher: str = ""
    semester: str = "1 семестр"
    # --- размеры ---
    students: int = 28
    periods: int = 4              # сколько периодов (столбцов «оценка N»)
    period_size: int = 4          # занятий в одном периоде
    practical: int = 7            # практических работ
    laboratory: int = 4           # лабораторных работ
    total_lessons: int = 32       # всего занятий (периоды + ПР + ЛР + прочие)
    homework: int = 4             # столбцов «ДЗ»
    # --- необязательные части ---
    extra_tasks: bool = True      # блок «доп.задания» (STEPIC, доп.баллы)
    exam: bool = True             # столбец «Диф. зачет»
    legend: bool = True           # справочник баллов под таблицей
    subgroups: bool = True        # лабораторные в двух подгруппах (график дат)
    rows_per_lesson: int = 2      # строк на занятие в «Даты_темы» (две темы за пару)
    # --- шкалы оценок ---
    period_5: float = 3.5         # сумма за период для «5» (>=)
    period_4: float = 2.5         # для «4» (>)
    period_3: float = 1.5         # для «3» (>)
    final_5: float = 31.0         # итог в баллах для «5» (>=)
    final_4: float = 25.0
    final_3: float = 21.0

    @property
    def period_lessons(self) -> int:
        return self.periods * self.period_size

    @property
    def rest_lessons(self) -> int:
        return self.total_lessons - self.period_lessons - self.practical - self.laboratory


def validate(cfg: TemplateConfig) -> list:
    """Список понятных пользователю ошибок; пустой — параметры корректны."""
    errors = []
    if not 1 <= cfg.students <= MAX_STUDENTS:
        errors.append(f"Количество студентов — от 1 до {MAX_STUDENTS}.")
    if not 1 <= cfg.total_lessons <= MAX_LESSONS:
        errors.append(f"Всего занятий — от 1 до {MAX_LESSONS}.")
    for name, value in (("Периодов", cfg.periods), ("Занятий в периоде", cfg.period_size),
                        ("Практических работ", cfg.practical), ("Лабораторных работ", cfg.laboratory),
                        ("Столбцов ДЗ", cfg.homework)):
        if value < 0:
            errors.append(f"«{name}» не может быть отрицательным.")
    if (cfg.periods > 0) != (cfg.period_size > 0):
        errors.append("Периоды: укажите и количество периодов, и число занятий в периоде (или оба — 0).")
    if not 1 <= cfg.rows_per_lesson <= 6:
        errors.append("Строк на занятие в «Даты_темы» — от 1 до 6.")
    if not errors and cfg.rest_lessons < 0:
        errors.append(
            f"Занятий не хватает: периоды ({cfg.period_lessons}) + ПР ({cfg.practical}) + "
            f"ЛР ({cfg.laboratory}) = {cfg.period_lessons + cfg.practical + cfg.laboratory}, "
            f"а всего занятий {cfg.total_lessons}.")
    if not cfg.period_5 > cfg.period_4 > cfg.period_3 >= 0:
        errors.append("Шкала периода: порог «5» > порога «4» > порога «3» ≥ 0.")
    if not cfg.final_5 > cfg.final_4 > cfg.final_3 >= 0:
        errors.append("Шкала итога: порог «5» > порога «4» > порога «3» ≥ 0.")
    return errors


# ----------------------------------------------------------------------
# Раскладка столбцов листа «Баллы, оценки»
# ----------------------------------------------------------------------

def _layout(cfg: TemplateConfig) -> list:
    """Столбцы по порядку (A — ФИО). Каждый: dict(kind, h1, h2, lesson, ...)."""
    cols = [dict(kind="fio", h1="Фамилия Имя")]
    n = 0

    def lesson(kind, h1, **extra):
        nonlocal n
        n += 1
        cols.append(dict(kind=kind, h1=h1 if h1 is not None else n, lesson=n, **extra))

    for p in range(1, cfg.periods + 1):
        first = len(cols) + 1
        for i in range(cfg.period_size):
            lesson("lesson", None, control=(i == cfg.period_size - 1))
        cols.append(dict(kind="grade", h1=f"оценка {p}", first=first, last=len(cols)))
    for k in range(1, cfg.practical + 1):
        lesson("pr", None)
        cols[-1]["h1"] = f"ПР{k}_ур.{n}"
    for k in range(1, cfg.laboratory + 1):
        lesson("lr", None)
        cols[-1]["h1"] = f"ЛР {k}_ур.{n}"
    for _ in range(max(cfg.rest_lessons, 0)):
        lesson("lesson", None, rest=True)
    cols.append(dict(kind="itog", h1="итог в баллах"))
    cols.append(dict(kind="abs", h1="кол-пропусков", h2=f"{cfg.total_lessons} урока"))
    if cfg.extra_tasks:
        cols += [dict(kind="extra", h1="доп.задания", h2="STEPIC"),
                 dict(kind="extra", h1=None, h2="доп.баллы"),
                 dict(kind="extra", h1=None, h2="доп.баллы")]
    for k in range(1, cfg.homework + 1):
        cols.append(dict(kind="hw", h1=f"ДЗ {k}"))
    if cfg.exam:
        cols.append(dict(kind="exam", h1=f"Диф. зачет_{cfg.total_lessons + 1}"))
    return cols


def _segments(indexes):
    """[2,3,4,6,7] -> [(2,4),(6,7)] — подряд идущие столбцы для формул."""
    out = []
    for i in sorted(indexes):
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def _range_list(indexes, row):
    return ",".join(f"{L(a)}{row}:{L(b)}{row}" if a != b else f"{L(a)}{row}"
                    for a, b in _segments(indexes))


def _fill(color):
    return PatternFill("solid", start_color=color, end_color=color)


def _num(x):
    return f"{x:g}".replace(".", ",")


HEADER_FILL = {"fio": YELLOW, "lesson": YELLOW, "grade": PERIOD_GRADE, "pr": GREEN, "lr": PINK,
               "itog": YELLOW, "abs": YELLOW, "extra": LIGHT_BLUE, "hw": LIGHT_BLUE, "exam": YELLOW}


# ----------------------------------------------------------------------
# Листы
# ----------------------------------------------------------------------

def _build_grades(ws, cfg: TemplateConfig):
    cols = _layout(cfg)
    first, last = 3, 2 + cfg.students
    idx = {}  # kind -> список номеров столбцов (с 1)
    for i, c in enumerate(cols, start=1):
        idx.setdefault(c["kind"], []).append(i)
    scored = [i for k in ("lesson", "pr", "lr") for i in idx.get(k, [])]
    grade_cols = idx.get("grade", [])

    # --- шапка: строка 1 — названия, строка 2 — даты/пояснения ---
    ws.row_dimensions[1].height = 36.75
    ws.row_dimensions[2].height = 21.75
    for i, c in enumerate(cols, start=1):
        h1, h2 = ws.cell(1, i), ws.cell(2, i)
        h1.value, h2.value = c["h1"], c.get("h2")
        h1.fill = _fill(HEADER_FILL[c["kind"]])
        h2.fill = _fill(LIGHT_BLUE if c["kind"] in ("extra", "hw") else "FFFFFF")
        h1.font = BOLD if c["kind"] in ("itog", "abs", "extra", "grade") else FONT
        h2.font = BOLD if c["kind"] in ("itog", "abs", "grade", "exam") else FONT
        h1.alignment = h2.alignment = CENTER
        h1.border = h2.border = BORDER
        if c["kind"] not in ("fio", "grade", "itog", "abs", "extra"):
            h2.number_format = DATE_FMT
        if c["kind"] == "grade":
            h2.value = None

    # --- ширины ---
    widths = {"fio": 38, "lesson": 7, "grade": 9, "pr": 11, "lr": 11, "itog": 10, "abs": 11,
              "extra": 11, "hw": 10, "exam": 13}
    for i, c in enumerate(cols, start=1):
        ws.column_dimensions[L(i)].width = widths[c["kind"]]

    # --- формулы ---
    def formula(c, i, r):
        kind = c["kind"]
        if kind == "grade":
            s = f"SUM({L(c['first'])}{r}:{L(c['last'])}{r})"
            return (f"=IF({s}>={cfg.period_5:g},5,IF({s}>{cfg.period_4:g},4,"
                    f"IF({s}>{cfg.period_3:g},3,2)))")
        if kind == "itog":
            return f"=SUM({_range_list(scored, r)})" if scored else None
        if kind == "abs":
            return f"={cfg.total_lessons}-COUNTA({_range_list(scored, r)})" if scored else None
        if kind == "exam":
            t = f"{L(idx['itog'][0])}{r}"
            return f"=IF({t}>={cfg.final_5:g},5,IF({t}>={cfg.final_4:g},4,IF({t}>={cfg.final_3:g},3,2)))"
        return None

    for r in range(first, last + 1):
        band = _fill(GREY) if (r - first) % 2 == 0 else _fill("FFFFFF")
        for i, c in enumerate(cols, start=1):
            cell = ws.cell(r, i)
            cell.value = formula(c, i, r)
            cell.fill, cell.border, cell.font = band, BORDER, FONT
            cell.alignment = LEFT if c["kind"] == "fio" else CENTER
            if c["kind"] in ("grade", "itog", "abs", "exam"):
                cell.font = BOLD
            if c["kind"] in ("lesson", "pr", "lr", "extra", "hw"):
                cell.number_format = "General"

    # --- строка с количеством оценок по занятиям ---
    r = last + 1
    for i in idx.get("lesson", []):
        cell = ws.cell(r, i, f"=COUNTA({L(i)}{first}:{L(i)}{last})")
        cell.fill, cell.border, cell.font, cell.alignment = _fill(GREY), BORDER, FONT, CENTER
    for kind, caption in (("pr", "ПРАКТИЧЕСКИЕ РАБОТЫ"), ("lr", "ЛАБОРАТОРНЫЕ РАБОТЫ")):
        cs = idx.get(kind)
        if not cs:
            continue
        for i in cs:
            ws.cell(r, i).fill, ws.cell(r, i).border = _fill(GREY), BORDER
        ws.cell(r, cs[0], caption).font = BOLD
        ws.cell(r, cs[0]).alignment = CENTER
        if len(cs) > 1:
            ws.merge_cells(start_row=r, start_column=cs[0], end_row=r, end_column=cs[-1])

    if cfg.legend:
        _build_legend(ws, cfg, cols, idx, r + 1)

    ws.freeze_panes = "B3"
    return cols


def _build_legend(ws, cfg, cols, idx, row):
    """Справочник баллов под таблицей. Столбцы «итог» и «пропуски» здесь пустые —
    иначе парсер принял бы эти строки за студентов."""
    def put(r, c, v, bold=False, fill=None, align=LEFT):
        cell = ws.cell(r, c, v)
        cell.font = BOLD if bold else FONT
        cell.alignment = align
        if fill:
            cell.fill = _fill(fill)
        return cell

    # Образцы: (подпись, балл за урок, балл за контрольную/работу, оценка)
    samples = [("ОТЛИЧНО (оценка 5)", 0.5, 2, 5), ("ХОРОШО (оценка 4)", 0.5, 1.5, 4),
               ("УДОВЛЕТВ. (оценка 3)", 0.5, 1, 3)]
    put(row, 1, "Итоговый балл и оценка:", bold=True)
    after_abs = idx["abs"][0] + 1            # первый столбец за «кол-пропусков»
    label_col = after_abs
    exam_col = idx.get("exam", [None])[0]
    totals = []
    for k, (title, base, ctrl, grade) in enumerate(samples, start=1):
        r = row + k
        band = GREY if k % 2 else "FFFFFF"
        put(r, 1, title, fill=band)
        total = 0.0
        for i, c in enumerate(cols, start=1):
            if i == 1:
                continue
            v = None
            if c["kind"] == "lesson":
                v = ctrl if c.get("control") else base
            elif c["kind"] in ("pr", "lr"):
                v = ctrl
            if v is not None:
                total += v
                put(r, i, v, fill=band, align=CENTER)
        totals.append(total)
        if exam_col:
            put(r, exam_col, grade, fill=band, align=CENTER)
    t5, t4, t3 = cfg.final_5, cfg.final_4, cfg.final_3
    labels = [f"от {_num(totals[0])} до {_num(t5)}", f"от {_num(t5 - 0.1)} до {_num(t4)}",
              f"от {_num(t4 - 0.1)} до {_num(t3)}"]
    for k, text in enumerate(labels, start=1):
        put(row + k, label_col, text, bold=True, fill=GREY if k % 2 else "FFFFFF")

    r = row + 5
    put(r, 1, "Промежуточный балл:", bold=True)
    for k, text in enumerate([f"{_num(cfg.period_5)} Балла >= оценка 5",
                              f"{_num(cfg.period_4)} Б < оценка 4 < {_num(cfg.period_5)} Б",
                              f"{_num(cfg.period_3)} Б < оценка 3 <= {_num(cfg.period_4)} Б"], start=1):
        put(r + k, 1, text, fill=GREY if k % 2 else "FFFFFF")

    r += 5
    put(r, 1, "Комментарии по баллам в таблице", bold=True, fill=GREY)
    rules = [("работа в классе", 0.5, None), ("все решено, ошибок нет", 2, "отлично"),
             ("все решено, ошибок мало", 1.5, "хорош."), ("все решено, ошибки", 1, "удовл.")]
    for k, (text, score, note) in enumerate(rules, start=1):
        put(r + k, 1, text, fill="FFFFFF" if k % 2 else GREY)
        put(r + k, 2, score, align=CENTER)
        if note:
            put(r + k, 3, note)

    r += len(rules) + 2
    put(r, 1, "ДОБИРАЕМ БАЛЛЫ по необходимости", bold=True, fill=GREY)
    bonus = [("Активность на уроке", 0.25), ("Дом. задание в moodle", 0.25),
             ("Дом. задание на уроке", 0.25), ("Наставник на уроке", 0.5),
             ("Разработка Google-форм, анализ", 0.5),
             ("Разработка презентаций к урокам по стандарту", 0.5),
             ("Участие в мероприятиях проф.направленности", 1)]
    for k, (text, score) in enumerate(bonus, start=1):
        put(r + k, 1, text, fill="FFFFFF" if k % 2 else GREY)
        put(r + k, 2, score, align=CENTER)


def _build_checklist(ws, cfg: TemplateConfig):
    heads = []
    lesson = 0
    for _ in range(cfg.periods):
        a, b = lesson + 1, lesson + cfg.period_size
        lesson = b
        heads += [(f"Вопросы уроков ({a}-{b})", None, None),
                  (f"ДЗ_{a}-{b} по учебнику", None, None),
                  (f"ИТОГ ({b} урок)", RED, "FFFFFF")]
    if cfg.practical:
        heads.append(("Темы Практических работ", ROYAL, "FFFFFF"))
    if cfg.laboratory:
        heads.append(("Темы Лабораторных работ", None, None))

    body = max(cfg.practical, cfg.laboratory, 6)
    ws.row_dimensions[1].height = 31.5
    for i, (text, color, font_color) in enumerate(heads, start=1):
        wide = text.startswith("Темы")
        ws.column_dimensions[L(i)].width = 58 if wide else (20 if text.startswith("Вопросы") else 14)
        h = ws.cell(1, i, text)
        h.font = Font(name="Arial", size=10, bold=True, color=font_color or "000000")
        h.alignment, h.border = CENTER, BORDER
        if color:
            h.fill = _fill(color)
        for r in range(2, body + 2):
            c = ws.cell(r, i)
            c.border, c.alignment, c.font = BORDER, LEFT, FONT
            if text.startswith("Темы Практ") and r - 1 <= cfg.practical:
                c.value = f"Практическая работа №{r - 1} "
            elif text.startswith("Темы Лаб") and r - 1 <= cfg.laboratory:
                c.value = f"Лабораторная работа №{r - 1} "

    foot = body + 4
    ws.cell(foot, 1, "Учебник: ").font = BOLD
    col = len(heads) - (1 if cfg.laboratory else 0) - (1 if cfg.practical else 0) + 1
    if cfg.practical:
        ws.cell(foot, col, "Обязательная предварительная подготовка к практическим заданиям, смотреть: ")
        ws.cell(foot, col).font, ws.cell(foot, col).alignment = BOLD, LEFT
        col += 1
    if cfg.laboratory:
        ws.cell(foot, col, "Обязательная предварительная подготовка к лабораторным заданиям, смотреть: ")
        ws.cell(foot, col).font, ws.cell(foot, col).alignment = BOLD, LEFT
    ws.freeze_panes = "A2"


def _build_dates(ws, cfg: TemplateConfig):
    ws["C1"] = f"Группа: {cfg.group}. {cfg.semester}"
    ws["C2"] = f"Дисциплина: {cfg.discipline}"
    ws["C3"] = f"ФИО преподавателя: {cfg.teacher}"
    for a in ("C1", "C2", "C3"):
        ws[a].font = BOLD
    for col, w in {"A": 4, "B": 7, "C": 15.5, "D": 85, "E": 8, "F": 24, "G": 17, "H": 19}.items():
        ws.column_dimensions[col].width = w

    for col, text in (("B", "№"), ("C", ""), ("D", "")):
        ws[f"{col}4"] = text or None
    ws["B5"], ws["C5"], ws["D5"] = "Урока", "Дата", "Тема занятия"
    for a in ("B4", "B5", "C5", "D5"):
        ws[a].font, ws[a].alignment, ws[a].border = BOLD, CENTER, BORDER

    # Сводка (F:G)
    ws["G1"] = "кол-во оценок"
    summary = [("итог_оценка за периоды", cfg.periods), ("практическая работа", cfg.practical),
               ("лабораторная работа", cfg.laboratory), ("теория", max(cfg.rest_lessons, 0))]
    for k, (name, val) in enumerate(summary, start=2):
        ws.cell(k, 6, name).font = BOLD
        ws.cell(k, 7, val)
    ws["G6"] = "=SUM(G2:G5)"
    for a in ("G1", "G6"):
        ws[a].font = BOLD

    # График лабораторных
    if cfg.laboratory:
        ws["G8"] = "1 подгр на уроке" if cfg.subgroups else "Дата"
        if cfg.subgroups:
            ws["H8"] = "2 подгр"
        for a in ("G8", "H8"):
            ws[a].font, ws[a].alignment = BOLD, CENTER
        for k in range(1, cfg.laboratory + 1):
            ws.cell(8 + k, 6, f"Лабораторная работа №{k}")
            for col in ((7, 8) if cfg.subgroups else (7,)):
                ws.cell(8 + k, col).number_format = DATE_FMT
                ws.cell(8 + k, col).border = BORDER

    # Занятия: в колонке B — номер урока из журнала, A — порядковый номер пары по расписанию
    lessons = cfg.total_lessons + (1 if cfg.exam else 0)
    row = 6
    for n in range(1, lessons + 1):
        ws.cell(row, 1, n).font = FONT
        b = ws.cell(row, 2, n)
        b.fill, b.alignment = _fill(YELLOW), CENTER
        ws.cell(row, 3).number_format = DATE_FMT
        for r in range(row, row + cfg.rows_per_lesson):
            for col in (2, 3, 4):
                c = ws.cell(r, col)
                c.border = BORDER
                if col == 4:
                    c.alignment = LEFT
                elif col == 3:
                    c.alignment = CENTER
                c.font = FONT
        row += cfg.rows_per_lesson
    ws.freeze_panes = "A6"


def build_workbook(cfg: TemplateConfig) -> Workbook:
    errors = validate(cfg)
    if errors:
        raise ValueError("\n".join(errors))
    wb = Workbook()
    ws_grades = wb.active
    ws_grades.title = SHEET_GRADES
    _build_grades(ws_grades, cfg)
    _build_checklist(wb.create_sheet(SHEET_CHECK), cfg)
    _build_dates(wb.create_sheet(SHEET_DATES), cfg)
    return wb


def save_template(cfg: TemplateConfig, path: str) -> None:
    wb = build_workbook(cfg)
    try:
        wb.save(path)
    except PermissionError:
        raise PermissionError("Файл занят другой программой (возможно, открыт в Excel). "
                              "Закройте его или выберите другое имя.")
