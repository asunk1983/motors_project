"""Одноразовая миграция: перенос записей из таблицы changelog_entries в data/changelog.json.

Использование (из корня проекта):
    python -X utf8 scripts/migrate_changelog_to_json.py

Что делает:
    1. Читает все записи из changelog_entries через db_connection().
    2. Сортирует по entry_date DESC, id DESC (как GET /api/changelog).
    3. Пишет data/changelog.json массивом [{"date": "...", "text": "..."}, ...].
       Поля id и created_at НЕ переносятся — они были нужны только для БД.

Важно:
    - Скрипт НЕ удаляет и НЕ изменяет таблицу changelog_entries.
    - Поле date в JSON соответствует entry_date из БД (YYYY-MM-DD).
    - Запускать строго из корня проекта (где лежит engine_data.db и modules/),
      иначе импорт modules.db не разрешится.
"""
import json
import os
import sys

# Корень проекта: .../motors_project/ (родитель каталога scripts/).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Скрипт лежит в scripts/, но импортирует пакет modules (из корня).
# По умолчанию Python не добавляет CWD в sys.path при запуске файла из подпапки,
# поэтому принудительно прокинем корень проекта в sys.path.
# Это позволяет запускать скрипт и как `python scripts/migrate_changelog_to_json.py`,
# и как `python -m scripts.migrate_changelog_to_json` из корня проекта.
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Безопасный вывод кириллицы в Windows-консоли (по умолчанию cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Импорт после reconfigure — безопасно даже при сбое настройки кодировки.
from modules.db import db_connection  # noqa: E402  (после sys.path)

OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "changelog.json")


def main() -> int:
    # Гарантируем наличие каталога data/ до записи.
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with db_connection() as conn:
        cursor = conn.cursor()
        # Сортировка ровно как в routes/changelog.py (GET /api/changelog):
        # свежие даты сверху, внутри одной даты — новые id сверху.
        cursor.execute(
            'SELECT entry_date, text '
            'FROM changelog_entries '
            'ORDER BY entry_date DESC, id DESC'
        )
        rows = cursor.fetchall()

    # rows — sqlite3.Row; row["entry_date"] / row["text"] достаём по имени.
    entries = [{"date": row["entry_date"], "text": row["text"]} for row in rows]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\n")  # финальный перенос строки — POSIX-стиль, удобно для git diff.

    print(f"OK: перенесено {len(entries)} записей -> {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())