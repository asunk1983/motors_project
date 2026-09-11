"""Тесты репозитория ticket_repo.py (ticket, failure, equipment_work).

ticket_repo.py — CRUD ticket/failure/equipment_work, TОЛЬКО SQL.
Здесь тестируем: list_tickets, get_ticket_by_id, create_ticket,
update_ticket_status, update_ticket, delete_ticket,
get_failure_by_id, create_failure, update_failure, get_work_for_failure,
create_work, delete_work, list_maintenance_action_types.
"""

import pytest


def _create_equipment(db_conn, equipment_id=1):
    """Создаёт equipment_type и equipment с заданным id для FK-тестов."""
    db_conn.execute(
        "INSERT INTO equipment_type (id, code, name) VALUES (?, ?, ?)",
        (1, "test", "Test Type"),
    )
    db_conn.execute(
        "INSERT INTO equipment (id, equipment_type_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, 1, f"Equipment {equipment_id}", "2026-01-01", "2026-01-01"),
    )
    db_conn.commit()
    return equipment_id


class TestTicketRepo:
    def test_create_ticket(self, db_conn):
        from repositories.ticket_repo import create_ticket

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Поиск неисправности двигателя",
            "created_by_user_id": 1,
            "equipment_id": 1,
            "priority": "high",
            "description": "Двигатель не запускается",
        })
        assert ticket_id > 0

        row = db_conn.execute(
            "SELECT * FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is not None
        assert row["title"] == "Поиск неисправности двигателя"
        assert row["status"] == "new"
        assert row["priority"] == "high"

    def test_list_tickets_empty(self, db_conn):
        from repositories.ticket_repo import list_tickets

        tickets = list_tickets(db_conn)
        assert tickets == []

    def test_list_tickets_filtered_by_status(self, db_conn):
        from repositories.ticket_repo import create_ticket, update_ticket_status, list_tickets

        _create_equipment(db_conn, 1)
        # create_ticket всегда создаёт со status='new' (хардкод в SQL)
        ticket1 = create_ticket(db_conn, {
            "title": "Новая заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        ticket2 = create_ticket(db_conn, {
            "title": "В процессе",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        ticket3 = create_ticket(db_conn, {
            "title": "Закрыта",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        # Меняем статусы после создания
        update_ticket_status(db_conn, ticket2, status="in_progress")
        update_ticket_status(db_conn, ticket3, status="closed")

        # Фильтр по статусу
        new_tickets = list_tickets(db_conn, status="new")
        assert len(new_tickets) == 1
        assert new_tickets[0]["title"] == "Новая заявка"

    def test_get_ticket_by_id(self, db_conn):
        from repositories.ticket_repo import create_ticket, get_ticket_by_id

        ticket_id = create_ticket(db_conn, {
            "title": "Тестовая заявка",
            "created_by_user_id": 1,
        })
        ticket = get_ticket_by_id(db_conn, ticket_id)
        assert ticket is not None
        assert ticket["id"] == ticket_id
        assert ticket["title"] == "Тестовая заявка"
        assert ticket["failure_ids"] == []

    def test_get_ticket_by_id_nonexistent(self, db_conn):
        from repositories.ticket_repo import get_ticket_by_id
        assert get_ticket_by_id(db_conn, 99999) is None

    def test_update_ticket(self, db_conn):
        from repositories.ticket_repo import create_ticket, update_ticket

        ticket_id = create_ticket(db_conn, {
            "title": "Исходная заявка",
            "created_by_user_id": 1,
        })
        update_ticket(db_conn, ticket_id, {
            "title": "Обновлённая заявка",
        })

        row = db_conn.execute(
            "SELECT title FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row["title"] == "Обновлённая заявка"

    def test_update_ticket_status(self, db_conn):
        from repositories.ticket_repo import create_ticket, update_ticket_status

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        update_ticket_status(db_conn, ticket_id, status="in_progress")

        row = db_conn.execute(
            "SELECT status FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row["status"] == "in_progress"

    def test_delete_ticket(self, db_conn):
        from repositories.ticket_repo import create_ticket, delete_ticket

        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
        })
        delete_ticket(db_conn, ticket_id)

        row = db_conn.execute(
            "SELECT id FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is None

def test_delete_ticket_cascades_failures_works_and_logs(self, db_conn):
        """delete_ticket удаляет связанные failure и equipment_work,
        а также пишет log_deletion в audit_log."""
        from repositories.ticket_repo import (
            create_ticket, create_failure, create_work, delete_ticket,
        )

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка с отказом",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "symptom": "перегрев",
            "description": "Описание",
        })
        work_id = create_work(db_conn, {
            "failure_id": failure_id,
            "action_type_id": 1,
            "description": "Ремонт",
        })

        delete_ticket(db_conn, ticket_id, actor={'id': 1, 'username': 'admin', 'display_name': 'Админ'})

        # Тикет, failure и work удалены каскадом
        assert db_conn.execute("SELECT id FROM ticket WHERE id = ?", (ticket_id,)).fetchone() is None
        assert db_conn.execute("SELECT id FROM failure WHERE id = ?", (failure_id,)).fetchone() is None
        assert db_conn.execute("SELECT id FROM equipment_work WHERE id = ?", (work_id,)).fetchone() is None

        # В аудите — строка удаления с названием заявки и актором
        row = db_conn.execute(
            "SELECT field_name, new_value, changed_by_display_name FROM audit_log "
            "WHERE entity_type = 'ticket' AND entity_id = ? ORDER BY id DESC LIMIT 1",
            (ticket_id,),
        ).fetchone()
        assert row is not None
        assert row["field_name"] == "__deleted__"
        assert row["changed_by_display_name"] == "Админ"
        assert row["new_value"] == "Заявка с отказом"

    def test_delete_ticket_not_found_false(self, db_conn):
        from repositories.ticket_repo import delete_ticket
        assert delete_ticket(db_conn, 99999) is False

class TestFailureRepo:
    def test_create_failure(self, db_conn):
        from repositories.ticket_repo import create_ticket, create_failure

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "symptom": "технологическая",
            "description": "Описание отказа",
        })
        assert failure_id > 0

        failure = db_conn.execute(
            "SELECT * FROM failure WHERE id = ?", (failure_id,)
        ).fetchone()
        assert failure["ticket_id"] == ticket_id
        assert failure["symptom"] == "технологическая"

    def test_get_failure_by_id(self, db_conn):
        from repositories.ticket_repo import create_ticket, create_failure, get_failure_by_id

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "symptom": "технологическая",
            "description": "Описание",
        })
        failure = get_failure_by_id(db_conn, failure_id)
        assert failure is not None
        assert failure["id"] == failure_id

    def test_update_failure(self, db_conn):
        from repositories.ticket_repo import create_ticket, create_failure, update_failure

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "symptom": "A",
            "description": "Исходное",
        })
        update_failure(db_conn, failure_id, {
            "symptom": "B",
            "description": "Обновлённое",
        })

        failure = db_conn.execute(
            "SELECT symptom, description FROM failure WHERE id = ?",
            (failure_id,),
        ).fetchone()
        assert failure["symptom"] == "B"
        assert failure["description"] == "Обновлённое"


