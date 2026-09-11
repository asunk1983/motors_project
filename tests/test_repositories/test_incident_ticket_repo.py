import pytest
from repositories.incident_ticket_repo import (
    create,
    get_by_id,
    update,
    delete,
    list_all,
    get_executors,
    set_executors,
    get_initiators,
    set_initiators,
    get_links,
    add_link,
    delete_link,
    get_location_counts,
    count_all,
    count_by_status,
    _ensure_updated_at_column,
    _ensure_no_users_fk,
    _ensure_last_edited_columns,
)


@pytest.fixture
def location_id(db_conn):
    cur = db_conn.execute(
        "INSERT INTO location_node (name, node_type) VALUES (?, ?)",
        ("Тестовый узел", "workshop"),
    )
    db_conn.commit()
    return cur.lastrowid


@pytest.fixture
def crew_id(db_conn):
    cur = db_conn.execute("INSERT INTO crew (full_name) VALUES ('Бригада 1')")
    db_conn.commit()
    return cur.lastrowid


class TestIncidentTicketRepo:
    def test_create_returns_id(self, db_conn, location_id):
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Течь насоса",
            created_by_user_id=1,
        )
        assert isinstance(ticket_id, int)
        assert ticket_id > 0

    def test_create_defaults(self, db_conn, location_id):
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Течь насоса",
            created_by_user_id=1,
        )
        ticket = get_by_id(db_conn, ticket_id)
        assert ticket["priority"] == "medium"
        assert ticket["status"] == "in_progress"
        assert ticket["solution"] is None
        assert ticket["closed_at"] is None

    def test_create_with_explicit_fields(self, db_conn, location_id):
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Авария",
            created_by_user_id=1,
            solution="Заменили насос",
            priority="high",
            status="resolved",
            closed_at="2026-01-01T00:00:00",
        )
        ticket = get_by_id(db_conn, ticket_id)
        assert ticket["priority"] == "high"
        assert ticket["status"] == "resolved"
        assert ticket["solution"] == "Заменили насос"
        assert ticket["closed_at"] == "2026-01-01T00:00:00"

    def test_get_by_id_not_found(self, db_conn):
        assert get_by_id(db_conn, 9999) is None

    def test_update_fields(self, db_conn, location_id):
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Проблема",
            created_by_user_id=1,
        )
        result = update(db_conn, ticket_id, status="resolved", solution="Исправлено")
        assert result is True
        ticket = get_by_id(db_conn, ticket_id)
        assert ticket["status"] == "resolved"
        assert ticket["solution"] == "Исправлено"

    def test_update_not_found(self, db_conn):
        result = update(db_conn, 9999, status="resolved")
        assert result is False

    def test_delete(self, db_conn, location_id):
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Проблема",
            created_by_user_id=1,
        )
        result = delete(db_conn, ticket_id)
        assert result is True
        assert get_by_id(db_conn, ticket_id) is None

    def test_delete_not_found(self, db_conn):
        assert delete(db_conn, 9999) is False

    def test_list_all_no_filters(self, db_conn, location_id):
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1)
        create(db_conn, location_node_id=location_id, problem="П2", created_by_user_id=1)
        tickets = list_all(db_conn)
        assert len(tickets) == 2

    def test_list_all_filter_by_status(self, db_conn, location_id):
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1, status="in_progress")
        create(db_conn, location_node_id=location_id, problem="П2", created_by_user_id=1, status="resolved")
        tickets = list_all(db_conn, status="resolved")
        assert len(tickets) == 1
        assert tickets[0]["status"] == "resolved"

    def test_list_all_filter_by_priority(self, db_conn, location_id):
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1, priority="high")
        create(db_conn, location_node_id=location_id, problem="П2", created_by_user_id=1, priority="low")
        tickets = list_all(db_conn, priority="high")
        assert len(tickets) == 1
        assert tickets[0]["priority"] == "high"

    def test_list_all_filter_by_location(self, db_conn, location_id):
        cur = db_conn.execute(
            "INSERT INTO location_node (name, node_type) VALUES (?, ?)",
            ("Другой узел", "workshop"),
        )
        db_conn.commit()
        other_location_id = cur.lastrowid
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1)
        create(db_conn, location_node_id=other_location_id, problem="П2", created_by_user_id=1)
        tickets = list_all(db_conn, location_node_id=location_id)
        assert len(tickets) == 1
        assert tickets[0]["location_node_id"] == location_id

    def test_executors_round_trip(self, db_conn, location_id, crew_id):
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        assert get_executors(db_conn, ticket_id) == []
        set_executors(db_conn, ticket_id, [crew_id])
        executors = get_executors(db_conn, ticket_id)
        assert len(executors) == 1

    def test_set_executors_replaces_existing(self, db_conn, location_id, crew_id):
        cur = db_conn.execute("INSERT INTO crew (full_name) VALUES ('Бригада 2')")
        db_conn.commit()
        second_crew_id = cur.lastrowid
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        set_executors(db_conn, ticket_id, [crew_id])
        set_executors(db_conn, ticket_id, [second_crew_id])
        executors = get_executors(db_conn, ticket_id)
        assert len(executors) == 1

    def test_initiators_round_trip(self, db_conn, location_id, crew_id):
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        assert get_initiators(db_conn, ticket_id) == []
        set_initiators(db_conn, ticket_id, [crew_id])
        initiators = get_initiators(db_conn, ticket_id)
        assert len(initiators) == 1

    def test_links_round_trip(self, db_conn, location_id):
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        assert get_links(db_conn, ticket_id) == []
        link_id = add_link(db_conn, ticket_id, url="https://example.com", caption="Фото")
        assert isinstance(link_id, int)
        links = get_links(db_conn, ticket_id)
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com"

    def test_delete_link(self, db_conn, location_id):
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        link_id = add_link(db_conn, ticket_id, url="https://example.com")
        result = delete_link(db_conn, link_id)
        assert result is True
        assert get_links(db_conn, ticket_id) == []

    def test_delete_link_not_found(self, db_conn):
        assert delete_link(db_conn, 9999) is False

    def test_count_all(self, db_conn, location_id):
        assert count_all(db_conn) == 0
        create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        assert count_all(db_conn) == 1

    def test_count_by_status(self, db_conn, location_id):
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1, status="in_progress")
        create(db_conn, location_node_id=location_id, problem="П2", created_by_user_id=1, status="resolved")
        assert count_by_status(db_conn, "in_progress") == 1
        assert count_by_status(db_conn, "resolved") == 1

    def test_get_location_counts_returns_dict(self, db_conn, location_id):
        create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        result = get_location_counts(db_conn)
        assert isinstance(result, dict)
    def test_get_location_counts_meaningful(self, db_conn, location_id):
        """get_location_counts возвращает dict с ключами-str (id узлов) и 'unassigned'."""
        create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        result = get_location_counts(db_conn)
        # Ключ — строка (str), а не int (см. комментарий в репозитории про jsonify sort_keys)
        assert isinstance(result, dict)
        assert str(location_id) in result
        assert result[str(location_id)] == 1
        assert "unassigned" in result

    def test_create_invalid_priority_raises(self, db_conn, location_id):
        """priority вне CHECK (low/medium/high) — IntegrityError."""
        with pytest.raises(Exception):
            create(
                db_conn,
                location_node_id=location_id,
                problem="Тест",
                created_by_user_id=1,
                priority="urgent",
            )

    def test_create_invalid_status_raises(self, db_conn, location_id):
        """status вне CHECK (in_progress/resolved/rejected) — IntegrityError."""
        with pytest.raises(Exception):
            create(
                db_conn,
                location_node_id=location_id,
                problem="Тест",
                created_by_user_id=1,
                status="closed",
            )

    def test_update_empty_fields_no_crash(self, db_conn, location_id):
        """update() без полей не должен падать — возвращает False (нечего обновлять)."""
        ticket_id = create(
            db_conn,
            location_node_id=location_id,
            problem="Проблема",
            created_by_user_id=1,
        )
        result = update(db_conn, ticket_id)
        # Нет полей — нечего обновлять, update возвращает False
        assert result is False
        ticket = get_by_id(db_conn, ticket_id)
        assert ticket["problem"] == "Проблема"

    def test_delete_cascades_executors_initiators_links(self, db_conn, location_id, crew_id):
        """DELETE тиката должен каскадно удалять связи из incident_ticket_executor,
        incident_ticket_initiator, incident_ticket_link."""
        ticket_id = create(db_conn, location_node_id=location_id, problem="П", created_by_user_id=1)
        set_executors(db_conn, ticket_id, [crew_id])
        set_initiators(db_conn, ticket_id, [crew_id])
        add_link(db_conn, ticket_id, url="https://example.com")

        # Проверяем что связи есть до удаления
        assert len(get_executors(db_conn, ticket_id)) == 1
        assert len(get_initiators(db_conn, ticket_id)) == 1
        assert len(get_links(db_conn, ticket_id)) == 1

        delete(db_conn, ticket_id)

        # Каскад должен был подчистить связи
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM incident_ticket_executor WHERE ticket_id = ?", (ticket_id,))
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM incident_ticket_initiator WHERE ticket_id = ?", (ticket_id,))
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM incident_ticket_link WHERE ticket_id = ?", (ticket_id,))
        assert cur.fetchone()[0] == 0

    def test_list_all_multiple_filters(self, db_conn, location_id):
        """list_all() с комбинацией status + priority."""
        create(db_conn, location_node_id=location_id, problem="П1", created_by_user_id=1,
               status="in_progress", priority="high")
        create(db_conn, location_node_id=location_id, problem="П2", created_by_user_id=1,
               status="in_progress", priority="low")
        create(db_conn, location_node_id=location_id, problem="П3", created_by_user_id=1,
               status="resolved", priority="high")
        tickets = list_all(db_conn, status="in_progress", priority="high")
        assert len(tickets) == 1
        assert tickets[0]["problem"] == "П1"



