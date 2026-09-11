"""Тесты репозитория оборудования — часть 1.

equipment_repo.py очень большой (63 функции). Делим на части.
Часть 1: equipment_type — CRUD, в использовании, удаление.
"""

import pytest


def _create_equipment(db_conn, equipment_id=1):
    """Создаёт equipment_type и equipment с заданным id для FK-тестов."""
    db_conn.execute(
        "INSERT INTO equipment_type (id, code, name) VALUES (?, ?, ?)",
        (1, "test", "Test Type"),
    )
    db_conn.execute(
        "INSERT INTO equipment (id, equipment_type_id, name, article, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (equipment_id, 1, f"Equipment {equipment_id}", f"ART{equipment_id}", "2026-01-01", "2026-01-01"),
    )
    db_conn.commit()
    return equipment_id


class TestEquipmentTypeCRUD:
    def test_list_equipment_types_empty(self, db_conn):
        from repositories.equipment_repo import list_equipment_types
        assert list_equipment_types(db_conn) == []

    def test_create_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type
        type_id = create_equipment_type(db_conn, code="pump", name="Насос", description="Насосное оборудование")
        assert type_id > 0

        row = db_conn.execute("SELECT * FROM equipment_type WHERE id = ?", (type_id,)).fetchone()
        assert row is not None
        assert row["code"] == "pump"
        assert row["name"] == "Насос"
        assert row["description"] == "Насосное оборудование"

    def test_get_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, get_equipment_type
        type_id = create_equipment_type(db_conn, code="motor", name="Двигатель")
        eq_type = get_equipment_type(db_conn, type_id)
        assert eq_type is not None
        assert eq_type["code"] == "motor"
        assert get_equipment_type(db_conn, 9999) is None

    def test_create_equipment_type_with_parent(self, db_conn):
        from repositories.equipment_repo import create_equipment_type
        parent_id = create_equipment_type(db_conn, code="machine", name="Машина", description="Родительский тип")
        child_id = create_equipment_type(
            db_conn, code="sub", name="Подтип",
            parent_type_id=parent_id, description="Дочерний"
        )
        assert child_id > 0

        row = db_conn.execute("SELECT * FROM equipment_type WHERE id = ?", (child_id,)).fetchone()
        assert row is not None
        assert row["parent_type_id"] == parent_id


