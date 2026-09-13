"""Тесты repository equipment_placement (repositories/equipment_placement_repo.py).

Покрывают: create, get_by_id, list_by_equipment, delete,
designation_exists_in_location (уникальность обозначения в рамках одной
локации; в разных локациях одинаковое обозначение разрешено).

Схема (modules/db.py): частичный уникальный индекс
idx_equipment_placement_unique_designation ON (location_node_id, designation)
WHERE designation IS NOT NULL — NULL-обозначения не конфликтуют.
"""

import pytest


def _make_equipment(db_conn, code='pump'):
    from repositories.equipment_repo import create_equipment_type, create_equipment
    type_id = create_equipment_type(db_conn, code=code, name=f'Name {code}')
    return create_equipment(db_conn, {
        'equipment_type_id': type_id, 'name': f'EQ {code}', 'article': f'ART {code}',
    })


@pytest.fixture
def equipment_id(db_conn):
    return _make_equipment(db_conn)


@pytest.fixture
def loc_ids(db_conn):
    from repositories.location_repo import create as create_location
    root = create_location(db_conn, 'Цех 1', 'workshop')
    line = create_location(db_conn, 'Линия 1', 'installation', parent_id=root)
    return {'root': root, 'line': line}


class TestCreateAndGet:
    def test_create_returns_id(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create
        pid = create(db_conn, equipment_id, loc_ids['root'], designation='КМ1', note='Шкаф E021')
        assert pid > 0

    def test_get_by_id_roundtrip(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, get_by_id
        pid = create(db_conn, equipment_id, loc_ids['line'], designation='КМ2')
        row = get_by_id(db_conn, pid)
        assert row is not None
        assert row['equipment_id'] == equipment_id
        assert row['location_node_id'] == loc_ids['line']
        assert row['designation'] == 'КМ2'
        assert row['note'] is None

    def test_get_by_id_not_found(self, db_conn):
        from repositories.equipment_placement_repo import get_by_id
        assert get_by_id(db_conn, 99999) is None

    def test_create_without_designation_ok(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create
        # два NULL-обозначения в одном месте не конфликтуют (частичный индекс)
        p1 = create(db_conn, equipment_id, loc_ids['root'])
        p2 = create(db_conn, equipment_id, loc_ids['root'])
        assert p1 > 0 and p2 > 0
class TestListByEquipment:
    def test_empty(self, db_conn, equipment_id):
        from repositories.equipment_placement_repo import list_by_equipment
        assert list_by_equipment(db_conn, equipment_id) == []

    def test_multiple_placements_sorted_with_breadcrumb(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, list_by_equipment
        create(db_conn, equipment_id, loc_ids['line'], designation='КМ3')
        create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        rows = list_by_equipment(db_conn, equipment_id)
        assert len(rows) == 2
        # сортировка по location_node_id (меньший id — root первым), затем designation
        assert rows[0]['designation'] == 'КМ1'
        assert rows[1]['designation'] == 'КМ3'
        assert rows[0]['location_path'] == 'Цех 1'
        assert rows[1]['location_path'] == 'Цех 1 → Линия 1'

    def test_does_not_leak_other_equipment(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, list_by_equipment
        other_eq = _make_equipment(db_conn, code='valve')
        create(db_conn, other_eq, loc_ids['root'], designation='КМ1')
        assert list_by_equipment(db_conn, equipment_id) == []


class TestDesignationExistsInLocation:
    def test_true_when_same_designation_in_same_location(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, designation_exists_in_location
        create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        assert designation_exists_in_location(db_conn, loc_ids['root'], 'КМ1') is True

    def test_false_for_different_designation(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, designation_exists_in_location
        create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        assert designation_exists_in_location(db_conn, loc_ids['root'], 'КМ2') is False

    def test_false_in_another_location(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, designation_exists_in_location
        create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        # то же обозначение в другой локации — не занято
        assert designation_exists_in_location(db_conn, loc_ids['line'], 'КМ1') is False

    def test_same_designation_allowed_in_different_locations(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, designation_exists_in_location
        create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        create(db_conn, equipment_id, loc_ids['line'], designation='КМ1')
        assert designation_exists_in_location(db_conn, loc_ids['root'], 'КМ1') is True
        assert designation_exists_in_location(db_conn, loc_ids['line'], 'КМ1') is True

    def test_empty_designation_never_conflicts(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import designation_exists_in_location
        assert designation_exists_in_location(db_conn, loc_ids['root'], None) is False
        assert designation_exists_in_location(db_conn, loc_ids['root'], '') is False


class TestDelete:
    def test_delete_success(self, db_conn, equipment_id, loc_ids):
        from repositories.equipment_placement_repo import create, delete, get_by_id
        pid = create(db_conn, equipment_id, loc_ids['root'], designation='КМ1')
        assert delete(db_conn, pid) is True
        assert get_by_id(db_conn, pid) is None

    def test_delete_not_found(self, db_conn):
        from repositories.equipment_placement_repo import delete
        assert delete(db_conn, 99999) is False