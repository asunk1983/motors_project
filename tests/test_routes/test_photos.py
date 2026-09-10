"""Тесты HTTP-слоя фото двигателей (routes/photos.py).

Менеджер уже покрыт unit-тестами (test_photo_manager/test_manager.py) —
здесь проверяем только делегирование: разбор запроса, коды ответов,
передачу параметров в photo_manager.
"""
from unittest.mock import patch

import pytest
from flask import Flask

from routes.photos import photos_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(photos_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetEnginePhotos:
    @patch('routes.photos.photo_manager.get_engine_photos')
    def test_ok(self, m_get, client):
        m_get.return_value = [{'filename': 'ID1_1.png', 'path': '/api/photos/ID1_1.png'}]
        r = client.get('/api/engine/1/photos')
        assert r.status_code == 200
        assert r.get_json() == [{'filename': 'ID1_1.png', 'path': '/api/photos/ID1_1.png'}]
        m_get.assert_called_once_with(1)

    @patch('routes.photos.photo_manager.get_engine_photos')
    def test_exception_returns_empty_200(self, m_get, client):
        m_get.side_effect = RuntimeError('boom')
        r = client.get('/api/engine/1/photos')
        assert r.status_code == 200
        assert r.get_json() == []


class TestGetPhoto:
    @patch('routes.photos.photo_manager.get_photo')
    def test_delegates(self, m_get_photo, client):
        m_get_photo.return_value = ({'error': 'Photo not found'}, 404)
        r = client.get('/api/photos/ID1_1.png')
        assert r.status_code == 404
        m_get_photo.assert_called_once_with('ID1_1.png')

    @patch('routes.photos.photo_manager.get_photo')
    def test_exception_500(self, m_get_photo, client):
        m_get_photo.side_effect = RuntimeError('boom')
        r = client.get('/api/photos/ID1_1.png')
        assert r.status_code == 500


class TestUploadEnginePhotos:
    @patch('routes.photos.db_connection')
    @patch('routes.photos.photo_manager.upload_engine_photos')
    def test_no_files_400(self, m_upload, m_db, client):
        r = client.post('/api/engine/1/photos', data={})
        assert r.status_code == 400
        m_upload.assert_not_called()

    @patch('routes.photos.db_connection')
    @patch('routes.photos.photo_manager.upload_engine_photos')
    def test_upload_delegates(self, m_upload, m_db, client):
        m_upload.return_value = ({'success': True, 'uploaded': 1}, 200)
        m_conn = m_db.return_value.__enter__.return_value
        data = {'photos': (BytesIO(b'data'), 'a.png')}
        r = client.post('/api/engine/1/photos', data=data,
                        content_type='multipart/form-data')
        assert r.status_code == 200
        m_upload.assert_called_once()
        assert m_upload.call_args[0][1] == 1
        assert m_upload.call_args[0][2]


class TestDeleteEnginePhoto:
    @patch('routes.photos.db_connection')
    @patch('routes.photos.photo_manager.delete_engine_photo')
    def test_delete_delegates(self, m_delete, m_db, client):
        m_delete.return_value = ({'success': True, 'photo_count': 0}, 200)
        r = client.delete('/api/engine/1/photos/ID1_1.png')
        assert r.status_code == 200
        m_delete.assert_called_once()
        assert m_delete.call_args[0][1] == 1
        assert m_delete.call_args[0][2] == 'ID1_1.png'


class TestReplaceEnginePhoto:
    @patch('routes.photos.photo_manager.replace_engine_photo')
    def test_replace_delegates(self, m_replace, client):
        m_replace.return_value = ({'success': True, 'filename': 'ID1_1.png'}, 200)
        data = {'photo': (BytesIO(b'data'), 'x.png')}
        r = client.put('/api/engine/1/photos/ID1_1.png', data=data,
                       content_type='multipart/form-data')
        assert r.status_code == 200
        m_replace.assert_called_once()
        assert m_replace.call_args[0][1] == 1
        assert m_replace.call_args[0][2] == 'ID1_1.png'
        assert m_replace.call_args[0][3] is not None