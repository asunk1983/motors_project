
# tests for equipment_repo.py
import pytest


class TestEquipmentTypeCRUD:
    def test_list_equipment_types_empty(self, conn):
        from repositories.equipment_repo import list_equipment_types
        assert list_equipment_types(conn) == []

    def test_create_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type
        type_id = create_equipment_type(conn, code="pump", name="Motor", description="Pump equipment")
        assert type_id > 0

        row = conn.execute("SELECT * FROM equipment_type WHERE id = ?", (type_id,)).fetchone()
        assert row is not None
        assert row["code"] == "pump"
        assert row["name"] == "Motor"
        assert row["description"] == "Pump equipment"

    def test_get_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type, get_equipment_type
        type_id = create_equipment_type(conn, code="motor", name="Engine")
        eq_type = get_equipment_type(conn, type_id)
        assert eq_type is not None
        assert eq_type["code"] == "motor"
        assert get_equipment_type(conn, 9999) is None

    def test_create_equipment_type_with_parent(self, conn):
        from repositories.equipment_repo import create_equipment_type
        parent_id = create_equipment_type(conn, code="machine", name="Machine", description="Parent type")
        child_id = create_equipment_type(
            conn, code="sub", name="Subtype",
            parent_type_id=parent_id, description="Child"
        )
        assert child_id > 0

        row = conn.execute("SELECT * FROM equipment_type WHERE id = ?", (child_id,)).fetchone()
        assert row is not None
        assert row["parent_type_id"] == parent_id


class TestEquipmentTypeInUseAndDelete:
    def test_equipment_type_in_use_false_for_empty(self, conn):
        from repositories.equipment_repo import create_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(conn, code="empty-type", name="Empty")
        assert equipment_type_in_use(conn, type_id) is False

    def test_equipment_type_in_use_true_with_equipment(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_type_in_use,
        )
        type_id = create_equipment_type(conn, code="with-eq", name="WithEquipment")
        create_equipment(conn, equipment_type_id=type_id, code="EQ001", description="Test")
        assert equipment_type_in_use(conn, type_id) is True

    def test_equipment_type_in_use_true_with_child_type(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, equipment_type_in_use,
        )
        parent_id = create_equipment_type(conn, code="parent", name="Parent")
        create_equipment_type(conn, code="child", name="Child", parent_type_id=parent_id)
        assert equipment_type_in_use(conn, parent_id) is True

    def test_delete_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type, delete_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(conn, code="delete-me", name="ToDelete")
        assert delete_equipment_type(conn, type_id) is True
        assert equipment_type_in_use(conn, type_id) is False

    def test_delete_equipment_type_not_found(self, conn):
        from repositories.equipment_repo import delete_equipment_type
        assert delete_equipment_type(conn, 9999) is False


class TestAttributeDefinition:
    def test_create_attribute_definition(self, conn):
        from repositories.equipment_repo import create_attribute_definition
        attr_id = create_attribute_definition(
            conn,
            key="test_key",
            label="Test attribute",
            group_name="group1",
            value_type="string",
            options_json="[]",
            default_value="default",
            weight=10,
        )
        assert attr_id > 0

        row = conn.execute(
            "SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)
        ).fetchone()
        assert row is not None
        assert row["key"] == "test_key"
        assert row["label"] == "Test attribute"

    def test_attribute_definition_in_use_false(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, attribute_definition_in_use,
        )
        attr_id = create_attribute_definition(
            conn, key="unused_key", label="Not used",
        )
        assert attribute_definition_in_use(conn, attr_id) is False

    def test_attribute_definition_in_use_true(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, create_equipment, create_attribute_assignment, attribute_definition_in_use,
        )
        attr_id = create_attribute_definition(conn, key="used_key", label="Used")
        eq_id = create_equipment(conn, equipment_type_id=1, code="EQ_USED")
        create_attribute_assignment(conn, eq_id, attr_id, "value123")
        assert attribute_definition_in_use(conn, attr_id) is True

    def test_delete_attribute_definition(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, delete_attribute_definition,
        )
        attr_id = create_attribute_definition(conn, key="del_key", label="For delete")
        ok = delete_attribute_definition(conn, attr_id)
        assert ok is True
        row = conn.execute(
            "SELECT * FROM attribute_definition WHERE id = ?", (attr_id,)
        ).fetchone()
        assert row is None

    def test_delete_attribute_definition_not_found_fails(self, conn):
        from repositories.equipment_repo import delete_attribute_definition
        assert delete_attribute_definition(conn, 9999) is False


