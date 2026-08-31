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