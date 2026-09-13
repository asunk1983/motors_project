"""Тесты бизнес-логики сервиса инцидентов (services/incident_service.py).

Написаны под актуальные сигнатуры сервиса:
- create_ticket(conn, *, location_node_id, problem, created_by_user_id, ...)
- update_ticket(conn, ticket_id, *, ...)
- delete_ticket / add_equipment_link / remove_equipment_link / move_location /
  delete_location / delete_crew

Контракт: ошибки возвращаются кортежем (None|False, текст_ошибки),
а не исключениями. Валидные статусы: in_progress / resolved / rejected.
Таблица incident_ticket (ед.ч.).
"""

import pytest


def _make_crew(db_conn, full_name='Иванов Иван'):
    cur = db_conn.execute('INSERT INTO crew (full_name) VALUES (?)', (full_name,))
    db_conn.commit()
    return cur.lastrowid


def _make_location(db_conn, name='Цех 1', node_type='workshop', parent_id=None):
    from repositories.location_repo import create as create_location
    return create_location(db_conn, name, node_type, parent_id=parent_id)


def _make_equipment(db_conn):
    from repositories.equipment_repo import create_equipment_type, create_equipment
    type_id = create_equipment_type(db_conn, code='pump', name='Насос')
    return create_equipment(db_conn, {
        'equipment_type_id': type_id, 'name': 'EQ001', 'article': 'EQ001',
    })


@pytest.fixture
def loc_id(db_conn):
    return _make_location(db_conn)


@pytest.fixture
def crew(db_conn):
    return _make_crew(db_conn)


@pytest.fixture
def ticket_id(db_conn, loc_id, crew):
    from services.incident_service import create_ticket
    ticket_id, err = create_ticket(
        db_conn, location_node_id=loc_id, problem='Течь насоса',
        created_by_user_id=1, initiator_ids=[crew],
    )
    assert err is None
    return ticket_id


def _select_ticket(db_conn, ticket_id):
    return db_conn.execute(
        'SELECT * FROM incident_ticket WHERE id = ?', (ticket_id,)
    ).fetchone()
class TestCreateTicket:
    def test_create_requires_problem(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='   ',
            created_by_user_id=1, initiator_ids=[crew],
        )
        assert ticket_id is None
        assert 'обязательно' in err

    def test_create_requires_at_least_one_initiator(self, db_conn, loc_id):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[],
        )
        assert ticket_id is None
        assert 'инициатор' in err

    def test_create_location_nonexistent_returns_error(self, db_conn, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=99999, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew],
        )
        assert ticket_id is None
        assert 'место' in err and 'не найдено' in err

    def test_create_crew_nonexistent_returns_error(self, db_conn, loc_id):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[99999],
        )
        assert ticket_id is None
        assert 'не найден' in err

    def test_create_invalid_priority_rejected(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew], priority='urgent',
        )
        assert ticket_id is None
        assert 'приоритет' in err

    def test_create_invalid_status_rejected(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew], status='closed',
        )
        assert ticket_id is None
        assert 'статус' in err

    def test_create_success_returns_id(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь насоса',
            created_by_user_id=1, initiator_ids=[crew],
        )
        assert err is None
        assert ticket_id is not None and ticket_id > 0

        row = _select_ticket(db_conn, ticket_id)
        assert row is not None
        assert row['location_node_id'] == loc_id
        assert row['problem'] == 'Течь насоса'
        assert row['priority'] == 'medium'
        assert row['status'] == 'in_progress'
        assert row['closed_at'] is None

    def test_create_with_executor(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        execr = _make_crew(db_conn, 'Пётр Петров')
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew], executor_ids=[execr],
        )
        assert err is None and ticket_id is not None
        from repositories.incident_ticket_repo import get_executors
        execs = get_executors(db_conn, ticket_id)
        assert [e['id'] for e in execs] == [execr]

    def test_create_auto_adds_closed_at_on_rejected(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew], status='rejected',
        )
        assert err is None
        row = _select_ticket(db_conn, ticket_id)
        assert row['status'] == 'rejected'
        assert row['closed_at'] is not None

    def test_create_resolved_keeps_explicit_closed_at(self, db_conn, loc_id, crew):
        from services.incident_service import create_ticket
        ticket_id, err = create_ticket(
            db_conn, location_node_id=loc_id, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew],
            status='resolved', closed_at='2026-09-01 10:00:00',
        )
        assert err is None
        assert _select_ticket(db_conn, ticket_id)['closed_at'] == '2026-09-01 10:00:00'
