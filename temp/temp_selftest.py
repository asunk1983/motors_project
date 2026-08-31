import io
import os
import sys
import tempfile
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import modules.db as db_module
import modules.auth.auth as auth_module

# Adjust these if your application uses different DB/config paths.
TEST_DB_PATH = ROOT / 'temp_test_engine_data.db'
TEST_CONFIG_DIR = ROOT / 'temp_test_config'
TEST_PHOTOS_FOLDER = ROOT / 'temp_test_photos'
TEST_BACKUPS_FOLDER = ROOT / 'temp_test_backups'
TEST_BACKUP_STAGING_FOLDER = ROOT / 'temp_test_backup_staging'
TEST_MOTORS_FOLDER = ROOT / 'temp_test_motors'

BACKUP_TARGETS = [
    db_module.DB_PATH,
    auth_module.FILE_USERS,
    auth_module.FILE_TOKENS,
]


def backup_file(path):
    if not path or not os.path.exists(path):
        return None
    backup_path = f'{path}.bak'
    shutil.copy2(path, backup_path)
    return backup_path


def patch_test_paths():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_CONFIG_DIR.exists():
        shutil.rmtree(TEST_CONFIG_DIR)
    if TEST_PHOTOS_FOLDER.exists():
        shutil.rmtree(TEST_PHOTOS_FOLDER)
    if TEST_BACKUPS_FOLDER.exists():
        shutil.rmtree(TEST_BACKUPS_FOLDER)
    if TEST_BACKUP_STAGING_FOLDER.exists():
        shutil.rmtree(TEST_BACKUP_STAGING_FOLDER)
    if TEST_MOTORS_FOLDER.exists():
        shutil.rmtree(TEST_MOTORS_FOLDER)

    db_module.DB_PATH = str(TEST_DB_PATH)
    db_module.PHOTOS_FOLDER = str(TEST_PHOTOS_FOLDER)
    db_module.BACKUPS_FOLDER = str(TEST_BACKUPS_FOLDER)
    db_module.BACKUP_STAGING_FOLDER = str(TEST_BACKUP_STAGING_FOLDER)
    db_module.MOTORS_FOLDER = str(TEST_MOTORS_FOLDER)

    auth_module.CONFIG_DIR = str(TEST_CONFIG_DIR)
    auth_module.FILE_USERS = str(TEST_CONFIG_DIR / 'users.json')
    auth_module.FILE_TOKENS = str(TEST_CONFIG_DIR / 'tokens.json')

    os.makedirs(TEST_CONFIG_DIR, exist_ok=True)
    os.makedirs(TEST_PHOTOS_FOLDER, exist_ok=True)
    os.makedirs(TEST_BACKUPS_FOLDER, exist_ok=True)
    os.makedirs(TEST_BACKUP_STAGING_FOLDER, exist_ok=True)
    os.makedirs(TEST_MOTORS_FOLDER, exist_ok=True)


def assert_response(resp, status=200):
    assert resp.status_code == status, (
        f'Expected status {status}, got {resp.status_code}: {resp.data.decode("utf-8", "replace")!r}'
    )
    assert resp.is_json, f'Response is not JSON: {resp.data.decode("utf-8", "replace")!r}'
    data = resp.get_json()
    assert data is not None, 'Response JSON payload is missing'
    return data


def assert_binary_response(resp, expected_prefix=b'PK', status=200):
    assert resp.status_code == status, f'Expected status {status}, got {resp.status_code}'
    assert resp.data is not None and resp.data.startswith(expected_prefix), 'Unexpected binary response data'
    return resp.data


def create_dummy_png_bytes(color=(255, 0, 0)):
    from PIL import Image as PILImage
    buf = io.BytesIO()
    img = PILImage.new('RGB', (16, 16), color=color)
    img.save(buf, format='PNG')
    return buf.getvalue()


