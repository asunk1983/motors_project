"""Схема валидации двигателя и связанных сущностей.

Централизует правила валидации, ранее дублированные в app.py
(_validate_numeric_value, _validate_mode_numeric_fields).
"""
from modules.db import ENGINE_COLUMNS_ORDERED, MODE_COLUMNS


def validate_numeric_value(value, label: str):
    """Проверяет, что value (если задано) является числом.

    Возвращает строку-ошибку или None (если ОК).
    Пустая строка / None — допустимы (поле необязательно).
    """
    if value is None or value == '':
        return None
    try:
        float(value)
    except (ValueError, TypeError):
        return f'Поле "{label}" должно быть числом, получено: {value}'
    return None


def validate_mode_numeric_fields(mode: dict):
    """Проверяет числовые поля режима работы (frequency, power, voltage, current, rpm).

    Возвращает строку-ошибку или None.
    """
    numeric_fields = {
        'frequency': 'Частота',
        'power': 'Мощность',
        'voltage': 'Напряжение',
        'current': 'Ток',
        'rpm': 'Обороты',
    }
    for key, label in numeric_fields.items():
        err = validate_numeric_value(mode.get(key), label)
        if err:
            return err
    return None


def validate_engine_payload(data: dict):
    """Валидирует payload создания/обновления двигателя.

    Возвращает (is_valid: bool, error: str | None).
    """
    for label_key, label in (('workshop', 'Цех'), ('shaft_diameter', 'Диаметр вала')):
        err = validate_numeric_value(data.get(label_key), label)
        if err:
            return False, err

    for mode in data.get('modes', []):
        err = validate_mode_numeric_fields(mode)
        if err:
            return False, err

    for work in data.get('works', []):
        err = validate_numeric_value(work.get('isolation'), 'Сопротивление изоляции')
        if err:
            return False, err

    return True, None


def sanitize_engine_data(data: dict) -> dict:
    """Очищает и нормализует данные двигателя перед записью в БД.

    - Стрирает строковые поля
    - Приводит photo_count к int
    - Фильтрует неизвестные поля
    """
    result = {}
    for col in ENGINE_COLUMNS_ORDERED:
        if col in data:
            val = data[col]
            if col == 'photo_count':
                result[col] = int(val) if val else 0
            elif isinstance(val, str):
                result[col] = val.strip()
            else:
                result[col] = val
    return result
