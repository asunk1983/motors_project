"""Тесты HTTP-слоя членов экипажа (routes/crew_routes.py).

crew_bp — /api/crew, /api/crew/<id>.

Модуль crew_repo покрыт тестами в test_repositories/test_crew_repo.py —
здесь проверяем HTTP-уровень: коды ответов, сообщения, работу guard'ов.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.crew_routes import crew_bp


def _conn_context_mock():
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=MagicMock())
    m.__exit__ = MagicMock(return_value=False)
    return m


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(crew_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetCrew:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_get_crew_success(self, m_db, m_repo, client):
        m_repo.list_all.return_value = [
            (1, "Член 1", "engineer"),
        ]
        m_db.return_value = _conn_context_mock()
        r = client.get("/api/crew")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["members"]) == 1
        assert data["members"][0]["id"] == 1
        assert data["members"][0]["name"] == "Член 1"


class TestCreateCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_create_success_as_admin(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None  # admin
        m_repo.create.return_value = 10
        m_db.return_value = _conn_context_mock()
        r = client.post("/api/crew", json={
            "name": "Новый член",
            "role": "engineer",
            "phone": "123",
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data["member"]["id"] == 10
        assert data["member"]["name"] == "Новый член"
        m_repo.create.assert_called_once_with(
            MagicMock(), "Новый член", "engineer", "123"
        )

    @patch("routes.crew_routes._require_admin")
    def test_create_forbidden_non_admin(self, m_require_admin, client):
        m_require_admin.return_value = ("Доступ запрещён", 403)
        r = client.post("/api/crew", json={
            "name": "Член",
        })
        assert r.status_code == 403

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_create_empty_name_400(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None
        m_db.return_value = _conn_context_mock()
        r = client.post("/api/crew", json={
            "name": "",
            "role": "engineer",
        })
        assert r.status_code == 400

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_create_duplicate_name_409(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None
        m_repo.create.side_effect = Exception("UNIQUE constraint failed")
        m_db.return_value = _conn_context_mock()
        r = client.post("/api/crew", json={
            "name": "Уже существует",
            "role": "engineer",
        })
        assert r.status_code == 409


class TestUpdateCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_update_success_as_admin(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None  # admin
        m_repo.update.return_value = True
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/1", json={
            "name": "Обновлённый",
            "role": "technician",
        })
        assert r.status_code == 200
        m_repo.update.assert_called_once_with(
            MagicMock(), 1, "Обновлённый", "technician", None
        )

    @patch("routes.crew_routes._require_admin")
    def test_update_forbidden_non_admin(self, m_require_admin, client):
        m_require_admin.return_value = ("Доступ запрещён", 403)
        r = client.put("/api/crew/1", json={"name": "Новый"})
        assert r.status_code == 403

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_update_not_found_404(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None
        m_repo.update.return_value = False
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/99999", json={"name": "Новый"})
        assert r.status_code == 404

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_update_empty_name_400(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/1", json={
            "name": "",
        })
        assert r.status_code == 400


class TestDeleteCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_delete_success_as_admin(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None  # admin
        m_repo.delete.return_value = True
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        m_repo.delete.assert_called_once_with(MagicMock(), 1)

    @patch("routes.crew_routes._require_admin")
    def test_delete_forbidden_non_admin(self, m_require_admin, client):
        m_require_admin.return_value = ("Доступ запрещён", 403)
        r = client.delete("/api/crew/1")
        assert r.status_code == 403

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_delete_not_found_404(self, m_db, m_repo, client):
        m_repo.delete.return_value = False
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/99999")
        assert r.status_code == 404

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes._require_admin")
    @patch("routes.crew_routes.db_connection")
    def test_delete_referenced_raises_400(self, m_db, m_require_admin, m_repo, client):
        m_require_admin.return_value = None
        m_repo.is_referenced.return_value = True
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/1")
        assert r.status_code == 400
        data = r.get_json()
        assert "используется" in data["error"].lower() or "referenced" in data["error"].lower()


class TestGetCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_get_crew_member_success(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = (1, "Член 1", "engineer", "123")
        m_db.return_value = _conn_context_mock()
        r = client.get("/api/crew/1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["member"]["id"] == 1
        assert data["member"]["name"] == "Член 1"

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_get_crew_member_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_context_mock()
        r = client.get("/api/crew/99999")
        assert r.status_code == 404