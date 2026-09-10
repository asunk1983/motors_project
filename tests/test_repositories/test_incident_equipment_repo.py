"""Тесты для incident_equipment_repo.py."""

import pytest


class TestIncidentEquipmentRepo:
    def test_get_relations_empty(self, db_conn):
        from repositories.incident_equipment_repo import get_relations
        rows = get_relations(db_conn, ticket_id=9999)
        assert rows == []

    def test_add_relation(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, get_relations
        db_conn.execute('INSERT INTO equipment (id, name) VALUES (1, "Насос 1")')
        db_conn.execute('INSERT INTO incident_ticket (id, title) VALUES (1, "Тикет 1")')
        db_conn.commit()
        add_relation(db_conn, ticket_id=1, equipment_id=1)
        rows = get_relations(db_conn, ticket_id=1)
        assert len(rows) == 1
        assert rows[0]["name"] == "Насос 1"

    def test_add_relation_duplicate_ignored(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, get_relations
        db_conn.execute('INSERT INTO equipment (id, name) VALUES (2, "Насос 2")')
        db_conn.execute('INSERT INTO incident_ticket (id, title) VALUES (2, "Тикет 2")')
        db_conn.commit()
        add_relation(db_conn, ticket_id=2, equipment_id=2)
        add_relation(db_conn, ticket_id=2, equipment_id=2)
        rows = get_relations(db_conn, ticket_id=2)
        assert len(rows) == 1

    def test_remove_relation(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, remove_relation, get_relations
        db_conn.execute('INSERT INTO equipment (id, name) VALUES (3, "Насос 3")')
        db_conn.execute('INSERT INTO incident_ticket (id, title) VALUES (3, "Тикет 3")')
        db_conn.commit()
        add_relation(db_conn, ticket_id=3, equipment_id=3)
        result = remove_relation(db_conn, ticket_id=3, equipment_id=3)
        assert result is True
        rows = get_relations(db_conn, ticket_id=3)
        assert len(rows) == 0

    def test_remove_relation_not_found(self, db_conn):
        from repositories.incident_equipment_repo import remove_relation
        result = remove_relation(db_conn, ticket_id=9999, equipment_id=9999)
        assert result is False

    def test_get_relations_multiple(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, get_relations
        db_conn.execute('INSERT INTO equipment (id, name) VALUES (4, "А")')
        db_conn.execute('INSERT INTO equipment (id, name) VALUES (5, "Б")')
        db_conn.execute('INSERT INTO incident_ticket (id, title) VALUES (4, "Тикет 4")')
        db_conn.commit()
        add_relation(db_conn, ticket_id=4, equipment_id=4)
        add_relation(db_conn, ticket_id=4, equipment_id=5)
        rows = get_relations(db_conn, ticket_id=4)
        assert len(rows) == 2

"""Тесты репозитория связи оборудования с заявками инцидентов.

incident_equipment_repo.py — простая M2M: connect/disconnect оборудования
и заявки инцидентов. Тестируем: добавление связи, удаление, получение всех
связей для заявки.
"""

import pytest


class TestIncidentEquipmentRepo:
    def test_get_relations_empty(self, db_conn):
        rows = list(db_conn.execute(
            'SELECT ie.incident_id, ie.equipment_id, e.equipment_type, e.equipment_manufacturer, '
            'e.equipment_model, e.equipment_serial, e.location_id, l.name, l.parent_id, l.parent_name'
            ' FROM incident_equipment ie LEFT JOIN equipment e ON ie.equipment_id = e.id '
            ' LEFT JOIN locations l ON e.location_id = l.id'
            ' WHERE ie.incident_id = ?', (9999,)
        ))
        assert len(rows) == 0

    def test_add_relation_success(self, db_conn):
        from repositories.incident_equipment_repo import add_relation
        ok = add_relation(db_conn, incident_id=1, equipment_id=50)
        assert ok is True

        # Проверяем, что связь добавилась
        rows = list(db_conn.execute(
            'SELECT * FROM incident_equipment WHERE incident_id = ? AND equipment_id = ?',
            (1, 50)
        ))
        assert len(rows) == 1

    def test_add_duplicate_relation_no_error(self, db_conn):
        from repositories.incident_equipment_repo import add_relation
        # Добавляем связь дважды — вторая должна быть silently ignored
        ok1 = add_relation(db_conn, incident_id=1, equipment_id=50)
        ok2 = add_relation(db_conn, incident_id=1, equipment_id=50)
        assert ok1 is True
        assert ok2 is True  # no error, just no-op

    def test_remove_relation_success(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, remove_relation
        add_relation(db_conn, incident_id=1, equipment_id=60)
        ok = remove_relation(db_conn, incident_id=1, equipment_id=60)
        assert ok is True

        rows = list(db_conn.execute(
            'SELECT * FROM incident_equipment WHERE incident_id = ? AND equipment_id = ?',
            (1, 60)
        ))
        assert len(rows) == 0

    def test_remove_nonexistent_relation_no_error(self, db_conn):
        from repositories.incident_equipment_repo import remove_relation
        ok = remove_relation(db_conn, incident_id=1, equipment_id=9999)
        assert ok is True  # нет связи — тоже ok, silent ignore