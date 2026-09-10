"""routes/audit_routes.py — API журнала изменений (audit_log), только чтение.

Доступ — только admin/superadmin (через общий _require_admin из
routes/auth.py, тот же паттерн, что admin_routes/equipment_routes для
"конструктора"): журнал показывает, кто и что менял в базе — это
административная информация, рядовым пользователям видеть её не нужно.
Один before_request на весь blueprint, а не per-route проверка — сам
blueprint целиком закрыт для не-admin.
"""
import logging
from flask import Blueprint, request, jsonify

from modules.db import db_connection
from routes.auth import _require_admin
from repositories import audit_repo

logger = logging.getLogger(__name__)
audit_bp = Blueprint('audit_bp', __name__, url_prefix='/api/audit')


@audit_bp.before_request
def _audit_require_admin():
    return _require_admin()


@audit_bp.route('/log', methods=['GET'])
def list_audit_log_route():
    try:
        entity_type = request.args.get('entity_type') or None
        entity_id_raw = request.args.get('entity_id')
        entity_id = int(entity_id_raw) if entity_id_raw else None
        actor_query = request.args.get('actor', '')
        date_from = request.args.get('date_from') or None
        date_to = request.args.get('date_to') or None
        # Потолок 200 — защита от случайного/намеренного запроса огромной
        # страницы с фронта; обычная страница — 50 (см. static/js/audit.js).
        limit = min(request.args.get('limit', 50, type=int) or 50, 200)
        offset = request.args.get('offset', 0, type=int) or 0

        with db_connection() as conn:
            entries, total = audit_repo.list_entries(
                conn, entity_type=entity_type, entity_id=entity_id,
                actor_query=actor_query, date_from=date_from, date_to=date_to,
                limit=limit, offset=offset,
            )
        return jsonify({'entries': entries, 'total': total})
    except Exception as e:
        logger.exception('list_audit_log_route failed')
        return jsonify({'error': str(e)}), 500


@audit_bp.route('/entity-types', methods=['GET'])
def list_entity_types_route():
    try:
        with db_connection() as conn:
            types = audit_repo.list_entity_types(conn)
        return jsonify(types)
    except Exception as e:
        logger.exception('list_entity_types_route failed')
        return jsonify({'error': str(e)}), 500


@audit_bp.route('/stats', methods=['GET'])
def audit_stats_route():
    """Динамика разрастания журнала — записей в день за последние N дней
    (по умолчанию 90) + общее количество строк в audit_log сейчас."""
    try:
        days = min(request.args.get('days', 90, type=int) or 90, 730)
        with db_connection() as conn:
            data = audit_repo.growth_stats(conn, days=days)
        return jsonify(data)
    except Exception as e:
        logger.exception('audit_stats_route failed')
        return jsonify({'error': str(e)}), 500
