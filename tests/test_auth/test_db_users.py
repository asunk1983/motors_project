"""Тесты управления DB-пользователями (modules/auth/db_users.py)."""
import sqlite3

import pytest

from modules.auth.db_users import (
    create_user, get_user_by_username, get_user_by_id, list_users,
    delete_user, update_user_password, update_user_crew_id,
    update_last_login, count_users, resolve_display_name,
)
from modules.auth.hashing import verify_password


def _add_crew(conn, full_name):
    cur = conn.cursor()
    cur.execute('INSERT INTO crew (full_name, position, workshop) VALUES (?, ?, ?)',
                (full_name, 'Инженер', 'Цех 1'))
    conn.commit()
    return cur.lastrowid


class TestCreateAndGet:
    def test_create_and_get(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'pass123', role='user')
        assert uid > 0
        user = get_user_by_username(db_conn, 'petrov')
        assert user['id'] == uid and user['role'] == 'user' and user['source'] == 'db'
        assert verify_password('pass123', user['password_hash'])

    def test_get_by_id(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'pass123')
        assert get_user_by_id(db_conn, uid)['username'] == 'petrov'

    def test_get_unknown_none(self, db_conn, file_users_env):
        assert get_user_by_username(db_conn, 'nobody') is None
        assert get_user_by_id(db_conn, 999999) is None

    def test_duplicate_username_raises(self, db_conn):
        create_user(db_conn, 'petrov', 'pass123')
        with pytest.raises(sqlite3.IntegrityError):
            create_user(db_conn, 'petrov', 'other')

    def test_timestamps_filled(self, db_conn, file_users_env):
        user = get_user_by_id(db_conn, create_user(db_conn, 'petrov', 'pass123'))
        assert user['created_at'] and user['last_edit']


class TestDisplayName:
    def test_from_crew(self, db_conn, file_users_env):
        crew_id = _add_crew(db_conn, 'Петров Пётр')
        uid = create_user(db_conn, 'petrov', 'pass123', crew_id=crew_id)
        user = get_user_by_username(db_conn, 'petrov')
        assert user['crew_id'] == crew_id
        assert user['display_name'] == 'Петров Пётр'

    def test_fallback_to_username(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'pass123')
        user = get_user_by_username(db_conn, 'petrov')
        assert user['crew_id'] is None and user['display_name'] == 'petrov'

    def test_missing_crew_record_fallback(self, db_conn, file_users_env):
        create_user(db_conn, 'petrov', 'pass123', crew_id=4242)
        assert get_user_by_username(db_conn, 'petrov')['display_name'] == 'petrov'

    def test_resolve_direct(self, db_conn):
        crew_id = _add_crew(db_conn, 'Иванов Иван')
        assert resolve_display_name(db_conn, crew_id, 'ivanov') == 'Иванов Иван'
        assert resolve_display_name(db_conn, None, 'ivanov') == 'ivanov'


class TestListAndUpdate:
    def test_list_keeps_display_name(self, db_conn, file_users_env):
        create_user(db_conn, 'petrov', 'pass123')
        users = list_users(db_conn)
        by_name = {u['username']: u for u in users}
        assert by_name['petrov']['display_name'] == 'petrov'
        assert all('display_name' in u and 'crew_id' in u for u in users)

    def test_delete(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'pass123')
        assert delete_user(db_conn, uid) is True
        assert get_user_by_id(db_conn, uid) is None

    def test_delete_unknown(self, db_conn, file_users_env):
        assert delete_user(db_conn, 999999) is False

    def test_update_password(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'oldpass')
        assert update_user_password(db_conn, uid, 'newpass') is True
        h = get_user_by_id(db_conn, uid)['password_hash']
        assert verify_password('newpass', h) and not verify_password('oldpass', h)

    def test_update_crew_id(self, db_conn, file_users_env):
        crew_id = _add_crew(db_conn, 'Петров Пётр')
        uid = create_user(db_conn, 'petrov', 'pass123')
        assert update_user_crew_id(db_conn, uid, crew_id) is True
        user = get_user_by_id(db_conn, uid)
        assert user['crew_id'] == crew_id and user['display_name'] == 'Петров Пётр'

    def test_update_crew_id_unbind(self, db_conn, file_users_env):
        crew_id = _add_crew(db_conn, 'Петров Пётр')
        uid = create_user(db_conn, 'petrov', 'pass123', crew_id=crew_id)
        assert update_user_crew_id(db_conn, uid, None) is True
        assert get_user_by_id(db_conn, uid)['crew_id'] is None

    def test_update_last_login(self, db_conn, file_users_env):
        uid = create_user(db_conn, 'petrov', 'pass123')
        assert update_last_login(db_conn, uid) is True
        assert get_user_by_id(db_conn, uid)['last_login']


class TestDefaultAdmin:
    def test_count_and_admin(self, db_conn, file_users_env):
        before = count_users(db_conn)
        create_user(db_conn, 'petrov', 'pass123')
        assert count_users(db_conn) == before + 1
        admin = get_user_by_username(db_conn, 'admin')
        assert admin is not None and admin['role'] == 'admin'