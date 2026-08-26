# routes/crew_routes.py — API справочника людей (модуль "Инциденты").
# ТЗ раздел 2.1.3: прав доступа нет — оба пользователя полноправны на
# создание/чтение/редактирование, только общий гейт "залогинен" от
# auth_bp.before_app_request (как и остальные не-superadmin роуты).

from flask import Blueprint, request, jsonify

from modules.db import db_connection
from repositories import crew_repo
from services import incident_service

crew_bp = Blueprint('crew_bp', __name__, url_prefix='/api/crew')


@crew_bp.route('', methods=['GET'])
def list_crew_route():
    with db_connection() as conn:
        return jsonify(crew_repo.list_all(conn))


@crew_bp.route('', methods=['POST'])
def create_crew_route():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    if not full_name:
        return jsonify({'error': 'ФИО обязательно'}), 400
    position = (data.get('position') or '').strip() or None
    workshop = (data.get('workshop') or '').strip() or None

    with db_connection() as conn:
        new_id = crew_repo.create(conn, full_name, position, workshop)
        return jsonify({'success': True, 'id': new_id, 'message': 'Человек добавлен'})


@crew_bp.route('/search', methods=['GET'])
def search_crew_route():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    with db_connection() as conn:
        return jsonify(crew_repo.search(conn, q))


@crew_bp.route('/<int:crew_id>', methods=['PUT'])
def update_crew_route(crew_id):
    data = request.get_json(silent=True) or {}
    full_name = data.get('full_name')
    if full_name is not None:
        full_name = full_name.strip()
        if not full_name:
            return jsonify({'error': 'ФИО не может быть пустым'}), 400
    position = data.get('position')
    workshop = data.get('workshop')

    with db_connection() as conn:
        if crew_repo.get_by_id(conn, crew_id) is None:
            return jsonify({'error': 'Человек не найден'}), 404
        ok = crew_repo.update(conn, crew_id, full_name=full_name, position=position, workshop=workshop)
        if not ok:
            return jsonify({'error': 'Нечего обновлять'}), 400
        return jsonify({'success': True, 'message': 'Данные обновлены'})


@crew_bp.route('/<int:crew_id>', methods=['DELETE'])
def delete_crew_route(crew_id):
    with db_connection() as conn:
        if crew_repo.get_by_id(conn, crew_id) is None:
            return jsonify({'error': 'Человек не найден'}), 404
        ok, error = incident_service.delete_crew(conn, crew_id)
        if not ok:
            return jsonify({'error': error or 'Не удалось удалить'}), 400
        return jsonify({'success': True, 'message': 'Удалено'})
