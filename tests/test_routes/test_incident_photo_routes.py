"""Тесты HTTP-слоя фото заявок Инцидентов (routes/incident_photo_routes.py).

read-only endpoint: GET /api/incident-photos/<filename>.
Менеджер (incident_manager) уже покрыт unit-тестами — здесь проверяем
только делегирование: коды ответов, передачу имени файла, что при
опасном пути не выплевывается файл.
"""

from unittest.mock import patch

import pytest
from flask import Flask

from routes.incident_photo_routes import incident_photo_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(incident_photo_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestIncidentPhoto:
    @patch('routes.incident_photo_routes.incident_manager.get_photo')
    def test_ok(self, m_get_photo, client):
        from flask import Response
        m_get_photo.return_value = Response(
            'photo data',
            mimetype='image/png',
            headers={
                'Content-Disposition': 'attachment; filename="ID_T20231106_1.png"',
            },
        )
        r = client.get('/api/incident-photos/ID_T20231106_1.png')
        assert r.status_code == 200
        assert r.mimetype == 'image/png'
        m_get_photo.assert_called_once_with('ID_T20231106_1.png')

    @patch('routes.incident_photo_routes.incident_manager.get_photo')
    def test_not_found_404(self, m_get_photo, client):
        m_get_photo.return_value = ({'error': 'Photo not found'}, 404)
        r = client.get('/api/incident-photos/ID_T20231106_99.png')
        assert r.status_code == 404
        m_get_photo.assert_called_once_with('ID_T20231106_99.png')

    @patch('routes.incident_photo_routes.incident_manager.get_photo')
    def test_traversal_not_exposed(self, m_get_photo, client):
        m_get_photo.return_value = ({'error': 'Invalid filename'}, 400)
        r = client.get('/api/incident-photos/../../../etc/passwd')
        assert r.status_code == 400
        m_get_photo.assert_called_once_with('../../../etc/passwd')
