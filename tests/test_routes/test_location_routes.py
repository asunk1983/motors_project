"""Тесты HTTP-слоя дерева мест (routes/location_routes.py).

Покрывает PATCH /api/locations/<id>/move — смену родителя существующего
узла. Остальные эндпоинты blueprint'а (list/create/search/children/
breadcrumb/update/delete) здесь не дублируются: их поведение проверяется
на уровне репозитория в tests/test_repositories/test_location_repo.py.

Паттерн — как в остальных route-тестах проекта (test_crew_routes.py,
test_equipment_routes.py): db_connection мокается на уровне модуля роута,
Flask-приложение поднимается из blueprint'а. Отличие в том, что здесь
нужен НАСТОЯЩИЙ conn (in-memory схема из фикстуры db_conn): проверяется не
только код ответа, но и связка "роут → location_repo.move() → БД" —
реально ли сменился parent_id перенесённого узла и не потерялись ли его
дети. Поэтому db_connection подменяется контекст-менеджером, отдающим
реальный db_conn.

ВАЖНО (расхождений с repo.move() не найдено): роут принимает перенос в
корень — new_parent_id: null / '' / 'null' / отсутствующий ключ все
превращаются в None (routes/location_routes.py:103-104) и передаются в
location_repo.move(), который для None пропускает проверку существования
родителя и пишет parent_id = NULL. Это поведение зафиксировано тестами.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from repositories.location_repo import create, get_by_id, get_children
from routes.location_routes import location_bp  # у bp уже url_prefix='/api/locations'


def _conn_cm(conn):
    """Контекст-менеджер поверх настоящего conn (паттерн db_connection).

    __exit__ возвращает False, поэтому with-блок не подавляет исключения и
    не закрывает соединение — после запроса conn ещё нужен для проверок.
    """
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=conn)
    m.__exit__ = MagicMock(return_value=False)
    return m


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(location_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def tree(db_conn):
    """Цех → Линия → Зона (та же форма дерева, что в тестах репозитория)."""
    root = create(db_conn, 'Цех №1', 'workshop')
    line = create(db_conn, 'Линия 2', 'installation', parent_id=root)
    zone = create(db_conn, 'Зона 3', 'zone', parent_id=line)
    return {'root': root, 'line': line, 'zone': zone}


class TestMoveLocationRoute:
    """PATCH /api/locations/<id>/move."""

    @patch('routes.location_routes.db_connection')
    def test_move_to_other_branch_success(self, m_db, client, db_conn, tree):
        """Успешный перенос: 200 и узел реально сменил родителя."""
        other = create(db_conn, 'Цех №2', 'workshop')
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["zone"]}/move', json={'parent_id': other})

        assert r.status_code == 200
        assert r.get_json()['success'] is True
        assert get_by_id(db_conn, tree['zone'])['parent_id'] == other

    @patch('routes.location_routes.db_connection')
    def test_move_into_own_subtree_rejected(self, m_db, client, db_conn, tree):
        """Перенос в собственное поддерево: 400 с текстом из repo.move()."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["root"]}/move', json={'parent_id': tree['zone']})

        assert r.status_code == 400
        assert r.get_json()['error'] == 'Нельзя перенести узел в собственное поддерево'
        assert get_by_id(db_conn, tree['root'])['parent_id'] is None

    @patch('routes.location_routes.db_connection')
    def test_move_to_nonexistent_parent_rejected(self, m_db, client, db_conn, tree):
        """Несуществующий родитель: роут отдаёт 400 (не 404) — так решил
        repo.move(), отдельной проверки существования родителя в роуте нет."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["zone"]}/move', json={'parent_id': 99999})

        assert r.status_code == 400
        assert r.get_json()['error'] == 'Новый родитель не найден'
        assert get_by_id(db_conn, tree['zone'])['parent_id'] == tree['line']

    @patch('routes.location_routes.db_connection')
    def test_move_to_self_rejected(self, m_db, client, db_conn, tree):
        """Попытка сделать узел родителем самого себя: 400."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["zone"]}/move', json={'parent_id': tree['zone']})

        assert r.status_code == 400
        assert r.get_json()['error'] == 'Нельзя сделать узел родителем самого себя'
        assert get_by_id(db_conn, tree['zone'])['parent_id'] == tree['line']

    @patch('routes.location_routes.db_connection')
    def test_move_to_root_explicit_null(self, m_db, client, db_conn, tree):
        """Перенос в корень (parent_id: null) — роут это поддерживает: 200,
        parent_id становится NULL."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["zone"]}/move', json={'parent_id': None})

        assert r.status_code == 200
        assert r.get_json()['success'] is True
        assert get_by_id(db_conn, tree['zone'])['parent_id'] is None

    @patch('routes.location_routes.db_connection')
    def test_move_to_root_when_key_missing(self, m_db, client, db_conn, tree):
        """Отсутствующий parent_id роут трактует так же, как null → корень."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["zone"]}/move', json={})

        assert r.status_code == 200
        assert get_by_id(db_conn, tree['zone'])['parent_id'] is None

    @patch('routes.location_routes.db_connection')
    def test_move_preserves_children(self, m_db, client, db_conn, tree):
        """Перенос узла с детьми: дети остаются привязаны к нему, их
        parent_id не меняется (переносится всё поддерево целиком)."""
        other = create(db_conn, 'Цех №3', 'workshop')
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch(f'/api/locations/{tree["line"]}/move', json={'parent_id': other})

        assert r.status_code == 200
        assert get_by_id(db_conn, tree['line'])['parent_id'] == other
        assert get_by_id(db_conn, tree['zone'])['parent_id'] == tree['line']
        assert [c['id'] for c in get_children(db_conn, tree['line'])] == [tree['zone']]

    @patch('routes.location_routes.db_connection')
    def test_move_unknown_node_returns_404(self, m_db, client, db_conn):
        """Перенос несуществующего узла: 404 от роута (до repo.move())."""
        m_db.return_value = _conn_cm(db_conn)

        r = client.patch('/api/locations/99999/move', json={'parent_id': None})

        assert r.status_code == 404
        assert r.get_json()['error'] == 'Место не найдено'