class TestIncidentTicketRepoMigrations:
    def test_ensure_updated_at_column_runs_cleanly(self, db_conn):
        _ensure_updated_at_column(db_conn)
        cursor = db_conn.execute("PRAGMA table_info(incident_ticket)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "updated_at" in columns

    def test_ensure_no_users_fk_runs_cleanly(self, db_conn):
        _ensure_no_users_fk(db_conn)
        cursor = db_conn.execute("PRAGMA foreign_key_list(incident_ticket)")
        fk_tables = set(row[2] for row in cursor.fetchall())
        assert "users" not in fk_tables
ACTOR = {'id': 3, 'username': 'sidorov', 'display_name': 'Сидоров С.'}


class TestIncidentTicketLastEdited:
    """last_edited_by/last_edited_at (incident_ticket_repo._ensure_last_edited_columns).

    Реальное поведение при actor=None: last_edited_by → NULL (update
    перезаписывает прежнего автора в NULL), last_edited_at и updated_at
    всё равно проставляются (datetime('now')). get_by_id() колонку
    last_edited_at не возвращает — читаем из таблицы напрямую.
    """

    def _last_edited(self, db_conn, ticket_id):
        row = db_conn.execute(
            'SELECT last_edited_by, last_edited_at, updated_at '
            'FROM incident_ticket WHERE id = ?',
            (ticket_id,)).fetchone()
        return row['last_edited_by'], row['last_edited_at'], row['updated_at']

    def test_create_with_actor_sets_both(self, db_conn, location_id):
        ticket_id = create(
            db_conn, location_node_id=location_id, problem='Течь насоса',
            created_by_user_id=1, actor=ACTOR,
        )
        editor, edited_at, _ = self._last_edited(db_conn, ticket_id)
        assert editor == 'Сидоров С.'
        assert edited_at is not None

    def test_create_without_actor_by_null_at_set(self, db_conn, location_id):
        ticket_id = create(
            db_conn, location_node_id=location_id, problem='Течь насоса',
            created_by_user_id=1,
        )
        editor, edited_at, _ = self._last_edited(db_conn, ticket_id)
        assert editor is None
        assert edited_at is not None

    def test_update_with_actor_updates_both(self, db_conn, location_id):
        ticket_id = create(
            db_conn, location_node_id=location_id, problem='П', created_by_user_id=1,
            actor=ACTOR,
        )
        assert update(
            db_conn, ticket_id,
            actor={'id': 5, 'username': 'petrov', 'display_name': 'Петров П.'},
            priority='high',
        ) is True

        editor, edited_at, updated_at = self._last_edited(db_conn, ticket_id)
        assert editor == 'Петров П.'
        # datetime('now') в SQL имеет секундную точность — строгое отличие от
        # create-значения проверить нельзя без пауз; проверяем, что update
        # переписал оба поля одной операцией (связаны с updated_at).
        assert edited_at is not None
        assert edited_at == updated_at

    def test_update_without_actor_overwrites_null(self, db_conn, location_id):
        ticket_id = create(
            db_conn, location_node_id=location_id, problem='П', created_by_user_id=1,
            actor=ACTOR,
        )
        assert update(db_conn, ticket_id, priority='low') is True

        editor, edited_at, _ = self._last_edited(db_conn, ticket_id)
        assert editor is None
        assert edited_at is not None

    def test_ensure_last_edited_columns_idempotent(self, db_conn, location_id):
        # init_db не содержит колонок — «старая» схема
        columns = [r[1] for r in db_conn.execute('PRAGMA table_info(incident_ticket)')]
        assert 'last_edited_by' not in columns and 'last_edited_at' not in columns

        _ensure_last_edited_columns(db_conn)
        _ensure_last_edited_columns(db_conn)  # повторный вызов — идемпотентен

        columns = [r[1] for r in db_conn.execute('PRAGMA table_info(incident_ticket)')]
        assert 'last_edited_by' in columns and 'last_edited_at' in columns

        # После миграции create() работает штатно
        ticket_id = create(
            db_conn, location_node_id=location_id, problem='П', created_by_user_id=1,
            actor=ACTOR,
        )
        editor, edited_at, _ = self._last_edited(db_conn, ticket_id)
        assert editor == 'Сидоров С.' and edited_at is not None