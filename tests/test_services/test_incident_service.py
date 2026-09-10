"""Тесты бизнес-логики сервиса инцидентов (services/incident_service.py).

incident_service.py — create/update/delete инцидентов, attach/detach оборудования,
move_location, delete_location, delete_crew.
"""

import pytest


class TestIncidentServiceCreate:
    def test_create_requires_title(self, db_conn):
        from services.incident_service import create_ticket
        with pytest.raises(ValueError, match="^title is required"):
            create_ticket(db_conn, title=None, description="Test", initiator_ids=[1])

    def test_create_requires_at_least_one_initiator(self, db_conn):
        from services.incident_service import create_ticket
        with pytest.raises(ValueError, match="^at least one initiator is required"):
            create_ticket(db_conn, title="Test", description="Test", initiator_ids=[])

    def test_create_success(self, db_conn):
        from services.incident_service import create_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Авария насоса",
            description="Отказ насоса 냉수ного цеха",
            initiator_ids=[1, 2],
            executor_ids=[3],
            location_id=5,
        )
        assert ticket_id > 0

        row = db_conn.execute(
            "SELECT id, title, description, status, location_id FROM incident_tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "Авария насоса"
        assert row[4] == 5

    def test_create_auto_adds_closed_at_on_closed_status(self, db_conn):
        from services.incident_service import create_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Закрытый инцидент",
            description="Инцидент, созданный сразу закрытым",
            initiator_ids=[1],
            status="closed",
        )
        row = db_conn.execute(
            "SELECT status, closed_at FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row[0] == "closed"
        assert row[1] is not None

    def test_create_without_location_allows(self, db_conn):
        from services.incident_service import create_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Без локации",
            description="Инцидент без привязки к локации",
            initiator_ids=[1],
        )
        assert ticket_id > 0

    def test_create_location_nonexistent_raises_error(self, db_conn):
        from services.incident_service import create_ticket
        with pytest.raises(ValueError, match="^location 9999 not found"):
            create_ticket(
                db_conn,
                title="Инцидент в несуществующей локации",
                description="Описание",
                initiator_ids=[1],
                location_id=9999,
            )


class TestIncidentServiceUpdate:
    def test_update_status_to_closed_auto_fills_closed_at(self, db_conn):
        from services.incident_service import create_ticket, update_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Инцидент",
            description="Описание",
            initiator_ids=[1],
        )
        update_ticket(db_conn, ticket_id=ticket_id, status="closed")
        row = db_conn.execute(
            "SELECT status, closed_at FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row[0] == "closed"
        assert row[1] is not None

    def test_update_status_from_closed_clears_closed_at(self, db_conn):
        from services.incident_service import create_ticket, update_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Инцидент",
            description="Описание",
            initiator_ids=[1],
            status="closed",
        )
        update_ticket(db_conn, ticket_id=ticket_id, status="in_progress")
        row = db_conn.execute(
            "SELECT status, closed_at FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row[0] == "in_progress"
        assert row[1] is None


class TestIncidentServiceDelete:
    def test_delete_incident_ticket_success(self, db_conn):
        from services.incident_service import create_ticket, delete_ticket
        ticket_id = create_ticket(
            db_conn,
            title="Инцидент для удаления",
            description="Описание",
            initiator_ids=[1],
        )
        ok = delete_ticket(db_conn, ticket_id)
        assert ok is True

        row = db_conn.execute(
            "SELECT id FROM incident_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        assert row is None


class TestIncidentServiceLocationGuards:
    def test_move_location_nonexistent_location_raises(self, db_conn):
        from services.incident_service import create_ticket, move_location
        ticket_id = create_ticket(
            db_conn,
            title="Инцидент",
            description="Описание",
            initiator_ids=[1],
        )
        with pytest.raises(ValueError, match="^location 9999 not found"):
            move_location(db_conn, ticket_id=ticket_id, location_id=9999)

    def test_delete_location_used_by_incident_raises(self, db_conn):
        from services.incident_service import create_ticket, delete_location
        loc_id = 50
        create_ticket(
            db_conn,
            title="Инцидент в локации",
            description="Описание",
            initiator_ids=[1],
            location_id=loc_id,
        )
        with pytest.raises(ValueError, match="^location 50 is referenced by an incident ticket"):
            delete_location(db_conn, location_id=loc_id)

    def test_delete_crew_used_by_incident_raises(self, db_conn):
        from services.incident_service import create_ticket, delete_crew
        crew_id = 70
        create_ticket(
            db_conn,
            title="Инцидент с экипажем",
            description="Описание",
            initiator_ids=[crew_id],
            executor_ids=[crew_id],
        )
        with pytest.raises(ValueError, match="^crew 70 is referenced by an incident ticket"):
            delete_crew(db_conn, crew_id)