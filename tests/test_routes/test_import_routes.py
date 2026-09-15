"""Тесты HTTP-слоя импорта и очистки (routes/import_routes.py).

import_bp — POST /api/import-folder (парсинг Excel, извлечение фото, запись в БД)
и POST /api/clear (пересоздание БД + удаление фото-папок).

Менеджеры фото покрыты unit-тестами в test_photo_manager/ — здесь проверяем
HTTP-уровень: разбор запроса, коды ответов, поведение при ошибках парсера и
при сбое извлечения фото.

ВАЖНО (изоляция): /api/clear работает с db_module.DB_PATH напрямую и УДАЛЯЕТ
файл БД, поэтому его тесты обязаны подменять DB_PATH и PHOTO_FOLDERS на
tmp_path — иначе прогон сносит боевую engine_data.db.
"""

import os
import sqlite3
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from modules import db as db_module
from routes.import_routes import import_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(import_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def motors_dir(tmp_path):
    """Каталог с одним xlsx-файлом — именно его находит glob(MOTORS_FOLDER).

    Без реального файла в папке роут отдаёт 400 «нет Excel файлов» ещё до
    вызова парсера, поэтому мок parse_file_fast вообще не вызывался.
    """
    folder = tmp_path / 'motors'
    folder.mkdir()
    (folder / 'test.xlsx').write_bytes(b'stub')
    return str(folder)


def _mode():
    """Режим в форме результата parse_file_fast — ключи, которые читает роут."""
    return {'frequency': '50', 'power': '1.5', 'voltage': '380',
            'connection_type': 'ЗВ', 'current': '2.5', 'rpm': '1420'}


def _work():
    return {'work_number': '1', 'date': '2024-01-15',
            'work_description': 'Проверка', 'isolation': '0.5',
            'inspection': 'ГУД', 'signature': 'Иванов'}


def _parse_ok(file_path, modes=None, works=None):
    """Реальный контракт parse_file_fast: success/filename/engine_tuple/
    modes/works/file_path — роут читает все эти ключи (в старом тесте их
    не было, из-за чего падал на data['file_path'])."""
    return {
        'success': True,
        'filename': 'test.xlsx',
        'engine_tuple': ('test.xlsx', None, None, 'Цех 1', None, None, None,
                         None, None, None, None, None, None, None, None, None, 0),
        'modes': [_mode()] if modes is None else modes,
        'works': [_work()] if works is None else works,
        'file_path': file_path,
    }


def _mock_db_conn(m_db, existing=0):
    """Настраивает мок db_connection: SELECT COUNT(*) FROM engines → existing
    (guard «массовый импорт только на пустую БД»). Возвращает conn.

    Без явного (0,) на fetchone() сравнение «existing_count > 0» падает с
    TypeError: MagicMock > int.

    cursor.fetchone() → (1,) — это ответ на 'SELECT last_insert_rowid()':
    из него роут вычисляет first_id, и без настоящего int engine_id в
    file_reports окажется MagicMock, который не сериализуется в JSON
    (ответ 500 «Object of type MagicMock is not JSON serializable»).
    """
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (existing,)
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)
    conn.cursor.return_value = cursor
    m_db.return_value.__enter__ = MagicMock(return_value=conn)
    m_db.return_value.__exit__ = MagicMock(return_value=False)
    return conn


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
    def test_success_import(self, m_db, m_extract, m_parse, client, motors_dir, monkeypatch):
        monkeypatch.setattr('routes.import_routes.MOTORS_FOLDER', motors_dir)
        m_parse.return_value = _parse_ok(os.path.join(motors_dir, 'test.xlsx'))
        m_extract.return_value = 0  # число сохранённых фото (int), не список
        _mock_db_conn(m_db, existing=0)

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
    def test_parser_error_reported(self, m_db, m_extract, m_parse, client, motors_dir, monkeypatch):
        monkeypatch.setattr('routes.import_routes.MOTORS_FOLDER', motors_dir)
        m_parse.return_value = {
            'success': False,
            'filename': 'test.xlsx',
            'error': 'Некорректный формат файла',
        }
        m_extract.return_value = 0
        _mock_db_conn(m_db)

        r = client.post('/api/import-folder')
        assert r.status_code == 400
        data = r.get_json()
        assert data['success'] is False
        assert data['file_reports'][0]['status'] == 'error'
        assert 'Некорректный формат' in data['file_reports'][0]['error']

    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.db_connection')
    def test_parser_exception_reported(self, m_db, m_extract, m_parse, client, motors_dir, monkeypatch):
        monkeypatch.setattr('routes.import_routes.MOTORS_FOLDER', motors_dir)
        m_parse.side_effect = RuntimeError('Unexpected crash')
        m_extract.return_value = 0
        _mock_db_conn(m_db)

        r = client.post('/api/import-folder')
        assert r.status_code == 400
        data = r.get_json()
        assert data['success'] is False
        assert data['file_reports'][0]['status'] == 'error'
        assert 'Unexpected crash' in data['file_reports'][0]['error']

    @patch('routes.import_routes.extract_images_from_excel')
    @patch('routes.import_routes.parse_file_fast')
    @patch('routes.import_routes.db_connection')
    def test_photo_extraction_count_reported(self, m_db, m_parse, m_extract,
                                             client, motors_dir, monkeypatch):
        """Фото при импорте извлекает extract_images_from_excel — photo_manager
        в этой ветке не участвует (прежний тест мокал несуществующий атрибут
        routes.import_routes.photo_manager и ждал upload_engine_photos).
        Контракт: extract_images_from_excel возвращает КОЛИЧЕСТВО сохранённых
        файлов, роут суммирует их в total_photos и обновляет engines.photo_count.
        """
        monkeypatch.setattr('routes.import_routes.MOTORS_FOLDER', motors_dir)
        file_path = os.path.join(motors_dir, 'test.xlsx')
        m_parse.return_value = _parse_ok(file_path, works=[])
        m_extract.return_value = 2
        conn = _mock_db_conn(m_db, existing=0)

        r = client.post('/api/import-folder')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['total_photos'] == 2
        assert data['file_reports'][0]['photos_count'] == 2

        # extract_images_from_excel(file_path, filename, engine_id, log_message)
        extract_args = m_extract.call_args.args
        assert len(extract_args) == 4
        assert extract_args[0] == file_path
        assert extract_args[1] == 'test.xlsx'

        # photo_count обновляется тем же (мок) соединением
        conn.executemany.assert_called_once()
        assert 'UPDATE engines SET photo_count' in conn.executemany.call_args.args[0]


