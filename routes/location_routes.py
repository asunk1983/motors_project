# routes/location_routes.py — API для дерева мест (location_node).
# ТЗ, раздел 1 + сводный API-контракт (раздел 6, "Общее location_bp").
# Права: как у engines/equipment — общий гейт auth_bp.before_app_request
# уже блокирует не-GET без токена и reader на запись; отдельных
# _require_admin/_require_superadmin здесь не нужно (см. HANDOFF.md /
# CLAUDE.md — "конструктор" защищается точечно, сами данные — общим гейтом).

from flask import Blueprint, request, jsonify

from modules.db import db_connection
from repositories import location_repo

location_bp = Blueprint('location_bp', __name__, url_prefix='/api/locations')


@location_bp.route('', methods=['GET'])
def list_locations_route():
    with db_connection() as conn:
        return jsonify(location_repo.list_all(conn))


@location_bp.route('', methods=['POST'])
def create_location_route():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    node_type = data.get('node_type') or 'other'
    parent_id = data.get('parent_id')
    parent_id = int(parent_id) if parent_id not in (None, '', 'null') else None

    if not name:
        return jsonify({'error': 'Название места обязательно'}), 400
    if node_type not in location_repo.VALID_NODE_TYPES:
        return jsonify({'error': f'Недопустимый тип узла: {node_type}'}), 400

    with db_connection() as conn:
        if parent_id is not None and location_repo.get_by_id(conn, parent_id) is None:
            return jsonify({'error': 'Родительский узел не найден'}), 400
        try:
            new_id = location_repo.create(conn, name, node_type, parent_id)
        except Exception as e:
            # UNIQUE(parent_id, name) — дубль имени в этой же ветке.
            if 'UNIQUE' in str(e):
                return jsonify({'error': 'Такое место уже существует в этой ветке'}), 400
            raise
        return jsonify({'success': True, 'id': new_id, 'message': 'Место добавлено'})


@location_bp.route('/search', methods=['GET'])
def search_locations_route():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    with db_connection() as conn:
        return jsonify(location_repo.search(conn, q))


@location_bp.route('/children', methods=['GET'])
def children_locations_route():
    parent_id_raw = request.args.get('parent_id')
    parent_id = int(parent_id_raw) if parent_id_raw not in (None, '', 'null') else None
    with db_connection() as conn:
        return jsonify(location_repo.get_children(conn, parent_id))


@location_bp.route('/<int:node_id>/breadcrumb', methods=['GET'])
def breadcrumb_location_route(node_id):
    with db_connection() as conn:
        if location_repo.get_by_id(conn, node_id) is None:
            return jsonify({'error': 'Место не найдено'}), 404
        return jsonify(location_repo.get_breadcrumb(conn, node_id))


@location_bp.route('/<int:node_id>', methods=['PUT'])
def update_location_route(node_id):
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    node_type = data.get('node_type')
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'error': 'Название места не может быть пустым'}), 400
    if node_type is not None and node_type not in location_repo.VALID_NODE_TYPES:
        return jsonify({'error': f'Недопустимый тип узла: {node_type}'}), 400

    with db_connection() as conn:
        if location_repo.get_by_id(conn, node_id) is None:
            return jsonify({'error': 'Место не найдено'}), 404
        try:
            ok = location_repo.update(conn, node_id, name=name, node_type=node_type)
        except Exception as e:
            if 'UNIQUE' in str(e):
                return jsonify({'error': 'Такое место уже существует в этой ветке'}), 400
            raise
        if not ok:
            return jsonify({'error': 'Нечего обновлять'}), 400
        return jsonify({'success': True, 'message': 'Место обновлено'})


@location_bp.route('/<int:node_id>/move', methods=['PATCH'])
def move_location_route(node_id):
    data = request.get_json(silent=True) or {}
    new_parent_id = data.get('parent_id')
    new_parent_id = int(new_parent_id) if new_parent_id not in (None, '', 'null') else None

    with db_connection() as conn:
        if location_repo.get_by_id(conn, node_id) is None:
            return jsonify({'error': 'Место не найдено'}), 404
        ok, error = location_repo.move(conn, node_id, new_parent_id)
        if not ok:
            return jsonify({'error': error or 'Не удалось перенести место'}), 400
        return jsonify({'success': True, 'message': 'Место перенесено'})


@location_bp.route('/<int:node_id>', methods=['DELETE'])
def delete_location_route(node_id):
    with db_connection() as conn:
        if location_repo.get_by_id(conn, node_id) is None:
            return jsonify({'error': 'Место не найдено'}), 404
        ok, error = location_repo.delete(conn, node_id)
        if not ok:
            return jsonify({'error': error or 'Не удалось удалить место'}), 400
        return jsonify({'success': True, 'message': 'Место удалено'})
