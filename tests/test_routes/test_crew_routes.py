"""Тесты HTTP-слоя справочника людей (routes/crew_routes.py).

crew_bp — /api/crew (GET список, POST создание), /api/crew/search (GET),
/api/crew/<id> (PUT, DELETE). GET /api/crew/<id> в API НЕТ — только PUT/DELETE.

Ролевых проверок в этом blueprint нет (ТЗ раздел 2.1.3: оба пользователя
полноправны, общий гейт «залогинен» висит на auth_bp.before_app_request).

Repo-функции покрыты тестами в test_repositories/test_crew_repo.py —
здесь проверяем HTTP-уровень: коды ответов, сообщения об ошибках.
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


class TestListCrew:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_list_crew_success(self, m_db, m_repo, client):
        m_repo.list_all.return_value = [
            {"id": 1, "full_name": "Член 1", "position": "engineer",
             "workshop": None, "created_at": "2026-01-01T00:00:00"},
        ]
        m_db.return_value = _conn_context_mock()
        r = client.get("/api/crew")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["full_name"] == "Член 1"


class TestSearchCrew:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_search_returns_matches(self, m_db, m_repo, client):
        m_repo.search.return_value = [
            {"id": 2, "full_name": "Иван Иванов", "position": "engineer",
             "workshop": "Цех 1"},
        ]
        m_db.return_value = _conn_context_mock()
        r = client.get("/api/crew/search", query_string={"q": "иван"})
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 2
        assert m_repo.search.call_args.args[1] == "иван"

    def test_search_empty_query_returns_empty_list(self, client):
        r = client.get("/api/crew/search")
        assert r.status_code == 200
        assert r.get_json() == []


class TestCreateCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_create_success(self, m_db, m_repo, client):
        m_repo.create.return_value = 10
        m_db.return_value = _conn_context_mock()
        r = client.post("/api/crew", json={
            "full_name": "Новый член",
            "position": "engineer",
            "workshop": "Цех 1",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["id"] == 10
        assert m_repo.create.call_count == 1
        args, kwargs = m_repo.create.call_args
        assert args[1] == "Новый член"  # full_name
        assert args[2] == "engineer"    # position
        assert args[3] == "Цех 1"       # workshop

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_create_position_and_workshop_optional(self, m_db, m_repo, client):
        m_repo.create.return_value = 11
        m_db.return_value = _conn_context_mock()
        r = client.post("/api/crew", json={"full_name": "Без должности"})
        assert r.status_code == 200
        args, kwargs = m_repo.create.call_args
        assert args[1] == "Без должности"
        assert args[2] is None
        assert args[3] is None

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_create_missing_name_400(self, m_db, m_repo, client):
        r = client.post("/api/crew", json={})
        assert r.status_code == 400
        data = r.get_json()
        assert "ФИО обязательно" in data["error"]
        m_repo.create.assert_not_called()

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_create_blank_name_400(self, m_db, m_repo, client):
        r = client.post("/api/crew", json={"full_name": "   "})
        assert r.status_code == 400
        m_repo.create.assert_not_called()

class TestUpdateCrewMember:
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_update_success(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = {"id": 1, "full_name": "Член 1"}
        m_repo.update.return_value = True
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/1", json={"full_name": "Новое ФИО"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert m_repo.update.call_count == 1
        args, kwargs = m_repo.update.call_args
        assert args[1] == 1
        assert kwargs.get("full_name") == "Новое ФИО"

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_update_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/99999", json={"full_name": "Новый"})
        assert r.status_code == 404
        data = r.get_json()
        assert "не найден" in data["error"].lower()
        m_repo.update.assert_not_called()

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_update_empty_name_400(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = {"id": 1, "full_name": "Член 1"}
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/1", json={"full_name": "   "})
        assert r.status_code == 400
        data = r.get_json()
        assert "пустым" in data["error"].lower()
        m_repo.update.assert_not_called()

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_update_nothing_to_change_400(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = {"id": 1, "full_name": "Член 1"}
        m_repo.update.return_value = False  # полей для обновления не передано
        m_db.return_value = _conn_context_mock()
        r = client.put("/api/crew/1", json={})
        assert r.status_code == 400
        data = r.get_json()
        assert "нечего обновлять" in data["error"].lower()


class TestDeleteCrewMember:
    @patch("routes.crew_routes.incident_service")
    @patch("routes.crew_routes.auth_module")
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_delete_success(self, m_db, m_repo, m_auth, m_incident_service, client):
        m_repo.get_by_id.return_value = {"id": 1, "full_name": "Член 1"}
        m_auth.is_file_crew_referenced.return_value = False
        m_incident_service.delete_crew.return_value = (True, None)
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        m_incident_service.delete_crew.assert_called_once()
        assert m_incident_service.delete_crew.call_args.args[1] == 1

    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_delete_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/99999")
        assert r.status_code == 404
        data = r.get_json()
        assert "не найден" in data["error"].lower()

    @patch("routes.crew_routes.incident_service")
    @patch("routes.crew_routes.auth_module")
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_delete_file_user_referenced_400(self, m_db, m_repo, m_auth, m_incident_service, client):
        m_repo.get_by_id.return_value = {"id": 2, "full_name": "Привязан к учётке"}
        m_auth.is_file_crew_referenced.return_value = True
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/2")
        assert r.status_code == 400
        data = r.get_json()
        assert "привязан" in data["error"].lower()
        m_incident_service.delete_crew.assert_not_called()

    @patch("routes.crew_routes.incident_service")
    @patch("routes.crew_routes.auth_module")
    @patch("routes.crew_routes.crew_repo")
    @patch("routes.crew_routes.db_connection")
    def test_delete_referenced_in_incident_400(self, m_db, m_repo, m_auth, m_incident_service, client):
        m_repo.get_by_id.return_value = {"id": 3, "full_name": "В заявке"}
        m_auth.is_file_crew_referenced.return_value = False
        m_incident_service.delete_crew.return_value = (
            False, "Человек указан хотя бы в одной заявке — удаление невозможно"
        )
        m_db.return_value = _conn_context_mock()
        r = client.delete("/api/crew/3")
        assert r.status_code == 400
        data = r.get_json()
        assert "заявке" in data["error"].lower()