def run_tests():
    patch_test_paths()
    import app

    # Ensure backup module uses the same test DB and paths when restoring.
    try:
        import modules.backup_system.backup as backup_module
        backup_module.DB_PATH = db_module.DB_PATH
        backup_module.PHOTOS_FOLDER = db_module.PHOTOS_FOLDER
        backup_module.BACKUPS_FOLDER = db_module.BACKUPS_FOLDER
        backup_module.BACKUP_STAGING_FOLDER = db_module.BACKUP_STAGING_FOLDER
    except Exception:
        pass

    app.init_db()
    client = app.app.test_client()

    print('=== Running self-test ===')

    resp = client.get('/test')
    data = assert_response(resp)
    assert data.get('status') == 'ok', '/test returned unexpected status'
    print('PASS /test')

    import uuid
    admin_username = f'test_admin_{uuid.uuid4().hex[:8]}'
    admin_password = 'testadmin123'
    admin_id = auth_module.create_file_user(admin_username, admin_password, role='admin')
    assert isinstance(admin_id, int), 'Failed to create admin file user'
    print('PASS create_file_user')

    resp = client.post('/api/auth/login', json={
        'username': admin_username,
        'password': admin_password,
    })
    data = assert_response(resp)
    assert data.get('success') is True
    token = data.get('token')
    assert token, 'Login did not return token'
    headers = {'Authorization': f'Bearer {token}'}
    print('PASS /api/auth/login')

    resp = client.get('/api/auth/me', headers=headers)
    data = assert_response(resp)
    assert data.get('username') == admin_username
    print('PASS /api/auth/me')

    resp = client.get('/api/auth/admin/users', headers=headers)
    data = assert_response(resp)
    assert isinstance(data, list)
    print('PASS /api/auth/admin/users GET')

    new_username = 'test_user'
    new_password = 'testpass123'
    resp = client.post('/api/auth/admin/users', headers=headers, json={
        'username': new_username,
        'password': new_password,
        'role': 'user',
    })
    data = assert_response(resp)
    assert data.get('success') is True
    new_user_id = data.get('id')
    assert isinstance(new_user_id, int)
    print('PASS /api/auth/admin/users POST')

    resp = client.post(f'/api/auth/admin/users/{new_user_id}/password', headers=headers, json={'password': 'newpass123'})
    data = assert_response(resp)
    assert data.get('success') is True
    print('PASS /api/auth/admin/users/<id>/password')

    resp = client.post(f'/api/auth/admin/users/{new_user_id}/revoke', headers=headers)
    data = assert_response(resp)
    assert data.get('success') is True
    print('PASS /api/auth/admin/users/<id>/revoke')

    resp = client.delete(f'/api/auth/admin/users/{new_user_id}', headers=headers)
    data = assert_response(resp)
    assert data.get('success') is True
    print('PASS /api/auth/admin/users/<id> DELETE')

    resp = client.get('/api/wishlist')
    data = assert_response(resp)
    assert isinstance(data, list)
    print('PASS /api/wishlist GET')

    resp = client.post('/api/wishlist', json={'text': 'Automated test wish'})
    data = assert_response(resp)
    assert data.get('success') is True
    item_id = data.get('id')
    print('PASS /api/wishlist POST')

    resp = client.put(f'/api/wishlist/{item_id}', json={'text': 'Updated test wish', 'done': True})
    data = assert_response(resp)
    assert data.get('success') is True
    print('PASS /api/wishlist/<id> PUT')

    resp = client.delete(f'/api/wishlist/{item_id}')
    data = assert_response(resp)
    assert data.get('success') is True
    print('PASS /api/wishlist/<id> DELETE')

    resp = client.get('/api/wishlist')
    data = assert_response(resp)
    assert all(item.get('id') != item_id for item in data)
    print('PASS /api/wishlist cleanup')

    # Engine CRUD tests
    engine_payload = {
        'filename': 'TEST_ENGINE_1',
        'purpose': 'Тест',
        'workshop': '1',
        'location': 'Test Location',
        'engine_type': 'Induction',
        'manufacturer': 'TestCo',
        'serial_number': 'SN12345',
        'bearing_front': 'Bearing A',
        'bearing_rear': 'Bearing B',
        'shaft_diameter': '45',
        'protection_class': 'IP55',
        'mounting_type': 'Horizontal',
        'temp_sensor': 'PT100',
        'encoder': 'No',
        'cooling': 'Air',
        'note': 'Generated by self-test',
        'modes': [
            {'frequency': '50', 'power': '15', 'voltage': '380', 'connection_type': 'Y', 'current': '30', 'rpm': '1500'}
        ],
        'works': [
            {'work_number': '1', 'date': '2026-01-01', 'work_description': 'Test work', 'isolation': '100', 'inspection': 'OK', 'signature': 'Tester'}
        ]
    }
    resp = client.post('/api/engine', json=engine_payload)
    data = assert_response(resp)
    engine_id = data.get('id')
    assert isinstance(engine_id, int), 'Expected engine id after create'
    print('PASS /api/engine POST')

    resp = client.get(f'/api/engine/{engine_id}')
    data = assert_response(resp)
    assert data.get('id') == engine_id
    assert data.get('filename') == 'TEST_ENGINE_1'
    assert len(data.get('modes', [])) == 1
    assert len(data.get('works', [])) == 1
    print('PASS /api/engine/<id> GET')

    resp = client.get('/api/engines')
    data = assert_response(resp)
    assert any(item.get('id') == engine_id for item in data)
    print('PASS /api/engines GET')

    update_payload = engine_payload.copy()
    update_payload['purpose'] = 'Updated test'
    resp = client.put(f'/api/engine/{engine_id}', json=update_payload)
    data = assert_response(resp)
    assert data.get('success')
    resp = client.get(f'/api/engine/{engine_id}')
    data = assert_response(resp)
    assert data.get('purpose') == 'Updated test'
    print('PASS /api/engine/<id> PUT')

    modes_payload = {'modes': [
        {'frequency': '60', 'power': '20', 'voltage': '400', 'connection_type': 'Delta', 'current': '35', 'rpm': '1800'}
    ]}
    resp = client.put(f'/api/engine/{engine_id}/modes', json=modes_payload)
    data = assert_response(resp)
    assert data.get('success')
    resp = client.get(f'/api/engine/{engine_id}')
    data = assert_response(resp)
    assert len(data.get('modes', [])) == 1
    assert data['modes'][0].get('frequency') == '60'
    print('PASS /api/engine/<id>/modes PUT')

    works_payload = {'works': [
        {'work_number': '2', 'date': '2026-02-02', 'work_description': 'Updated work', 'isolation': '120', 'inspection': 'OK', 'signature': 'Tester2'}
    ]}
    resp = client.put(f'/api/engine/{engine_id}/works', json=works_payload)
    data = assert_response(resp)
    assert data.get('success')
    resp = client.get(f'/api/engine/{engine_id}')
    data = assert_response(resp)
    assert len(data.get('works', [])) == 1
    assert data['works'][0].get('work_number') == '2'
    print('PASS /api/engine/<id>/works PUT')

    # Upload and verify photo handling
    photo_bytes = create_dummy_png_bytes()
    resp = client.post(
        f'/api/engine/{engine_id}/photos',
        data={
            'photos': (io.BytesIO(photo_bytes), 'test.png')
        },
        content_type='multipart/form-data'
    )
    data = assert_response(resp)
    assert data.get('uploaded') == 1
    print('PASS /api/engine/<id>/photos POST')

    resp = client.get(f'/api/engine/{engine_id}/photos')
    data = assert_response(resp)
    assert isinstance(data, list) and len(data) == 1
    photo_file = data[0].get('filename')
    assert photo_file
    print('PASS /api/engine/<id>/photos GET')

    resp = client.get(f'/api/photos/{photo_file}')
    assert resp.status_code == 200
    assert resp.data.startswith(b'\x89PNG')
    print('PASS /api/photos/<filename> GET')

    # Backup and restore
    backup_resp = client.post('/api/backup/create')
    zip_bytes = assert_binary_response(backup_resp)
    assert zip_bytes.startswith(b'PK'), 'Expected zip archive from backup create'
    print('PASS /api/backup/create')

    resp = client.get('/api/backup/list')
    data = assert_response(resp)
    assert isinstance(data, list) and len(data) >= 1
    backup_filename = data[0].get('filename')
    assert backup_filename.endswith('.zip')
    print('PASS /api/backup/list GET')

    # clear data, restore backup, and verify engine/photo are restored
    resp = client.post('/api/clear')
    data = assert_response(resp)
    assert data.get('success')
    resp = client.get(f'/api/engine/{engine_id}')
    assert resp.status_code == 404
    print('PASS /api/clear POST')

    resp = client.post(f'/api/backup/restore/{backup_filename}')
    data = assert_response(resp)
    assert data.get('success')
    print('PASS /api/backup/restore/<filename> POST')

    resp = client.get(f'/api/engine/{engine_id}')
    data = assert_response(resp)
    assert data.get('id') == engine_id
    print('PASS /api/engine/<id> GET after restore')

    resp = client.get(f'/api/engine/{engine_id}/photos')
    data = assert_response(resp)
    assert isinstance(data, list) and len(data) == 1
    print('PASS /api/engine/<id>/photos GET after restore')

    # UI simulation via browser-like fetches
    resp = client.get('/')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8', errors='ignore').lower()
    assert 'server' in body or 'engine' in body or 'сервер' in body
    print('PASS / GET')

    resp = client.get(f'/print/{engine_id}')
    assert resp.status_code == 200
    assert b'<html' in resp.data.lower()
    print('PASS /print/<id> GET')

    resp = client.get('/static/js/auth.js')
    assert resp.status_code == 200
    assert b'function' in resp.data or b'Auth' in resp.data
    print('PASS /static/js/auth.js GET')

    print('=== Self-test completed successfully ===')


if __name__ == '__main__':
    run_tests()
