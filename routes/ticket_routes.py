"""Маршруты заявок (ticket), отказов (failure) и работ (equipment_work).

Открыто всем ролям (как /api/engine*) — это основной рабочий функционал,
не административная настройка. Общий гейт для не-reader на запись уже
обеспечен auth_bp.before_app_request, точечных проверок роли здесь нет.

created_by_user_id/executor_user_id берутся из request.current_user,
а не из тела запроса — иначе кто угодно мог бы создать заявку от чужого
имени, просто подставив другой id в JSON.
"""
import logging
from flask import Blueprint, request, jsonify

from modules.db import db_connection
from repositories.ticket_repo import (
    list_tickets, get_ticket_by_id, create_ticket, update_ticket,
    update_ticket_status, delete_ticket,
    get_failure_by_id, create_failure, update_failure,
    create_work, delete_work, list_maintenance_action_types,
)
from schemas.ticket_schema import (
    validate_ticket_payload, sanitize_ticket_data, validate_status_payload,
    validate_failure_payload, sanitize_failure_data,
    validate_work_payload, sanitize_work_data,
)

logger = logging.getLogger(__name__)
ticket_bp = Blueprint('ticket', __name__, url_prefix='/api')


def _current_user_id():
    user = getattr(request, 'current_user', None)
    return user.get('id') if user else None


# ---------------------------------------------------------------------
# ticket
# ---------------------------------------------------------------------

@ticket_bp.route('/tickets', methods=['GET'])
def get_tickets():
    try:
        status = request.args.get('status', '')
        equipment_id = request.args.get('equipment', type=int)
        with db_connection() as conn:
            tickets = list_tickets(conn, status=status, equipment_id=equipment_id)
        return jsonify(tickets)
    except Exception as e:
        logger.exception('get_tickets failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket/<int:ticket_id>', methods=['GET'])
def get_ticket_route(ticket_id):
    try:
        with db_connection() as conn:
            ticket = get_ticket_by_id(conn, ticket_id)
        if not ticket:
            return jsonify({'error': 'Заявка не найдена'}), 404
        return jsonify(ticket)
    except Exception as e:
        logger.exception('get_ticket_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket', methods=['POST'])
def create_ticket_route():
    try:
        data = request.json or {}
        is_valid, err = validate_ticket_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_ticket_data(data)
        clean['created_by_user_id'] = _current_user_id()
        with db_connection() as conn:
            ticket_id = create_ticket(conn, clean)
        return jsonify({'success': True, 'id': ticket_id, 'message': 'Заявка создана'})
    except Exception as e:
        logger.exception('create_ticket_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket/<int:ticket_id>', methods=['PUT'])
def update_ticket_route(ticket_id):
    try:
        data = request.json or {}
        is_valid, err = validate_ticket_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_ticket_data(data)
        with db_connection() as conn:
            if not get_ticket_by_id(conn, ticket_id):
                return jsonify({'error': 'Заявка не найдена'}), 404
            update_ticket(conn, ticket_id, clean)
        return jsonify({'success': True, 'message': 'Заявка обновлена'})
    except Exception as e:
        logger.exception('update_ticket_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket/<int:ticket_id>/status', methods=['PUT'])
def update_ticket_status_route(ticket_id):
    try:
        data = request.json or {}
        is_valid, err = validate_status_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        with db_connection() as conn:
            if not get_ticket_by_id(conn, ticket_id):
                return jsonify({'error': 'Заявка не найдена'}), 404
            update_ticket_status(conn, ticket_id, data['status'], data.get('rejection_reason'))
        return jsonify({'success': True, 'message': 'Статус заявки обновлён'})
    except Exception as e:
        logger.exception('update_ticket_status_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket/<int:ticket_id>', methods=['DELETE'])
def delete_ticket_route(ticket_id):
    try:
        with db_connection() as conn:
            if not get_ticket_by_id(conn, ticket_id):
                return jsonify({'error': 'Заявка не найдена'}), 404
            delete_ticket(conn, ticket_id)
        return jsonify({'success': True, 'message': 'Заявка удалена'})
    except Exception as e:
        logger.exception('delete_ticket_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# failure — подтверждение заявки как отказа
# ---------------------------------------------------------------------

@ticket_bp.route('/failure/<int:failure_id>', methods=['GET'])
def get_failure_route(failure_id):
    try:
        with db_connection() as conn:
            failure = get_failure_by_id(conn, failure_id)
        if not failure:
            return jsonify({'error': 'Отказ не найден'}), 404
        return jsonify(failure)
    except Exception as e:
        logger.exception('get_failure_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/ticket/<int:ticket_id>/confirm-failure', methods=['POST'])
def confirm_failure_route(ticket_id):
    """Подтвердить заявку как отказ — создаёт failure и переводит
    заявку в in_progress одной операцией (типичный сценарий: диагностика
    завершена, дальше идёт устранение)."""
    try:
        data = request.json or {}
        data['ticket_id'] = ticket_id
        with db_connection() as conn:
            ticket = get_ticket_by_id(conn, ticket_id)
            if not ticket:
                return jsonify({'error': 'Заявка не найдена'}), 404
            if not data.get('equipment_id'):
                data['equipment_id'] = ticket.get('equipment_id')
            is_valid, err = validate_failure_payload(data)
            if not is_valid:
                return jsonify({'error': err}), 400
            clean = sanitize_failure_data(data)
            failure_id = create_failure(conn, clean)
            update_ticket_status(conn, ticket_id, 'in_progress')
        return jsonify({'success': True, 'id': failure_id, 'message': 'Отказ подтверждён'})
    except Exception as e:
        logger.exception('confirm_failure_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/failure/<int:failure_id>', methods=['PUT'])
def update_failure_route(failure_id):
    try:
        data = request.json or {}
        with db_connection() as conn:
            if not get_failure_by_id(conn, failure_id):
                return jsonify({'error': 'Отказ не найден'}), 404
            clean = sanitize_failure_data(data)
            update_failure(conn, failure_id, clean)
        return jsonify({'success': True, 'message': 'Отказ обновлён'})
    except Exception as e:
        logger.exception('update_failure_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# equipment_work
# ---------------------------------------------------------------------

@ticket_bp.route('/maintenance-action-types', methods=['GET'])
def get_maintenance_action_types():
    try:
        with db_connection() as conn:
            types = list_maintenance_action_types(conn)
        return jsonify(types)
    except Exception as e:
        logger.exception('get_maintenance_action_types failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/failure/<int:failure_id>/work', methods=['POST'])
def create_work_route(failure_id):
    try:
        data = request.json or {}
        data['failure_id'] = failure_id
        is_valid, err = validate_work_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_work_data(data)
        clean['executor_user_id'] = _current_user_id()
        with db_connection() as conn:
            if not get_failure_by_id(conn, failure_id):
                return jsonify({'error': 'Отказ не найден'}), 404
            work_id = create_work(conn, clean)
        return jsonify({'success': True, 'id': work_id, 'message': 'Работа добавлена'})
    except Exception as e:
        logger.exception('create_work_route failed')
        return jsonify({'error': str(e)}), 500


@ticket_bp.route('/work/<int:work_id>', methods=['DELETE'])
def delete_work_route(work_id):
    try:
        with db_connection() as conn:
            deleted = delete_work(conn, work_id)
        if not deleted:
            return jsonify({'error': 'Работа не найдена'}), 404
        return jsonify({'success': True, 'message': 'Работа удалена'})
    except Exception as e:
        logger.exception('delete_work_route failed')
        return jsonify({'error': str(e)}), 500
