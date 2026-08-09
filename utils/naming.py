"""Утилиты для нормализации имён файлов.

Единый источник правды для parser.py и photo_manager. Раньше
normalize_base_name дублировалась в обоих модулях.
"""
import os
import re


def normalize_base_name(filename: str, engine_id: int | None = None) -> str:
    """Нормализует базовое имя файла (без расширения).

    - Убирает расширение
    - Заменяет недопустимые символы на _
    - Если имя пустое — использует engine_id

    ВАЖНО: НЕ обрезаем до 100 символов — это нарушило бы обратную
    совместимость с существующими фото в photos/.
    """
    base_name = os.path.splitext(filename or '')[0] or f'engine_{engine_id}'
    base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
    return base_name
