"""Тесты HTTP-слоя заявок Инцидентов (routes/incident_ticket_routes.py).

Покрывает эндпоинты:
  - CRUD заявки: list, create, get, patch, delete;
  - location-counts, привязка/отвязка оборудования, фото, экспорт.

Паттерн — как в существующих route-тестах проекта (test_engines.py,
test_crew_routes.py): db_connection и repo-функции мокаются на уровне модуля
роута; текущий пользователь — мок _current_user_id; admin-гейт удаления —
мок _require_admin.

ВАЖНО: никакие файловые операции (фото, экспорт) реально не выполняются —
incident_manager и export_service мокаются, на диск ничего не пишется.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.incident_ticket_routes import incident_ticket_bp


def _conn_mock():
    """Контекст-менеджер-мок для db_connection (паттерн test_auth_routes)."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=MagicMock())
    m.__exit__ = MagicMock(return_value=False)
    return m


def _ticket_row(ticket_id=1, **overrides):
    row = {
        'id': ticket_id,
        'location_node_id': 5,
        'problem': 'Течь насоса',
        'priority': 'medium',
        'status': 'in_progress',
        'created_by_user_id': 1,
    }
    row.update(overrides)
    return row


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(incident_ticket_bp)  # у bp уже есть url_prefix='/api/incident-tickets'
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------
# Список заявок
# ---------------------------------------------------------------------
class TestListTickets:
    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_list_tickets_success(self, m_db, m_repo, client):
        m_repo.list_all.return_value = [_ticket_row()]
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets')
        assert r.status_code == 200
        assert r.get_json()[0]['id'] == 1

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_list_tickets_filters_passed(self, m_db, m_repo, client):
        m_repo.list_all.return_value = []
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets?status=in_progress&priority=high&location_node_id=5')
        assert r.status_code == 200
        args, kwargs = m_repo.list_all.call_args
        assert kwargs.get('status') == 'in_progress'
        assert kwargs.get('priority') == 'high'
        assert kwargs.get('location_node_id') == 5


# ---------------------------------------------------------------------
# Создание заявки
# ---------------------------------------------------------------------
class TestCreateTicket:
    @patch('routes.incident_ticket_routes._current_user_id')
    def test_create_ticket_requires_user_401(self, m_user_id, client):
        m_user_id.return_value = None
        r = client.post('/api/incident-tickets', json={
            'location_node_id': 5, 'problem': 'Течь',
        })
        assert r.status_code == 401
        assert 'пользователя' in r.get_json()['error'].lower()

    @patch('routes.incident_ticket_routes._current_user_id')
    def test_create_ticket_location_required_400(self, m_user_id, client):
        m_user_id.return_value = 1
        r = client.post('/api/incident-tickets', json={'problem': 'Течь'})
        assert r.status_code == 400
        assert 'Место обязательно' == r.get_json()['error']

    @patch('routes.incident_ticket_routes._current_user_id')
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_create_ticket_success(self, m_db, m_service, m_user_id, client):
        m_user_id.return_value = 1
        m_service.create_ticket.return_value = (42, None)
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets', json={
            'location_node_id': 5, 'problem': 'Течь насоса',
            'initiator_ids': [1],
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 42

    @patch('routes.incident_ticket_routes._current_user_id')
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_create_ticket_service_error_400(self, m_db, m_service, m_user_id, client):
        m_user_id.return_value = 1
        m_service.create_ticket.return_value = (None, 'Указанное место не найдено')
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets', json={
            'location_node_id': 999, 'problem': 'Течь', 'initiator_ids': [1],
        })
        assert r.status_code == 400
        assert 'место' in r.get_json()['error'].lower()
# ---------------------------------------------------------------------
# Получение заявки
# ---------------------------------------------------------------------
class TestGetTicket:
    @patch('routes.incident_ticket_routes.incident_manager')
    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_get_ticket_success(self, m_db, m_repo, m_manager, client):
        m_repo.get_by_id.return_value = _ticket_row()
        m_manager.get_ticket_photos.return_value = []
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets/1')
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1
        assert data['photos'] == []

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_get_ticket_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets/999')
        assert r.status_code == 404
        assert 'не найдена' in r.get_json()['error'].lower()


