"""Тесты для mode_repo.py."""

import pytest


def _make_engine(db_conn, engine_id=1):
    """Создаёт минимальную запись в engines для FK operating_modes.engine_id."""
    db_conn.execute(
        "INSERT INTO engines (id, status) VALUES (?, 'work')",
        (engine_id,),
    )
    db_conn.commit()
    return engine_id


class TestModeRepo:
    def test_get_all_empty(self, db_conn):
        from repositories.mode_repo import get_all
        rows = get_all(db_conn, engine_id=9999)
        assert len(rows) == 0

    def test_create_mode(self, db_conn):
        from repositories.mode_repo import create
        _make_engine(db_conn, 1)
        mid = create(db_conn, engine_id=1, mode={"mode_name": "S4", "measured_value": "1200", "voltage": "380"})
        assert mid > 0

    def test_replace_all_deletes_old_inserts_new(self, db_conn):
        from repositories.mode_repo import create, replace_all
        _make_engine(db_conn, 1)
        create(db_conn, engine_id=1, mode={"mode_name": "OLD1", "measured_value": "100", "power": "10"})
        create(db_conn, engine_id=1, mode={"mode_name": "OLD2", "measured_value": "200", "rpm": "1500"})
        rows_before = list(db_conn.execute('SELECT * FROM operating_modes WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows_before) == 2
        new_modes = [
            {"mode_name": "S1", "measured_value": "500", "voltage": "220"},
            {"mode_name": "S2", "measured_value": "1500", "frequency": "50"},
        ]
        replace_all(db_conn, engine_id=1, modes=new_modes)
        rows_after = list(db_conn.execute('SELECT * FROM operating_modes WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows_after) == 2

    def test_delete_all_for_engine(self, db_conn):
        from repositories.mode_repo import create, delete_all_for_engine
        _make_engine(db_conn, 1)
        create(db_conn, engine_id=1, mode={"mode_name": "S1", "measured_value": "500", "current": "5"})
        create(db_conn, engine_id=1, mode={"mode_name": "S2", "measured_value": "1500", "connection_type": "star"})
        delete_all_for_engine(db_conn, engine_id=1)
        rows = list(db_conn.execute('SELECT * FROM operating_modes WHERE engine_id = ?', (1,)).fetchall())
        assert len(rows) == 0