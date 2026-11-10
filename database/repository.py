"""Все SQL-запросы приложения в одном месте. UI работает только с этими функциями."""
from dataclasses import dataclass
from typing import Optional

from config import NO_CONTROL_SCORE
from database.database_manager import db_session

SORT_OPTIONS = {
    "Без сортировки": None,
    "Баллы (по возрастанию)": ("itog_ball", "ASC"),
    "Баллы (по убыванию)": ("itog_ball", "DESC"),
    "Пропуски (по возрастанию)": ("missed", "ASC"),
    "Пропуски (по убыванию)": ("missed", "DESC"),
}

# Тип активности, который считается «занятием» (а не самостоятельной работой/зачётом)
LESSON_TYPE = "Урок"

# Подзапрос: сколько прошедших уроков (до :up_to) у студента s без выставленной оценки.
# Будущие уроки (дата позже :up_to) сюда не попадают — они просто ещё не проведены.
_MISSED_LESSONS_SQL = """(
    SELECT COUNT(*) FROM Activities a
    LEFT JOIN Grades g ON g.activity_id = a.id AND g.student_id = s.id
    WHERE a.tip = 'Урок' AND a.data != '' AND a.data <= :up_to
      AND g.poluchenny_ball IS NULL AND g.raw_value IS NULL
)"""


@dataclass
class Stats:
    total: int
    avg_score: Optional[float]
    avg_missed: Optional[float]


def database_has_data() -> bool:
    try:
        with db_session() as conn:
            return conn.execute("SELECT COUNT(*) FROM Students").fetchone()[0] > 0
    except Exception:
        return False


def get_students(search: str = "", sort_key: str = "Без сортировки",
                 sort_column: Optional[str] = None, sort_dir: str = "ASC",
                 up_to_iso: Optional[str] = None) -> list:
    """
    Список студентов вместе с числом реально пропущенных уроков (прошедших и без оценки).
    Поиск регистронезависимый и для кириллицы
    (SQLite NOCASE работает только с латиницей, поэтому фильтруем в Python).
    Пустые значения всегда уходят в конец списка.
    """
    if up_to_iso is None:
        up_to_iso = get_last_graded_date()
    if sort_column is None and SORT_OPTIONS.get(sort_key):
        sort_column, sort_dir = SORT_OPTIONS[sort_key]

    query = f"SELECT s.id, s.fio, s.itog_ball, {_MISSED_LESSONS_SQL} AS missed FROM Students s"
    if sort_column in ("itog_ball", "missed", "fio"):
        column = f"s.{sort_column}" if sort_column != "missed" else "missed"
        direction = "DESC" if sort_dir == "DESC" else "ASC"
        query += f" ORDER BY {column} IS NULL, {column} {direction}"
    else:
        query += " ORDER BY s.id"

    with db_session() as conn:
        rows = conn.execute(query, {"up_to": up_to_iso}).fetchall()

    needle = search.strip().casefold()
    if needle:
        rows = [r for r in rows if needle in (r["fio"] or "").casefold()]
    return rows


def get_stats(up_to_iso: Optional[str] = None) -> Stats:
    if up_to_iso is None:
        up_to_iso = get_last_graded_date()
    with db_session() as conn:
        total, avg_score = conn.execute(
            "SELECT COUNT(*), AVG(itog_ball) FROM Students").fetchone()
        avg_missed = conn.execute(
            f"SELECT AVG(missed) FROM (SELECT {_MISSED_LESSONS_SQL} AS missed FROM Students s)",
            {"up_to": up_to_iso}
        ).fetchone()[0]
    return Stats(total or 0, avg_score, avg_missed)


def get_student(student_id: int, up_to_iso: Optional[str] = None):
    if up_to_iso is None:
        up_to_iso = get_last_graded_date()
    with db_session() as conn:
        return conn.execute(
            f"SELECT s.id, s.fio, s.itog_ball, {_MISSED_LESSONS_SQL} AS missed "
            f"FROM Students s WHERE s.id = :sid",
            {"up_to": up_to_iso, "sid": student_id}
        ).fetchone()


def get_lesson_overview() -> dict:
    """
    Сводка по урокам курса: всего уроков и сколько из них ещё не проведено
    (дата позже даты последней выставленной оценки). Одинаково для всех студентов,
    поэтому не привязано к конкретному ФИО и показывается отдельно от таблицы.
    """
    cutoff = get_last_graded_date()
    with db_session() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM Activities WHERE tip = 'Урок' AND data != ''").fetchone()[0]
        remaining = conn.execute(
            "SELECT COUNT(*) FROM Activities WHERE tip = 'Урок' AND data != '' AND data > ?",
            (cutoff,)).fetchone()[0]
    return {"total": total, "remaining": remaining, "cutoff": cutoff}


def get_rank(student_id: int) -> Optional[int]:
    """Место в группе. Студенты с одинаковым баллом делят место."""
    with db_session() as conn:
        row = conn.execute("SELECT itog_ball FROM Students WHERE id = ?", (student_id,)).fetchone()
        if row is None or row["itog_ball"] is None:
            return None
        better = conn.execute(
            "SELECT COUNT(*) FROM Students WHERE itog_ball > ?", (row["itog_ball"],)
        ).fetchone()[0]
    return better + 1


