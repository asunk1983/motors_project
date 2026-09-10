"""Тесты репозитория ticket_repo.py (ticket, failure, equipment_work).

ticket_repo.py — CRUD ticket/failure/equipment_work, TОЛЬКО SQL.
Здесь тестируем: list_tickets, get_ticket_by_id, create_ticket,
update_ticket_status, update_ticket, delete_ticket,
get_failure_by_id, create_failure, update_failure, get_work_for_failure,
create_work, delete_work, list_maintenance_action_types.
"""

import pytest


class TestTicketRepo:
    def test_create_ticket(self, conn):
        from repositories.ticket_repo import create_ticket

        ticket_id = create_ticket(conn, {
            "title": "Поиск неисправности двигателя",
            "created_by_user_id": 1,
            "equipment_id": 1,
            "priority": "high",
            "description": "Двигатель не запускается",
        })
        assert ticket_id > 0

        row = conn.execute(
            "SELECT * FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is not None
        assert row["title"] == "Поиск неисправности двигателя"
        assert row["status"] == "new"
        assert row["priority"] == "high"

    def test_list_tickets_empty(self, conn):
        from repositories.ticket_repo import list_tickets

        tickets = list_tickets(conn)
        assert tickets == []

    def test_list_tickets_filtered_by_status(self, conn):
        from repositories.ticket_repo import create_ticket, list_tickets

        create_ticket(conn, {
            "title": "Новая заявка",
            "created_by_user_id": 1,
            "status": "new",
        })
        create_ticket(conn, {
            "title": "В процессе",
            "created_by_user_id": 1,
            "status": "in_progress",
        })
        create_ticket(conn, {
            "title": "Закрыта",
            "created_by_user_id": 1,
            "status": "closed",
        })

        # Фильтр по статусу
        new_tickets = list_tickets(conn, status="new")
        assert len(new_tickets) == 1
        assert new_tickets[0]["title"] == "Новая заявка"

    def test_get_ticket_by_id(self, conn):
        from repositories.ticket_repo import create_ticket, get_ticket_by_id

        ticket_id = create_ticket(conn, {
            "title": "Тестовая заявка",
            "created_by_user_id": 1,
        })
        ticket = get_ticket_by_id(conn, ticket_id)
        assert ticket is not None
        assert ticket["id"] == ticket_id
        assert ticket["title"] == "Тестовая заявка"
        assert ticket["failure_ids"] == []

    def test_get_ticket_by_id_nonexistent(self, conn):
        from repositories.ticket_repo import get_ticket_by_id
        assert get_ticket_by_id(conn, 99999) is None

    def test_update_ticket(self, conn):
        from repositories.ticket_repo import create_ticket, update_ticket

        ticket_id = create_ticket(conn, {
            "title": "Исходная заявка",
            "created_by_user_id": 1,
        })
        update_ticket(conn, ticket_id, {
            "title": "Обновлённая заявка",
            "description": "Новое описание",
        })

        ticket = conn.execute(
            "SELECT title, description FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert ticket["title"] == "Обновлённая заявка"
        assert ticket["description"] == "Новое описание"

    def test_update_ticket_status(self, conn):
        from repositories.ticket_repo import create_ticket, update_ticket_status

        ticket_id = create_ticket(conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
        })
        update_ticket_status(conn, ticket_id, "in_progress")

        row = conn.execute(
            "SELECT status, updated_at FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row["status"] == "in_progress"
        assert row["updated_at"] is not None

    def test_delete_ticket(self, conn):
        from repositories.ticket_repo import create_ticket, delete_ticket

        ticket_id = create_ticket(conn, {
            "title": "Заявка для удаления",
            "created_by_user_id": 1,
        })
        delete_ticket(conn, ticket_id)

        row = conn.execute(
            "SELECT id FROM ticket WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is None


class TestFailureRepo:
    def test_create_failure(self, conn):
        from repositories.ticket_repo import create_ticket, create_failure

        ticket_id = create_ticket(conn, {
            "title": "Заявка",
            "created_by_user_id": 1,
        })
        failure_id = create_failure(conn, {
            "ticket_id": ticket_id,
            "failure_type": "технологическая",
            "failure_description": "Поломка узла",
            "symptom": "Не запускается",
            "description": "Подробное описание",
            "confirmed": True,
        })
        assert failure_id > 0

        failure = conn.execute(
            "SELECT * FROM failure WHERE id = ?", (failure_id,)
        ).fetchone()
        assert failure["ticket_id"] == ticket_id
        assert failure["failure_type"] == "технологическая"

    def test_get_failure_by_id(self, conn):
        from repositories.ticket_repo import create_ticket, create_failure, get_failure_by_id

        ticket_id = create_ticket(conn, {"title": "Заявка", "created_by_user_id": 1})
        failure_id = create_failure(conn, {
            "ticket_id": ticket_id,
            "failure_type": "технологическая",
            "failure_description": "Описание",
        })
        failure = get_failure_by_id(conn, failure_id)
        assert failure is not None
        assert failure["id"] == failure_id

    def test_update_failure(self, conn):
        from repositories.ticket_repo import create_ticket, create_failure, update_failure

        ticket_id = create_ticket(conn, {"title": "Заявка", "created_by_user_id": 1})
        failure_id = create_failure(conn, {
            "ticket_id": ticket_id,
            "failure_type": "A",
            "failure_description": "Исходное",
        })
        update_failure(conn, failure_id, {
            "failure_type": "B",
            "failure_description": "Обновлённое",
        })

        failure = conn.execute(
            "SELECT failure_type, failure_description FROM failure WHERE id = ?",
            (failure_id,),
        ).fetchone()
        assert failure["failure_type"] == "B"
        assert failure["failure_description"] == "Обновлённое"


class TestWorkRepo:
    def test_create_work(self, conn):
        from repositories.ticket_repo import create_ticket, create_failure, create_work

        ticket_id = create_ticket(conn, {"title": "Заявка", "created_by_user_id": 1})
        failure_id = create_failure(conn, {
            "ticket_id": ticket_id,
            "failure_type": "A",
            "failure_description": "Описание",
        })
        work_id = create_work(conn, {
            "failure_id": failure_id,
            "action_type_id": 1,
            "description": "Ремонт",
        })
        assert work_id > 0

        work = conn.execute(
            "SELECT * FROM equipment_work WHERE id = ?", (work_id,)
        ).fetchone()
        assert work["failure_id"] == failure_id
        assert work["description"] == "Ремонт"

    def test_delete_work(self, conn):
        from repositories.ticket_repo import create_ticket, create_failure, create_work, delete_work

        ticket_id = create_ticket(conn, {"title": "Заявка", "created_by_user_id": 1})
        failure_id = create_failure(conn, {
            "ticket_id": ticket_id,
            "failure_type": "A",
            "failure_description": "Описание",
        })
        work_id = create_work(conn, {
            "failure_id": failure_id,
            "action_type_id": 1,
            "description": "Ремонт",
        })
        delete_work(conn, work_id)

        row = conn.execute(
            "SELECT id FROM equipment_work WHERE id = ?", (work_id,)
        ).fetchone()
        assert row is None

    def test_list_maintenance_action_types(self, conn):
        from repositories.ticket_repo import list_maintenance_action_types

        types = list_maintenance_action_types(conn)
        assert isinstance(types, list)
        assert all("id" in t for t in types)
        assert all("name" in t for t in types)