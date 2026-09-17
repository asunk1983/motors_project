"""Тесты HTTP-слоя аутентификации (routes/auth.py).

Покрывает эндпоинты: login, me, logout, admin/users (список/create/update/delete/password/revoke).

Модуль auth (auth_module) покрыт unit-тестами в test_auth/ — здесь проверяем
HTTP-уровень: коды ответов, сообщения об ошибках, работу guard'ов.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.auth import auth_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestLogin:
    @patch('routes.auth.auth_module.update_last_login')
    @patch('routes.auth.auth_module.issue_token')
    @patch('routes.auth.auth_module.verify_password')
    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_success(self, m_db, m_get_user, m_verify, m_issue_token, m_update_login, client):
        # DB-пользователь с верным паролем: роут находит пользователя, проверяет пароль,
        # выпускает токен через issue_token и обновляет last_login через update_last_login.
        m_get_user.return_value = {'id': 1, 'username': 'testuser', 'password_hash': 'hash123', 'role': 'user', 'source': 'db'}
        m_verify.return_value = True
        m_issue_token.return_value = 'abc123'
        m_update_login.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'testuser', 'password': 'secret'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['token'] == 'abc123'
        assert data['user']['id'] == 1
        m_get_user.assert_called_once_with(conn, 'testuser')
        m_verify.assert_called_once_with('secret', 'hash123')
        m_issue_token.assert_called_once_with(conn, 1)

    @patch('routes.auth.auth_module.update_file_user_last_login')
    @patch('routes.auth.auth_module.issue_token')
    @patch('routes.auth.auth_module.verify_password')
    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_existing_user(self, m_db, m_get_user, m_verify, m_issue_token, m_update_file_login, client):
        # Файловый пользователь (source='file') — last_login обновляется отдельной функцией.
        m_get_user.return_value = {'id': 1, 'username': 'existing', 'password_hash': 'hash123', 'role': 'user', 'source': 'file'}
        m_verify.return_value = True
        m_issue_token.return_value = 'abc123'
        m_update_file_login.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'existing', 'password': 'secret'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['token'] == 'abc123'
        m_issue_token.assert_called_once_with(conn, 1)
        m_update_file_login.assert_called_once_with(1)

    @patch('routes.auth.auth_module.verify_password')
    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_bad_password_401(self, m_db, m_get_user, m_verify, client):
        m_get_user.return_value = {'id': 1, 'username': 'existing', 'password_hash': 'hash123', 'role': 'user', 'source': 'db'}
        m_verify.return_value = False

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'existing', 'password': 'wrong'})
        assert r.status_code == 401
        data = r.get_json()
        assert data['error'] == 'Неверный логин или пароль'

    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_empty_body_401(self, m_db, m_get_user, client):
        # Роут login не имеет отдельной валидации пустого тела: пустой username
        # не находится, пароль не проверяется → 401.
        m_get_user.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={})
        assert r.status_code == 401
        data = r.get_json()
        assert data['error'] == 'Неверный логин или пароль'


class TestMe:
    @patch('routes.auth.auth_module.get_user_from_token')
    @patch('routes.auth.db_connection')
    def test_me_success(self, m_db, m_get_user, client):
        m_get_user.return_value = {'id': 1, 'username': 'testuser', 'role': 'user'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/auth/me', headers={'Authorization': 'Bearer validtoken'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1
        assert data['username'] == 'testuser'

    @patch('routes.auth.auth_module.get_user_from_token')
    @patch('routes.auth.db_connection')
    def test_me_not_authenticated_401(self, m_db, m_get_user, client):
        m_get_user.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/auth/me')
        assert r.status_code == 401
        data = r.get_json()
        assert 'Требуется авторизация' in data['error']


class TestLogout:
    @patch('routes.auth.auth_module.revoke_token')
    @patch('routes.auth.db_connection')
    def test_logout_success(self, m_db, m_revoke, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/logout')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_revoke.assert_not_called()  # logout не требует валидации токена

    @patch('routes.auth.auth_module.get_user_from_token')
    @patch('routes.auth.db_connection')
    def test_logout_invalid_token_still_works(self, m_db, m_get_user, client):
        m_get_user.return_value = None  # токен невалидный, но logout всё равно работает

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/logout')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True


class TestAdminUsersList:
    @patch('routes.auth.auth_module.list_users')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_list_users_success(self, m_db, m_require_admin, m_list_users, client):
        m_require_admin.return_value = None  # admin
        m_list_users.return_value = [
            {'id': 1, 'username': 'user1', 'role': 'user'},
            {'id': 2, 'username': 'admin1', 'role': 'admin'},
        ]

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/auth/admin/users')
        assert r.status_code == 200
        data = r.get_json()
        # Роут отдаёт jsonify(users) — плоский JSON-массив, без обёртки {'users': [...]}
        assert len(data) == 2
        assert data[0]['username'] == 'user1'

    @patch('routes.auth._require_admin')
    def test_list_users_forbidden_non_admin(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.get('/api/auth/admin/users')
        assert r.status_code == 403


class TestAdminCreateUser:
    @patch('routes.auth.auth_module.create_file_user')
    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_create_user_success(self, m_db, m_cur, m_require_admin, m_get_user, m_create_file, client):
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = None  # пользователя с таким логином нет
        m_create_file.return_value = 3  # id нового файлового пользователя

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users', json={
            'username': 'newuser',
            'password': 'secret',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 3
        m_create_file.assert_called_once_with('newuser', 'secret', role='user', crew_id=None)

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_create_user_forbidden(self, m_cur, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 1, 'role': 'user', 'source': 'db'}

        r = client.post('/api/auth/admin/users', json={'username': 'newuser', 'password': 'secret'})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_create_user_empty_username_400(self, m_db, m_cur, m_require_admin, client):
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users', json={'username': ''})
        assert r.status_code == 400
        data = r.get_json()
        assert 'Логин и пароль' in data['error']


class TestAdminUserEdit:
    @patch('routes.auth.auth_module.update_user_crew_id')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth.crew_repo')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_user_crew_id_success(self, m_db, m_cur, m_require_admin, m_crew_repo, m_get_user, m_update, client):
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'edituser', 'role': 'user', 'source': 'db'}
        m_crew_repo.get_by_id.return_value = {'id': 100, 'name': 'Test Crew'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 100})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_update.assert_called_once_with(conn, 1, 100)

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_edit_user_forbidden(self, m_cur, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 1, 'role': 'user', 'source': 'db'}  # обычный пользователь

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 100})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_user_invalid_crew_id_400(self, m_db, m_cur, m_require_admin, client):
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 'invalid'})
        assert r.status_code == 400
        data = r.get_json()
        assert 'crew_id' in data['error']

    @patch('routes.auth.auth_module.update_user_crew_id')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_user_unlink_crew_success(self, m_db, m_cur, m_require_admin, m_get_user, m_update, client):
        """crew_id: null — отвязка учётки от записи в справочнике crew."""
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'edituser', 'role': 'user', 'source': 'db'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': None})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_update.assert_called_once_with(conn, 1, None)

    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_user_not_found_404(self, m_db, m_cur, m_require_admin, m_get_user, client):
        """Несуществующий user_id -> 404."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = None  # пользователя с id=999 нет

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/999', json={'crew_id': 100})
        assert r.status_code == 404
        data = r.get_json()
        assert 'Пользователь не найден' in data['error']

    @patch('routes.auth.crew_repo')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_user_nonexistent_crew_400(self, m_db, m_cur, m_require_admin, m_get_user, m_crew_repo, client):
        """Существующий пользователь + несуществующий crew_id -> 400."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'edituser', 'role': 'user', 'source': 'db'}
        m_crew_repo.get_by_id.return_value = None  # crew с id=999 нет

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 999})
        assert r.status_code == 400
        data = r.get_json()
        assert 'не найден' in data['error']

    @patch('routes.auth.auth_module.update_file_user_crew_id')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth.crew_repo')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_edit_file_user_crew_id_success(self, m_db, m_cur, m_require_admin, m_crew_repo, m_get_user, m_update_file, client):
        """Файловый пользователь (source='file') — привязка через update_file_user_crew_id."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 5, 'username': 'fileuser', 'role': 'user', 'source': 'file'}
        m_crew_repo.get_by_id.return_value = {'id': 100, 'name': 'Test Crew'}
        m_update_file.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/5', json={'crew_id': 100})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_update_file.assert_called_once_with(5, 100)


