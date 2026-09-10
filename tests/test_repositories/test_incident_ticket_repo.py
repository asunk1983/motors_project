"""Тесты для incident_ticket_repo.py."""

import pytest


class TestIncidentTicketRepo:
    def _create_ticket(self, db_conn, title="Тикет", status="open"):
        from repositories.incident_ticket_repo import create_ticket
        return create_ticket(db_conn, {"title": title, "status": status})

    def test_get_ticket_not_found(self, db_conn):
        from repositories.incident_ticket_repo import get_ticket
        result = get_ticket(db_conn, 9999)
        assert result is None

    def test_create_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket
        tid = create_ticket(db_conn, {"title": "Перегрев двигателя", "status": "open"})
        assert tid > 0

    def test_get_ticket_returns_created(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, get_ticket
        tid = create_ticket(db_conn, {"title": "Вибрация", "status": "in_progress"})
        row = get_ticket(db_conn, tid)
        assert row is not None
        assert row["title"] == "Вибрация"
        assert row["status"] == "in_progress"

    def test_list_tickets_empty(self, db_conn):
        from repositories.incident_ticket_repo import list_tickets
        rows = list_tickets(db_conn)
        assert rows == []

    def test_list_tickets_returns_all(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, list_tickets
        create_ticket(db_conn, {"title": "Тикет 1"})
        create_ticket(db_conn, {"title": "Тикет 2"})
        rows = list_tickets(db_conn)
        assert len(rows) == 2

    def test_list_tickets_filter_by_status(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, list_tickets
        create_ticket(db_conn, {"title": "Открытый", "status": "open"})
        create_ticket(db_conn, {"title": "Закрытый", "status": "closed"})
        rows = list_tickets(db_conn, filters={"status": "open"})
        assert len(rows) == 1
        assert rows[0]["title"] == "Открытый"

    def test_update_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, update_ticket, get_ticket
        tid = create_ticket(db_conn, {"title": "Старый заголовок"})
        result = update_ticket(db_conn, tid, {"title": "Новый заголовок"})
        assert result is True
        row = get_ticket(db_conn, tid)
        assert row["title"] == "Новый заголовок"

    def test_delete_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, delete_ticket, get_ticket
        tid = create_ticket(db_conn, {"title": "Удалить"})
        result = delete_ticket(db_conn, tid)
        assert result is True
        assert get_ticket(db_conn, tid) is None

    def test_get_executors_empty(self, db_conn):
        from repositories.incident_ticket_repo import get_executors
        rows = get_executors(db_conn, ticket_id=9999)
        assert rows == []

    def test_replace_executors(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, replace_executors, get_executors
        tid = create_ticket(db_conn, {"title": "Тикет"})
        db_conn.execute('INSERT INTO crew (id, name) VALUES (1, "Бригада 1")')
        db_conn.commit()
        replace_executors(db_conn, ticket_id=tid, crew_ids=[1])
        rows = get_executors(db_conn, ticket_id=tid)
        assert len(rows) == 1

    def test_get_links_empty(self, db_conn):
        from repositories.incident_ticket_repo import get_links
        rows = get_links(db_conn, ticket_id=9999)
        assert rows == []

    def test_add_link(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, add_link, get_links
        tid = create_ticket(db_conn, {"title": "Тикет"})
        lid = add_link(db_conn, ticket_id=tid, url="http://example.com", caption="Ссылка")
        assert lid > 0
        rows = get_links(db_conn, ticket_id=tid)
        assert len(rows) == 1
        assert rows[0]["url"] == "http://example.com"

    def test_delete_link(self, db_conn):
        from repositories.incident_ticket_repo import create_ticket, add_link, delete_link, get_links
        tid = create_ticket(db_conn, {"title": "Тикет"})
        lid = add_link(db_conn, ticket_id=tid, url="http://example.com")
        result = delete_link(db_conn, link_id=lid)
        assert result is True
        rows = get_links(db_conn, ticket_id=tid)
        assert len(rows) == 0

    def test_get_location_counts(self, db_conn):
        from repositories.incident_ticket_repo import get_location_counts
        counts = get_location_counts(db_conn)
        assert isinstance(counts, dict)
        assert "unassigned" in counts

    def test_count_all(self, db_conn):
        from repositories.incident_ticket_repo import count_all, create_ticket
        assert count_all(db_conn) == 0
        create_ticket(db_conn, {"title": "Тикет"})
        assert count_all(db_conn) == 1

    def test_count_by_status(self, db_conn):
        from repositories.incident_ticket_repo import count_by_status, create_ticket
        create_ticket(db_conn, {"title": "Открытый", "status": "open"})
        create_ticket(db_conn, {"title": "Закрытый", "status": "closed"})
        assert count_by_status(db_conn, "open") == 1
        assert count_by_status(db_conn, "closed") == 1
        assert count_by_status(db_conn, "nonexistent") == 0

"""Тесты репозитория заявок инцидентов (incident_ticket_repo.py).

incident_ticket_repo.py — CRUD заявок инцидентов, включая каскадное удаление
failureи work. Также тестирует самомиграции.
"""

import pytest


class TestIncidentTicketRepo:
    def test_create_incident_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create
        ticket_id = create(
            db_conn,
            title='Протечка в сосуде',
            description='Обнаружена протечка в теплообменнике',
            initiator_ids=[1, 2],
            executor_ids=[3, 4],
        )
        assert ticket_id > 0

        row = db_conn.execute(
            "SELECT id, title, description, status FROM incident_tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "Протечка в сосуде"
        assert row[2] == "Обнаружена протечка в теплообменнике"
        assert row[3] == "new"

    def test_create_minimal_incident_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create
        ticket_id = create(
            db_conn,
            title="Критическая поломка",
            description=None,
            initiator_ids=[1],
            executor_ids=[],
        )
        assert ticket_id > 0

        row = db_conn.execute(
            "SELECT * FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is not None
        assert row[1] == "Критическая поломка"
        assert row[3] == "new"

    def test_update_incident_ticket(self, db_conn):
        from repositories.incident_ticket_repo import create, update
        ticket_id = create(
            db_conn,
            title="Исходящий инцидент",
            description="Исходное описание",
            initiator_ids=[1, 2],
            executor_ids=[3],
        )
        ok = update(
            db_conn,
            ticket_id=ticket_id,
            title="Обновлённый инцидент",
            description="Новое описание",
            status="in_progress",
            initiator_ids=[1],
            executor_ids=[2, 3],
        )
        assert ok is True

        row = db_conn.execute(
            "SELECT * FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row[1] == "Обновлённый инцидент"
        assert row[3] == "in_progress"

    def test_update_nonexistent_ticket(self, db_conn):
        from repositories.incident_ticket_repo import update
        ok = update(db_conn, ticket_id=99999, title="Несуществующий")
        assert ok is False

    def test_delete_incident_ticket_cascades(self, db_conn):
        from repositories.incident_ticket_repo import create, delete
        ticket_id = create(
            db_conn,
            title="Инцидент с failure",
            description="Описание",
            initiator_ids=[1],
            executor_ids=[],
        )

        from repositories.incident_ticket_repo import create_failure
        failure_id = create_failure(
            db_conn,
            ticket_id=ticket_id,
            failure_type="технологическая",
            failure_description="Поломка узла",
        )
        assert failure_id > 0

        from repositories.incident_ticket_repo import create_work
        work_id = create_work(
            db_conn,
            failure_id=failure_id,
            work_type="ремонт",
            work_description="Ремонт узла",
        )
        assert work_id > 0

        ok = delete(db_conn, ticket_id)
        assert ok is True

        failure_row = db_conn.execute(
            "SELECT * FROM failure WHERE id = ?", (failure_id,)
        ).fetchone()
        assert failure_row is None

        work_row = db_conn.execute(
            "SELECT * FROM work WHERE id = ?", (work_id,)
        ).fetchone()
        assert work_row is None

    def test_delete_nonexistent_ticket(self, db_conn):
        from repositories.incident_ticket_repo import delete
        ok = delete(db_conn, 99999)
        assert ok is True

    def test_get_by_id(self, db_conn):
        from repositories.incident_ticket_repo import create, get_by_id
        ticket_id = create(
            db_conn,
            title="Поиск по id",
            description="Поиск",
            initiator_ids=[1],
            executor_ids=[],
        )
        ticket = get_by_id(db_conn, ticket_id)
        assert ticket is not None
        assert ticket[0] == ticket_id
        assert ticket[1] == "Поиск по id"

        assert get_by_id(db_conn, 99999) is None

    def test_list_all(self, db_conn):
        from repositories.incident_ticket_repo import create, list_all
        for i in range(3):
            create(
                db_conn,
                title=f"Инцидент {i}",
                description=f"Описание {i}",
                initiator_ids=[1],
                executor_ids=[],
            )

        tickets = list_all(db_conn)
        assert len(tickets) == 3


class TestIncidentTicketRepoMigrations:
    def test_ensure_updated_at_column_runs_cleanly(self, db_conn):
        from repositories.incident_ticket_repo import _ensure_updated_at_column
        _ensure_updated_at_column(db_conn)
        cursor = db_conn.execute("PRAGMA table_info(incident_tickets)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "updated_at" in columns

    def test_ensure_no_users_fk_runs_cleanly(self, db_conn):
        from repositories.incident_ticket_repo import _ensure_no_users_fk
        _ensure_no_users_fk(db_conn)
        cursor = db_conn.execute("PRAGMA foreign_key_list(incident_tickets)")
        fk_tables = set(row[2] for row in cursor.fetchall())
        assert "users" not in fk_tables