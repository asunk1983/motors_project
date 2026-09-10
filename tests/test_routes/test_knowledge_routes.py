"""Тесты HTTP-слоя базы знаний (routes/knowledge_routes.py).

knowledge_bp — справочники failure_mode/failure_cause + статьи.
Доступ: справочники на чтение — публичный (any user), все остальные
эндпоинты — только superadmin (через _require_superadmin).
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.knowledge_routes import knowledge_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(knowledge_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestPublicDictionaryRead:
    @patch('routes.knowledge_routes.db_connection')
    def test_get_failure_modes_public(self, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.fetchall.return_value = [
            {'id': 1, 'code': 'FM001', 'name': 'Перегрев'},
        ]

        r = client.get('/api/knowledge/failure-modes')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]['code'] == 'FM001'

    @patch('routes.knowledge_routes.db_connection')
    def test_get_failure_causes_public(self, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.fetchall.return_value = [
            {'id': 1, 'code': 'FC001', 'name': 'Механический износ'},
        ]

        r = client.get('/api/knowledge/failure-causes')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]['code'] == 'FC001'


class TestFailureModeAdminRoutes:
    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_create_failure_mode_success(self, m_db, m_require, client):
        m_require.return_value = None  # superadmin
        conn = MagicMock()
        conn.cursor.return_value.lastrowid = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/knowledge/failure-modes', json={
            'code': 'FM001',
            'name': 'Перегрев',
            'description': 'Повышение температуры',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 1

    @patch('routes.knowledge_routes._require_superadmin')
    def test_create_failure_mode_forbidden_non_superadmin(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль superadmin)'}, 403)

        r = client.post('/api/knowledge/failure-modes', json={
            'code': 'FM001',
            'name': 'Перегрев',
        })
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_delete_failure_mode_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.rowcount = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/knowledge/failure-modes/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_delete_failure_mode_in_use_400(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.rowcount = 1
        conn.cursor.return_value.fetchone.return_value = {'id': 1}  # в_use = True
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/knowledge/failure-modes/1')
        assert r.status_code == 400
        data = r.get_json()
        assert 'используется' in data['error']

    @patch('routes.knowledge_routes._require_superadmin')
    def test_delete_failure_mode_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.delete('/api/knowledge/failure-modes/1')
        assert r.status_code == 403


class TestFailureCauseAdminRoutes:
    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_create_failure_cause_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.lastrowid = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/knowledge/failure-causes', json={
            'code': 'FC001',
            'name': 'Механический износ',
            'description': 'Износ деталей',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 1

    @patch('routes.knowledge_routes._require_superadmin')
    def test_create_failure_cause_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.post('/api/knowledge/failure-causes', json={
            'code': 'FC001',
            'name': 'Test',
        })
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_delete_failure_cause_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.rowcount = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/knowledge/failure-causes/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True

    @patch('routes.knowledge_routes._require_superadmin')
    def test_delete_failure_cause_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.delete('/api/knowledge/failure-causes/1')
        assert r.status_code == 403


class TestArticlesAdminRoutes:
    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_get_articles_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchall.return_value = [
            {'id': 1, 'title': 'Статья А'},
        ]
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/knowledge/articles')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1

    @patch('routes.knowledge_routes._require_superadmin')
    def test_get_articles_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.get('/api/knowledge/articles')
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_get_article_by_id_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = {
            'id': 1, 'title': 'Статья А', 'symptom': 'Symptom',
        }
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/knowledge/article/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_get_article_by_id_not_found(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = None
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/knowledge/article/99999')
        assert r.status_code == 404

    @patch('routes.knowledge_routes._require_superadmin')
    def test_get_article_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.get('/api/knowledge/article/1')
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_create_article_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.lastrowid = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/knowledge/article', json={
            'title': 'Статья А',
            'symptom': 'Symptom',
            'failure_mode_id': 1,
            'diagnostic_steps': 'Steps',
            'recommended_action': 'Action',
            'cause_ids': [1, 2],
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 1

    @patch('routes.knowledge_routes._require_superadmin')
    def test_create_article_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.post('/api/knowledge/article', json={'title': 'Test'})
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_update_article_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = {
            'id': 1, 'title': 'Статья А',
        }
        conn.cursor.return_value.rowcount = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.put('/api/knowledge/article/1', json={
            'title': 'Updated',
            'symptom': 'NewSymptom',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True

    @patch('routes.knowledge_routes._require_superadmin')
    def test_update_article_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.put('/api/knowledge/article/1', json={'title': 'Updated'})
        assert r.status_code == 403

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_update_article_not_found(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = None
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.put('/api/knowledge/article/99999', json={'title': 'Updated'})
        assert r.status_code == 404

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_delete_article_success(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = {'id': 1}
        conn.cursor.return_value.rowcount = 1
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/knowledge/article/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True

    @patch('routes.knowledge_routes._require_superadmin')
    @patch('routes.knowledge_routes.db_connection')
    def test_delete_article_not_found(self, m_db, m_require, client):
        m_require.return_value = None
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = None
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/knowledge/article/99999')
        assert r.status_code == 404

    @patch('routes.knowledge_routes._require_superadmin')
    def test_delete_article_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён'}, 403)

        r = client.delete('/api/knowledge/article/1')
        assert r.status_code == 403