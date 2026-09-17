"""Тесты файлового хранилища пользователей (modules/auth/file_users.py).

Базовая работа с файловыми пользователями частично покрыта в
test_tokens.py (там они нужны для токенов) — здесь отдельно проверяется
смена роли, добавленная для админки: на неё опирается
routes/auth.py::admin_update_user (source='file').
"""
from modules.auth.file_users import (
    FILE_USER_ID_OFFSET, create_file_user, update_file_user_role,
    _load_file_users,
)


def _stored(uid):
    return [u for u in _load_file_users() if u.get('id') == uid][0]


class TestUpdateFileUserRole:
    def test_update_role(self, file_users_env):
        uid = create_file_user('file_op', 'pass123', role='user')
        assert update_file_user_role(uid, 'reader') is True
        assert _stored(uid)['role'] == 'reader'

    def test_update_role_bumps_last_edit(self, file_users_env):
        uid = create_file_user('file_op', 'pass123', role='user')
        before = _stored(uid)['last_edit']
        update_file_user_role(uid, 'admin')
        assert _stored(uid)['last_edit'] >= before

    def test_update_role_unknown_user(self, file_users_env):
        create_file_user('file_op', 'pass123', role='user')
        assert update_file_user_role(FILE_USER_ID_OFFSET + 999, 'admin') is False

    def test_update_role_keeps_other_fields(self, file_users_env):
        uid = create_file_user('file_op', 'pass123', role='user', crew_id=7)
        assert update_file_user_role(uid, 'superadmin') is True
        stored = _stored(uid)
        assert stored['role'] == 'superadmin'
        assert stored['username'] == 'file_op'
        assert stored['crew_id'] == 7
        assert stored['password_hash']