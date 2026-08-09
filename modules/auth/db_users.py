"""DB-пользователи (таблица users в SQLite).

Вынесено из auth.py. Используется tokens.py и file_users.py (fallback).
"""
from datetime import datetime

from modules.auth.hashing import hash_password


def _row_to_dict(row):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return {k: row[k] for k in row.keys()}
    return row


def create_user(conn, username, password, role='user'):
    """Создаёт пользователя в БД. Возвращает id или кидает исключение
    при нарушении уникальности username."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO users (username, password_hash, role, created_at, last_edit) '
        'VALUES (?, ?, ?, ?, ?)',
        (username, hash_password(password), role, now, now)
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_username(conn, username):
    """Ищет пользователя: сначала в БД, затем в файле (fallback)."""
    # Check DB first
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        if row:
            d = _row_to_dict(row)
            d['source'] = 'db'
            return d
    except Exception:
        pass
    # Fallback to file users
    from modules.auth.file_users import _load_file_users
    for u in _load_file_users():
        if u.get('username') == username:
            d = dict(u)
            d['source'] = 'file'
            return d
    return None


def get_user_by_id(conn, user_id):
    """Ищет пользователя по ID: сначала в БД (положительные id),
    затем в файле (id >= FILE_USER_ID_OFFSET)."""
    # DB users: positive ids
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cur.fetchone()
        if row:
            d = _row_to_dict(row)
            d['source'] = 'db'
            return d
    except Exception:
        pass
    # File users: ids >= FILE_USER_ID_OFFSET
    from modules.auth.file_users import _load_file_users
    for u in _load_file_users():
        if u.get('id') == user_id:
            d = dict(u)
            d['source'] = 'file'
            return d
    return None


def list_users(conn):
    """Список всех пользователей (DB + file)."""
    users = []
    cur = conn.cursor()
    cur.execute('SELECT id, username, role, created_at, last_login, last_edit FROM users ORDER BY id')
    db_users = [dict(r) for r in cur.fetchall()]
    for u in db_users:
        u['source'] = 'db'
        users.append(u)
    # append file users
    from modules.auth.file_users import _load_file_users
    for fu in _load_file_users():
        u = dict(fu)
        u['source'] = 'file'
        users.append(u)
    return users


def delete_user(conn, user_id):
    """Удаляет DB-пользователя вместе с токенами (ON DELETE CASCADE)."""
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    return cur.rowcount > 0


def update_user_password(conn, user_id, new_password):
    """Обновляет пароль DB-пользователя."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'UPDATE users SET password_hash = ?, last_edit = ? WHERE id = ?',
        (hash_password(new_password), now, user_id)
    )
    conn.commit()
    return cur.rowcount > 0


def update_last_login(conn, user_id):
    """Обновляет время последнего входа DB-пользователя."""
    cur = conn.cursor()
    cur.execute(
        'UPDATE users SET last_login = ? WHERE id = ?',
        (datetime.now().isoformat(), user_id)
    )
    conn.commit()
    return cur.rowcount > 0


def count_users(conn):
    """Количество DB-пользователей."""
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    return cur.fetchone()[0]
