import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r"C:\motors_project\engine_data.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Схема таблицы
cur.execute("SELECT sql FROM sqlite_master WHERE name='audit_log'")
schema = cur.fetchone()
print("=== Схема таблицы audit_log ===")
if schema:
    print(schema[0])
else:
    print("Таблица не найдена!")

# Общее количество записей
cur.execute("SELECT COUNT(*) AS cnt FROM audit_log")
print()
print(f"Всего записей в audit_log: {cur.fetchone()['cnt']}")

# Все таблицы в БД
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print()
print("Все таблицы в БД:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

conn.close()