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