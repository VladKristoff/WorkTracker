"""
Что о студенте стоит показать преподавателю. Без tkinter: только данные из репозитория
и пороги, поэтому модуль можно проверять отдельно. Сами расчёты баллов, пропусков
и контрольных остаются в database/repository.py.
"""
from database import repository

WORST_COUNT = 5  # сколько худших по баллам отмечаем всегда


def fmt_number(value, empty="—"):
    """7.5 -> '7.5', 8.0 -> '8', None -> '—'."""
    return empty if value is None else f"{value:g}"


def fmt_average(value):
    return fmt_number(None if value is None else round(value, 2))


def short_name(fio):
    """Иванов Иван Иванович -> Иванов И.И."""
    parts = fio.split()
    if len(parts) <= 1:
        return fio
    return f"{parts[0]} " + "".join(f"{w[0]}." for w in parts[1:3])


def worst_ids(rows):
    """id пяти студентов с наименьшим баллом (rows — строки get_students в порядке файла)."""
    scored = sorted((r for r in rows if r["itog_ball"] is not None), key=lambda r: r["itog_ball"])
    return {r["id"] for r in scored[:WORST_COUNT]}


def students(low_score, high_absences, search="", sort_column=None, sort_dir="ASC"):
    """Студенты в нужном порядке вместе с признаками проблем."""
    everyone = repository.get_students()
    worst = worst_ids(everyone)
    rows = everyone
    if search or sort_column:
        rows = repository.get_students(search, sort_column=sort_column, sort_dir=sort_dir)
    controls = {}
    for item in repository.get_control_report():
        controls.setdefault(item["student_id"], []).append(item["period"])
    result = []
    for r in rows:
        score, missed = r["itog_ball"], r["missed"]
        result.append({
            "id": r["id"], "fio": r["fio"], "score": score, "missed": missed,
            "low": score is not None and score < low_score,
            "many": missed is not None and missed > high_absences,
            "worst": r["id"] in worst,
            "control_periods": controls.get(r["id"], []),
        })
    return result


def needs_attention(s):
    return bool(s["low"] or s["many"] or s["control_periods"])


def notes(s, rank=True):
    """Словами, почему студент отмечен (цвет — не единственный признак)."""
    parts = []
    if s["low"]:
        parts.append("низкий балл")
    if s["many"]:
        parts.append("много пропусков")
    if s["control_periods"]:
        parts.append("контрольные " + ", ".join(f"П{n}" for n in s["control_periods"]))
    if rank and s["worst"]:
        parts.append("в пятёрке худших")
    return " · ".join(parts)


def row_tag(s, index):
    if s["low"]:
        return "danger"
    if s["many"]:
        return "warn"
    return "even" if index % 2 else "odd"
