"""CLI-утилита: добавить запись в лог изменений напрямую в data/changelog.json.

Файл отсортирован по entry_date DESC, поэтому новая запись вставляется
в правильную позицию (не просто в начало), чтобы сохранить порядок.

Использование:
    python -X utf8 scripts/add_changelog_entry.py --text "Что изменилось"
    python -X utf8 scripts/add_changelog_entry.py --text "Что изменилось" --date 2026-09-06

Запуск только из корня проекта (где лежит engine_data.db и data/).
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# Безопасный вывод кириллицы в Windows-консоли (по умолчанию cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Скрипт лежит в scripts/, но ему нужен config.settings для BASE_DIR.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import BASE_DIR

CHANGELOG_JSON_PATH = Path(BASE_DIR) / "data" / "changelog.json"


def _insert_sorted(entries: list[dict], new_entry: dict) -> list[dict]:
    """Вставляет new_entry в отсортированный по entry_date DESC список entries.

    Бинарный поиск: ищем первую запись с датой <= новой,
    вставляем перед ней. Это сохраняет порядок entry_date DESC.
    """
    new_date = new_entry["date"]
    lo, hi = 0, len(entries)
    while lo < hi:
        mid = (lo + hi) // 2
        if entries[mid]["date"] > new_date:
            lo = mid + 1
        else:
            hi = mid
    entries.insert(lo, new_entry)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Добавить запись в лог изменений (data/changelog.json)."
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Текст записи (обязательный).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Дата в формате YYYY-MM-DD. Если не указана - текущая дата.",
    )
    args = parser.parse_args()

    # Валидация текста.
    text = args.text.strip()
    if not text:
        print("Ошибка: текст записи не может быть пустым.", file=sys.stderr)
        return 2

    # Валидация / подстановка даты.
    entry_date: str
    if args.date is not None:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
            print("Ошибка: --date должен быть в формате YYYY-MM-DD", file=sys.stderr)
            return 2
        entry_date = args.date
    else:
        entry_date = date.today().isoformat()

    new_entry = {"date": entry_date, "text": text}

    # Читаем существующий файл (или начинаем с пустого списка).
    if CHANGELOG_JSON_PATH.exists():
        try:
            with open(CHANGELOG_JSON_PATH, encoding="utf-8") as f:
                entries = json.load(f)
        except (OSError, ValueError) as e:
            print(f"Ошибка при чтении {CHANGELOG_JSON_PATH}: {e}", file=sys.stderr)
            return 1
        if not isinstance(entries, list):
            print(
                f"Ошибка: {CHANGELOG_JSON_PATH} содержит не массив, а {type(entries).__name__}.",
                file=sys.stderr,
            )
            return 1
    else:
        entries = []

    # Вставляем в отсортированную позицию.
    _insert_sorted(entries, new_entry)

    # Гарантируем каталог data/ (на случай первого запуска).
    CHANGELOG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Пишем обратно.
    try:
        with open(CHANGELOG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"Ошибка при записи {CHANGELOG_JSON_PATH}: {e}", file=sys.stderr)
        return 1

    print(f"Запись добавлена: {entry_date} - {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())