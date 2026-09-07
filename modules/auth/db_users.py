"""DB-пользователи (таблица users в SQLite).

Вынесено из auth.py. Используется tokens.py и file_users.py (fallback).

Возвращаемые dict'ы содержат вычисляемое поле display_name — «человеческое»
имя пользователя: берётся из связанной записи crew.full_name, если
users.crew_id задан и запись в crew существует; иначе — fallback на
username. Это позволяет UI показывать ФИО вместо логина без отдельного
запроса на каждый рендер.
"""
from datetime import datetime

from modules.auth.hashing import hash_password


def _row_to_dict(row):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return {k: row[k] for k in row.keys()}
    return row


def resolve_display_name(conn, crew_id, username):
    """Единый резолвер «отображаемого имени» пользователя.

    crew_id — опциональная привязка учётки к записи справочника людей.
    Если crew_id задан и запись существует — возвращаем crew.full_name.
    Иначе — username (fallback). Никогда не возвращает None/пустую строку:
    фронт может безопасно рендерить результат без доп. проверок.
    """
    if crew_id is not None:
        try:
            cur = conn.cursor()
            cur.execute('SELECT full_name FROM crew WHERE id = ?', (crew_id,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
        except Exception:
            # crew-таблица может быть ещё не создана (старые БД до добавления
            # модуля инцидентов) — не валим резолв, возвращаем username.
            pass
    return username


def _attach_display_name(conn, user_dict):
    """Мутирует переданный dict, дописывая display_name и нормализуя crew_id
    (None вместо отсутствующего ключа). crew_id нужен в JSON для админки —
    чтобы можно было показать «привязан / не привязан» и для PATCH-а."""
    if user_dict is None:
        return None
    crew_id = user_dict.get('crew_id')
    user_dict['crew_id'] = crew_id
    user_dict['display_name'] = resolve_display_name(
        conn, crew_id, user_dict.get('username', '')
    )
    return user_dict


def create_user(conn, username, password, role='user', crew_id=None):
    """Создаёт пользователя в БД. Возвращает id или кидает исключение
    при нарушении уникальности username. crew_id — опциональная привязка
    к записи справочника crew (None = без привязки)."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO users (username, password_hash, role, created_at, last_edit, crew_id) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (username, hash_password(password), role, now, now, crew_id)
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_username(conn, username):
    """Ищет пользователя: сначала в БД, затем в файле (fallback).

    DB-юзеры возвращаются с display_name/crew_id (через _attach_display_name).
    Файловые юзеры — без crew_id, с display_name, посчитанным файловым
    helper'ом (см. file_users._attach_file_display_name).
    """
    # Check DB first
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        if row:
            d = _row_to_dict(row)
            d['source'] = 'db'
            return _attach_display_name(conn, d)
    except Exception:
        pass
    # Fallback to file users
    from modules.auth.file_users import _load_file_users, _attach_file_display_name
    for u in _load_file_users():
        if u.get('username') == username:
            d = dict(u)
            d['source'] = 'file'
            _attach_file_display_name(conn, d)
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
            return _attach_display_name(conn, d)
    except Exception:
        pass
    # File users: ids >= FILE_USER_ID_OFFSET
    from modules.auth.file_users import _load_file_users, _attach_file_display_name
    for u in _load_file_users():
        if u.get('id') == user_id:
            d = dict(u)
            d['source'] = 'file'
            _attach_file_display_name(conn, d)
            return d
    return None


def list_users(conn):
    """Список всех пользователей (DB + file).

    Возвращаемый список гарантированно содержит display_name и crew_id
    у КАЖДОГО пользователя — иначе фронт показал бы 'undefined'.
    """
    users = []
    cur = conn.cursor()
    cur.execute(
        'SELECT id, username, role, created_at, last_login, last_edit, crew_id '
        'FROM users ORDER BY id'
    )
    db_users = [dict(r) for r in cur.fetchall()]
    for u in db_users:
        u['source'] = 'db'
        _attach_display_name(conn, u)
        users.append(u)
    # append file users
    from modules.auth.file_users import _load_file_users, _attach_file_display_name
    for fu in _load_file_users():
        u = dict(fu)
        u['source'] = 'file'
        _attach_file_display_name(conn, u)
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


def update_user_crew_id(conn, user_id, crew_id):
    """Обновляет привязку DB-пользователя к crew. crew_id=None — сбросить
    привязку (отвязать учётку от записи справочника). last_edit обновляется,
    чтобы было видно в админке. Возвращает True если запись существует."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'UPDATE users SET crew_id = ?, last_edit = ? WHERE id = ?',
        (crew_id, now, user_id)
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

