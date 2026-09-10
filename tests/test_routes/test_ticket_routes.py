"""Тесты HTTP-слоя заявок (routes/ticket_routes.py).

ticket_bp (url_prefix='/api') — эндпоинты: /tickets, /ticket/<id>, /ticket (POST),
/ticket/<id> (PUT), /ticket/<id>/status, /ticket/<id>/confirm-failure,
/failure/<id>/work, /work/<id> (DELETE), /maintenance-action-types.

Repo-тесты и HTTP-тесты покрывают одинаковые функции: репозиторий — низкоуровневые
SQL-запросы, HTTP-роуты — валидацию входящих данных, коды ответов, права доступа.

Все эндпоинты открыты всем ролям (глобальный гейт auth_bp.before_app_request
обеспечивает авторизацию для пишущих запросов) — точечных проверок ролей здесь нет.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.ticket_routes import ticket_bp

# ---------------------------------------------------------------------
# фикстуры
# ---------------------------------------------------------------------
@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(ticket_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------
# ticket CRUD
# ---------------------------------------------------------------------
class TestTicketRoutes:
    @patch('routes.ticket_routes.db_connection')
    def test_get_tickets_empty(self, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute().fetchall.return_value = []

        r = client.get('/api/tickets')
        assert r.status_code == 200
        data = r.get_json()
        assert data == []

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.list_tickets')
    def test_get_tickets_with_status(self, m_list_tickets, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        m_list_tickets.return_value = [
            {'id': 1, 'title': 'Test ticket', 'status': 'new'},
        ]

        r = client.get('/api/tickets?status=new')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]['title'] == 'Test ticket'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.list_tickets')
    def test_get_tickets_with_equipment_filter(self, m_list_tickets, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        m_list_tickets.return_value = [
            {'id': 1, 'title': 'Ticket for equipment 1'},
        ]

        r = client.get('/api/tickets?equipment=1')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.get_ticket_by_id')
    def test_get_ticket_success(self, m_get_ticket, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        m_get_ticket.return_value = {
            'id': 1,
            'title': 'Test ticket',
            'status': 'new',
            'failure_ids': [],
        }

        r = client.get('/api/ticket/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1
        assert data['title'] == 'Test ticket'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.get_ticket_by_id')
    def test_get_ticket_not_found(self, m_get_ticket, m_db, client):
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        m_get_ticket.return_value = None

        r = client.get('/api/ticket/99999')
        assert r.status_code == 404
        data = r.get_json()
        assert 'не найдена' in data['error']

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes._current_user_id')
    @patch('routes.ticket_routes.create_ticket')
    @patch('routes.ticket_routes.validate_ticket_payload')
    @patch('routes.ticket_routes.sanitize_ticket_data')
    def test_create_ticket_success(self, m_sanitize, m_validate, m_create, m_user_id, m_db, client):
        m_user_id.return_value = 1
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {
            'title': 'New ticket',
            'description': 'Desc',
            'equipment_id': 1,
        }
        m_create.return_value = 123

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/ticket', json={
            'title': 'New ticket',
            'description': 'Desc',
            'equipment_id': 1,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 123
        assert data['message'] == 'Заявка создана'

    @patch('routes.ticket_routes.validate_ticket_payload')
    def test_create_ticket_invalid_payload(self, m_validate, client):
        m_validate.return_value = (False, 'title is required')

        r = client.post('/api/ticket', json={})
        assert r.status_code == 400
        data = r.get_json()
        assert data['error'] == 'title is required'


# ---------------------------------------------------------------------
# ticket update & delete
# ---------------------------------------------------------------------
class TestTicketUpdateDeleteRoutes:
    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes._current_user_id')
    @patch('routes.ticket_routes.update_ticket')
    @patch('routes.ticket_routes.validate_ticket_payload')
    @patch('routes.ticket_routes.sanitize_ticket_data')
    @patch('routes.ticket_routes.get_ticket_by_id')
    def test_update_ticket_success(self, m_get_ticket, m_sanitize, m_validate, m_update, m_user_id, m_db, client):
        m_get_ticket.return_value = {'id': 1, 'title': 'Old'}
        m_user_id.return_value = 1
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'title': 'Updated'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.put('/api/ticket/1', json={'title': 'Updated'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['message'] == 'Заявка обновлена'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes._current_user_id')
    @patch('routes.ticket_routes.update_ticket_status')
    def test_update_ticket_status_success(self, m_update_status, m_user_id, m_db, client):
        m_user_id.return_value = 1
        m_update_status.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.patch('/api/ticket/1/status', json={'status': 'closed'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['message'] == 'Статус заявки обновлён'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.delete_ticket')
    def test_delete_ticket_success(self, m_delete, m_db, client):
        m_delete.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/ticket/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['message'] == 'Заявка удалена'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.delete_ticket')
    def test_delete_ticket_not_found(self, m_delete, m_db, client):
        m_delete.return_value = False

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/ticket/99999')
        assert r.status_code == 404
        data = r.get_json()
        assert 'не найдена' in data['error']


# ---------------------------------------------------------------------
# failure routes
# ---------------------------------------------------------------------
class TestFailureRoutes:
    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes._current_user_id')
    @patch('routes.ticket_routes.update_ticket_status')
    @patch('routes.ticket_routes.create_failure')
    @patch('routes.ticket_routes.get_ticket_by_id')
    @patch('routes.ticket_routes.get_failure_by_id')
    @patch('routes.ticket_routes.validate_failure_payload')
    @patch('routes.ticket_routes.sanitize_failure_data')
    def test_confirm_failure_success(self, m_sanitize, m_validate, m_get_failure, m_get_ticket,
                                     m_create_failure, m_update_status, m_user_id, m_db, client):
        m_get_ticket.return_value = {'id': 1, 'equipment_id': 1}
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'symptom': 'Test symptom'}
        m_create_failure.return_value = 456
        m_update_status.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/ticket/1/confirm-failure', json={
            'failure_mode_id': 1,
            'failure_cause_id': 1,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 456
        assert data['message'] == 'Отказ подтверждён'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.get_failure_by_id')
    @patch('routes.ticket_routes.update_failure')
    @patch('routes.ticket_routes.sanitize_failure_data')
    def test_update_failure_success(self, m_sanitize, m_update, m_get_failure, m_db, client):
        m_get_failure.return_value = {'id': 1, 'symptom': 'Old symptom'}
        m_sanitize.return_value = {'symptom': 'New symptom'}
        m_update.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.put('/api/failure/1', json={'symptom': 'New symptom'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['message'] == 'Отказ обновлён'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.get_failure_by_id')
    def test_update_failure_not_found(self, m_get_failure, m_db, client):
        m_get_failure.return_value = None

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.put('/api/failure/99999', json={})
        assert r.status_code == 404
        data = r.get_json()
        assert 'не найден' in data['error']


# ---------------------------------------------------------------------
# work routes
# ---------------------------------------------------------------------
class TestWorkRoutes:
    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes._current_user_id')
    @patch('routes.ticket_routes.create_work')
    @patch('routes.ticket_routes.get_failure_by_id')
    @patch('routes.ticket_routes.validate_work_payload')
    @patch('routes.ticket_routes.sanitize_work_data')
    def test_create_work_success(self, m_sanitize, m_validate, m_get_failure, m_create_work,
                                 m_user_id, m_db, client):
        m_get_failure.return_value = {'id': 1}
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'description': 'Test work'}
        m_create_work.return_value = 789

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/failure/1/work', json={
            'action_type_id': 1,
            'description': 'Test work',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 789
        assert data['message'] == 'Работа добавлена'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.delete_work')
    def test_delete_work_success(self, m_delete, m_db, client):
        m_delete.return_value = True

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/work/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['message'] == 'Работа удалена'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.delete_work')
    def test_delete_work_not_found(self, m_delete, m_db, client):
        m_delete.return_value = False

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.delete('/api/work/99999')
        assert r.status_code == 404
        data = r.get_json()
        assert 'не найдена' in data['error']


# ---------------------------------------------------------------------
# maintenance action types
# ---------------------------------------------------------------------
class TestMaintenanceActionTypes:
    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.list_maintenance_action_types')
    def test_get_maintenance_action_types_success(self, m_list_types, m_db, client):
        m_list_types.return_value = [
            {'id': 1, 'name': 'Замена'},
            {'id': 2, 'name': 'Ремонт'},
        ]

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/maintenance-action-types')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 2
        assert data[0]['name'] == 'Замена'
        assert data[1]['name'] == 'Ремонт'

    @patch('routes.ticket_routes.db_connection')
    @patch('routes.ticket_routes.list_maintenance_action_types')
    def test_get_maintenance_action_types_empty(self, m_list_types, m_db, client):
        m_list_types.return_value = []

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.get('/api/maintenance-action-types')
        assert r.status_code == 200
        data = r.get_json()
        assert data == []
