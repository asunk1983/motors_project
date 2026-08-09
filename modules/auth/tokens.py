"""Токен-менеджмент (issue / validate / revoke).

Вынесено из auth.py. Использует hashing.py, db_users.py и file_users.py.
"""
from datetime import datetime, timedelta

from modules.auth.hashing import hash_token, generate_token
from modules.auth.file_users import (
    FILE_USER_ID_OFFSET, _load_file_users, _load_file_tokens,
    _save_file_tokens,
)


def _row_to_dict(row):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return {k: row[k] for k in row.keys()}
    return row


def issue_token(conn, user_id, expires_in_days=None):
    """Генерирует токен, сохраняет его хэш, возвращает САМ токен.

    Для DB-пользователей (id < FILE_USER_ID_OFFSET) токен сохраняется в таблице
    tokens. Для файловых пользователей — в tokens.json.
    """
    token = generate_token()
    token_hash = hash_token(token)
    expires_at = None
    if expires_in_days:
        expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

    # DB users
    if conn is not None and user_id is not None and 0 < user_id < FILE_USER_ID_OFFSET:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO tokens (user_id, token_hash, created_at, expires_at) '
            'VALUES (?, ?, ?, ?)',
            (user_id, token_hash, datetime.now().isoformat(), expires_at)
        )
        conn.commit()
        return token

    # File users
    username = None
    for u in _load_file_users():
        if u.get('id') == user_id:
            username = u.get('username')
            break
    tokens = _load_file_tokens()
    tokens.append({
        'token_hash': token_hash,
        'username': username,
        'created_at': datetime.now().isoformat(),
        'expires_at': expires_at
    })
    _save_file_tokens(tokens)
    return token


def get_user_from_token(conn, token):
    """По токену (из заголовка) возвращает dict пользователя или None."""
    if not token:
        return None
    token_hash = hash_token(token)

    # Check DB tokens first
    try:
        if conn is not None:
            cur = conn.cursor()
            cur.execute('SELECT expires_at, user_id FROM tokens WHERE token_hash = ?', (token_hash,))
            row = cur.fetchone()
            if row:
                row = _row_to_dict(row)
                expires_at = row.get('expires_at')
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at) < datetime.now():
                            return None
                    except Exception:
                        pass
                cur.execute(
                    'SELECT u.* FROM users u JOIN tokens t ON t.user_id = u.id '
                    'WHERE t.token_hash = ?',
                    (token_hash,)
                )
                result = _row_to_dict(cur.fetchone())
                if result:
                    result['source'] = 'db'
                    return result
    except Exception:
        pass

    # Fallback: check file tokens
    for t in _load_file_tokens():
        if t.get('token_hash') == token_hash:
            expires_at = t.get('expires_at')
            if expires_at:
                try:
                    if datetime.fromisoformat(expires_at) < datetime.now():
                        return None
                except Exception:
                    pass
            username = t.get('username')
            if not username:
                return None
            for u in _load_file_users():
                if u.get('username') == username:
                    u2 = dict(u)
                    u2['source'] = 'file'
                    return u2
    return None


def revoke_token(conn, token):
    """Отзывает конкретный токен (выход одной сессии)."""
    token_hash = hash_token(token)
    removed = False
    try:
        if conn is not None:
            cur = conn.cursor()
            cur.execute('DELETE FROM tokens WHERE token_hash = ?', (token_hash,))
            conn.commit()
            removed = cur.rowcount > 0
    except Exception:
        pass
    # remove from file tokens as well
    tokens = _load_file_tokens()
    new = [t for t in tokens if t.get('token_hash') != token_hash]
    if len(new) != len(tokens):
        _save_file_tokens(new)
        removed = True
    return removed


def revoke_all_for_user(conn, user_id):
    """Отзывает все токены пользователя (принудительный сброс сессий)."""
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM tokens WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception:
        pass
    # Also remove file tokens for file-based users (match by username)
    try:
        for u in _load_file_users():
            if u.get('id') == user_id:
                username = u.get('username')
                tokens = _load_file_tokens()
                new = [t for t in tokens if t.get('username') != username]
                if len(new) != len(tokens):
                    _save_file_tokens(new)
                break
    except Exception:
        pass