def get_last_graded_date() -> str:
    """
    Дата последнего урока, по которому хоть у кого-то выставлена оценка (ISO).
    Всё, что позже, считается «ещё не проведённым», а не пропущенным.
    Итоговые столбцы («оценка 1») не учитываем: они заполнены формулами наперёд.
    """
    with db_session() as conn:
        row = conn.execute("""
            SELECT MAX(a.data) FROM Activities a
            JOIN Grades g ON g.activity_id = a.id
            WHERE g.poluchenny_ball IS NOT NULL AND a.data != '' AND a.tip IN ('Урок')
        """).fetchone()
    return row[0] or ""


def get_missed_lessons(student_id: int, up_to_iso: str) -> list:
    """Прошедшие уроки (тип «Урок») до указанной даты, по которым у студента нет оценки."""
    with db_session() as conn:
        return conn.execute("""
            SELECT a.data, a.nazvanie, a.tema
            FROM Activities a
            LEFT JOIN Grades g ON g.activity_id = a.id AND g.student_id = ?
            WHERE a.tip = 'Урок' AND a.data != '' AND a.data <= ?
              AND g.poluchenny_ball IS NULL AND g.raw_value IS NULL
            ORDER BY a.data, a.id
        """, (student_id, up_to_iso)).fetchall()


def get_score_distribution(bin_size: float = 1.0) -> list:
    """[(начало_интервала, количество)] — для будущих графиков."""
    with db_session() as conn:
        scores = [r[0] for r in conn.execute(
            "SELECT itog_ball FROM Students WHERE itog_ball IS NOT NULL")]
    if not scores:
        return []
    start = int(min(scores) // bin_size * bin_size)
    result = {}
    for s in scores:
        b = int(s // bin_size * bin_size)
        result[b] = result.get(b, 0) + 1
    return [(b, result.get(b, 0)) for b in range(start, int(max(scores)) + 1, int(bin_size))]


def get_worst_five_ids() -> set:
    """
    ID пяти студентов с наименьшим итоговым баллом (среди тех, у кого балл есть).
    При равенстве баллов — стабильный порядок по id.
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT id FROM Students
            WHERE itog_ball IS NOT NULL
            ORDER BY itog_ball ASC, id ASC
            LIMIT 5
        """).fetchall()
    return {r["id"] for r in rows}


def period_grade(total: float) -> int:
    """Оценка за период по сумме баллов: та же шкала, что в формулах Excel."""
    if total >= 3.5:
        return 5
    if total > 2.5:
        return 4
    if total > 1.5:
        return 3
    return 2


def get_control_report() -> list:
    """
    Студенты, у которых по итогам периода есть проблема: не писали контрольную
    (последнее занятие периода пусто или равно NO_CONTROL_SCORE) и/или оценка за период — 2.

    Периоды задаются столбцами «оценка N» из файла: период — это занятия между двумя такими
    столбцами, контрольная — последнее занятие перед столбцом оценки. Занятия после
    последнего столбца оценки (например, уроки 28–32 после практических) в периоды не входят.
    Число периодов и занятий в периоде может быть любым.

    Оценка считается здесь по сумме баллов, а не берётся из столбца «оценка N» файла:
    формулы Excel после сортировки списка могут ссылаться на чужие строки.
    Период считается проведённым, только если контрольную писал хоть кто-то —
    иначе все получили бы «двойку» за ещё не прошедшие занятия.

    Возвращает [{"student_id", "fio", "period", "date", "control", "total", "grade", "reasons"}].
    """
    with db_session() as conn:
        # id идут в порядке столбцов файла, поэтому порядок по id = порядок в таблице Excel
        activities = conn.execute(
            "SELECT id, tip, data FROM Activities ORDER BY id").fetchall()
        students = conn.execute("SELECT id, fio FROM Students ORDER BY id").fetchall()
        scores = {(r["student_id"], r["activity_id"]): r["poluchenny_ball"]
                  for r in conn.execute(
                      "SELECT student_id, activity_id, poluchenny_ball FROM Grades")}

    # Делим занятия на периоды по столбцам «оценка N»
    periods, block = [], []
    for a in activities:
        if a["tip"] == LESSON_TYPE:
            block.append(a)
        elif a["tip"] == "Оценка":
            if block:
                periods.append(block)
            block = []

    result = []
    for period, block in enumerate(periods, 1):
        control = block[-1]
        if not any(scores.get((s["id"], control["id"])) is not None for s in students):
            continue  # контрольную ещё не проводили / не вносили
        for s in students:
            ctrl = scores.get((s["id"], control["id"]))
            total = sum(scores.get((s["id"], a["id"])) or 0 for a in block)
            grade = period_grade(total)
            reasons = []
            if ctrl is None or ctrl == NO_CONTROL_SCORE:
                reasons.append("не писал контрольную")
            if grade == 2:
                reasons.append("оценка 2")
            if reasons:
                result.append({"student_id": s["id"], "fio": s["fio"], "period": period,
                               "date": control["data"], "control": ctrl,
                               "total": round(total, 2), "grade": grade, "reasons": reasons})
    return result
