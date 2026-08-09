"""Хэширование паролей и токенов.

Вынесено из auth.py в отдельный модуль — чистая функция без зависимостей
на БД или файлы. Используется db_users.py, file_users.py и tokens.py.
"""
import hashlib
import secrets

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    """Возвращает хэш пароля для хранения в БД (pbkdf2:scrypt)."""
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль против сохранённого хэша."""
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def hash_token(token: str) -> str:
    """SHA-256 хэш токена (именно он хранится в БД/файле)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def generate_token() -> str:
    """Случайный URL-safe токен длиной 32 байта (43 символа base64url)."""
    return secrets.token_urlsafe(32)
