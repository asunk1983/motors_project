"""Тесты чтения журнала изменений (repositories/audit_repo.py)."""
from datetime import datetime

from repositories import audit_repo


def _add_audit(conn, entity_type='engine', entity_id=1, field_name='location',
               old_value='Цех 1', new_value='Цех 2', author='Иванов Иван',
               changed_at='2026-09-01T10:00:00'):
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO audit_log (entity_type, entity_id, field_name, old_value, new_value, '
        'changed_by_user_id, changed_by_display_name, changed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (entity_type, entity_id, field_name, old_value, new_value, 1, author, changed_at)
    )
    conn.commit()


class TestListEntries:
    def test_empty_journal(self, db_conn):
        rows, total = audit_repo.list_entries(db_conn)
        assert rows == [] and total == 0

    def test_all_entries_and_total(self, db_conn):
        _add_audit(db_conn, changed_at='2026-09-01T10:00:00')
        _add_audit(db_conn, entity_type='equipment', changed_at='2026-09-02T10:00:00')
        _add_audit(db_conn, changed_at='2026-09-03T10:00:00')
        rows, total = audit_repo.list_entries(db_conn)
        assert total == 3 and len(rows) == 3

    def test_filter_by_entity_type(self, db_conn):
        _add_audit(db_conn)
        _add_audit(db_conn, entity_type='equipment')
        rows, total = audit_repo.list_entries(db_conn, entity_type='equipment')
        assert total == 1 and rows[0]['entity_type'] == 'equipment'

    def test_filter_by_entity_id(self, db_conn):
        _add_audit(db_conn, entity_id=1)
        _add_audit(db_conn, entity_id=2)
        rows, total = audit_repo.list_entries(db_conn, entity_id=2)
        assert total == 1 and rows[0]['entity_id'] == 2

    def test_filter_by_date_range(self, db_conn):
        _add_audit(db_conn, changed_at='2026-09-01T10:00:00')
        _add_audit(db_conn, changed_at='2026-09-05T10:00:00')
        _add_audit(db_conn, changed_at='2026-09-10T10:00:00')
        rows, total = audit_repo.list_entries(db_conn, date_from='2026-09-05', date_to='2026-09-06T23:59:59')
        assert total == 1 and rows[0]['changed_at'] == '2026-09-05T10:00:00'

    def test_filter_by_actor_registry_cyrillic(self, db_conn):
        # кириллица: встроенный SQLite LIKE/COLLATE NOCASE не матчит — фильтр в Python
        _add_audit(db_conn, author='Иванов Иван')
        _add_audit(db_conn, author='Петров Пётр')
        rows, total = audit_repo.list_entries(db_conn, actor_query='иванов')
        assert total == 1 and rows[0]['changed_by_display_name'] == 'Иванов Иван'

    def test_pagination(self, db_conn):
        for i in range(5):
            _add_audit(db_conn, entity_id=i + 1, changed_at=f'2026-09-0{i+1}T10:00:00')
        p1, total = audit_repo.list_entries(db_conn, limit=2, offset=0)
        assert len(p1) == 2 and total == 5
        assert len(audit_repo.list_entries(db_conn, limit=2, offset=2)[0]) == 2

    def test_order_by_changed_at_desc(self, db_conn):
        _add_audit(db_conn, field_name='first', changed_at='2026-09-01T10:00:00')
        _add_audit(db_conn, field_name='second', changed_at='2026-09-02T10:00:00')
        rows, _ = audit_repo.list_entries(db_conn)
        assert [r['field_name'] for r in rows] == ['second', 'first']


class TestLocationValueLabel:
    def test_location_node_id_resolved_to_breadcrumb(self, db_conn):
        from repositories.location_repo import create
        root = create(db_conn, 'Цех №1', 'workshop')
        zone = create(db_conn, 'Зона 3', 'zone', parent_id=root)
        cur = db_conn.cursor()
        cur.execute(
            'INSERT INTO audit_log (entity_type, entity_id, field_name, old_value, new_value, changed_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            ('engine', 1, 'location_node_id', str(root), str(zone), '2026-09-01T10:00:00'))
        db_conn.commit()
        rows, _ = audit_repo.list_entries(db_conn)
        assert rows[0]['old_value_display'] == 'Цех №1'
        assert rows[0]['new_value_display'] == 'Цех №1 → Зона 3'

    def test_unknown_location_keeps_raw(self, db_conn):
        cur = db_conn.cursor()
        cur.execute(
            'INSERT INTO audit_log (entity_type, entity_id, field_name, old_value, new_value, changed_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            ('engine', 1, 'location_node_id', '999', None, '2026-09-01T10:00:00'))
        db_conn.commit()
        rows, _ = audit_repo.list_entries(db_conn)
        assert rows[0]['old_value_display'] is None
        assert rows[0]['new_value_display'] is None


class TestGrowthStats:
    def test_growth_stats(self, db_conn):
        today = datetime.now().date().isoformat()
        _add_audit(db_conn, changed_at=f'{today}T10:00:00')
        _add_audit(db_conn, changed_at=f'{today}T12:00:00')
        _add_audit(db_conn, changed_at='2000-01-01T10:00:00')
        stats = audit_repo.growth_stats(db_conn, days=90)
        assert stats['total'] == 3
        assert stats['days'] == 90
        assert stats['by_day'][today] == 2
        assert '2000-01-01' not in stats['by_day']


class TestListEntityTypes:
    """Список различных entity_type для фильтра журнала."""

    def test_empty_journal(self, db_conn):
        assert audit_repo.list_entity_types(db_conn) == []

    def test_distinct_sorted(self, db_conn):
        _add_audit(db_conn, entity_type='engine')
        _add_audit(db_conn, entity_type='equipment')
        _add_audit(db_conn, entity_type='engine')
        _add_audit(db_conn, entity_type='crew')
        assert audit_repo.list_entity_types(db_conn) == ['crew', 'engine', 'equipment']
