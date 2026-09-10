"""Тесты HTTP-слоя журнала изменений (routes/audit_routes.py).

Покрывает GET /api/audit/entity-types: гейт доступа (before_request,
_require_admin) и ответ для admin (список DISTINCT entity_type).
db_connection в пространстве роута подменяется на in-memory БД (паттерн
tests/test_routes/test_engines.py).
"""
import pytest
from flask import Flask

from routes.audit_routes import audit_bp


def _add_audit(conn, entity_type):
    cur = conn.execute(
        'INSERT INTO audit_log (entity_type, entity_id, field_name, old_value, new_value, changed_at) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (entity_type, 1, 'field', 'old', 'new', '2026-09-01T10:00:00')
    )
    conn.commit()
    return cur


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(audit_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_conn_adapter(monkeypatch):
    """In-memory БД; db_connection в routes.audit_routes отдаёт её."""
    from contextlib import contextmanager

    from modules.db import get_db_connection, init_db

    conn = get_db_connection(':memory:')
    init_db(conn)

    @contextmanager
    def _fake_db_connection(*args, **kwargs):
        yield conn

    monkeypatch.setattr('routes.audit_routes.db_connection', _fake_db_connection)
    yield conn
    conn.close()


def _as_admin(monkeypatch):
    monkeypatch.setattr('routes.audit_routes._require_admin', lambda: None)


class TestListEntityTypes:
    def test_non_admin_forbidden(self, client):
        """Без подмены _require_admin реальный гейт возвращает 403."""
        r = client.get('/api/audit/entity-types')
        assert r.status_code == 403

    def test_admin_empty(self, client, db_conn_adapter, monkeypatch):
        _as_admin(monkeypatch)
        r = client.get('/api/audit/entity-types')
        assert r.status_code == 200
        assert r.get_json() == []

    def test_admin_distinct_sorted(self, client, db_conn_adapter, monkeypatch):
        _as_admin(monkeypatch)
        _add_audit(db_conn_adapter, 'engine')
        _add_audit(db_conn_adapter, 'equipment')
        _add_audit(db_conn_adapter, 'engine')
        r = client.get('/api/audit/entity-types')
        assert r.status_code == 200
        assert r.get_json() == ['engine', 'equipment']