class TestAdminUserRoleChange:
    """Смена роли существующего пользователя через PATCH /admin/users/<id>.

    Действующий пользователь попадает в request.current_user: в тестовом
    приложении before_app_request (load_current_user) вызывает именно
    routes.auth.get_current_user, поэтому она и подменяется.

    Границы прав: роль admin выдаёт и снимает только суперадмин (как при
    создании/удалении), роль superadmin через эту функцию не назначается и
    не снимается вообще ни для кого (только при создании пользователя),
    свою роль менять нельзя.
    """

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_superadmin_success(self, m_db, m_cur, m_require_admin,
                                            m_get_user, m_update, client):
        """Суперадмин повышает обычного пользователя до admin."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/2', json={'role': 'admin'})
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        m_update.assert_called_once_with(conn, 2, 'admin')

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_admin_demotes_user_to_reader(self, m_db, m_cur, m_require_admin,
                                                      m_get_user, m_update, client):
        """Обычный админ может выдать младшую роль (reader) обычному пользователю."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/2', json={'role': 'reader'})
        assert r.status_code == 200
        m_update.assert_called_once_with(conn, 2, 'reader')

    @patch('routes.auth.auth_module.update_file_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_file_user_success(self, m_db, m_cur, m_require_admin,
                                           m_get_user, m_update_file, client):
        """Файловый пользователь (source='file') — роль через update_file_user_role."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 1000000001, 'username': 'file_op',
                                   'role': 'user', 'source': 'file'}
        m_update_file.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1000000001', json={'role': 'reader'})
        assert r.status_code == 200
        m_update_file.assert_called_once_with(1000000001, 'reader')


    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_and_crew_id_together(self, m_db, m_cur, m_require_admin,
                                              m_get_user, m_update, client):
        """Оба ключа в одном PATCH применяются независимо."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        with patch('routes.auth.crew_repo') as m_crew_repo, \
                patch('routes.auth.auth_module.update_user_crew_id') as m_update_crew:
            m_crew_repo.get_by_id.return_value = {'id': 5, 'full_name': 'Петров Пётр'}
            m_update_crew.return_value = True
            r = client.patch('/api/auth/admin/users/2', json={'role': 'admin', 'crew_id': 5})
        assert r.status_code == 200
        m_update.assert_called_once_with(conn, 2, 'admin')
        m_update_crew.assert_called_once_with(conn, 2, 5)

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_same_value_is_noop(self, m_db, m_cur, m_require_admin,
                                            m_get_user, m_update, client):
        """Повторная отправка той же роли — 200 без записи в хранилище."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'reader', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/2', json={'role': 'reader'})
        assert r.status_code == 200
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_admin_cannot_assign_admin_role(self, m_db, m_cur, m_require_admin,
                                            m_get_user, m_update, client):
        """Обычный админ не может выдать роль admin — как и при создании."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/2', json={'role': 'admin'})
        assert r.status_code == 403
        assert 'суперадмин' in r.get_json()['error'].lower()
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_cannot_raise_to_superadmin(self, m_db, m_cur, m_require_admin,
                                       m_get_user, m_update, client):
        """Повысить до superadmin через смену роли нельзя никому — даже
        суперадмину: эта роль задаётся только при создании пользователя."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/2', json={'role': 'superadmin'})
        assert r.status_code == 400
        assert 'superadmin' in r.get_json()['error']
        assert 'создании' in r.get_json()['error'].lower()
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_cannot_change_superadmin_target(self, m_db, m_cur, m_require_admin,
                                            m_get_user, m_update, client):
        """Понизить пользователя с ролью superadmin нельзя никому — ни
        обычному админу, ни другому суперадмину."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'root', 'role': 'superadmin', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        for role in ('admin', 'user', 'reader'):
            r = client.patch('/api/auth/admin/users/1', json={'role': role})
            assert r.status_code == 400, role
            assert 'superadmin' in r.get_json()['error']
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_admin_cannot_change_admin_target(self, m_db, m_cur, m_require_admin,
                                             m_get_user, m_update, client):
        """Обычный админ не может снять роль с admin (как при удалении)."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 3, 'username': 'chief', 'role': 'admin', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/3', json={'role': 'user'})
        assert r.status_code == 403
        assert 'администратор' in r.get_json()['error'].lower()
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_superadmin_cannot_change_own_role(self, m_db, m_cur, m_require_admin,
                                              m_get_user, m_update, client):
        """Свою роль не меняет и суперадмин: его роль вообще не может быть
        целью смены роли, так что ответ — 400 про superadmin."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'root', 'role': 'superadmin', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        for role in ('admin', 'user', 'reader'):
            r = client.patch('/api/auth/admin/users/1', json={'role': role})
            assert r.status_code == 400, role
            assert 'superadmin' in r.get_json()['error']
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_admin_cannot_change_own_role(self, m_db, m_cur, m_require_admin,
                                          m_get_user, m_update, client):
        """Защита от самоблокировки: admin не может поменять роль себе."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 10, 'username': 'adm', 'role': 'admin', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        for role in ('user', 'reader'):
            r = client.patch('/api/auth/admin/users/10', json={'role': role})
            assert r.status_code == 400, role
            assert 'собственную' in r.get_json()['error'].lower()
        m_update.assert_not_called()

    @patch('routes.auth.auth_module.update_user_role')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_role_invalid_400(self, m_db, m_cur, m_require_admin,
                                     m_get_user, m_update, client):
        """Значение роли вне _ALLOWED_ROLES (в т.ч. null) — 400."""
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 10, 'role': 'superadmin', 'source': 'db'}
        m_get_user.return_value = {'id': 2, 'username': 'petrov', 'role': 'user', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        for bad in ('god', '', None, 42):
            r = client.patch('/api/auth/admin/users/2', json={'role': bad})
            assert r.status_code == 400, bad
            assert 'Недопустимая роль' in r.get_json()['error']
        m_update.assert_not_called()

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_change_role_forbidden_non_admin(self, m_cur, m_require_admin, client):
        """Без прав администратора — 403 (тот же гейт, что у остальных admin-роутов)."""
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 2, 'role': 'user', 'source': 'db'}

        r = client.patch('/api/auth/admin/users/3', json={'role': 'reader'})
        assert r.status_code == 403


class TestAdminUserDelete:
    @patch('routes.auth.auth_module.delete_user')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth._is_admin_role')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_delete_user_success(self, m_db, m_cur, m_is_admin, m_require_admin, m_get_user, m_delete, client):
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 99, 'role': 'admin', 'source': 'db'}  # другой админ
        m_is_admin.return_value = False  # удаляемый пользователь не admin
        m_get_user.return_value = {'id': 1, 'username': 'todelete', 'role': 'user', 'source': 'db'}
        m_delete.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/auth/admin/users/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_delete.assert_called_once_with(conn, 1)

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_delete_user_forbidden(self, m_cur, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 1, 'role': 'user', 'source': 'db'}

        r = client.delete('/api/auth/admin/users/1')
        assert r.status_code == 403

    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_delete_user_not_found_404(self, m_db, m_cur, m_require_admin, m_get_user, client):
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 99, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = None  # пользователь с id=999 не найден
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/auth/admin/users/999')
        assert r.status_code == 404
        data = r.get_json()
        assert 'не найден' in data['error'].lower()


class TestAdminUserPassword:
    @patch('routes.auth.auth_module.update_user_password')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_password_success(self, m_db, m_cur, m_require_admin, m_get_user, m_update, client):
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 99, 'role': 'admin', 'source': 'db'}
        m_get_user.return_value = {'id': 1, 'username': 'user1', 'role': 'user', 'source': 'db'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users/1/password', json={'password': 'newpass123'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_update.assert_called_once_with(conn, 1, 'newpass123')

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_change_password_forbidden(self, m_cur, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 1, 'role': 'user', 'source': 'db'}

        r = client.post('/api/auth/admin/users/1/password', json={'password': 'newpass'})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_change_password_short_400(self, m_db, m_cur, m_require_admin, client):
        m_require_admin.return_value = None
        m_cur.return_value = {'id': 1, 'role': 'admin', 'source': 'db'}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users/1/password', json={'password': 'abc'})
        assert r.status_code == 400
        data = r.get_json()
        assert 'короче 6' in data['error']


class TestAdminUserRevoke:
    @patch('routes.auth.auth_module.revoke_all_for_user')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    @patch('routes.auth.db_connection')
    def test_revoke_success(self, m_db, m_cur, m_require_admin, m_revoke, client):
        m_require_admin.return_value = None  # admin
        m_cur.return_value = {'id': 99, 'role': 'admin', 'source': 'db'}
        m_revoke.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users/1/revoke')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_revoke.assert_called_once_with(conn, 1)

    @patch('routes.auth._require_admin')
    @patch('routes.auth.get_current_user')
    def test_revoke_forbidden(self, m_cur, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)
        m_cur.return_value = {'id': 1, 'role': 'user', 'source': 'db'}

        r = client.post('/api/auth/admin/users/1/revoke')
        assert r.status_code == 403