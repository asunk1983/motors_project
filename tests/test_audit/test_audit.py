"""Тесты модуля записи журнала изменений (modules/audit.py::log_field_changes).

Журнал изменений (audit_log) — единая точка для всех UPDATE в проекте:
одна строка на каждое РЕАЛЬНО изменившееся поле. Здесь проверяется сама
семантика сравнения (по строковому представлению), обработка None,
частичного набора полей и атрибуция автора.
"""
from modules.audit import log_field_changes


def _entries(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM audit_log ORDER BY id')
    return [dict(r) for r in cur.fetchall()]


def _insert_engine(conn, **overrides):
    fields = {'location': 'Цех 1', 'engine_type': 'АИР112',
              'serial_number': 'SN1', 'photo_count': 0, 'note': None}
    fields.update(overrides)
    cols = ', '.join(fields)
    ph = ', '.join('?' for _ in fields)
    cur = conn.cursor()
    cur.execute(f'INSERT INTO engines ({cols}) VALUES ({ph})', list(fields.values()))
    conn.commit()
    return cur.lastrowid


class TestLogFieldChanges:
    def test_old_row_none_writes_nothing(self, db_conn):
        log_field_changes(db_conn, 'engine', 1, None, None, {'location': 'Цех 2'})
        assert _entries(db_conn) == []

    def test_unchanged_fields_written_nothing(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None,
                          {'location': 'Цех 1'}, {'location': 'Цех 1'})
        assert _entries(db_conn) == []

    def test_changed_field_written(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None,
                          {'location': 'Цех 1', 'engine_type': 'АИР112'},
                          {'location': 'Цех 2'})
        row = _entries(db_conn)[0]
        assert row['entity_type'] == 'engine'
        assert row['entity_id'] == eid
        assert row['field_name'] == 'location'
        assert row['old_value'] == 'Цех 1'
        assert row['new_value'] == 'Цех 2'

    def test_field_absent_in_old_row_skipped(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None,
                          {'location': 'Цех 1'},            # нет engine_type в old
                          {'engine_type': 'АИР112', 'location': 'Цех 2'})
        assert [r['field_name'] for r in _entries(db_conn)] == ['location']

    def test_none_to_value_written(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None, {'note': None}, {'note': 'добавлено'})
        row = _entries(db_conn)[0]
        assert row['old_value'] is None
        assert row['new_value'] == 'добавлено'

    def test_value_to_none_written(self, db_conn):
        eid = _insert_engine(db_conn, note='важно')
        log_field_changes(db_conn, 'engine', eid, None, {'note': 'важно'}, {'note': None})
        row = _entries(db_conn)[0]
        assert row['old_value'] == 'важно'
        assert row['new_value'] is None

    def test_compare_is_str_insensitive_to_types(self, db_conn):
        # SQLite вернёт int, JSON/фронт — строку: '3' == 3 не должно считаться изменением
        eid = _insert_engine(db_conn, photo_count=3)
        log_field_changes(db_conn, 'engine', eid, None, {'photo_count': 3}, {'photo_count': '3'})
        assert _entries(db_conn) == []

    def test_multiple_fields_multiple_rows(self, db_conn):
        eid = _insert_engine(db_conn)
        old = {'location': 'Цех 1', 'engine_type': 'АИР112', 'serial_number': 'SN1'}
        log_field_changes(db_conn, 'engine', eid, None, old,
                          {'location': 'Цех 2', 'engine_type': 'АИР113', 'serial_number': 'SN1'})
        assert [r['field_name'] for r in _entries(db_conn)] == ['location', 'engine_type']

    def test_actor_display_name_written(self, db_conn):
        eid = _insert_engine(db_conn)
        actor = {'id': 7, 'username': 'login', 'display_name': 'Иванов Иван'}
        log_field_changes(db_conn, 'engine', eid, actor, {'location': 'Цех 1'}, {'location': 'Цех 2'})
        row = _entries(db_conn)[0]
        assert row['changed_by_user_id'] == 7
        assert row['changed_by_display_name'] == 'Иванов Иван'

    def test_actor_fallback_to_username(self, db_conn):
        eid = _insert_engine(db_conn)
        actor = {'id': 7, 'username': 'ivanov'}
        log_field_changes(db_conn, 'engine', eid, actor, {'location': 'Цех 1'}, {'location': 'Цех 2'})
        assert _entries(db_conn)[0]['changed_by_display_name'] == 'ivanov'

    def test_no_actor_writes_null(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None, {'location': 'Цех 1'}, {'location': 'Цех 2'})
        row = _entries(db_conn)[0]
        assert row['changed_by_user_id'] is None
        assert row['changed_by_display_name'] is None

    def test_changed_at_is_iso_format(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None, {'location': 'Цех 1'}, {'location': 'Цех 2'})
        changed_at = _entries(db_conn)[0]['changed_at']
        assert 'T' in changed_at
        assert len(changed_at.split('T')[0]) == 10

    def test_does_not_commit_itself(self, db_conn):
        eid = _insert_engine(db_conn)
        log_field_changes(db_conn, 'engine', eid, None, {'location': 'Цех 1'}, {'location': 'Цех 2'})
        # контракт: функция не делает commit — коммитит вызывающая repo-функция
        assert db_conn.in_transaction is True