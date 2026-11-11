import json

from config import SETTINGS_PATH, LOW_SCORE_THRESHOLD, HIGH_ABSENCES_THRESHOLD


def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_setting(key: str, value) -> None:
    data = load_settings()
    data[key] = value
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # настройки не критичны для работы


def load_thresholds() -> tuple:
    """
    Пороги подсветки (низкий балл, много пропусков), сохранённые преподавателем.
    Если значения нет или оно некорректно — берутся значения по умолчанию из config.
    """
    data = load_settings()

    def read(key, default):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return float(default)
        return float(value)

    return (read("low_score_threshold", LOW_SCORE_THRESHOLD),
            read("high_absences_threshold", HIGH_ABSENCES_THRESHOLD))
