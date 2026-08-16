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


def validate_numeric_or_range_value(value, label: str):
    """Проверяет, что value — либо число, либо диапазон вида "220-240".

    Используется ТОЛЬКО для voltage (единственное поле, где диапазон
    имеет смысл и реально вводится в UI — см. engineCard.js: <input
    type="text"> вместо type="number" именно и только для voltage).
    Без этой отдельной ветки validate_numeric_value() отклонял бы
    диапазон с ошибкой "должно быть числом" ещё до записи в БД.

    Формат: "<число>-<число>", с необязательными пробелами вокруг
    дефиса. Отрицательные значения намеренно не поддерживаются (для
    напряжения отрицательных величин не бывает), поэтому дефис
    однозначно читается как разделитель диапазона, а не как знак минуса.

    Возвращает строку-ошибку или None (если ОК).
    Пустая строка / None — допустимы (поле необязательно).
    """
    if value is None or value == '':
        return None
    text = str(value).strip()
    if '-' in text:
        parts = [p.strip() for p in text.split('-', 1)]
        if len(parts) == 2 and all(parts):
            try:
                low, high = float(parts[0]), float(parts[1])
            except (ValueError, TypeError):
                return f'Поле "{label}" должно быть числом или диапазоном вида "220-240", получено: {value}'
            if low > high:
                return f'Поле "{label}": начало диапазона больше конца ({value})'
            return None
        return f'Поле "{label}" должно быть числом или диапазоном вида "220-240", получено: {value}'
    return validate_numeric_value(value, label)


def validate_mode_numeric_fields(mode: dict):
    """Проверяет числовые поля режима работы (frequency, power, voltage, current, rpm).

    Диапазон ("220-240") допускается ТОЛЬКО для voltage — см.
    validate_numeric_or_range_value. Остальные поля (frequency, power,
    current, rpm) — строго число, как и раньше.

    Возвращает строку-ошибку или None.
    """
    strict_numeric_fields = {
        'frequency': 'Частота',
        'power': 'Мощность',
        'current': 'Ток',
        'rpm': 'Обороты',
    }
    for key, label in strict_numeric_fields.items():
        err = validate_numeric_value(mode.get(key), label)
        if err:
            return err

    err = validate_numeric_or_range_value(mode.get('voltage'), 'Напряжение')
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
