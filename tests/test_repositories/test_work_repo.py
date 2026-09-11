"""Тесты для work_repo.py."""

import pytest


def _make_engine(db_conn, engine_id=1):
    """Создаёт минимальную запись в engines для FK maintenance_works.engine_id."""
    db_conn.execute(
        "INSERT INTO engines (id, status) VALUES (?, 'work')",
        (engine_id,),
    )
    db_conn.commit()
    return engine_id


class TestWorkRepo:
    def test_get_all_empty(self, db_conn):
        from repositories.work_repo import get_all
        rows = get_all(db_conn, engine_id=9999)
        assert len(rows) == 0

    def test_create_work(self, db_conn):
        from repositories.work_repo import create
        _make_engine(db_conn, 1)
        wid = create(db_conn, engine_id=1, work={"work_number": 1001, "date": "2024-01-15", "work_description": "Замена масла"})
        assert wid > 0

    def test_replace_all_deletes_old_inserts_new(self, db_conn):
        from repositories.work_repo import create, replace_all
        _make_engine(db_conn, 1)
        create(db_conn, engine_id=1, work={"work_number": 2001, "date": "2024-01-01", "work_description": "Старая 1"})
        create(db_conn, engine_id=1, work={"work_number": 2002, "date": "2024-01-02", "work_description": "Старая 2"})
        rows_before = list(db_conn.execute('SELECT * FROM maintenance_works WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows_before) == 2
        new_works = [
            {"work_number": 3001, "date": "2024-02-01", "work_description": "Новая 1"},
            {"work_number": 3002, "date": "2024-02-02", "work_description": "Новая 2"},
        ]
        replace_all(db_conn, engine_id=1, works=new_works)
        rows_after = list(db_conn.execute('SELECT * FROM maintenance_works WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows_after) == 2

    def test_delete_all_for_engine(self, db_conn):
        from repositories.work_repo import create, delete_all_for_engine
        _make_engine(db_conn, 1)
        create(db_conn, engine_id=1, work={"work_number": 4001, "date": "2024-03-01", "work_description": "Удалить 1"})
        create(db_conn, engine_id=1, work={"work_number": 4002, "date": "2024-03-02", "work_description": "Удалить 2"})
        delete_all_for_engine(db_conn, engine_id=1)
        rows = list(db_conn.execute('SELECT * FROM maintenance_works WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows) == 0
