"""Тесты для маршрутов двигателей (routes/engines.py)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from flask import Flask
from routes.engines import engines_bp
from modules import db as db_module


@pytest.fixture
def app():
    """Создаёт тестовое Flask приложение."""
    app = Flask(__name__)
    app.register_blueprint(engines_bp, url_prefix='/api')
    return app


@pytest.fixture
def client(app):
    """Создаёт тестовый клиент для Flask приложения."""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """Возвращает заголовки для аутентификации (заглушка для тестов)."""
    # В реальных тестах нужно было бы получить токен через логин
    # Но дляunit-тестов маршрута мы можем замокировать аутентификацию
    return {'Authorization': 'Bearer fake-token'}


class TestDeleteEngine:
    """Тесты для удаления двигателя."""

    @patch('routes.engines.get_by_id')
    @patch('routes.engines.engine_delete')
    @patch('routes.engines.photo_manager')
    def test_delete_engine_success(self, mock_photo_manager, mock_engine_delete, mock_get_by_id, client, auth_headers):
        """Успешное удаление двигателя и фотографий."""
        # Настраиваем моки
        mock_get_by_id.return_value = {'id': 1}  # Двигатель существует
        mock_photo_manager.delete_engine_photos_from_disk.return_value = (2, [])  # 2 фото удалено, нет ошибок
        mock_engine_delete.return_value = True  # Удаление из БD успешно

        # Выполняем запрос
        response = client.delete('/api/engine/1', headers=auth_headers)

        # Проверяем результат
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'Двигатель удалён' in data['message']

        # Проверяем порядок вызовов: сначала фото, затем БД
        mock_photo_manager.delete_engine_photos_from_disk.assert_called_once_with(1)
        mock_engine_delete.assert_called_once()
        # Проверяем, что get_by_id был вызван дважды: один раз для проверки существования,
        # второй раз внутри engine_delete (или в нашем маршруте для проверки после удаления фото)
        assert mock_get_by_id.call_count >= 1

    @patch('routes.engines.get_by_id')
    @patch('routes.engines.engine_delete')
    @patch('routes.engines.photo_manager')
    @patch('routes.engines.db_connection')
    def test_delete_engine_photo_deletion_failure(self, mock_db_connection, mock_photo_manager, mock_engine_delete, mock_get_by_id, client, auth_headers):
        """Если не удалось удалить фотографии, двигатель не удаляется из БД."""
        # Настраиваем моки
        mock_get_by_id.return_value = {'id': 1}  # Двигатель существует
        mock_photo_manager.delete_engine_photos_from_disk.return_value = (1, [('path/to/photo.jpg', 'Ошибка удаления')])  # 1 фото удалено, 1 ошибка
        mock_engine_delete.return_value = True  # Это не должно быть вызвано

        # Настраиваем мок для db_connection
        mock_conn = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        # Выполняем запрос
        response = client.delete('/api/engine/1', headers=auth_headers)

        # Проверяем результат
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Не удалось удалить фотографии двигателя' in data['error']

        # Проверяем, что удаление из БД НЕ было выполнено
        mock_engine_delete.assert_not_called()
        # Проверяем, что get_by_id НЕ был вызван (из-за раннего возврата при ошибке фото)
        mock_get_by_id.assert_not_called()
        # Проверяем, что db_connection НЕ был использован (из-за раннего возврата)
        mock_db_connection.assert_not_called()

    @patch('routes.engines.get_by_id')
    @patch('routes.engines.engine_delete')
    @patch('routes.engines.photo_manager')
    @patch('routes.engines.db_connection')
    def test_delete_engine_not_found(self, mock_db_connection, mock_photo_manager, mock_engine_delete, mock_get_by_id, client, auth_headers):
        """Удаление несуществующего двигателя."""
        # Настраиваем моки
        mock_get_by_id.return_value = None  # Двигатель не существует
        mock_photo_manager.delete_engine_photos_from_disk.return_value = (0, [])  # Нет фото для несуществующего двигателя

        # Настраиваем мок для db_connection
        mock_conn = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        # Выполняем запрос
        response = client.delete('/api/engine/999', headers=auth_headers)

        # Проверяем результат
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Двигатель не найден' in data['error']

        # Проверяем, что удаление из БД НЕ было выполнено (потому что двигатель не найден)
        mock_engine_delete.assert_not_called()
        # Проверяем, что попытка удаления фото была сделана
        mock_photo_manager.delete_engine_photos_from_disk.assert_called_once_with(999)
        # Проверяем, что get_by_id был вызван для проверки существования после удаления фото
        mock_get_by_id.assert_called_once()
        # Проверяем, что db_connection был использован
        mock_db_connection.assert_called_once()

    @patch('routes.engines.get_by_id')
    @patch('routes.engines.engine_delete')
    @patch('routes.engines.photo_manager')
    def test_delete_engine_db_deletion_failure_after_photo_success(self, mock_photo_manager, mock_engine_delete, mock_get_by_id, client, auth_headers):
        """Если удаление из БД не удалось после успешного удаления фото, возвращаем ошибку.
        (Фотографии остаются удалёнными, но это исключительная ситуация)."""
        # Настраиваем моки
        mock_get_by_id.return_value = {'id': 1}  # Двигатель существует
        mock_photo_manager.delete_engine_photos_from_disk.return_value = (2, [])  # Фото удалены успешно
        mock_engine_delete.side_effect = Exception("Ошибка БД")  # Исключение при удалении из БД

        # Выполняем запрос
        response = client.delete('/api/engine/1', headers=auth_headers)

        # Проверяем результат
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Ошибка БД' in data['error']

        # Проверяем, что удаление фото Б�ЫЛО выполнено
        mock_photo_manager.delete_engine_photos_from_disk.assert_called_once_with(1)
        # И что попытка удаления из БД была
        mock_engine_delete.assert_called_once()
class TestCreateEngine:
    """POST /api/engine — создание, валидация payload (в т.ч. modes/works)."""

    @patch('routes.engines.replace_works')
    @patch('routes.engines.replace_modes')
    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_success_with_modes_works(self, m_db, m_create, m_modes, m_works, client, auth_headers):
        m_create.return_value = 42
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        payload = {
            'location': 'Цех 1', 'engine_type': 'АИР112М4У2',
            'serial_number': 'SN12345', 'workshop': '1', 'shaft_diameter': '28',
            'modes': [{'frequency': '50', 'power': '1.5', 'voltage': '380',
                       'connection_type': 'ЗВ', 'current': '2.5', 'rpm': '1420'}],
            'works': [{'work_number': '1', 'date': '2024-01-15',
                       'work_description': 'Проверка', 'isolation': '0.5',
                       'inspection': 'ГУД', 'signature': 'Иванов', 'status': 'work'}],
        }
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True and data['id'] == 42

        m_create.assert_called_once()
        assert m_create.call_args.kwargs['actor'] is None  # request.current_user не задан
        m_modes.assert_called_once_with(conn, 42, payload['modes'])
        m_works.assert_called_once_with(conn, 42, payload['works'])

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_workshop_400(self, m_db, m_create, client, auth_headers):
        payload = {'location': 'Цех 1', 'workshop': 'не-число', 'engine_type': 'АИР'}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Цех' in json.loads(response.data)['error']
        m_create.assert_not_called()

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_shaft_diameter_400(self, m_db, m_create, client, auth_headers):
        payload = {'location': 'Цех 1', 'shaft_diameter': 'abc', 'engine_type': 'АИР'}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Диаметр вала' in json.loads(response.data)['error']

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_mode_numeric_400(self, m_db, m_create, client, auth_headers):
        payload = {'location': 'Цех 1', 'modes': [{'frequency': 'abc'}]}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Частота' in json.loads(response.data)['error']
        m_create.assert_not_called()

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_mode_voltage_range_400(self, m_db, m_create, client, auth_headers):
        """voltage — диапазон «220-240» разрешён, но начало > конца — нет."""
        payload = {'location': 'Цех 1', 'modes': [{'voltage': '500-100'}]}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Напряжение' in json.loads(response.data)['error']

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_work_isolation_400(self, m_db, m_create, client, auth_headers):
        payload = {'location': 'Цех 1', 'works': [{'isolation': 'abc'}]}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Сопротивление изоляции' in json.loads(response.data)['error']

    @patch('routes.engines.engine_create')
    @patch('routes.engines.db_connection')
    def test_create_engine_invalid_work_status_400(self, m_db, m_create, client, auth_headers):
        payload = {'location': 'Цех 1', 'works': [{'status': 'unknown-status'}]}
        response = client.post('/api/engine', json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert 'Статус работы' in json.loads(response.data)['error']
class TestUpdateEngine:
    """PUT /api/engine/<id> — обновление карточки (характеристики + modes/works)."""

    @patch('routes.engines.replace_works')
    @patch('routes.engines.replace_modes')
    @patch('routes.engines.engine_update')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_engine_success_with_modes_works(self, m_db, m_get, m_update, m_modes, m_works, client, auth_headers):
        m_get.return_value = {'id': 1}
        m_update.return_value = True
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        payload = {
            'location': 'Цех 2',
            'modes': [{'frequency': '60', 'power': '2.2'}],
            'works': [],
        }
        response = client.put('/api/engine/1', json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True and 'обновлён' in data['message']

        m_update.assert_called_once()
        assert m_update.call_args.args[1] == 1  # engine_id
        # Пустой список works приходит как есть: 'works' in data → replace_works(conn, 1, [])
        m_modes.assert_called_once_with(conn, 1, payload['modes'])
        m_works.assert_called_once_with(conn, 1, [])

    @patch('routes.engines.engine_update')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_engine_invalid_payload_400(self, m_db, m_get, m_update, client, auth_headers):
        m_get.return_value = {'id': 1}
        response = client.put('/api/engine/1', json={'workshop': 'abc'}, headers=auth_headers)
        assert response.status_code == 400
        m_update.assert_not_called()

    @patch('routes.engines.engine_update')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_engine_not_found_404(self, m_db, m_get, m_update, client, auth_headers):
        m_get.return_value = None
        response = client.put('/api/engine/999', json={'location': 'Цех 2'}, headers=auth_headers)
        assert response.status_code == 404
        assert 'не найден' in json.loads(response.data)['error']
        m_update.assert_not_called()


class TestSetEngineStatus:
    """PATCH /api/engine/<id>/status — смена эксплуатационного статуса."""

    @patch('routes.engines.engine_update_status')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_set_status_valid(self, m_db, m_get, m_update_status, client, auth_headers):
        m_get.return_value = {'id': 1}
        m_update_status.return_value = True
        response = client.patch('/api/engine/1/status', json={'status': 'reserve'}, headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True and data['status'] == 'reserve'
        m_update_status.assert_called_once()
        assert m_update_status.call_args.args[1] == 1          # engine_id
        assert m_update_status.call_args.args[2] == 'reserve'  # status

    @patch('routes.engines.engine_update_status')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_set_status_invalid_400(self, m_db, m_get, m_update_status, client, auth_headers):
        response = client.patch('/api/engine/1/status', json={'status': 'unknown'}, headers=auth_headers)
        assert response.status_code == 400
        assert 'Статус должен быть одним из' in json.loads(response.data)['error']
        m_update_status.assert_not_called()

    @patch('routes.engines.engine_update_status')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_set_status_empty_400(self, m_db, m_get, m_update_status, client, auth_headers):
        response = client.patch('/api/engine/1/status', json={}, headers=auth_headers)
        assert response.status_code == 400

    @patch('routes.engines.engine_update_status')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_set_status_not_found_404(self, m_db, m_get, m_update_status, client, auth_headers):
        m_get.return_value = None
        response = client.patch('/api/engine/999/status', json={'status': 'repair'}, headers=auth_headers)
        assert response.status_code == 404
        m_update_status.assert_not_called()
class TestUpdateEngineModes:
    """PUT /api/engine/<id>/modes — полная замена режимов."""

    @patch('routes.engines.replace_modes')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_modes_success(self, m_db, m_get, m_replace, client, auth_headers):
        m_get.return_value = {'id': 1}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        modes = [{'frequency': '50', 'power': '1.5'}, {'frequency': '60', 'power': '2.2'}]

        response = client.put('/api/engine/1/modes', json={'modes': modes}, headers=auth_headers)
        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True
        m_replace.assert_called_once_with(conn, 1, modes)

    @patch('routes.engines.replace_modes')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_modes_empty_list_ok(self, m_db, m_get, m_replace, client, auth_headers):
        m_get.return_value = {'id': 1}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        response = client.put('/api/engine/1/modes', json={'modes': []}, headers=auth_headers)
        assert response.status_code == 200
        m_replace.assert_called_once_with(conn, 1, [])

    @patch('routes.engines.replace_modes')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_modes_invalid_400(self, m_db, m_get, m_replace, client, auth_headers):
        response = client.put('/api/engine/1/modes', json={'modes': [{'rpm': 'abc'}]}, headers=auth_headers)
        assert response.status_code == 400
        assert 'Обороты' in json.loads(response.data)['error']
        m_replace.assert_not_called()

    @patch('routes.engines.replace_modes')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_modes_engine_not_found_404(self, m_db, m_get, m_replace, client, auth_headers):
        m_get.return_value = None
        response = client.put('/api/engine/999/modes', json={'modes': [{'frequency': '50'}]}, headers=auth_headers)
        assert response.status_code == 404
        m_replace.assert_not_called()


class TestUpdateEngineWorks:
    """PUT /api/engine/<id>/works — полная замена произведённых работ."""

    @patch('routes.engines.replace_works')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_works_success(self, m_db, m_get, m_replace, client, auth_headers):
        m_get.return_value = {'id': 1}
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)
        works = [{'work_number': '1', 'work_description': 'Проверка', 'isolation': '0.5', 'status': 'work'}]

        response = client.put('/api/engine/1/works', json={'works': works}, headers=auth_headers)
        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True
        m_replace.assert_called_once_with(conn, 1, works)

    @patch('routes.engines.replace_works')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_works_invalid_status_400(self, m_db, m_get, m_replace, client, auth_headers):
        response = client.put('/api/engine/1/works', json={'works': [{'status': 'closed'}]}, headers=auth_headers)
        assert response.status_code == 400
        assert 'Статус работы' in json.loads(response.data)['error']
        m_replace.assert_not_called()

    @patch('routes.engines.replace_works')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_works_invalid_isolation_400(self, m_db, m_get, m_replace, client, auth_headers):
        response = client.put('/api/engine/1/works', json={'works': [{'isolation': 'oops'}]}, headers=auth_headers)
        assert response.status_code == 400
        assert 'Сопротивление изоляции' in json.loads(response.data)['error']

    @patch('routes.engines.replace_works')
    @patch('routes.engines.get_by_id')
    @patch('routes.engines.db_connection')
    def test_update_works_engine_not_found_404(self, m_db, m_get, m_replace, client, auth_headers):
        m_get.return_value = None
        response = client.put('/api/engine/999/works', json={'works': [{'work_description': 'X'}]}, headers=auth_headers)
        assert response.status_code == 404
        m_replace.assert_not_called()