"""Интеграция repositories/engine_repo.py с журналом изменений (audit_log).

update/update_status/update_photo_count обязаны писать дифф через
modules/audit.py::log_field_changes.
"""
from repositories.engine_repo import create, update, update_status, update_photo_count, get_locations_tree


def _entries(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM audit_log ORDER BY id')
    return [dict(r) for r in cur.fetchall()]


def _make_engine(db_conn):
    return create(db_conn, {
        'location': 'Цех 1', 'engine_type': 'АИР112М4У2',
        'serial_number': 'SN12345', 'note': 'старая заметка', 'photo_count': 0,
    })


def test_update_logs_only_changed_fields(db_conn):
    eid = _make_engine(db_conn)
    update(db_conn, eid, {'location': 'Цех 2', 'note': 'новая'})
    rows = _entries(db_conn)
    assert {r['field_name'] for r in rows} == {'location', 'note'}
    assert all(r['entity_type'] == 'engine' and r['entity_id'] == eid for r in rows)


def test_update_same_values_no_log(db_conn):
    eid = _make_engine(db_conn)
    update(db_conn, eid, {'location': 'Цех 1'})
    assert _entries(db_conn) == []


def test_update_with_actor(db_conn):
    eid = _make_engine(db_conn)
    update(db_conn, eid, {'location': 'Цех 2'},
           actor={'id': 3, 'username': 'sidorov', 'display_name': 'Сидоров С.'})
    row = _entries(db_conn)[0]
    assert row['changed_by_user_id'] == 3 and row['changed_by_display_name'] == 'Сидоров С.'


def test_update_without_actor_null(db_conn):
    eid = _make_engine(db_conn)
    update(db_conn, eid, {'location': 'Цех 2'})
    row = _entries(db_conn)[0]
    assert row['changed_by_user_id'] is None and row['changed_by_display_name'] is None


def test_update_status_logs(db_conn):
    eid = _make_engine(db_conn)
    assert update_status(db_conn, eid, 'reserve',
                         actor={'id': 1, 'username': 'admin', 'display_name': 'Админ'}) is True
    row = _entries(db_conn)[0]
    assert row['field_name'] == 'status'
    assert row['old_value'] == 'work' and row['new_value'] == 'reserve'


def test_update_status_same_value_no_log(db_conn):
    eid = _make_engine(db_conn)   # дефолтный статус 'work'
    update_status(db_conn, eid, 'work')
    assert _entries(db_conn) == []


def test_update_photo_count_logs(db_conn):
    eid = _make_engine(db_conn)
    update_photo_count(db_conn, eid, 3)
    row = _entries(db_conn)[0]
    assert row['field_name'] == 'photo_count'
    assert row['old_value'] == '0' and row['new_value'] == '3'


def test_get_locations_tree(db_conn):
    create(db_conn, {'workshop': 'Цех 1', 'location': 'Линия A'})
    create(db_conn, {'workshop': 'Цех 1', 'location': 'Линия A'})
    create(db_conn, {'workshop': 'Цех 1', 'location': 'Линия B'})
    tree = get_locations_tree(db_conn)
    assert tree['Цех 1']['Линия A'] == 2
    assert tree['Цех 1']['Линия B'] == 1