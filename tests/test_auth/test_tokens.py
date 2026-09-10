"""Тесты токен-менеджмента (modules/auth/tokens.py): issue -> validate -> revoke.

Отдельно для DB-пользователей (таблица tokens) и файловых
(config/tokens.json — изолируется фикстурой file_users_env).
"""
import json
from datetime import datetime

import pytest

from modules.auth.db_users import create_user
from modules.auth.hashing import hash_token
from modules.auth.tokens import issue_token, get_user_from_token, revoke_token, revoke_all_for_user

FILE_ID_OFFSET = 1_000_000_000


@pytest.fixture
def db_user(db_conn):
    return create_user(db_conn, 'operator', 'pass123', role='user')


class TestIssue:
    def test_db_user_into_tokens(self, db_conn, db_user, file_users_env):
        token = issue_token(db_conn, db_user)
        cur = db_conn.cursor()
        cur.execute('SELECT token_hash, expires_at FROM tokens WHERE user_id = ?', (db_user,))
        row = cur.fetchone()
        assert row['token_hash'] == hash_token(token)
        assert row['expires_at'] is None

    def test_with_expiration(self, db_conn, db_user, file_users_env):
        issue_token(db_conn, db_user, expires_in_days=30)
        cur = db_conn.cursor()
        cur.execute('SELECT expires_at FROM tokens WHERE user_id = ?', (db_user,))
        assert datetime.fromisoformat(cur.fetchone()['expires_at']) > datetime.now()


class TestValidate:
    def test_valid_db_token(self, db_conn, db_user, file_users_env):
        token = issue_token(db_conn, db_user)
        user = get_user_from_token(db_conn, token)
        assert user is not None
        assert user['id'] == db_user
        assert user['source'] == 'db'
        assert user['display_name']

    def test_invalid_token_none(self, db_conn, file_users_env):
        assert get_user_from_token(db_conn, 'no-such-token') is None

    def test_empty_token_none(self, db_conn, file_users_env):
        assert get_user_from_token(db_conn, '') is None
        assert get_user_from_token(db_conn, None) is None

    def test_expired_token_none(self, db_conn, db_user, file_users_env):
        token = issue_token(db_conn, db_user, expires_in_days=-1)
        assert get_user_from_token(db_conn, token) is None


class TestRevoke:
    def test_revoke(self, db_conn, db_user, file_users_env):
        token = issue_token(db_conn, db_user)
        assert revoke_token(db_conn, token) is True
        assert get_user_from_token(db_conn, token) is None

    def test_revoke_unknown_false(self, db_conn, file_users_env):
        assert revoke_token(db_conn, 'unknown-token') is False

    def test_revoke_all(self, db_conn, db_user, file_users_env):
        t1, t2 = issue_token(db_conn, db_user), issue_token(db_conn, db_user)
        revoke_all_for_user(db_conn, db_user)
        assert get_user_from_token(db_conn, t1) is None
        assert get_user_from_token(db_conn, t2) is None

    def test_revoke_one_keeps_others(self, db_conn, db_user, file_users_env):
        t1, t2 = issue_token(db_conn, db_user), issue_token(db_conn, db_user)
        revoke_token(db_conn, t1)
        assert get_user_from_token(db_conn, t1) is None
        assert get_user_from_token(db_conn, t2) is not None


class TestFileUserTokens:
    def test_issue_and_validate_file_user(self, db_conn, file_users_env):
        from modules.auth.file_users import create_file_user
        uid = create_file_user('file_op', 'pass123', role='user')
        assert uid >= FILE_ID_OFFSET

        token = issue_token(db_conn, uid)
        user = get_user_from_token(db_conn, token)
        assert user is not None
        assert user['id'] == uid
        assert user['source'] == 'file'
        assert user['username'] == 'file_op'

        with open(file_users_env['tokens'], encoding='utf-8') as f:
            tokens = json.load(f)
        assert tokens[0]['token_hash'] == hash_token(token)

    def test_revoke_file_token(self, db_conn, file_users_env):
        from modules.auth.file_users import create_file_user
        uid = create_file_user('file_op', 'pass123')
        token = issue_token(db_conn, uid)
        assert revoke_token(db_conn, token) is True
        assert get_user_from_token(db_conn, token) is None