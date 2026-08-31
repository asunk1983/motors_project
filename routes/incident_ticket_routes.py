# routes/incident_ticket_routes.py — API заявок модуля "Инциденты".
#
# Открыто всем ролям на чтение/создание/редактирование (как /api/tickets
# в routes/ticket_routes.py) — общий гейт для не-reader на запись уже
# обеспечен auth_bp.before_app_request, точечных проверок роли здесь нет,
# КРОМЕ удаления заявки (ТЗ раздел 2.1.4 — только superadmin, см. ниже).
#
# created_by_user_id берётся из request.current_user, а не из тела
# запроса — тот же принцип, что и в routes/ticket_routes.py::
# create_ticket_route (иначе кто угодно мог бы создать заявку от чужого
# имени, подставив другой id в JSON).
#
# Печать (/print/incident/<id>) — отдельно, требует шаблон print.html
# для сверки (см. INTEGRATION.md). Экспорт — ниже, POST /export.

from flask import Blueprint, request, jsonify, send_file
import io

from modules.db import db_connection
from modules.photo_manager import incident_manager
from repositories import incident_ticket_repo
from routes.auth import _require_superadmin
from services import incident_service, export_service

incident_ticket_bp = Blueprint('incident_ticket_bp', __name__, url_prefix='/api/incident-tickets')

EXPORT_MAX_IDS = 100


def _current_user_id():
    user = getattr(request, 'current_user', None)
    return user.get('id') if user else None


# ---------------------------------------------------------------------
# CRUD заявки
# ---------------------------------------------------------------------

@incident_ticket_bp.route('', methods=['GET'])
def list_tickets_route():
    status = request.args.get('status') or None
    priority = request.args.get('priority') or None
    location_raw = request.args.get('location_node_id')
    location_node_id = int(location_raw) if location_raw else None

    with db_connection() as conn:
        return jsonify(incident_ticket_repo.list_all(
            conn, status=status, priority=priority, location_node_id=location_node_id
        ))


@incident_ticket_bp.route('', methods=['POST'])
def create_ticket_route():
    data = request.get_json(silent=True) or {}
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({'error': 'Не удалось определить текущего пользователя'}), 401

    location_raw = data.get('location_node_id')
    if location_raw in (None, '', 'null'):
        return jsonify({'error': 'Место обязательно'}), 400

    with db_connection() as conn:
        ticket_id, error = incident_service.create_ticket(
            conn,
            location_node_id=int(location_raw),
            problem=data.get('problem') or '',
            created_by_user_id=user_id,
            solution=data.get('solution'),
            priority=data.get('priority') or 'medium',
            status=data.get('status') or 'in_progress',
            initiator_ids=[int(x) for x in (data.get('initiator_ids') or [])],
            executor_ids=[int(x) for x in (data.get('executor_ids') or [])],
            closed_at=data.get('closed_at'),
        )
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'success': True, 'id': ticket_id, 'message': 'Заявка создана'})


@incident_ticket_bp.route('/<int:ticket_id>', methods=['GET'])
def get_ticket_route(ticket_id):
    with db_connection() as conn:
        ticket = incident_ticket_repo.get_by_id(conn, ticket_id)
        if ticket is None:
            return jsonify({'error': 'Заявка не найдена'}), 404
        ticket['photos'] = incident_manager.get_ticket_photos(ticket_id)
        return jsonify(ticket)


@incident_ticket_bp.route('/<int:ticket_id>', methods=['PATCH'])
def update_ticket_route(ticket_id):
    data = request.get_json(silent=True) or {}

    location_node_id = None
    if 'location_node_id' in data and data['location_node_id'] not in (None, '', 'null'):
        location_node_id = int(data['location_node_id'])

    initiator_ids = None
    if 'initiator_ids' in data:
        initiator_ids = [int(x) for x in (data['initiator_ids'] or [])]
    executor_ids = None
    if 'executor_ids' in data:
        executor_ids = [int(x) for x in (data['executor_ids'] or [])]

    with db_connection() as conn:
        ok, error = incident_service.update_ticket(
            conn, ticket_id,
            location_node_id=location_node_id,
            problem=data.get('problem'),
            solution=data.get('solution'),
            priority=data.get('priority'),
            status=data.get('status'),
            initiator_ids=initiator_ids,
            executor_ids=executor_ids,
            closed_at=data.get('closed_at'),
            closed_at_explicitly_set=('closed_at' in data),
        )
        if not ok:
            status_code = 404 if error == 'Заявка не найдена' else 400
            return jsonify({'error': error}), status_code
        return jsonify({'success': True, 'message': 'Заявка обновлена'})


@incident_ticket_bp.route('/<int:ticket_id>', methods=['DELETE'])
def delete_ticket_route(ticket_id):
    # ТЗ раздел 2.1.4: физическое удаление — только superadmin. Тот же
    # helper, что уже используется в routes/knowledge_routes.py — единый
    # источник правды для проверки роли, а не своя копия условия.
    denied = _require_superadmin()
    if denied:
        return denied

    with db_connection() as conn:
        ok, error = incident_service.delete_ticket(conn, ticket_id)
        if not ok:
            return jsonify({'error': error or 'Не удалось удалить заявку'}), 404
        # Фото удаляем ПОСЛЕ успешного удаления записи из БД — тот же
        # порядок, что manager.py::delete_engine_photos_from_disk у
        # routes/engines.py (осиротевшие файлы не блокируют сам факт
        # удаления заявки, даже если что-то не удалится с диска).
        incident_manager.delete_ticket_photos_from_disk(ticket_id)
        return jsonify({'success': True, 'message': 'Заявка удалена'})