class TestUpdateTicket:
    def test_update_not_found(self, db_conn):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, 99999, status='resolved')
        assert ok is False
        assert 'не найдена' in err

    def test_update_fields(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, problem='Перегрев', priority='high')
        assert ok is True and err is None
        row = _select_ticket(db_conn, ticket_id)
        assert row['problem'] == 'Перегрев'
        assert row['priority'] == 'high'

    def test_update_status_to_resolved_fills_closed_at(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, status='resolved')
        assert ok is True and err is None
        assert _select_ticket(db_conn, ticket_id)['closed_at'] is not None

    def test_update_back_to_in_progress_clears_closed_at(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        update_ticket(db_conn, ticket_id, status='resolved')
        ok, err = update_ticket(db_conn, ticket_id, status='in_progress')
        assert ok is True and err is None
        row = _select_ticket(db_conn, ticket_id)
        assert row['status'] == 'in_progress'
        assert row['closed_at'] is None

    def test_update_explicit_closed_at_clear(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        update_ticket(db_conn, ticket_id, status='resolved')
        ok, err = update_ticket(
            db_conn, ticket_id, closed_at_explicitly_set=True, closed_at=None,
        )
        assert ok is True and err is None
        assert _select_ticket(db_conn, ticket_id)['closed_at'] is None

    def test_update_invalid_priority_rejected(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, priority='urgent')
        assert ok is False
        assert 'приоритет' in err

    def test_update_invalid_status_rejected(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, status='closed')
        assert ok is False
        assert 'статус' in err

    def test_update_empty_problem_rejected(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, problem='  ')
        assert ok is False
        assert 'Проблема' in err

    def test_update_nonexistent_location_rejected(self, db_conn, ticket_id):
        from services.incident_service import update_ticket
        ok, err = update_ticket(db_conn, ticket_id, location_node_id=99999)
        assert ok is False
        assert 'место' in err


class TestDeleteTicket:
    def test_delete_success(self, db_conn, ticket_id):
        from services.incident_service import delete_ticket
        ok, err = delete_ticket(db_conn, ticket_id)
        assert ok is True and err is None
        assert _select_ticket(db_conn, ticket_id) is None

    def test_delete_not_found(self, db_conn):
        from services.incident_service import delete_ticket
        ok, err = delete_ticket(db_conn, 99999)
        assert ok is False
        assert 'не найдена' in err
class TestEquipmentLinks:
    def test_add_link_success(self, db_conn, ticket_id):
        from services.incident_service import add_equipment_link
        eq_id = _make_equipment(db_conn)
        ok, err = add_equipment_link(db_conn, ticket_id, eq_id)
        assert ok is True and err is None
        rows = db_conn.execute(
            'SELECT equipment_id FROM incident_ticket_equipment WHERE ticket_id = ?',
            (ticket_id,),
        ).fetchall()
        assert [r['equipment_id'] for r in rows] == [eq_id]

    def test_add_link_duplicate_ignored(self, db_conn, ticket_id):
        from services.incident_service import add_equipment_link
        eq_id = _make_equipment(db_conn)
        assert add_equipment_link(db_conn, ticket_id, eq_id)[0] is True
        ok, err = add_equipment_link(db_conn, ticket_id, eq_id)
        assert ok is True and err is None
        rows = db_conn.execute(
            'SELECT equipment_id FROM incident_ticket_equipment WHERE ticket_id = ?',
            (ticket_id,),
        ).fetchall()
        assert len(rows) == 1

    def test_add_link_nonexistent_ticket(self, db_conn):
        from services.incident_service import add_equipment_link
        eq_id = _make_equipment(db_conn)
        ok, err = add_equipment_link(db_conn, 99999, eq_id)
        assert ok is False
        assert 'не найдена' in err

    def test_add_link_nonexistent_equipment(self, db_conn, ticket_id):
        from services.incident_service import add_equipment_link
        ok, err = add_equipment_link(db_conn, ticket_id, 99999)
        assert ok is False
        assert 'не найдено' in err

    def test_remove_link_success(self, db_conn, ticket_id):
        from services.incident_service import add_equipment_link, remove_equipment_link
        eq_id = _make_equipment(db_conn)
        add_equipment_link(db_conn, ticket_id, eq_id)
        ok, err = remove_equipment_link(db_conn, ticket_id, eq_id)
        assert ok is True and err is None
        rows = db_conn.execute(
            'SELECT equipment_id FROM incident_ticket_equipment WHERE ticket_id = ?',
            (ticket_id,),
        ).fetchall()
        assert rows == []

    def test_remove_link_not_found(self, db_conn, ticket_id):
        from services.incident_service import remove_equipment_link
        ok, err = remove_equipment_link(db_conn, ticket_id, 99999)
        assert ok is False
        assert 'Связь не найдена' in err
class TestMoveAndDeleteLocation:
    def test_move_location_ok(self, db_conn):
        from services.incident_service import move_location
        root = _make_location(db_conn, 'Цех 1')
        line = _make_location(db_conn, 'Линия 1', 'installation', parent_id=root)
        other = _make_location(db_conn, 'Цех 2')
        ok, err = move_location(db_conn, line, other)
        assert ok is True and err is None

    def test_move_location_to_itself_rejected(self, db_conn):
        from services.incident_service import move_location
        root = _make_location(db_conn, 'Цех 1')
        ok, err = move_location(db_conn, root, root)
        assert ok is False
        assert err is not None

    def test_delete_location_used_by_ticket_rejected(self, db_conn, ticket_id, loc_id):
        from services.incident_service import delete_location
        ok, err = delete_location(db_conn, loc_id)
        assert ok is False
        assert err is not None

    def test_delete_free_location_ok(self, db_conn):
        from services.incident_service import delete_location
        loc = _make_location(db_conn, 'Свободный цех')
        ok, err = delete_location(db_conn, loc)
        assert ok is True and err is None


class TestDeleteCrew:
    def test_delete_crew_used_by_ticket_rejected(self, db_conn, crew):
        from services.incident_service import create_ticket, delete_crew
        loc = _make_location(db_conn, 'Цех 1')
        create_ticket(
            db_conn, location_node_id=loc, problem='Течь',
            created_by_user_id=1, initiator_ids=[crew],
        )
        ok, err = delete_crew(db_conn, crew)
        assert ok is False
        assert err is not None

    def test_delete_free_crew_ok(self, db_conn):
        from services.incident_service import delete_crew
        crew_id = _make_crew(db_conn, 'Николай Свободный')
        ok, err = delete_crew(db_conn, crew_id)
        assert ok is True and err is None