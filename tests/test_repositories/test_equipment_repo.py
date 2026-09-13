# tests for equipment_repo.py
import pytest


class TestEquipmentTypeCRUD:
    def test_list_equipment_types_empty(self, db_conn):
        from repositories.equipment_repo import list_equipment_types
        assert list_equipment_types(db_conn) == []

    def test_create_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type
        type_id = create_equipment_type(db_conn, code="pump", name="Motor", description="Pump equipment")
        assert type_id > 0

        row = db_conn.execute("SELECT * FROM equipment_type WHERE id = ?", (type_id,)).fetchone()
        assert row is not None
        assert row["code"] == "pump"
        assert row["name"] == "Motor"
        assert row["description"] == "Pump equipment"

    def test_get_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, get_equipment_type
        type_id = create_equipment_type(db_conn, code="motor", name="Engine")
        eq_type = get_equipment_type(db_conn, type_id)
        assert eq_type is not None
        assert eq_type["code"] == "motor"
        assert get_equipment_type(db_conn, 9999) is None

    def test_create_equipment_type_with_parent(self, db_conn):
        from repositories.equipment_repo import create_equipment_type
        parent_id = create_equipment_type(db_conn, code="machine", name="Machine", description="Parent type")
        child_id = create_equipment_type(
            db_conn, code="sub", name="Subtype",
            parent_type_id=parent_id, description="Child"
        )
        assert child_id > 0

        row = db_conn.execute("SELECT * FROM equipment_type WHERE id = ?", (child_id,)).fetchone()
        assert row is not None
        assert row["parent_type_id"] == parent_id


