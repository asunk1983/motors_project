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