# ---------------------------------------------------------------------
# Обновление заявки
# ---------------------------------------------------------------------
class TestUpdateTicket:
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_update_ticket_success(self, m_db, m_service, client):
        m_service.update_ticket.return_value = (True, None)
        m_db.return_value = _conn_mock()
        r = client.patch('/api/incident-tickets/1', json={'problem': 'Новая проблема'})
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        m_service.update_ticket.assert_called_once()

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_update_ticket_not_found_404(self, m_db, m_service, client):
        m_service.update_ticket.return_value = (False, 'Заявка не найдена')
        m_db.return_value = _conn_mock()
        r = client.patch('/api/incident-tickets/999', json={'problem': 'X'})
        assert r.status_code == 404
        assert 'не найдена' in r.get_json()['error'].lower()

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_update_ticket_validation_400(self, m_db, m_service, client):
        m_service.update_ticket.return_value = (False, 'Недопустимый статус: closed')
        m_db.return_value = _conn_mock()
        r = client.patch('/api/incident-tickets/1', json={'status': 'closed'})
        assert r.status_code == 400
        assert 'статус' in r.get_json()['error'].lower()


# ---------------------------------------------------------------------
# Удаление заявки (только admin)
# ---------------------------------------------------------------------
class TestDeleteTicket:
    @patch('routes.incident_ticket_routes._require_admin')
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.incident_manager')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_delete_ticket_success(self, m_db, m_manager, m_service, m_require, client):
        m_require.return_value = None
        m_service.delete_ticket.return_value = (True, None)
        # фото удаляются только через мок — реального доступа к диску нет
        m_manager.delete_ticket_photos_from_disk.return_value = (0, [])
        m_db.return_value = _conn_mock()
        r = client.delete('/api/incident-tickets/1')
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        m_manager.delete_ticket_photos_from_disk.assert_called_once_with(1)

    @patch('routes.incident_ticket_routes._require_admin')
    def test_delete_ticket_forbidden_non_admin(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль admin)'}, 403)
        r = client.delete('/api/incident-tickets/1')
        assert r.status_code == 403

    @patch('routes.incident_ticket_routes._require_admin')
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_delete_ticket_not_found_404(self, m_db, m_service, m_require, client):
        m_require.return_value = None
        m_service.delete_ticket.return_value = (False, 'Заявка не найдена')
        m_db.return_value = _conn_mock()
        r = client.delete('/api/incident-tickets/999')
        assert r.status_code == 404
# ---------------------------------------------------------------------
# Счётчики по местам
# ---------------------------------------------------------------------
class TestLocationCounts:
    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_location_counts_success(self, m_db, m_repo, client):
        m_repo.get_location_counts.return_value = {5: 2}
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets/location-counts')
        assert r.status_code == 200
        # jsonify -> строковые ключи
        assert r.get_json() == {'5': 2}


# ---------------------------------------------------------------------
# Привязка/отвязка оборудования
# ---------------------------------------------------------------------
class TestEquipmentLinks:
    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_add_equipment_missing_id_400(self, m_db, m_service, client):
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/1/equipment', json={})
        assert r.status_code == 400
        assert 'equipment_id' in r.get_json()['error']
        m_service.add_equipment_link.assert_not_called()

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_add_equipment_success(self, m_db, m_service, client):
        m_service.add_equipment_link.return_value = (True, None)
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/1/equipment', json={'equipment_id': 3})
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_add_equipment_link_error_404(self, m_db, m_service, client):
        m_service.add_equipment_link.return_value = (False, 'Заявка не найдена')
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/999/equipment', json={'equipment_id': 3})
        assert r.status_code == 404

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_remove_equipment_success(self, m_db, m_service, client):
        m_service.remove_equipment_link.return_value = (True, None)
        m_db.return_value = _conn_mock()
        r = client.delete('/api/incident-tickets/1/equipment/3')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.incident_ticket_routes.incident_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_remove_equipment_error_404(self, m_db, m_service, client):
        m_service.remove_equipment_link.return_value = (False, 'Связь не найдена')
        m_db.return_value = _conn_mock()
        r = client.delete('/api/incident-tickets/1/equipment/999')
        assert r.status_code == 404
