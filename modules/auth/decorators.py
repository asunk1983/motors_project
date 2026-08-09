"""Декораторы для проверки авторизации.

Вынесено из auth.py. Используется в routes/ для защиты эндпоинтов.
"""
from functools import wraps

from flask import request, jsonify

from modules.db import db_connection
from modules.auth.tokens import get_user_from_token


def _extract_bearer_token():
    """Извлекает токен из заголовка Authorization: Bearer <token>
    или query-параметра ?token=<token>."""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[len('Bearer '):].strip()
    token_arg = request.args.get('token')
    if token_arg:
        return token_arg.strip()
    return None


def get_current_user():
    """Получить текущего пользователя из токена (или None)."""
    token = _extract_bearer_token()
    if not token:
        return None
    with db_connection() as conn:
        return get_user_from_token(conn, token)


def require_auth(f):
    """Декоратор: требует авторизацию.

    Если токен отсутствует или недействителен — возвращает 401.
    Текущий пользователь доступен в request.current_user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Требуется авторизация'}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Декоратор: требует роль admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Требуется авторизация'}), 401
        if user.get('role') != 'admin':
            return jsonify({'error': 'Доступ запрещён (нужна роль admin)'}), 403
        request.current_user = user
        return f(*args, **kwargs)
    return decorated
