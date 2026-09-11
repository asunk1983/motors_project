"""Тесты для location_repo.py."""

import pytest

from repositories.location_repo import (
    create, get_by_id, list_all, get_children, search,
    get_breadcrumb_text, move, delete, get_subtree_ids, update,
)


def _entries(db_conn):
    """Возвращает audit-записи, исключая __created__ (лог создания отдельно)."""
    cur = db_conn.cursor()
    cur.execute("SELECT * FROM audit_log WHERE field_name != '__created__' ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


@pytest.fixture
def tree(db_conn):
    root = create(db_conn, 'Цех №1', 'workshop')
    line = create(db_conn, 'Линия 2', 'installation', parent_id=root)
    zone = create(db_conn, 'Зона 3', 'zone', parent_id=line)
    return {'root': root, 'line': line, 'zone': zone}


def test_create_and_get(db_conn):
    nid = create(db_conn, 'Цех 1', 'workshop')
    node = get_by_id(db_conn, nid)
    assert node['name'] == 'Цех 1' and node['node_type'] == 'workshop' and node['parent_id'] is None


def test_children_root_only(db_conn, tree):
    assert [c['id'] for c in get_children(db_conn, None)] == [tree['root']]


def test_list_sorted_roots_first(db_conn, tree):
    assert list_all(db_conn)[0]['id'] == tree['root']


def test_subtree_ids(db_conn, tree):
    assert sorted(get_subtree_ids(db_conn, tree['root'])) == sorted(tree.values())


def test_breadcrumb_text(db_conn, tree):
    assert get_breadcrumb_text(db_conn, tree['zone']) == 'Цех №1 → Линия 2 → Зона 3'


def test_search_cyrillic_case_insensitive(db_conn, tree):
    results = search(db_conn, 'зона')
    assert [r['id'] for r in results] == [tree['zone']]
    assert results[0]['path'] == 'Цех №1 → Линия 2 → Зона 3'


def test_move_to_other_branch_ok_and_audit(db_conn, tree):
    other = create(db_conn, 'Цех №2', 'workshop')
    ok, err = move(db_conn, tree['zone'], other)
    assert ok is True and err is None
    assert get_by_id(db_conn, tree['zone'])['parent_id'] == other
    assert _entries(db_conn)[0]['field_name'] == 'parent_id'


def test_move_to_itself_rejected(db_conn, tree):
    ok, err = move(db_conn, tree['root'], tree['root'])
    assert ok is False and 'родителем самого себя' in err


def test_move_into_subtree_rejected(db_conn, tree):
    ok, err = move(db_conn, tree['root'], tree['zone'])
    assert ok is False and 'собственное поддерево' in err


def test_move_to_missing_parent_rejected(db_conn, tree):
    ok, err = move(db_conn, tree['zone'], 999999)
    assert ok is False and 'родитель не найден' in err


def test_move_same_parent_no_audit(db_conn, tree):
    ok, err = move(db_conn, tree['line'], tree['root'])
    assert ok is True
    assert _entries(db_conn) == []


def test_update_name_and_audit(db_conn, tree):
    assert update(db_conn, tree['root'], name='Цех №1 (переименован)',
                  actor={'id': 1, 'username': 'admin', 'display_name': 'Админ'}) is True
    assert get_by_id(db_conn, tree['root'])['name'] == 'Цех №1 (переименован)'
    row = _entries(db_conn)[0]
    assert row['field_name'] == 'name' and row['changed_by_display_name'] == 'Админ'


def test_update_no_fields_false(db_conn, tree):
    assert update(db_conn, tree['root']) is False


def test_delete_with_children_rejected(db_conn, tree):
    ok, err = delete(db_conn, tree['root'])
    assert ok is False and 'дочерние места' in err


def test_delete_leaf_ok(db_conn, tree):
    ok, err = delete(db_conn, tree['zone'])
    assert ok is True and get_by_id(db_conn, tree['zone']) is None
def test_delete_referenced_by_incident_rejected(db_conn, tree):
    """Узел, на который ссылается заявка Инцидента, удалить нельзя."""
    from repositories.incident_ticket_repo import create as create_ticket

    create_ticket(db_conn, location_node_id=tree['line'], problem='П', created_by_user_id=1)

    ok, err = delete(db_conn, tree['line'])
    assert ok is False and 'используется' in err
    assert get_by_id(db_conn, tree['line']) is not None


def test_delete_referenced_by_equipment_rejected(db_conn, tree):
    """Узел, на который ссылается equipment.location_node_id, удалить нельзя."""
    from repositories.equipment_repo import create_equipment_type, create_equipment

    type_id = create_equipment_type(db_conn, code='pump', name='Насос')
    create_equipment(db_conn, {
        'equipment_type_id': type_id, 'name': 'EQ001', 'article': 'EQ001',
        'location_node_id': tree['line'],
    })

    ok, err = delete(db_conn, tree['line'])
    assert ok is False and 'используется' in err


def test_delete_referenced_by_placement_rejected(db_conn, tree):
    """Узел, на который ссылается equipment_placement.location_node_id,
    удалить нельзя."""
    from repositories.equipment_repo import create_equipment_type, create_equipment
    from repositories.equipment_placement_repo import create as create_placement

    type_id = create_equipment_type(db_conn, code='pump', name='Насос')
    eq_id = create_equipment(db_conn, {
        'equipment_type_id': type_id, 'name': 'EQ001', 'article': 'EQ001',
    })
    create_placement(db_conn, eq_id, tree['line'], designation='КМ1')

    ok, err = delete(db_conn, tree['line'])
    assert ok is False and 'используется' in err
    assert get_by_id(db_conn, tree['line']) is not None


def test_is_referenced_true_false(db_conn, tree):
    """is_referenced: False для свободного узла, True при ссылке заявки."""
    from repositories.location_repo import is_referenced
    from repositories.incident_ticket_repo import create as create_ticket

    assert is_referenced(db_conn, tree['zone']) is False
    create_ticket(db_conn, location_node_id=tree['zone'], problem='П', created_by_user_id=1)
    assert is_referenced(db_conn, tree['zone']) is True