@incident_ticket_bp.route('/location-counts', methods=['GET'])
def get_incident_location_counts_route():
    """{location_node_id: count} — только СОБСТВЕННЫЕ счётчики узлов, без
    суммирования по поддереву (суммирует фронтенд — дерево уже загружено
    целиком, см. incidentLocationTree.js). Тот же контракт ответа, что и
    у /api/equipment/location-counts (equipment_routes.py)."""
    with db_connection() as conn:
        return jsonify(incident_ticket_repo.get_location_counts(conn))


# ---------------------------------------------------------------------
# Ссылки
# ---------------------------------------------------------------------

@incident_ticket_bp.route('/<int:ticket_id>/links', methods=['POST'])
def add_link_route(ticket_id):
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'URL обязателен'}), 400
    caption = (data.get('caption') or '').strip() or None

    with db_connection() as conn:
        if incident_ticket_repo.get_by_id(conn, ticket_id) is None:
            return jsonify({'error': 'Заявка не найдена'}), 404
        link_id = incident_ticket_repo.add_link(conn, ticket_id, url, caption)
        return jsonify({'success': True, 'id': link_id, 'message': 'Ссылка добавлена'})


@incident_ticket_bp.route('/<int:ticket_id>/links/<int:link_id>', methods=['DELETE'])
def delete_link_route(ticket_id, link_id):
    with db_connection() as conn:
        ok = incident_ticket_repo.delete_link(conn, link_id)
        if not ok:
            return jsonify({'error': 'Ссылка не найдена'}), 404
        return jsonify({'success': True, 'message': 'Ссылка удалена'})


# ---------------------------------------------------------------------
# Привязка оборудования
# ---------------------------------------------------------------------

@incident_ticket_bp.route('/<int:ticket_id>/equipment', methods=['POST'])
def add_equipment_route(ticket_id):
    data = request.get_json(silent=True) or {}
    equipment_id = data.get('equipment_id')
    if not equipment_id:
        return jsonify({'error': 'equipment_id обязателен'}), 400

    with db_connection() as conn:
        ok, error = incident_service.add_equipment_link(conn, ticket_id, int(equipment_id))
        if not ok:
            return jsonify({'error': error}), 404
        return jsonify({'success': True, 'message': 'Оборудование привязано'})


@incident_ticket_bp.route('/<int:ticket_id>/equipment/<int:equipment_id>', methods=['DELETE'])
def remove_equipment_route(ticket_id, equipment_id):
    with db_connection() as conn:
        ok, error = incident_service.remove_equipment_link(conn, ticket_id, equipment_id)
        if not ok:
            return jsonify({'error': error}), 404
        return jsonify({'success': True, 'message': 'Оборудование отвязано'})


# ---------------------------------------------------------------------
# Фото (modules/photo_manager/incident_manager.py — работает только с
# диском, БД не трогает; существование заявки проверяем здесь).
# ---------------------------------------------------------------------

@incident_ticket_bp.route('/<int:ticket_id>/photos', methods=['GET'])
def list_ticket_photos_route(ticket_id):
    with db_connection() as conn:
        if incident_ticket_repo.get_by_id(conn, ticket_id) is None:
            return jsonify({'error': 'Заявка не найдена'}), 404
    return jsonify(incident_manager.get_ticket_photos(ticket_id))


@incident_ticket_bp.route('/<int:ticket_id>/photos', methods=['POST'])
def upload_ticket_photos_route(ticket_id):
    with db_connection() as conn:
        if incident_ticket_repo.get_by_id(conn, ticket_id) is None:
            return jsonify({'error': 'Заявка не найдена'}), 404
    files = request.files.getlist('photos')
    return incident_manager.upload_ticket_photos(ticket_id, files)


@incident_ticket_bp.route('/<int:ticket_id>/photos/<filename>', methods=['DELETE'])
def delete_ticket_photo_route(ticket_id, filename):
    return incident_manager.delete_ticket_photo(ticket_id, filename)


# ---------------------------------------------------------------------
# Экспорт в Excel (ТЗ раздел 2.6) — плоская таблица, лимит 100 заявок за
# раз проверяется здесь (HTTP-слой), сама export_service ничего не
# ограничивает.
# ---------------------------------------------------------------------

@incident_ticket_bp.route('/export', methods=['POST'])
def export_tickets_route():
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []
    if not ids:
        return jsonify({'error': 'Не выбрано ни одной заявки'}), 400
    if len(ids) > EXPORT_MAX_IDS:
        return jsonify({'error': f'Слишком много заявок за раз (максимум {EXPORT_MAX_IDS})'}), 400

    with db_connection() as conn:
        xlsx_bytes = export_service.export_incidents_to_xlsx(conn, [int(i) for i in ids])

    from datetime import datetime
    filename = f"incidents_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(
        io.BytesIO(xlsx_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )
