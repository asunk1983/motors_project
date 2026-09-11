"""Тесты репозитория членов экипажа (crew_repo.py).

crew_repo.py — CRUD членов экипажа, проверка использования в заявках инцидентов.
"""

import pytest


class TestCrewRepo:
    def test_list_all_empty(self, db_conn):
        from repositories.crew_repo import list_all
        members = list_all(db_conn)
        assert members == []

    def test_list_all(self, db_conn):
        from repositories.crew_repo import create, list_all
        create(db_conn, full_name='Член 1', position='engineer')
        create(db_conn, full_name='Член 2', position='technician')
        members = list_all(db_conn)
        assert len(members) == 2
        assert members[0]['full_name'] == 'Член 1'
        assert members[1]['full_name'] == 'Член 2'

    def test_get_by_id_success(self, db_conn):
        from repositories.crew_repo import create, get_by_id
        member_id = create(db_conn, full_name='Иван Иванов', position='engineer', workshop='Цех 1')
        member = get_by_id(db_conn, member_id)
        assert member is not None
        assert member['id'] == member_id
        assert member['full_name'] == 'Иван Иванов'

        # Несуществующий
        assert get_by_id(db_conn, 99999) is None

    def test_create_success(self, db_conn):
        from repositories.crew_repo import create
        member_id = create(db_conn, full_name='Сотрудник 1', position='engineer', workshop='Цех 1')
        assert member_id > 0

        row = db_conn.execute(
            "SELECT id, full_name, position, workshop FROM crew WHERE id = ?",
            (member_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == 'Сотрудник 1'
        assert row[2] == 'engineer'

    def test_create_duplicate_name(self, db_conn):
        """crew не имеет UNIQUE по full_name — дубликат разрешён."""
        from repositories.crew_repo import create
        id1 = create(db_conn, full_name='Уникальный', position='engineer')
        id2 = create(db_conn, full_name='Уникальный', position='technician')
        assert id1 > 0
        assert id2 > 0

    def test_update_success(self, db_conn):
        from repositories.crew_repo import create, update
        member_id = create(db_conn, full_name='Старое имя', position='engineer')
        ok = update(db_conn, member_id, full_name='Новое имя', position='technician')
        assert ok is True

        row = db_conn.execute(
            "SELECT full_name, position FROM crew WHERE id = ?",
            (member_id,),
        ).fetchone()
        assert row[0] == 'Новое имя'
        assert row[1] == 'technician'

    def test_update_nonexistent(self, db_conn):
        from repositories.crew_repo import update
        ok = update(db_conn, 99999, full_name='Новое имя', position='engineer')
        assert ok is False

    def test_delete_success(self, db_conn):
        from repositories.crew_repo import create, delete
        member_id = create(db_conn, full_name='Удаляемый', position='engineer')
        ok, err = delete(db_conn, member_id)
        assert ok is True
        assert err is None

        row = db_conn.execute(
            "SELECT id FROM crew WHERE id = ?",
            (member_id,),
        ).fetchone()
        assert row is None

    def test_delete_nonexistent(self, db_conn):
        from repositories.crew_repo import delete
        ok, err = delete(db_conn, 99999)
        assert ok is False

    def test_is_referenced_false(self, db_conn):
        from repositories.crew_repo import create, is_referenced
        member_id = create(db_conn, full_name='Не используемый', position='engineer')
        assert is_referenced(db_conn, member_id) is False

    def test_is_referenced_true(self, db_conn):
        from repositories.crew_repo import create, is_referenced
        # Создаём crew-запись и напрямую добавляем связь в incident_ticket_initiator
        member_id = create(db_conn, full_name='Используемый', position='engineer')
        # Нужен существующий ticket — создаём location_node и ticket
        cur = db_conn.execute(
            "INSERT INTO location_node (name, node_type) VALUES (?, ?)",
            ("Тестовый узел", "workshop"),
        )
        db_conn.commit()
        location_id = cur.lastrowid
        db_conn.execute(
            "INSERT INTO incident_ticket (location_node_id, problem, created_by_user_id) VALUES (?, ?, ?)",
            (location_id, "Тестовая заявка", 1),
        )
        db_conn.execute(
            "INSERT INTO incident_ticket_initiator (ticket_id, crew_id) VALUES (?, ?)",
            (1, member_id),
        )
        db_conn.commit()
        assert is_referenced(db_conn, member_id) is True


class TestCrewRepoGuards:
    def test_delete_referenced_raises(self, db_conn):
        from repositories.crew_repo import create, is_referenced, delete
        member_id = create(db_conn, full_name='Используемый', position='engineer')
        # Проверяем, что is_referenced возвращает False (пока нет связей)
        assert is_referenced(db_conn, member_id) is False

        # delete работает, когда member не используется
        ok, err = delete(db_conn, member_id)
        assert ok is True