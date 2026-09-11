"""Тесты для incident_equipment_repo.py."""

import pytest


def _make_equipment(db_conn, equipment_id):
    """Создаёт equipment_type и equipment с заданным id для FK-тестов."""
    db_conn.execute(
        "INSERT INTO equipment_type (id, code, name) VALUES (?, ?, ?)",
        (equipment_id, f"type{equipment_id}", f"Type {equipment_id}"),
    )
    db_conn.execute(
        "INSERT INTO equipment (id, equipment_type_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, equipment_id, f"Equipment {equipment_id}", "2026-01-01", "2026-01-01"),
    )
    db_conn.commit()
    return equipment_id


def _make_ticket(db_conn, ticket_id, title="Тикет"):
    """Создаёт location_node и incident_ticket (колонка problem, не title)."""
    db_conn.execute(
        "INSERT INTO location_node (name, node_type) VALUES (?, ?)",
        ("Тестовый узел", "workshop"),
    )
    db_conn.commit()
    location_id = db_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    db_conn.execute(
        "INSERT INTO incident_ticket (id, location_node_id, problem, created_by_user_id) VALUES (?, ?, ?, 1)",
        (ticket_id, location_id, title),
    )
    db_conn.commit()
    return ticket_id


class TestIncidentEquipmentRepo:
    def test_get_relations_empty(self, db_conn):
        from repositories.incident_equipment_repo import get_relations
        rows = get_relations(db_conn, ticket_id=9999)
        assert rows == []

    def test_add_relation(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, get_relations
        _make_equipment(db_conn, 1)
        _make_ticket(db_conn, 1, "Тикет 1")
        add_relation(db_conn, ticket_id=1, equipment_id=1)
        rows = get_relations(db_conn, ticket_id=1)
        assert len(rows) == 1
        assert rows[0]["name"] == "Equipment 1"

    def test_add_relation_duplicate_ignored(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, get_relations
        _make_equipment(db_conn, 2)
        _make_ticket(db_conn, 2, "Тикет 2")
        add_relation(db_conn, ticket_id=2, equipment_id=2)
        add_relation(db_conn, ticket_id=2, equipment_id=2)
        rows = get_relations(db_conn, ticket_id=2)
        assert len(rows) == 1

    def test_remove_relation(self, db_conn):
        from repositories.incident_equipment_repo import add_relation, remove_relation, get_relations
        _make_equipment(db_conn, 3)
        _make_ticket(db_conn, 3, "Тикет 3")
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
        _make_equipment(db_conn, 4)
        _make_equipment(db_conn, 5)
        _make_ticket(db_conn, 4, "Тикет 4")
        add_relation(db_conn, ticket_id=4, equipment_id=4)
        add_relation(db_conn, ticket_id=4, equipment_id=5)
        rows = get_relations(db_conn, ticket_id=4)
        assert len(rows) == 2