class TestEquipmentTypeInUseAndDelete:
    def test_equipment_type_in_use_false_for_empty(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(db_conn, code="empty-type", name="Пустой тип")
        assert equipment_type_in_use(db_conn, type_id) is False

    def test_equipment_type_in_use_true_with_equipment(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_type_in_use,
        )
        type_id = create_equipment_type(db_conn, code="with-eq", name="С оборудованием")
        create_equipment(db_conn, {
            "equipment_type_id": type_id, "name": "EQ001", "article": "EQ001", "note": "Тестовое",
        })
        assert equipment_type_in_use(db_conn, type_id) is True

    def test_equipment_type_in_use_true_with_child_type(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, equipment_type_in_use,
        )
        parent_id = create_equipment_type(db_conn, code="parent", name="Родитель")
        create_equipment_type(db_conn, code="child", name="Дочерний", parent_type_id=parent_id)
        assert equipment_type_in_use(db_conn, parent_id) is True

    def test_delete_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, delete_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(db_conn, code="delete-me", name="Удаляемый")
        assert delete_equipment_type(db_conn, type_id) is True
        assert equipment_type_in_use(db_conn, type_id) is False

    def test_delete_equipment_type_not_found(self, db_conn):
        from repositories.equipment_repo import delete_equipment_type
        assert delete_equipment_type(db_conn, 9999) is False


# ---------------------------------------------------------------------
# attribute_definition — переиспользуемый пул (часть 2)
# ---------------------------------------------------------------------

class TestAttributeDefinition:
    def test_create_attribute_definition(self, db_conn):
        from repositories.equipment_repo import create_attribute_definition
        attr_id = create_attribute_definition(db_conn, {
            "key": "test_key", "label": "Тестовый атрибут",
            "group_name": "group1", "value_type": "text",
            "options": [], "default_value": "default", "weight": 10,
        })
        assert attr_id > 0

        row = db_conn.execute(
            "SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)
        ).fetchone()
        assert row is not None
        assert row["key"] == "test_key"
        assert row["label"] == "Тестовый атрибут"

    def test_attribute_definition_in_use_false(self, db_conn):
        from repositories.equipment_repo import (
            create_attribute_definition, attribute_definition_in_use,
        )
        attr_id = create_attribute_definition(db_conn, {"key": "unused_key", "label": "Не используется"})
        assert attribute_definition_in_use(db_conn, attr_id) is False

    def test_attribute_definition_in_use_true(self, db_conn):
        from repositories.equipment_repo import (
            create_attribute_definition, create_equipment_type, create_equipment,
            set_type_attributes, attribute_definition_in_use,
        )
        type_id = create_equipment_type(db_conn, code="with-attr", name="WithAttr")
        attr_id = create_attribute_definition(db_conn, {"key": "used_key", "label": "Используется"})
        create_equipment(db_conn, {"equipment_type_id": type_id, "name": "EQ_USED", "article": "EQ_USED"})
        set_type_attributes(db_conn, type_id, [{"attribute_definition_id": attr_id, "show_in_list": True}])
        assert attribute_definition_in_use(db_conn, attr_id) is True

    def test_delete_attribute_definition_self(self, db_conn):
        from repositories.equipment_repo import (
            create_attribute_definition, delete_attribute_definition,
        )
        attr_id = create_attribute_definition(db_conn, {"key": "del_key", "label": "Для удаления"})
        ok = delete_attribute_definition(db_conn, attr_id)
        assert ok is True
        row = db_conn.execute(
            "SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)
        ).fetchone()
        assert row is None

    def test_delete_attribute_definition_not_found_fails(self, db_conn):
        from repositories.equipment_repo import delete_attribute_definition
        assert delete_attribute_definition(db_conn, 9999) is False
class TestAttributeInheritance:
    """Наследование атрибутов типа: get_assigned_attributes (только свои)
    vs get_effective_attributes (с наследованием от родителя), переопределение
    на дочернем уровне (ближе к листу побеждает)."""

    def _make_hierarchy(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_attribute_definition, set_type_attributes,
        )
        parent = create_equipment_type(db_conn, code='pump', name='Насос')
        child = create_equipment_type(db_conn, code='centrifugal', name='Центробежный', parent_type_id=parent)
        attr_a = create_attribute_definition(db_conn, {'key': 'flow', 'label': 'Расход', 'weight': 10})
        attr_b = create_attribute_definition(db_conn, {'key': 'head', 'label': 'Напор', 'weight': 20})
        attr_c = create_attribute_definition(db_conn, {'key': 'power', 'label': 'Мощность', 'weight': 30})

        # Родитель: a (show_in_list), b; ребёнок: b (переопределён), c.
        set_type_attributes(db_conn, parent, [
            {'attribute_definition_id': attr_a, 'show_in_list': True},
            {'attribute_definition_id': attr_b},
        ])
        set_type_attributes(db_conn, child, [
            {'attribute_definition_id': attr_b, 'is_required': True, 'weight_override': 99},
            {'attribute_definition_id': attr_c},
        ])
        return {'parent': parent, 'child': child, 'a': attr_a, 'b': attr_b, 'c': attr_c}

    def test_assigned_only_own(self, db_conn):
        from repositories.equipment_repo import get_assigned_attributes
        ids = self._make_hierarchy(db_conn)

        parent_keys = {a['key'] for a in get_assigned_attributes(db_conn, ids['parent'])}
        child_keys = {a['key'] for a in get_assigned_attributes(db_conn, ids['child'])}
        assert parent_keys == {'flow', 'head'}
        # У ребёнка ТОЛЬКО свои атрибуты — наследования тут нет
        assert child_keys == {'head', 'power'}
        assert 'flow' not in child_keys  # атрибут родителя не попадает в assigned

    def test_effective_inherits_parent_attributes(self, db_conn):
        from repositories.equipment_repo import get_effective_attributes
        ids = self._make_hierarchy(db_conn)

        attrs = get_effective_attributes(db_conn, ids['child'])
        keys = {a['key'] for a in attrs}
        # flow унаследован от родителя, head и power — свои
        assert keys == {'flow', 'head', 'power'}

    def test_effective_child_overrides_parent(self, db_conn):
        from repositories.equipment_repo import get_effective_attributes
        ids = self._make_hierarchy(db_conn)

        attrs = get_effective_attributes(db_conn, ids['child'])
        by_key = {a['key']: a for a in attrs}
        # head задан и у родителя (без флагов), и у ребёнка (is_required,
        # weight_override=99) — ближе к листу побеждает
        assert by_key['head']['is_required'] == 1
        assert by_key['head']['weight_override'] == 99
        # flow пришёл от родителя без переопределения
        assert by_key['flow']['is_required'] == 0
        assert by_key['flow']['weight_override'] is None

    def test_effective_parent_without_child_override(self, db_conn):
        from repositories.equipment_repo import get_effective_attributes
        ids = self._make_hierarchy(db_conn)

        attrs = get_effective_attributes(db_conn, ids['parent'])
        assert {a['key'] for a in attrs} == {'flow', 'head'}

    def test_show_in_list_effective(self, db_conn):
        from repositories.equipment_repo import get_show_in_list_attributes
        ids = self._make_hierarchy(db_conn)

        shown = get_show_in_list_attributes(db_conn, ids['child'])
        # show_in_list проставлен только у flow (на родителе) — наследуется
        assert [s['key'] for s in shown] == ['flow']
class TestEquipmentGuardsAndCount:
    def test_equipment_referenced_by_incidents_false_without_relation(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_referenced_by_incidents,
        )
        type_id = create_equipment_type(db_conn, code='pump', name='Насос')
        eq_id = create_equipment(db_conn, {
            'equipment_type_id': type_id, 'name': 'EQ100', 'article': 'EQ100',
        })
        assert equipment_referenced_by_incidents(db_conn, eq_id) is False

    def test_equipment_referenced_by_incidents_true_with_relation(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_referenced_by_incidents,
        )
        from repositories.incident_ticket_repo import create as create_ticket
        from repositories.incident_equipment_repo import add_relation

        type_id = create_equipment_type(db_conn, code='pump', name='Насос')
        eq_id = create_equipment(db_conn, {
            'equipment_type_id': type_id, 'name': 'EQ101', 'article': 'EQ101',
        })
        cur = db_conn.execute(
            "INSERT INTO location_node (name, node_type) VALUES ('Цех', 'workshop')"
        )
        db_conn.commit()
        loc_id = cur.lastrowid
        ticket_id = create_ticket(
            db_conn, location_node_id=loc_id, problem='П', created_by_user_id=1,
        )
        assert equipment_referenced_by_incidents(db_conn, eq_id) is False
        add_relation(db_conn, ticket_id, eq_id)
        assert equipment_referenced_by_incidents(db_conn, eq_id) is True

    def test_equipment_referenced_unknown_id_false(self, db_conn):
        from repositories.equipment_repo import equipment_referenced_by_incidents
        assert equipment_referenced_by_incidents(db_conn, 99999) is False

    def test_count_all(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, count_all,
        )
        assert count_all(db_conn) == 0
        type_id = create_equipment_type(db_conn, code='pump', name='Насос')
        create_equipment(db_conn, {'equipment_type_id': type_id, 'name': 'E1', 'article': 'A1'})
        create_equipment(db_conn, {'equipment_type_id': type_id, 'name': 'E2', 'article': 'A2'})
        assert count_all(db_conn) == 2
        assert shown[0]['label'] == 'Расход'