"""Тесты репозитория оборудования — часть 1.

equipment_repo.py очень большой (63 функции). Делим на части.
Часть 1: equipment_type — CRUD, в использовании, удаление.
"""

import pytest


class TestEquipmentTypeCRUD:
    def test_list_equipment_types_empty(self, conn):
        from repositories.equipment_repo import list_equipment_types
        assert list_equipment_types(conn) == []

    def test_create_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type
        type_id = create_equipment_type(conn, code='pump', name='Насос', description='Насосное оборудование')
        assert type_id > 0

        row = conn.execute('SELECT * FROM equipment_type WHERE id = ?', (type_id,)).fetchone()
        assert row is not None
        assert row['code'] == 'pump'
        assert row['name'] == 'Насос'
        assert row['description'] == 'Насосное оборудование'

    def test_get_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type, get_equipment_type
        type_id = create_equipment_type(conn, code='motor', name='Двигатель')
        eq_type = get_equipment_type(conn, type_id)
        assert eq_type is not None
        assert eq_type['code'] == 'motor'
        assert get_equipment_type(conn, 9999) is None

    def test_create_equipment_type_with_parent(self, conn):
        from repositories.equipment_repo import create_equipment_type
        parent_id = create_equipment_type(conn, code='machine', name='Машина', description='Родительский тип')
        child_id = create_equipment_type(
            conn, code='sub', name='Подтип',
            parent_type_id=parent_id, description='Дочерний'
        )
        assert child_id > 0

        row = conn.execute('SELECT * FROM equipment_type WHERE id = ?', (child_id,)).fetchone()
        assert row is not None
        assert row['parent_type_id'] == parent_id


class TestEquipmentTypeInUseAndDelete:
    def test_equipment_type_in_use_false_for_empty(self, conn):
        from repositories.equipment_repo import create_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(conn, code='empty-type', name='Пустой тип')
        assert equipment_type_in_use(conn, type_id) is False

    def test_equipment_type_in_use_true_with_equipment(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, create_equipment, equipment_type_in_use,
        )
        type_id = create_equipment_type(conn, code='with-eq', name='С оборудованием')
        create_equipment(conn, equipment_type_id=type_id, code='EQ001', description='Тестовое')
        assert equipment_type_in_use(conn, type_id) is True

    def test_equipment_type_in_use_true_with_child_type(self, conn):
        from repositories.equipment_repo import (
            create_equipment_type, equipment_type_in_use,
        )
        parent_id = create_equipment_type(conn, code='parent', name='Родитель')
        create_equipment_type(conn, code='child', name='Дочерний', parent_type_id=parent_id)
        assert equipment_type_in_use(conn, parent_id) is True

    def test_delete_equipment_type(self, conn):
        from repositories.equipment_repo import create_equipment_type, delete_equipment_type, equipment_type_in_use
        type_id = create_equipment_type(conn, code='delete-me', name='Удаляемый')
        assert delete_equipment_type(conn, type_id) is True
        assert equipment_type_in_use(conn, type_id) is False

    def test_delete_equipment_type_not_found(self, conn):
        from repositories.equipment_repo import delete_equipment_type
        assert delete_equipment_type(conn, 9999) is False

# ---------------------------------------------------------------------
# attribute_definition — переиспользуемый пул (часть 2)
# ---------------------------------------------------------------------

class TestAttributeDefinition:
    def test_create_attribute_definition(self, conn):
        from repositories.equipment_repo import create_attribute_definition
        attr_id = create_attribute_definition(
            conn,
            key='test_key',
            label='Тестовый атрибут',
            group_name='group1',
            value_type='string',
            options_json='[]',
            default_value='default',
            weight=10,
        )
        assert attr_id > 0

        row = conn.execute(
            'SELECT * FROM attribute_definition WHERE id = ?', (attr_id,)
        ).fetchone()
        assert row is not None
        assert row['key'] == 'test_key'
        assert row['label'] == 'Тестовый атрибут'

    def test_attribute_definition_in_use_false(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, attribute_definition_in_use,
        )
        attr_id = create_attribute_definition(
            conn, key='unused_key', label='Не используется',
        )
        assert attribute_definition_in_use(conn, attr_id) is False

    def test_attribute_definition_in_use_true(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, create_attribute_assignment, attribute_definition_in_use,
        )
        attr_id = create_attribute_definition(conn, key='used_key', label='Используется')
        eq_id = create_equipment(conn, equipment_type_id=1, code='EQ_USED')
        create_attribute_assignment(conn, eq_id, attr_id, 'value123')
        assert attribute_definition_in_use(conn, attr_id) is True

    def test_delete_attribute_definition_self(self, conn):
        from repositories.equipment_repo import (
            create_attribute_definition, delete_attribute_definition,
        )
        attr_id = create_attribute_definition(conn, key='del_key', label='Для удаления')
        ok = delete_attribute_definition(conn, attr_id)
        assert ok is True
        row = conn.execute(
            'SELECT * FROM attribute_definition WHERE id = ?', (attr_id,)
        ).fetchone()
        assert row is None

    def test_delete_attribute_definition_not_found_fails(self, conn):
        from repositories.equipment_repo import delete_attribute_definition
        assert delete_attribute_definition(conn, 9999) is False