class TestWorkRepo:
    def test_create_work(self, db_conn):
        from repositories.ticket_repo import create_ticket, create_failure, create_work

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "failure_type": "A",
            "failure_description": "Описание",
        })
        work_id = create_work(db_conn, {
            "failure_id": failure_id,
            "action_type_id": 1,
            "description": "Ремонт",
        })
        assert work_id > 0

        work = db_conn.execute(
            "SELECT * FROM equipment_work WHERE id = ?", (work_id,)
        ).fetchone()
        assert work["failure_id"] == failure_id
        assert work["description"] == "Ремонт"

    def test_delete_work(self, db_conn):
        from repositories.ticket_repo import create_ticket, create_failure, create_work, delete_work

        _create_equipment(db_conn, 1)
        ticket_id = create_ticket(db_conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
            "equipment_id": 1,
        })
        failure_id = create_failure(db_conn, {
            "ticket_id": ticket_id,
            "equipment_id": 1,
            "failure_type": "A",
            "failure_description": "Описание",
        })
        work_id = create_work(db_conn, {
            "failure_id": failure_id,
            "action_type_id": 1,
            "description": "Ремонт",
        })
        delete_work(db_conn, work_id)

        row = db_conn.execute(
            "SELECT id FROM equipment_work WHERE id = ?", (work_id,)
        ).fetchone()
        assert row is None

    def test_list_maintenance_action_types(self, db_conn):
        from repositories.ticket_repo import list_maintenance_action_types

        types = list_maintenance_action_types(db_conn)
        assert isinstance(types, list)
        assert all("id" in t for t in types)
        assert all("name" in t for t in types)