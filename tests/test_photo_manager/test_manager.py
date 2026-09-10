"""Тесты modules/photo_manager/manager.py — фото двигателей.

Дисковая схема: PhotoE/{ID}{engine_id}_{n}.{ext}, кеш путей,
атомарная запись через _save_upload_atomically, пересчёт photo_count
в БД при upload/delete.
"""
import os
from io import BytesIO

import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

from modules import db as db_module
from modules.photo_manager import manager as pm


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.fixture
def photos_folder(tmp_path, monkeypatch):
    folder = str(tmp_path / 'photos')
    os.makedirs(folder, exist_ok=True)
    monkeypatch.setattr(db_module, 'PHOTOS_FOLDER', folder)
    return folder


@pytest.fixture(autouse=True)
def _clear_cache():
    pm.invalidate_photo_cache()
    yield
    pm.invalidate_photo_cache()


def _make_photo(folder, engine_id, n, ext='.png'):
    path = os.path.join(folder, f'ID{engine_id}_{n}{ext}')
    with open(path, 'wb') as f:
        f.write(b'fake-image')
    return path


def _file_storage(filename='photo.png', data=b'bytes'):
    return FileStorage(stream=BytesIO(data), filename=filename)


class TestDiskPaths:
    def test_empty(self, photos_folder):
        assert pm.engine_photo_disk_paths(1) == []

    def test_sorts_paths(self, photos_folder):
        _make_photo(photos_folder, 1, 2)
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 1, 10)
        paths = pm.engine_photo_disk_paths(1)
        assert len(paths) == 3
        names = [os.path.basename(p) for p in paths]
        assert names == ['ID1_1.png', 'ID1_10.png', 'ID1_2.png']

    def test_filters_by_engine_id(self, photos_folder):
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 2, 1)
        names = [os.path.basename(p) for p in pm.engine_photo_disk_paths(1)]
        assert names == ['ID1_1.png']

    def test_cache_used(self, photos_folder):
        p = _make_photo(photos_folder, 1, 1)
        first = pm.engine_photo_disk_paths(1)
        os.remove(p)
        second = pm.engine_photo_disk_paths(1)
        assert first == second  # кеш: второй вызов НЕ пересканирует диск

    def test_invalidate_clears_cache(self, photos_folder):
        _make_photo(photos_folder, 1, 1)
        _ = pm.engine_photo_disk_paths(1)
        pm.invalidate_photo_cache()
        assert pm.engine_photo_disk_paths(1) == []


class TestNextPhotoIndex:
    def test_empty_is_one(self, photos_folder):
        assert pm.next_photo_index(1) == 1

    def test_max_plus_one(self, photos_folder):
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 1, 3)
        assert pm.next_photo_index(1) == 4

    def test_ignores_other_engines(self, photos_folder):
        _make_photo(photos_folder, 2, 5)
        assert pm.next_photo_index(1) == 1


class TestGetEnginePhotos:
    def test_returns_filename_and_path(self, photos_folder):
        _make_photo(photos_folder, 7, 1)
        photos = pm.get_engine_photos(7)
        assert photos == [{'filename': 'ID7_1.png', 'path': '/api/photos/ID7_1.png'}]

    def test_empty(self, photos_folder):
        assert pm.get_engine_photos(7) == []


class TestGetPhoto:
    def test_invalid_filename_400(self, app, photos_folder):
        with app.test_request_context():
            for bad in ('../etc/passwd', 'a/b.png', 'a\\b.png'):
                resp, code = pm.get_photo(bad)
                assert code == 400

    def test_not_found_404(self, app, photos_folder):
        with app.test_request_context():
            resp, code = pm.get_photo('ID1_1.png')
            assert code == 404
class TestDeleteEnginePhoto:
    def test_invalid_filename_400(self, db_conn, photos_folder):
        resp, code = pm.delete_engine_photo(db_conn, 1, '../x.png')
        assert code == 400

    def test_not_owner_403(self, db_conn, photos_folder):
        _make_photo(photos_folder, 1, 1)
        resp, code = pm.delete_engine_photo(db_conn, 2, 'ID1_1.png')
        assert code == 403

    def test_not_found_404(self, db_conn, photos_folder):
        resp, code = pm.delete_engine_photo(db_conn, 1, 'ID1_99.png')
        assert code == 404

    def test_delete_updates_photo_count(self, db_conn, photos_folder):
        from repositories.engine_repo import create
        engine_id = create(db_conn, {'location': 'Цех 1', 'engine_type': 'АИР'})
        _make_photo(photos_folder, engine_id, 1)
        _make_photo(photos_folder, engine_id, 2)
        resp, code = pm.delete_engine_photo(db_conn, engine_id, f'ID{engine_id}_1.png')
        assert code == 200
        data = resp.get_json()
        assert data['success'] is True and data['photo_count'] == 1
        row = db_conn.execute('SELECT photo_count FROM engines WHERE id = ?', (engine_id,)).fetchone()
        assert row['photo_count'] == 1


class TestDeleteEnginePhotosFromDisk:
    def test_no_photos(self, photos_folder):
        removed, errors = pm.delete_engine_photos_from_disk(1)
        assert removed == 0 and errors == []

    def test_removes_only_own(self, photos_folder):
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 1, 2)
        _make_photo(photos_folder, 2, 1)
        removed, errors = pm.delete_engine_photos_from_disk(1)
        assert removed == 2 and errors == []
        assert pm.engine_photo_disk_paths(1) == []
        assert len(pm.engine_photo_disk_paths(2)) == 1

    def test_errors_do_not_stop(self, photos_folder, monkeypatch):
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 1, 2)

        def _boom(path):
            raise OSError('denied')

        monkeypatch.setattr(os, 'remove', _boom)
        removed, errors = pm.delete_engine_photos_from_disk(1)
        assert removed == 0 and len(errors) == 2


