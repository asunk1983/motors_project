"""Утилиты для файлового ввода-вывода (JSON).

Раньше load/save JSON дублировались в auth.py (load_file_users,
load_file_tokens, save_file_users, save_file_tokens). Теперь одна
функция load_json / save_json.
"""
import json
import os


def load_json(path: str, default=None):
    """Загружает JSON из файла. Возвращает default при ошибке."""
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: str, data) -> None:
    """Сохраняет данные в JSON-файл (читаемый, ensure_ascii=False)."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
