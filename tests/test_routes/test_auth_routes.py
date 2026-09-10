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
    @patch('routes.auth.auth_module.login')
    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.auth_module.create_user')
    @patch('routes.auth.auth_module.hash_password')
    @patch('routes.auth.db_connection')
    def test_login_success(self, m_db, m_hash, m_create, m_get_user, m_login, client):
        m_get_user.return_value = None  # нет пользователя — создадим
        m_create.return_value = 1  # id нового пользователя
        m_hash.return_value = 'hashed'
        m_login.return_value = {'token': 'abc123', 'username': 'testuser'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'testuser', 'password': 'secret'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['token'] == 'abc123'
        m_create.assert_called_once_with(conn, 'testuser', 'hashed', 'user')

    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.auth_module.login')
    @patch('routes.auth.db_connection')
    def test_login_existing_user(self, m_db, m_login, m_get_user, client):
        m_get_user.return_value = {'id': 1, 'username': 'existing', 'password_hash': 'hash123', 'role': 'user', 'source': 'db'}
        m_login.return_value = {'token': 'abc123', 'username': 'existing'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'existing', 'password': 'secret'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['token'] == 'abc123'
        m_login.assert_called_once_with(conn, {'id': 1, 'username': 'existing', 'password_hash': 'hash123'})

    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_bad_password_401(self, m_db, m_get_user, client):
        m_get_user.return_value = {'id': 1, 'username': 'existing', 'password_hash': 'hash123', 'role': 'user', 'source': 'db'}

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={'username': 'existing', 'password': 'wrong'})
        assert r.status_code == 401
        data = r.get_json()
        assert data['error'] == 'Неверный пароль'

    @patch('routes.auth.auth_module.get_user_by_username')
    @patch('routes.auth.db_connection')
    def test_login_empty_body_400(self, m_db, m_get_user, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/login', json={})
        assert r.status_code == 400
        data = r.get_json()
        assert 'username' in data['error'] or 'password' in data['error']


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
        assert len(data['users']) == 2
        assert data['users'][0]['username'] == 'user1'

    @patch('routes.auth._require_admin')
    def test_list_users_forbidden_non_admin(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.get('/api/auth/admin/users')
        assert r.status_code == 403


class TestAdminCreateUser:
    @patch('routes.auth.auth_module.create_user')
    @patch('routes.auth.auth_module.hash_password')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_create_user_success(self, m_db, m_require_admin, m_hash, m_create, client):
        m_require_admin.return_value = None  # admin
        m_hash.return_value = 'hashed'
        m_create.return_value = 3  # id нового пользователя

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users', json={
            'username': 'newuser',
            'password': 'secret',
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data['success'] is True
        assert data['user']['id'] == 3
        assert data['user']['username'] == 'newuser'
        m_create.assert_called_once_with(conn, 'newuser', 'hashed', 'user')

    @patch('routes.auth._require_admin')
    def test_create_user_forbidden(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.post('/api/auth/admin/users', json={'username': 'newuser', 'password': 'secret'})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_create_user_empty_username_400(self, m_db, m_require_admin, client):
        m_require_admin.return_value = None
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users', json={'username': ''})
        assert r.status_code == 400
        data = r.get_json()
        assert 'username' in data['error']


class TestAdminUserEdit:
    @patch('routes.auth.auth_module.update_user_crew_id')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth.crew_repo')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_edit_user_crew_id_success(self, m_db, m_require_admin, m_crew_repo, m_get_user, m_update, client):
        m_require_admin.return_value = None  # admin
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
    def test_edit_user_forbidden(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 100})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_edit_user_invalid_crew_id_400(self, m_db, m_require_admin, client):
        m_require_admin.return_value = None
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock.return_value(conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/auth/admin/users/1', json={'crew_id': 'invalid'})
        assert r.status_code == 400
        data = r.get_json()
        assert 'crew_id' in data['error']


class TestAdminUserDelete:
    @patch('routes.auth.auth_module.delete_user')
    @patch('routes.auth.auth_module.get_user_by_id')
    @patch('routes.auth._require_admin')
    @patch('routes.auth._is_admin_role')
    @patch('routes.auth.db_connection')
    def test_delete_user_success(self, m_db, m_is_admin, m_require_admin, m_get_user, m_delete, client):
        m_require_admin.return_value = None  # admin
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
    def test_delete_user_forbidden(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.delete('/api/auth/admin/users/1')
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_delete_user_not_found_404(self, m_db, m_require_admin, client):
        m_require_admin.return_value = None
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
    @patch('routes.auth.db_connection')
    def test_change_password_success(self, m_db, m_require_admin, m_get_user, m_update, client):
        m_require_admin.return_value = None  # admin
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
    def test_change_password_forbidden(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.post('/api/auth/admin/users/1/password', json={'password': 'newpass'})
        assert r.status_code == 403

    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_change_password_short_400(self, m_db, m_require_admin, client):
        m_require_admin.return_value = None
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock.return_value(conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/auth/admin/users/1/password', json={'password': 'abc'})
        assert r.status_code == 400
        data = r.get_json()
        assert 'короче 6' in data['error']


class TestAdminUserRevoke:
    @patch('routes.auth.auth_module.revoke_all_for_user')
    @patch('routes.auth._require_admin')
    @patch('routes.auth.db_connection')
    def test_revoke_success(self, m_db, m_require_admin, m_revoke, client):
        m_require_admin.return_value = None  # admin
        m_revoke.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock.return_value(conn)
        m_db.return_value.__exit__ = MagicMock.return_value(False)

        r = client.post('/api/auth/admin/users/1/revoke')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        m_revoke.assert_called_once_with(conn, 1)

    @patch('routes.auth._require_admin')
    def test_revoke_forbidden(self, m_require_admin, client):
        m_require_admin.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.post('/api/auth/admin/users/1/revoke')
        assert r.status_code == 403