class TestEquipmentTypeInUseAndDelete:
    def test_equipment_type_in_use_false_for_empty(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(db_conn, code="empty-type", name="Empty")
        assert equipment_type_in_use(db_conn, type_id) is False

    def test_equipment_type_in_use_true_with_equipment(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_type_in_use,
        )
        type_id = create_equipment_type(db_conn, code="with-eq", name="WithEquipment")
        eq_id = create_equipment(db_conn, {
            "equipment_type_id": type_id, "name": "EQ001", "article": "EQ001", "note": "Test",
        })
        assert equipment_type_in_use(db_conn, type_id) is True

    def test_equipment_type_in_use_true_with_child_type(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, equipment_type_in_use,
        )
        parent_id = create_equipment_type(db_conn, code="parent", name="Parent")
        create_equipment_type(db_conn, code="child", name="Child", parent_type_id=parent_id)
        assert equipment_type_in_use(db_conn, parent_id) is True

    def test_delete_equipment_type(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, delete_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(db_conn, code="delete-me", name="ToDelete")
        ok = delete_equipment_type(db_conn, type_id)
        assert ok is True
        assert equipment_type_in_use(db_conn, type_id) is False

    def test_delete_equipment_type_not_found(self, db_conn):
        from repositories.equipment_repo import delete_equipment_type
        ok = delete_equipment_type(db_conn, 9999)
        assert ok is False


class TestAttributeDefinition:
    def test_create_attribute_definition(self, db_conn):
        from repositories.equipment_repo import create_attribute_definition
        attr_id = create_attribute_definition(db_conn, {"key": "model", "label": "Model"})
        assert attr_id > 0

        row = db_conn.execute("SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)).fetchone()
        assert row is not None
        assert row["key"] == "model"

    def test_attribute_definition_in_use_false(self, db_conn):
        from repositories.equipment_repo import create_attribute_definition, attribute_definition_in_use
        attr_id = create_attribute_definition(db_conn, {"key": "unused_key", "label": "Unused"})
        assert attribute_definition_in_use(db_conn, attr_id) is False

    def test_attribute_definition_in_use_true(self, db_conn):
        from repositories.equipment_repo import (
            create_attribute_definition, create_equipment_type, create_equipment,
            set_type_attributes, attribute_definition_in_use,
        )
        type_id = create_equipment_type(db_conn, code="with-attr", name="WithAttr")
        eq_id = create_equipment(db_conn, {"equipment_type_id": type_id, "name": "EQ010", "article": "EQ010"})
        attr_id = create_attribute_definition(db_conn, {"key": "used_key", "label": "Used"})
        set_type_attributes(db_conn, type_id, [{"attribute_definition_id": attr_id, "show_in_list": True}])
        assert attribute_definition_in_use(db_conn, attr_id) is True

    def test_delete_attribute_definition(self, db_conn):
        from repositories.equipment_repo import create_attribute_definition, delete_attribute_definition
        attr_id = create_attribute_definition(db_conn, {"key": "del_key", "label": "ToDelete"})
        ok = delete_attribute_definition(db_conn, attr_id)
        assert ok is True

        row = db_conn.execute("SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)).fetchone()
        assert row is None

    def test_delete_attribute_definition_not_found_fails(self, db_conn):
        from repositories.equipment_repo import delete_attribute_definition
        ok = delete_attribute_definition(db_conn, 9999)
        assert ok is False


class TestEquipmentCRUD:
    def test_create_equipment(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, create_equipment
        type_id = create_equipment_type(db_conn, code="motor", name="Engine")
        eq_id = create_equipment(db_conn, {
            "equipment_type_id": type_id, "name": "EQ002", "article": "EQ002", "note": "Test equipment",
        })
        assert eq_id > 0

        row = db_conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row is not None
        assert row["article"] == "EQ002"

    def test_get_equipment_by_id(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, create_equipment, get_equipment_by_id
        type_id = create_equipment_type(db_conn, code="pump", name="Pump")
        eq_id = create_equipment(db_conn, {"equipment_type_id": type_id, "name": "EQ003", "article": "EQ003"})
        eq = get_equipment_by_id(db_conn, eq_id)
        assert eq is not None
        assert eq["id"] == eq_id
        assert eq["article"] == "EQ003"
        assert get_equipment_by_id(db_conn, 9999) is None

    def test_update_equipment(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, update_equipment,
        )
        type_id = create_equipment_type(db_conn, code="motor", name="Engine")
        eq_id = create_equipment(db_conn, {
            "equipment_type_id": type_id, "name": "EQ003", "article": "EQ003", "note": "Original",
        })
        ok = update_equipment(db_conn, eq_id, {
            "equipment_type_id": type_id, "name": "EQ003_UPDATED", "article": "EQ003_UPDATED", "note": "Updated",
        })
        assert ok is True

        row = db_conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row["article"] == "EQ003_UPDATED"
        assert row["note"] == "Updated"

    def test_delete_equipment(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, delete_equipment,
        )
        type_id = create_equipment_type(db_conn, code="pump", name="Pump")
        eq_id = create_equipment(db_conn, {
            "equipment_type_id": type_id, "name": "EQ004", "article": "EQ004", "note": "To delete",
        })
        ok = delete_equipment(db_conn, eq_id)
        assert ok is True

        row = db_conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row is None

    def test_delete_equipment_not_found(self, db_conn):
        from repositories.equipment_repo import delete_equipment
        assert delete_equipment(db_conn, 9999) is False


class TestGetStockSummary:
    def test_get_stock_summary_empty(self, db_conn):
        from repositories.equipment_repo import get_stock_summary
        summary = get_stock_summary(db_conn)
        # get_stock_summary возвращает список dict'ов
        assert isinstance(summary, list)
        assert summary == []

    def test_get_stock_summary_with_data(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, get_stock_summary,
            update_equipment_type_min_stock_qty,
        )
        type_id = create_equipment_type(db_conn, code="pump", name="Pump")
        update_equipment_type_min_stock_qty(db_conn, type_id, 5)
        create_equipment(db_conn, {"equipment_type_id": type_id, "name": "EQ020", "article": "EQ020"})
        create_equipment(db_conn, {"equipment_type_id": type_id, "name": "EQ021", "article": "EQ021"})
        summary = get_stock_summary(db_conn)
        # summary — список dict'ов, ищем нужный тип
        assert isinstance(summary, list)
        assert len(summary) == 1
        assert summary[0]["equipment_type_id"] == type_id
        assert summary[0]["total"] == 2


class TestUpdateEquipmentTypeMinStockQty:
    def test_update_equipment_type_min_stock_qty(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, update_equipment_type_min_stock_qty,
        )
        type_id = create_equipment_type(db_conn, code="pump", name="Pump")
        ok = update_equipment_type_min_stock_qty(db_conn, type_id, 10)
        assert ok is True

        row = db_conn.execute("SELECT * FROM equipment_type WHERE id = ?", (type_id,)).fetchone()
        assert row["min_stock_qty"] == 10

    def test_update_equipment_type_min_stock_qty_not_found(self, db_conn):
        from repositories.equipment_repo import update_equipment_type_min_stock_qty
        assert update_equipment_type_min_stock_qty(db_conn, 9999, 10) is False
ACTOR = {"id": 3, "username": "sidorov", "display_name": "Сидоров С."}


class TestEquipmentLastEdited:
    """last_edited_by/last_edited_at (equipment_repo._ensure_last_edited_columns).

    Реальное поведение: create/update всегда проставляют last_edited_at
    серверным временем; last_edited_by = display_name/username актора, при
    actor=None — NULL, а update(actor=None) перезаписывает прежнего автора
    в NULL.
    """

    def _last_edited(self, db_conn, eq_id):
        row = db_conn.execute(
            "SELECT last_edited_by, last_edited_at FROM equipment WHERE id = ?",
            (eq_id,)).fetchone()
        return row["last_edited_by"], row["last_edited_at"]

    def test_create_with_actor_sets_both(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, create_equipment
        type_id = create_equipment_type(db_conn, code="pump", name="Насос")
        eq_id = create_equipment(
            db_conn,
            {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001"},
            actor=ACTOR,
        )
        editor, edited_at = self._last_edited(db_conn, eq_id)
        assert editor == "Сидоров С."
        assert edited_at is not None

    def test_create_without_actor_by_null_at_set(self, db_conn):
        from repositories.equipment_repo import create_equipment_type, create_equipment
        type_id = create_equipment_type(db_conn, code="pump", name="Насос")
        eq_id = create_equipment(
            db_conn, {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001"}
        )
        editor, edited_at = self._last_edited(db_conn, eq_id)
        assert editor is None
        assert edited_at is not None

    def test_update_with_actor_updates_both(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, update_equipment,
        )
        type_id = create_equipment_type(db_conn, code="pump", name="Насос")
        eq_id = create_equipment(
            db_conn,
            {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001"},
            actor=ACTOR,
        )
        _, first_at = self._last_edited(db_conn, eq_id)

        assert update_equipment(
            db_conn, eq_id,
            {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001", "note": "правка"},
            actor={"id": 5, "username": "petrov", "display_name": "Петров П."},
        ) is True

        editor, edited_at = self._last_edited(db_conn, eq_id)
        assert editor == "Петров П."
        assert edited_at is not None and edited_at != first_at

    def test_update_without_actor_overwrites_null(self, db_conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, update_equipment,
        )
        type_id = create_equipment_type(db_conn, code="pump", name="Насос")
        eq_id = create_equipment(
            db_conn,
            {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001"},
            actor=ACTOR,
        )

        assert update_equipment(
            db_conn, eq_id,
            {"equipment_type_id": type_id, "name": "EQ001", "article": "EQ001", "note": "правка"},
        ) is True

        editor, edited_at = self._last_edited(db_conn, eq_id)
        assert editor is None
        assert edited_at is not None

    def test_ensure_last_edited_columns_idempotent(self, db_conn):
        from repositories.equipment_repo import _ensure_last_edited_columns

        # init_db не содержит колонок — это «старая» схема
        columns = [r[1] for r in db_conn.execute("PRAGMA table_info(equipment)")]
        assert "last_edited_by" not in columns and "last_edited_at" not in columns

        _ensure_last_edited_columns(db_conn)
        _ensure_last_edited_columns(db_conn)  # повторный вызов — идемпотентен

        columns = [r[1] for r in db_conn.execute("PRAGMA table_info(equipment)")]
        assert "last_edited_by" in columns and "last_edited_at" in columns


# ---------------------------------------------------------------------
# Уникальные тесты, перенесённые из test_equipment_repo_part1.py
# (классы TestAttributeInheritance, TestEquipmentGuardsAndCount).
# ---------------------------------------------------------------------

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