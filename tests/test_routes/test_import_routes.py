"""Тесты HTTP-слоя импорта и очистки (routes/import_routes.py).

import_bp — POST /api/import-folder (парсинг Excel, сохранение фото, запись в БД)
и POST /api/clear (пересоздание БД + удаление фото-папок).

Менеджеры фото покрыты unit-тестами в test_photo_manager/ — здесь проверяем
HTTP-уровень: разбор запроса, коды ответов, поведение при ошибках парсера и
сбоях сохранения фото.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.import_routes import import_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(import_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestImportFolder:
    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.db_connection')
    def test_no_excel_files_400(self, m_db, m_extract, m_parse, client):
        import os
        orig = os.path.join
        try:
            os.path.join = lambda a, b: '/tmp/mock_motors/' + b
            r = client.post('/api/import-folder')
            assert r.status_code == 400
            data = r.get_json()
            assert data['success'] is False
            assert 'нет Excel файлов' in data['error']
        finally:
            os.path.join = orig

    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.MOTORS_FOLDER', '/tmp/mock_motors')
    def test_success_import(self, m_db, m_extract, m_parse, client):
        m_parse.return_value = {
            'success': True,
            'filename': 'test.xlsx',
            'engine_id': 1,
            'modes': [{'mode_id': 1, 'value': '1500'}],
            'works': [{'work_id': 1, 'description': 'Замена масла'}],
        }
        m_extract.return_value = []
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/import-folder')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert len(data['file_reports']) == 1
        assert data['file_reports'][0]['status'] == 'success'
        assert data['file_reports'][0]['filename'] == 'test.xlsx'
        assert data['file_reports'][0]['modes_count'] == 1
        assert data['file_reports'][0]['works_count'] == 1

    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.MOTORS_FOLDER', '/tmp/mock_motors')
    def test_parser_error_reported(self, m_db, m_extract, m_parse, client):
        m_parse.return_value = {
            'success': False,
            'filename': 'test.xlsx',
            'error': 'Некорректный формат файла',
        }
        m_extract.return_value = []
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/import-folder')
        assert r.status_code == 400
        data = r.get_json()
        assert data['success'] is False
        assert data['file_reports'][0]['status'] == 'error'
        assert 'Некорректный формат' in data['file_reports'][0]['error']

    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.MOTORS_FOLDER', '/tmp/mock_motors')
    def test_parser_exception_reported(self, m_db, m_extract, m_parse, client):
        m_parse.side_effect = RuntimeError('Unexpected crash')
        m_extract.return_value = []
        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/import-folder')
        assert r.status_code == 400
        data = r.get_json()
        assert data['success'] is False
        assert data['file_reports'][0]['status'] == 'error'
        assert 'Unexpected crash' in data['file_reports'][0]['error']

    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.photo_manager')
    @patch('routes.import_routes.MOTORS_FOLDER', '/tmp/mock_motors')
    def test_photo_upload_on_success(self, m_photo_manager, m_db, m_parse, m_extract, client):
        m_parse.return_value = {
            'success': True,
            'filename': 'test.xlsx',
            'engine_id': 1,
            'modes': [],
            'works': [],
        }
        m_extract.return_value = [{
            'path': '/tmp/photo1.png',
            'filename': 'test_1.png',
        }]
        upload_mock = MagicMock(return_value=({'success': True, 'uploaded': 1}, 200))
        m_photo_manager.upload_engine_photos = upload_mock

        conn = MagicMock()
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post('/api/import-folder')
        assert r.status_code == 200
        upload_mock.assert_called_once()
        call_args = upload_mock.call_args
        assert call_args[0][1] == 1  # engine_id
        assert call_args[0][2] is not None  # photo_entries


class TestClear:
    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.photo_manager')
    def test_clear_success(self, m_photo_manager, m_db, client):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        m_db.return_value.__enter__ = MagicMock(return_value=conn)
        m_db.return_value.__exit__ = MagicMock(return_value=False)

        import shutil, os
        orig_rmtree = shutil.rmtree
        orig_makedirs = os.makedirs
        shutil.rmtree = lambda path, ignore_errors=True: None
        os.makedirs = MagicMock()
        try:
            m_photo_manager.invalidate_photo_cache.return_value = None
            r = client.post('/api/clear')
            assert r.status_code == 200
            data = r.get_json()
            assert data['success'] is True
            assert 'База данных и фото очищены' in data['message']
            m_photo_manager.invalidate_photo_cache.assert_called_once()
        finally:
            shutil.rmtree = orig_rmtree
            os.makedirs = orig_makedirs

    @patch('routes.import_routes.db_connection')
    @patch('routes.import_routes.photo_manager')
    def test_clear_db_error_500(self, m_photo_manager, m_db, client):
        import sqlite3
        m_db.side_effect = sqlite3.Error("DB error")
        m_photo_manager.invalidate_photo_cache.return_value = None
        r = client.post('/api/clear')
        assert r.status_code == 500
        data = r.get_json()
        assert data['success'] is False
        assert 'Внутренняя ошибка при очистке' in data['error']