class TestReplaceEnginePhoto:
    def _prepare(self, db_conn, photos_folder, ext='.png'):
        from repositories.engine_repo import create
        engine_id = create(db_conn, {'location': 'Цех 1', 'engine_type': 'АИР'})
        _make_photo(photos_folder, engine_id, 1, ext=ext)
        return engine_id

    def test_invalid_filename_400(self, db_conn, photos_folder, app):
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(1, '../x.png', _file_storage())
            assert code == 400

    def test_not_found_404(self, db_conn, photos_folder, app):
        engine_id = self._prepare(db_conn, photos_folder)
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(engine_id, f'ID{engine_id}_9.png', _file_storage())
            assert code == 404

    def test_not_owner_403(self, db_conn, photos_folder, app):
        engine_id = self._prepare(db_conn, photos_folder)
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(engine_id + 1, f'ID{engine_id}_1.png', _file_storage())
            assert code == 403

    def test_bad_extension_400(self, db_conn, photos_folder, app):
        engine_id = self._prepare(db_conn, photos_folder)
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(engine_id, f'ID{engine_id}_1.png', _file_storage('x.txt'))
            assert code == 400

    def test_replace_success(self, db_conn, photos_folder, app):
        engine_id = self._prepare(db_conn, photos_folder)
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(engine_id, f'ID{engine_id}_1.png', _file_storage('new.png'))
            assert code == 200
            data = resp.get_json()
            assert data['success'] is True and data['filename'] == f'ID{engine_id}_1.png'
        assert os.path.exists(os.path.join(photos_folder, f'ID{engine_id}_1.png'))

    def test_replace_changes_extension(self, db_conn, photos_folder, app):
        engine_id = self._prepare(db_conn, photos_folder, ext='.jpg')
        with app.test_request_context():
            resp, code = pm.replace_engine_photo(engine_id, f'ID{engine_id}_1.jpg', _file_storage('x.png'))
            assert code == 200
            assert resp.get_json()['filename'] == f'ID{engine_id}_1.png'
        assert os.path.exists(os.path.join(photos_folder, f'ID{engine_id}_1.png'))
        assert not os.path.exists(os.path.join(photos_folder, f'ID{engine_id}_1.jpg'))


class TestSaveUploadAtomically:
    def test_saves_file(self, tmp_path):
        dest = str(tmp_path / 'out.png')
        pm._save_upload_atomically(_file_storage('a.png', b'content'), dest)
        with open(dest, 'rb') as f:
            assert f.read() == b'content'

    def test_retries_on_error(self, tmp_path, monkeypatch):
        dest = str(tmp_path / 'out.png')
        calls = []

        class _Flaky:
            def __init__(self, inner):
                self._inner = inner

            @property
            def stream(self):
                return self._inner.stream

            def save(self, path):
                calls.append(path)
                if len(calls) == 1:
                    raise OSError('locked')
                self._inner.save(path)

        monkeypatch.setattr(pm.time, 'sleep', lambda s: None)
        pm._save_upload_atomically(_Flaky(_file_storage('a.png', b'data')), dest)
        assert os.path.exists(dest)
        _make_photo(photos_folder, 1, 1)
        _make_photo(photos_folder, 1, 2)
        def _boom(path):
            raise OSError('denied')
        monkeypatch.setattr(os, 'remove', _boom)
        removed, errors = pm.delete_engine_photos_from_disk(1)
        assert removed == 0 and len(errors) == 2

    def test_ok_no_cache(self, app, photos_folder):
        _make_photo(photos_folder, 1, 1)
        with app.test_request_context():
            resp = pm.get_photo('ID1_1.png')
            assert resp.status_code == 200
            assert resp.headers['Cache-Control'] == 'no-cache'


class TestUploadEnginePhotos:
    def test_engine_not_found_404(self, db_conn, photos_folder):
        resp, code = pm.upload_engine_photos(db_conn, 999, [_file_storage()])
        assert code == 404

    def test_upload_and_photo_count(self, db_conn, photos_folder):
        from repositories.engine_repo import create
        engine_id = create(db_conn, {'location': 'Цех 1', 'engine_type': 'АИР'})
        files = [_file_storage('a.png'), _file_storage('b.jpg'), _file_storage('bad.txt')]
        resp, code = pm.upload_engine_photos(db_conn, engine_id, files)
        assert code == 200
        data = resp.get_json()
        assert data['uploaded'] == 2 and data['skipped'] == 1
        names = [os.path.basename(p) for p in pm.engine_photo_disk_paths(engine_id)]
        assert names == [f'ID{engine_id}_1.png', f'ID{engine_id}_2.jpg']
        row = db_conn.execute('SELECT photo_count FROM engines WHERE id = ?', (engine_id,)).fetchone()
        assert row['photo_count'] == 2

    def test_upload_after_existing_continues_index(self, db_conn, photos_folder):
        from repositories.engine_repo import create
        engine_id = create(db_conn, {'location': 'Цех 1', 'engine_type': 'АИР'})
        _make_photo(photos_folder, engine_id, 1)
        pm.upload_engine_photos(db_conn, engine_id, [_file_storage('c.png')])
        names = sorted(os.path.basename(p) for p in pm.engine_photo_disk_paths(engine_id))
        assert names == [f'ID{engine_id}_1.png', f'ID{engine_id}_2.png']