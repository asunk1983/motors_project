"""Утилиты для работы с датами.

Единый источник правды для backend. Frontend-аналог — _formatRuDate в
static/js/common.js. Раньше format_ru_date дублировался в app.py, а
_formatRuDate — в engines.js и print.js.
"""
import re


def format_ru_date(iso_date: str) -> str:
    """Преобразует ISO-дату (YYYY-MM-DD) в русский формат (DD.MM.YYYY).

    Если строка не похожа на дату — возвращает как есть (без экранирования,
    т.к. это backend-функция; экранирование делается на фронте).
    """
    if not iso_date:
        return ''
    date_str = str(iso_date)
    if not is_valid_iso_date(date_str):
        return date_str
    parts = date_str.split('-')
    return f'{parts[2]}.{parts[1]}.{parts[0]}'


def is_valid_iso_date(date_str: str) -> bool:
    """Проверяет, что строка соответствует формату YYYY-MM-DD."""
    if not date_str:
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)))
