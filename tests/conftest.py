"""Тестовые фикстуры.

Предоставляет in-memory SQLite со схемой БД — без необходимости
поднимать production engine_data.db.
"""
import pytest
from modules.db import init_db, db_connection


@pytest.fixture
def db_conn():
    """In-memory SQLite с полной схемой (таблицы, индексы, admin-пользователь).

    Используется в тестах repository и service слоёв.
    """
    with db_connection(':memory:') as conn:
        init_db(conn)
        yield conn


@pytest.fixture
def file_users_env(tmp_path, monkeypatch):
    """Изолированное файловое хранилище users.json / tokens.json.

    Патчит глобальные пути модуля file_users на временную директорию,
    чтобы тесты auth не читали и не перезаписывали реальные
    config/users.json и config/tokens.json.
    """
    from modules.auth import file_users as fu
    users_path = str(tmp_path / 'users.json')
    tokens_path = str(tmp_path / 'tokens.json')
    monkeypatch.setattr(fu, 'CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(fu, 'FILE_USERS', users_path)
    monkeypatch.setattr(fu, 'FILE_TOKENS', tokens_path)
    return {'users': users_path, 'tokens': tokens_path}