class TestClear:
    @pytest.fixture
    def clear_env(self, tmp_path, monkeypatch):
        """Изолирует /api/clear от боевых данных.

        Роут работает напрямую с modules.db.DB_PATH (читает оттуда
        пользователей, УДАЛЯЕТ файл БД, затем пересоздаёт схему) и с
        PHOTO_FOLDERS. Без подмены обоих путей тест снёс бы реальную
        engine_data.db и боевые фото-папки.
        """
        from modules.photo_manager import manager as photo_manager

        db_path = str(tmp_path / 'engine_data.db')
        # Своя БД с «живым» пользователем: clear_database() обязан прочитать
        # users до очистки и вернуть их в пересозданную базу.
        conn = sqlite3.connect(db_path)
        db_module.init_db(conn)
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES ('keeper', 'hash', 'user', '2024-01-01')"
        )
        conn.commit()
        conn.close()

        photos_dir = tmp_path / 'photos'
        photos_dir.mkdir()
        (photos_dir / 'old.png').write_bytes(b'old')

        monkeypatch.setattr(db_module, 'DB_PATH', db_path)
        # Роут делает локальный import, поэтому подменяем значение в источнике
        monkeypatch.setattr('config.settings.PHOTO_FOLDERS',
                            [('photos', str(photos_dir))])
        invalidate = MagicMock()
        monkeypatch.setattr(photo_manager, 'invalidate_photo_cache', invalidate)

        return {'db_path': db_path, 'photos_dir': str(photos_dir),
                'invalidate': invalidate}

    def test_clear_success(self, clear_env, client):
        r = client.post('/api/clear')
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert 'База данных и фото очищены' in data['message']
        clear_env['invalidate'].assert_called_once()

        # Фото-папка очищена и пересоздана пустой
        assert os.path.isdir(clear_env['photos_dir'])
        assert os.listdir(clear_env['photos_dir']) == []

        # БД пересоздана с нуля, но сохранённый пользователь вернулся
        conn = sqlite3.connect(clear_env['db_path'])
        try:
            assert conn.execute('SELECT COUNT(*) FROM engines').fetchone()[0] == 0
            usernames = [row[0] for row in conn.execute('SELECT username FROM users')]
        finally:
            conn.close()
        assert 'keeper' in usernames

    def test_clear_db_error_500(self, clear_env, client, monkeypatch):
        # Единственное место, откуда /api/clear может упасть на работе с БД, —
        # пересоздание схемы: db_connection в этом роуте не используется
        # вовсе (прежний тест патчил его и падал на несуществующем атрибуте
        # routes.import_routes.photo_manager).
        monkeypatch.setattr(db_module, 'init_db',
                            MagicMock(side_effect=sqlite3.Error('DB error')))
        r = client.post('/api/clear')
        assert r.status_code == 500
        data = r.get_json()
        assert data['success'] is False
        assert 'Внутренняя ошибка при очистке' in data['error']