class TestEquipmentCRUD:
    def test_create_equipment(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment,
        )
        type_id = create_equipment_type(conn, code="pump", name="Pump", description="Pump equipment")
        eq_id = create_equipment(
            conn,
            equipment_type_id=type_id,
            code="EQ001",
            description="Test equipment",
            location_id=1,
        )
        assert eq_id > 0

        row = conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row is not None
        assert row["code"] == "EQ001"
        assert row["description"] == "Test equipment"
        assert row["location_id"] == 1

    def test_get_equipment_by_id(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, get_equipment_by_id,
        )
        type_id = create_equipment_type(conn, code="motor", name="Engine")
        eq_id = create_equipment(
            conn,
            equipment_type_id=type_id,
            code="EQ002",
            description="Test equipment 2",
        )
        eq = get_equipment_by_id(conn, eq_id)
        assert eq is not None
        assert eq["code"] == "EQ002"
        assert get_equipment_by_id(conn, 9999) is None

    def test_update_equipment(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, update_equipment,
        )
        type_id = create_equipment_type(conn, code="motor", name="Engine")
        eq_id = create_equipment(
            conn,
            equipment_type_id=type_id,
            code="EQ003",
            description="Original",
            location_id=1,
        )
        ok = update_equipment(
            conn,
            equipment_id=eq_id,
            code="EQ003_UPDATED",
            description="Updated",
            location_id=2,
        )
        assert ok is True

        row = conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row["code"] == "EQ003_UPDATED"
        assert row["description"] == "Updated"
        assert row["location_id"] == 2

    def test_delete_equipment(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, delete_equipment,
        )
        type_id = create_equipment_type(conn, code="pump", name="Pump")
        eq_id = create_equipment(
            conn,
            equipment_type_id=type_id,
            code="EQ004",
            description="To delete",
        )
        ok = delete_equipment(conn, eq_id)
        assert ok is True

        row = conn.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,)).fetchone()
        assert row is None

    def test_delete_equipment_not_found(self, conn):
        from repositories.equipment_repo import delete_equipment
        assert delete_equipment(conn, 9999) is False


class TestGetStockSummary:
    def test_get_stock_summary_empty(self, conn):
        from repositories.equipment_repo import get_stock_summary
        summary = get_stock_summary(conn)
        assert summary["total"] == 0
        assert summary["types"] == 0
        assert summary["min_stock_qty_types"] == 0
        assert summary["max_motor_count"] == 0

    def test_get_stock_summary_with_data(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, get_stock_summary,
        )
        type_id = create_equipment_type(conn, code="pump", name="Pump", min_stock_qty=5)
        create_equipment(conn, equipment_type_id=type_id, code="EQ020")
        create_equipment(conn, equipment_type_id=type_id, code="EQ021")
        summary = get_stock_summary(conn)
        assert summary["total"] == 2
        assert summary["types"] == 1
        assert summary["min_stock_qty_types"] == 1


class TestUpdateEquipmentTypeMinStockQty:
    def test_update_equipment_type_min_stock_qty(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, update_equipment_type_min_stock_qty,
        )
        type_id = create_equipment_type(conn, code="pump", name="Pump", min_stock_qty=5)
        ok = update_equipment_type_min_stock_qty(conn, type_id, 10)
        assert ok is True

        row = conn.execute("SELECT * FROM equipment_type WHERE id = ?", (type_id,)).fetchone()
        assert row["min_stock_qty"] == 10

    def test_update_equipment_type_min_stock_qty_not_found(self, conn):
        from repositories.equipment_repo import update_equipment_type_min_stock_qty
        assert update_equipment_type_min_stock_qty(conn, 9999, 10) is False