# ---------------------------------------------------------------------
# Фото заявки — только моки, диск не трогается
# ---------------------------------------------------------------------
class TestTicketPhotos:
    @patch('routes.incident_ticket_routes.incident_manager')
    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_get_photos_success(self, m_db, m_repo, m_manager, client):
        m_repo.get_by_id.return_value = _ticket_row()
        m_manager.get_ticket_photos.return_value = [{'filename': 'ID1_1.jpg'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets/1/photos')
        assert r.status_code == 200
        assert r.get_json()[0]['filename'] == 'ID1_1.jpg'

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_get_photos_ticket_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/incident-tickets/999/photos')
        assert r.status_code == 404

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.incident_manager')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_upload_photos_success(self, m_db, m_manager, m_repo, client):
        m_repo.get_by_id.return_value = _ticket_row()
        m_manager.upload_ticket_photos.return_value = (
            {'success': True, 'uploaded': 1, 'skipped': 0}, 200,
        )
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/1/photos',
                        data={'photos': (b'abc', 'x.jpg')},
                        content_type='multipart/form-data')
        assert r.status_code == 200
        assert r.get_json()['uploaded'] == 1

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_upload_photos_ticket_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/999/photos',
                        data={'photos': (b'abc', 'x.jpg')},
                        content_type='multipart/form-data')
        assert r.status_code == 404

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.incident_manager')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_replace_photo_success(self, m_db, m_manager, m_repo, client):
        m_repo.get_by_id.return_value = _ticket_row()
        m_manager.replace_ticket_photo.return_value = (
            {'success': True, 'message': 'Фото заменено'}, 200,
        )
        m_db.return_value = _conn_mock()
        r = client.put('/api/incident-tickets/1/photos/ID1_1.jpg',
                       data={'photo': (b'abc', 'y.jpg')},
                       content_type='multipart/form-data')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.incident_ticket_routes.incident_ticket_repo')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_replace_photo_ticket_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/incident-tickets/999/photos/ID1_1.jpg',
                       data={'photo': (b'abc', 'y.jpg')},
                       content_type='multipart/form-data')
        assert r.status_code == 404

    @patch('routes.incident_ticket_routes.incident_manager')
    def test_delete_photo_success(self, m_manager, client):
        m_manager.delete_ticket_photo.return_value = (
            {'success': True, 'message': 'Фото удалено'}, 200,
        )
        r = client.delete('/api/incident-tickets/1/photos/ID1_1.jpg')
        assert r.status_code == 200
        assert r.get_json()['success'] is True


# ---------------------------------------------------------------------
# Экспорт заявок — только моки, файл не создаётся на диске
# ---------------------------------------------------------------------
class TestExportTickets:
    def test_export_no_ids_400(self, client):
        r = client.post('/api/incident-tickets/export', json={})
        assert r.status_code == 400
        assert 'Не выбрано' in r.get_json()['error']

    def test_export_too_many_ids_400(self, client):
        r = client.post('/api/incident-tickets/export', json={'ids': list(range(101))})
        assert r.status_code == 400
        assert 'Слишком много' in r.get_json()['error']

    @patch('routes.incident_ticket_routes.export_service')
    @patch('routes.incident_ticket_routes.db_connection')
    def test_export_success(self, m_db, m_export, client):
        m_export.export_incidents_to_xlsx.return_value = b'PK\x03\x04fake-xlsx'
        m_db.return_value = _conn_mock()
        r = client.post('/api/incident-tickets/export', json={'ids': [1, 2]})
        assert r.status_code == 200
        assert r.data == b'PK\x03\x04fake-xlsx'
        assert 'spreadsheetml' in r.headers.get('Content-Type', '')
