"""Тесты HTTP-слоя фото оборудования (routes/equipment_photo_routes.py).

read-only endpoint: GET /api/equipment-photos/<filename>.
Менеджер (equipment_manager) уже покрыт unit-тестами — здесь проверяем
только делегирование: коды ответов, передачу имени файла, что при
опасном пути менеджер не отдаёт файл.
"""

from unittest.mock import patch

import pytest
from flask import Flask

from routes.equipment_photo_routes import equipment_photo_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(equipment_photo_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestEquipmentPhoto:
    @patch('routes.equipment_photo_routes.equipment_manager.get_photo')
    def test_ok(self, m_get_photo, client):
        from flask import Response
        m_get_photo.return_value = Response(
            'photo data',
            mimetype='image/png',
            headers={
                'Content-Disposition': 'attachment; filename="ID10_1.png"',
            },
        )
        r = client.get('/api/equipment-photos/ID10_1.png')
        assert r.status_code == 200
        assert r.mimetype == 'image/png'
        m_get_photo.assert_called_once_with('ID10_1.png')

    @patch('routes.equipment_photo_routes.equipment_manager.get_photo')
    def test_not_found_404(self, m_get_photo, client):
        m_get_photo.return_value = ({'error': 'Photo not found'}, 404)
        r = client.get('/api/equipment-photos/ID10_99.png')
        assert r.status_code == 404
        m_get_photo.assert_called_once_with('ID10_99.png')

    @patch('routes.equipment_photo_routes.equipment_manager.get_photo')
    def test_traversal_not_exposed(self, m_get_photo, client):
        # Менеджер видит опасный путь и спокойно реагирует (None/path-traversal
        # блокируется внутри get_photo). Роут пассивно делегирует — не оборачивает
        # имя файла дополнительно, поэтому после рефакторинга менеджера важно
        # помнить про эту защиту.
        m_get_photo.return_value = ({'error': 'Invalid filename'}, 400)
        r = client.get('/api/equipment-photos/../../../etc/passwd')
        assert r.status_code == 400
        m_get_photo.assert_called_once_with('../../../etc/passwd')
