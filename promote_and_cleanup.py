#!/usr/bin/env python3
"""
Одноразовый скрипт: продвижение пользователя 'admin' до superadmin
и очистка тестовых пользователей.

Подключается к SQLite-базе engine_data.db и:
  1. UPDATE users SET role = 'superadmin' WHERE username = 'admin'
  2. Находит и удаляет всех пользователей, чей username LIKE 'test_admin_%'
  3. Печатает в консоль, что именно сделано (id/username удалённых)

Запускать вручную один раз:
    python promote_and_cleanup.py
"""

import sqlite3
import sys
from pathlib import Path
from config.settings import DB_PATH


def main():
    if not Path(DB_PATH).exists():
        print(f'ОШИБКА: база данных не найдена: {DB_PATH}')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Продвижение пользователя 'admin' до superadmin
    cur.execute("UPDATE users SET role = 'superadmin' WHERE username = 'admin'")
    updated = cur.rowcount
    conn.commit()
    print(f'UPDATE: пользователю "admin" назначена роль superadmin (затронуто строк: {updated})')

    # 2. Поиск и удаление тестовых пользователей
    cur.execute("SELECT id, username FROM users WHERE username LIKE 'test_admin_%'")
    to_delete = cur.fetchall()

    if not to_delete:
        print('DELETE: пользователи с username LIKE "test_admin_%" не найдены')
    else:
        print(f'DELETE: найдено {len(to_delete)} тестовых пользователей для удаления:')
        for row in to_delete:
            print(f'  - id={row["id"]}, username={row["username"]}')
        cur.execute("DELETE FROM users WHERE username LIKE 'test_admin_%'")
        conn.commit()
        print(f'DELETE: удалено {cur.rowcount} пользователей')

    conn.close()
    print('Готово.')


if __name__ == '__main__':
    main()
