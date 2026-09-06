"""Одноразовый скрипт: перенести существующие записи из wishlist_items в JSON.

Использование:
    python -X utf8 scripts/migrate_wishlist_to_json.py

Запуск из корня проекта. Читает записи из БД (config.settings.DB_PATH),
пишет data/wishlist.json. Таблицу wishlist_items не трогает и не удаляет —
это отдельный будущий шаг.
"""
import sys
import json
from pathlib import Path

# Безопасный вывод кириллицы в Windows-консоли (по умолчанию cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Скрипт лежит в scripts/, но ему нужны modules/config из корня проекта.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import BASE_DIR
from modules.db import db_connection

WISHLIST_JSON_PATH = Path(BASE_DIR) / "data" / "wishlist.json"


def main() -> int:
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, text, done, created_at FROM wishlist_items "
            "ORDER BY done ASC, id DESC"
        )
        rows = cursor.fetchall()

    items = [
        {
            "id": row["id"],
            "text": row["text"],
            "done": bool(row["done"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

    WISHLIST_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WISHLIST_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OK: перенесено {len(items)} записей в {WISHLIST_JSON_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
