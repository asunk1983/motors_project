"""Тесты modules/photo_manager/incident_manager.py — фото заявок Инцидентов.

Только диск (PhotoI/), без синхронизации с БД. Схема ID{ticket_id}_{n}.{ext}.
"""
import os
from io import BytesIO

import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

from modules import db as db_module
from modules.photo_manager import incident_manager as pm


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.fixture
def pi_folder(tmp_path, monkeypatch):
    folder = str(tmp_path / 'PhotoI')
    os.makedirs(folder, exist_ok=True)
    monkeypatch.setattr(db_module, 'INCIDENT_PHOTOS_FOLDER', folder)
    return folder


@pytest.fixture(autouse=True)
def _clear_cache():
    pm.invalidate_photo_cache()
    yield
    pm.invalidate_photo_cache()


def _make_photo(folder, ticket_id, n, ext='.png'):
    path = os.path.join(folder, f'ID{ticket_id}_{n}{ext}')
    with open(path, 'wb') as f:
        f.write(b'fake-image')
    return path


def _file_storage(filename='photo.png', data=b'bytes'):
    return FileStorage(stream=BytesIO(data), filename=filename)


class TestDiskPaths:
    def test_empty(self, pi_folder):
        assert pm.ticket_photo_disk_paths(1) == []

    def test_sorts_and_filters(self, pi_folder):
        _make_photo(pi_folder, 1, 2)
        _make_photo(pi_folder, 1, 1)
        _make_photo(pi_folder, 2, 1)
        names = [os.path.basename(p) for p in pm.ticket_photo_disk_paths(1)]
        assert names == ['ID1_1.png', 'ID1_2.png']

    def test_invalidate_clears_cache(self, pi_folder):
        p = _make_photo(pi_folder, 1, 1)
        _ = pm.ticket_photo_disk_paths(1)
        os.remove(p)
        pm.invalidate_photo_cache()
        assert pm.ticket_photo_disk_paths(1) == []


class TestNextPhotoIndex:
    def test_empty_is_one(self, pi_folder):
        assert pm.next_photo_index(1) == 1

    def test_max_plus_one(self, pi_folder):
        _make_photo(pi_folder, 1, 2)
        _make_photo(pi_folder, 1, 5)
        assert pm.next_photo_index(1) == 6


class TestUploadTicketPhotos:
    def test_upload_skips_bad_ext(self, pi_folder):
        files = [_file_storage('a.png'), _file_storage('b.jpg'), _file_storage('bad.txt')]
        resp, code = pm.upload_ticket_photos(7, files)
        assert code == 200
        data = resp.get_json()
        assert data['uploaded'] == 2 and data['skipped'] == 1
        names = [os.path.basename(p) for p in pm.ticket_photo_disk_paths(7)]
        assert names == ['ID7_1.png', 'ID7_2.jpg']

    def test_continues_index(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        pm.upload_ticket_photos(1, [_file_storage('c.png')])
        names = sorted(os.path.basename(p) for p in pm.ticket_photo_disk_paths(1))
        assert names == ['ID1_1.png', 'ID1_2.png']


class TestDeleteTicketPhoto:
    def test_invalid_400(self, pi_folder):
        resp, code = pm.delete_ticket_photo(1, '../x.png')
        assert code == 400

    def test_not_owner_403(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        resp, code = pm.delete_ticket_photo(2, 'ID1_1.png')
        assert code == 403

    def test_not_found_404(self, pi_folder):
        resp, code = pm.delete_ticket_photo(1, 'ID1_99.png')
        assert code == 404

    def test_delete_success(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        resp, code = pm.delete_ticket_photo(1, 'ID1_1.png')
        assert code == 200
        assert pm.ticket_photo_disk_paths(1) == []


class TestDeleteTicketPhotosFromDisk:
    def test_removes_only_own(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        _make_photo(pi_folder, 1, 2)
        _make_photo(pi_folder, 2, 1)
        removed, errors = pm.delete_ticket_photos_from_disk(1)
        assert removed == 2 and errors == []
        assert pm.ticket_photo_disk_paths(1) == []
        assert len(pm.ticket_photo_disk_paths(2)) == 1
class TestReplaceTicketPhoto:
    def test_invalid_400(self, pi_folder):
        resp, code = pm.replace_ticket_photo(1, '../x.png', _file_storage())
        assert code == 400

    def test_not_owner_403(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        resp, code = pm.replace_ticket_photo(2, 'ID1_1.png', _file_storage())
        assert code == 403

    def test_not_found_404(self, pi_folder):
        resp, code = pm.replace_ticket_photo(1, 'ID1_9.png', _file_storage())
        assert code == 404

    def test_no_file_400(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        resp, code = pm.replace_ticket_photo(1, 'ID1_1.png', None)
        assert code == 400

    def test_replace_success(self, pi_folder):
        _make_photo(pi_folder, 1, 1, '.jpg')
        resp, code = pm.replace_ticket_photo(1, 'ID1_1.jpg', _file_storage('x.png'))
        assert code == 200
        assert resp.get_json()['filename'] == 'ID1_1.png'
        assert os.path.exists(os.path.join(pi_folder, 'ID1_1.png'))
        assert not os.path.exists(os.path.join(pi_folder, 'ID1_1.jpg'))


class TestCountAllPhotos:
    def test_empty_folder(self, pi_folder):
        assert pm.count_all_photos() == 0

    def test_counts_all(self, pi_folder):
        _make_photo(pi_folder, 1, 1)
        _make_photo(pi_folder, 1, 2)
        _make_photo(pi_folder, 2, 1, '.jpg')
        assert pm.count_all_photos() == 3

    def test_missing_folder_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_module, 'INCIDENT_PHOTOS_FOLDER', str(tmp_path / 'nope'))
        assert pm.count_all_photos() == 0

    def test_errors_do_not_stop(self, pi_folder, monkeypatch):
        _make_photo(pi_folder, 1, 1)
        _make_photo(pi_folder, 1, 2)

        def _boom(path):
            raise OSError('denied')

        monkeypatch.setattr(os, 'remove', _boom)
        removed, errors = pm.delete_ticket_photos_from_disk(1)
        assert removed == 0 and len(errors) == 2
class TestGetTicketPhotos:
    def test_returns_filename_and_path(self, pi_folder):
        _make_photo(pi_folder, 3, 1)
        assert pm.get_ticket_photos(3) == [
            {'filename': 'ID3_1.png', 'path': '/api/incident-photos/ID3_1.png'}
        ]


class TestGetPhoto:
    def test_invalid_filename_400(self, app, pi_folder):
        with app.test_request_context():
            for bad in ('../x', 'a/b.png', 'a\\b.png'):
                resp, code = pm.get_photo(bad)
                assert code == 400

    def test_not_found_404(self, app, pi_folder):
        with app.test_request_context():
            resp, code = pm.get_photo('ID1_1.png')
            assert code == 404

    def test_ok_no_cache(self, app, pi_folder):
        _make_photo(pi_folder, 1, 1)
        with app.test_request_context():
            resp = pm.get_photo('ID1_1.png')
            assert resp.status_code == 200
            assert resp.headers['Cache-Control'] == 'no-cache'