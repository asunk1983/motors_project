"""Маршруты номенклатуры оборудования: equipment_type, attribute_definition,
equipment_type_attribute, equipment.

Стиль — как в routes/engines.py и routes/knowledge_routes.py.

Разграничение доступа (осознанное решение, отличное от knowledge_bp):
- Конструктор (типы, атрибуты, назначение атрибутов типу) — требует
  _require_admin() поточечно в соответствующих роутах, как
  admin_* роуты в routes/auth.py. Это конфигурация схемы, не должна
  трогаться кем попало.
- CRUD самих записей оборудования — БЕЗ дополнительной проверки роли,
  как /api/engine* в routes/engines.py. Полагается на общий гейт в
  auth_bp.before_app_request (reader не может писать, остальные могут).
  Это основной рабочий функционал, а не административная настройка.
"""
import io
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

from modules.db import db_connection
from modules.photo_manager import equipment_manager
from routes.auth import _require_admin
from services import export_service
from repositories.equipment_repo import (
    list_equipment_types, get_equipment_type, create_equipment_type,
    equipment_type_in_use, delete_equipment_type,
    list_attribute_definitions, create_attribute_definition,
    attribute_definition_in_use, delete_attribute_definition,
    get_assigned_attributes, get_effective_attributes, set_type_attributes,
    get_equipment_by_id, list_equipment, create_equipment, update_equipment, delete_equipment,
    get_equipment_location_counts, get_show_in_list_attributes,
    get_stock_summary, update_equipment_type_min_stock_qty,
    equipment_referenced_by_incidents,
)
from schemas.equipment_schema import (
    validate_equipment_type_payload, sanitize_equipment_type_data,
    validate_attribute_definition_payload, sanitize_attribute_definition_data,
    validate_equipment_payload, sanitize_equipment_data,
)

logger = logging.getLogger(__name__)
equipment_bp = Blueprint('equipment', __name__, url_prefix='/api')


# ---------------------------------------------------------------------
# Конструктор: типы оборудования (admin+)
# ---------------------------------------------------------------------

@equipment_bp.route('/equipment-types', methods=['GET'])
def get_equipment_types():
    try:
        with db_connection() as conn:
            types = list_equipment_types(conn)
        return jsonify(types)
    except Exception as e:
        logger.exception('get_equipment_types failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types', methods=['POST'])
def create_equipment_type_route():
    denied = _require_admin()
    if denied:
        return denied
    try:
        data = request.json or {}
        is_valid, err = validate_equipment_type_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_equipment_type_data(data)
        with db_connection() as conn:
            type_id = create_equipment_type(
                conn, clean['code'], clean['name'],
                clean.get('parent_type_id'), clean.get('description')
            )
        return jsonify({'success': True, 'id': type_id, 'message': 'Тип оборудования создан'})
    except Exception as e:
        logger.exception('create_equipment_type_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types/<int:type_id>', methods=['DELETE'])
def delete_equipment_type_route(type_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        with db_connection() as conn:
            if equipment_type_in_use(conn, type_id):
                return jsonify({'error': 'Тип используется оборудованием или имеет дочерние типы — удаление запрещено'}), 400
            deleted = delete_equipment_type(conn, type_id)
        if not deleted:
            return jsonify({'error': 'Тип не найден'}), 404
        return jsonify({'success': True, 'message': 'Тип удалён'})
    except Exception as e:
        logger.exception('delete_equipment_type_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types/<int:type_id>', methods=['PATCH'])
def patch_equipment_type_route(type_id):
    """ТЗ раздел 3.7: inline-редактирование нормы ЗИП прямо в таблице
    сводки — {min_stock_qty}. Отдельный узкий роут (не общий update),
    т.к. это единственное редактируемое после создания поле типа."""
    try:
        data = request.json or {}
        if 'min_stock_qty' not in data:
            return jsonify({'error': 'min_stock_qty обязателен'}), 400
        raw = data['min_stock_qty']
        min_stock_qty = None
        if raw is not None and raw != '':
            try:
                min_stock_qty = int(raw)
            except (TypeError, ValueError):
                return jsonify({'error': 'min_stock_qty должен быть целым числом'}), 400
            if min_stock_qty < 0:
                return jsonify({'error': 'min_stock_qty не может быть отрицательным'}), 400

        with db_connection() as conn:
            if not get_equipment_type(conn, type_id):
                return jsonify({'error': 'Тип не найден'}), 404
            update_equipment_type_min_stock_qty(conn, type_id, min_stock_qty)
        return jsonify({'success': True, 'message': 'Норма ЗИП обновлена'})
    except Exception as e:
        logger.exception('patch_equipment_type_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/stock-summary', methods=['GET'])
def get_stock_summary_route():
    """ТЗ раздел 3.7 — сводка по типам для вкладки 'Учёт ЗИП'."""
    try:
        with db_connection() as conn:
            summary = get_stock_summary(conn)
        return jsonify(summary)
    except Exception as e:
        logger.exception('get_stock_summary_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# Конструктор: пул атрибутов (admin+)
# ---------------------------------------------------------------------

@equipment_bp.route('/attribute-definitions', methods=['GET'])
def get_attribute_definitions():
    try:
        with db_connection() as conn:
            attrs = list_attribute_definitions(conn)
        return jsonify(attrs)
    except Exception as e:
        logger.exception('get_attribute_definitions failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/attribute-definitions', methods=['POST'])
def create_attribute_definition_route():
    denied = _require_admin()
    if denied:
        return denied
    try:
        data = request.json or {}
        is_valid, err = validate_attribute_definition_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_attribute_definition_data(data)
        with db_connection() as conn:
            attr_id = create_attribute_definition(conn, clean)
        return jsonify({'success': True, 'id': attr_id, 'message': 'Атрибут создан'})
    except Exception as e:
        logger.exception('create_attribute_definition_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/attribute-definitions/<int:attribute_id>', methods=['DELETE'])
def delete_attribute_definition_route(attribute_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        with db_connection() as conn:
            if attribute_definition_in_use(conn, attribute_id):
                return jsonify({'error': 'Атрибут назначен хотя бы одному типу — удаление запрещено'}), 400
            deleted = delete_attribute_definition(conn, attribute_id)
        if not deleted:
            return jsonify({'error': 'Атрибут не найден'}), 404
        return jsonify({'success': True, 'message': 'Атрибут удалён'})
    except Exception as e:
        logger.exception('delete_attribute_definition_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# Конструктор: назначение атрибутов типу (admin+)
# ---------------------------------------------------------------------

@equipment_bp.route('/equipment-types/<int:type_id>/attributes', methods=['GET'])
def get_type_attributes(type_id):
    """Возвращает ЭФФЕКТИВНЫЙ (с наследованием) набор — используется и
    конструктором (показать, что унаследовано), и формой добавления
    оборудования (какие поля рисовать)."""
    try:
        with db_connection() as conn:
            if not get_equipment_type(conn, type_id):
                return jsonify({'error': 'Тип не найден'}), 404
            attrs = get_effective_attributes(conn, type_id)
        return jsonify(attrs)
    except Exception as e:
        logger.exception('get_type_attributes failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types/<int:type_id>/own-attributes', methods=['GET'])
def get_type_own_attributes(type_id):
    """Атрибуты, назначенные именно этому типу, БЕЗ наследования —
    для конструктора (что реально настроено на этом уровне)."""
    try:
        with db_connection() as conn:
            if not get_equipment_type(conn, type_id):
                return jsonify({'error': 'Тип не найден'}), 404
            attrs = get_assigned_attributes(conn, type_id)
        return jsonify(attrs)
    except Exception as e:
        logger.exception('get_type_own_attributes failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types/<int:type_id>/attributes', methods=['PUT'])
def set_type_attributes_route(type_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        data = request.json or {}
        assignments = data.get('assignments', [])
        if not isinstance(assignments, list):
            return jsonify({'error': 'assignments должен быть списком'}), 400
        with db_connection() as conn:
            if not get_equipment_type(conn, type_id):
                return jsonify({'error': 'Тип не найден'}), 404
            set_type_attributes(conn, type_id, assignments)
        return jsonify({'success': True, 'message': 'Атрибуты типа обновлены'})
    except Exception as e:
        logger.exception('set_type_attributes_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# Оборудование — CRUD (открыто, как engines; см. docstring модуля)
# ---------------------------------------------------------------------

@equipment_bp.route('/equipment', methods=['GET'])
def get_equipment_list():
    try:
        equipment_type_id = request.args.get('type', type=int)
        search = request.args.get('search', '')
        location_node_id = request.args.get('location_node_id', type=int)
        sort = request.args.get('sort')
        order = request.args.get('order', 'desc')

        # ТЗ раздел 3.4: attr_<key>=<value> в query — только когда выбран
        # конкретный тип; ключи ОБЯЗАТЕЛЬНО сверяются с
        # get_effective_attributes(type_id) до попадания в SQL — не
        # семантика "нельзя, инъекция" (json_extract и так параметризован,
        # см. docstring list_equipment), а "нельзя фильтровать по
        # атрибуту, которого у этого типа вообще нет".
        attr_filters = {}
        if equipment_type_id:
            with db_connection() as conn:
                valid_keys = {a['key'] for a in get_effective_attributes(conn, equipment_type_id)}
            for param_name, value in request.args.items():
                if param_name.startswith('attr_') and value:
                    key = param_name[len('attr_'):]
                    if key in valid_keys:
                        attr_filters[key] = value

        with db_connection() as conn:
            items = list_equipment(
                conn, equipment_type_id=equipment_type_id, search=search,
                location_node_id=location_node_id, sort=sort, order=order,
                attr_filters=attr_filters,
            )
        return jsonify(items)
    except Exception as e:
        logger.exception('get_equipment_list failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment-types/<int:type_id>/show-in-list-attributes', methods=['GET'])
def get_show_in_list_attributes_route(type_id):
    """ТЗ раздел 3.2: 2-3 "главных" атрибута типа для динамических
    колонок таблицы номенклатуры, когда фильтр "Тип" сужен до
    конкретного типа. ОТДЕЛЬНЫЙ роут, а не встроено в ответ
    GET /api/equipment?type=<id> — так GET /api/equipment остаётся
    стабильным "плоским массивом" для всех существующих потребителей
    (например, привязка оборудования к заявке Инцидента через
    /api/equipment?search=... в incidents.js), а не то там объект, то
    там массив в зависимости от наличия query-параметра."""
    try:
        with db_connection() as conn:
            if not get_equipment_type(conn, type_id):
                return jsonify({'error': 'Тип не найден'}), 404
            attrs = get_show_in_list_attributes(conn, type_id)
        return jsonify(attrs)
    except Exception as e:
        logger.exception('get_show_in_list_attributes_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/location-counts', methods=['GET'])
def get_equipment_location_counts_route():
    """{location_node_id: count} — только СОБСТВЕННЫЕ счётчики узлов, без
    суммирования по поддереву (суммирует фронтенд, дерево уже загружено
    целиком — см. equipmentLocationTree.js)."""
    try:
        with db_connection() as conn:
            counts = get_equipment_location_counts(conn)
        return jsonify(counts)
    except Exception as e:
        logger.exception('get_equipment_location_counts_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>', methods=['GET'])
def get_equipment_route(equipment_id):
    try:
        with db_connection() as conn:
            item = get_equipment_by_id(conn, equipment_id)
        if not item:
            return jsonify({'error': 'Оборудование не найдено'}), 404
        return jsonify(item)
    except Exception as e:
        logger.exception('get_equipment_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment', methods=['POST'])
def create_equipment_route():
    try:
        data = request.json or {}
        is_valid, err = validate_equipment_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_equipment_data(data)
        with db_connection() as conn:
            if not get_equipment_type(conn, clean['equipment_type_id']):
                return jsonify({'error': 'Указанный тип оборудования не найден'}), 400
            equipment_id = create_equipment(conn, clean)
        return jsonify({'success': True, 'id': equipment_id, 'message': 'Оборудование добавлено'})
    except Exception as e:
        logger.exception('create_equipment_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>', methods=['PUT'])
def update_equipment_route(equipment_id):
    try:
        data = request.json or {}
        is_valid, err = validate_equipment_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400
        clean = sanitize_equipment_data(data)
        with db_connection() as conn:
            if not get_equipment_by_id(conn, equipment_id):
                return jsonify({'error': 'Оборудование не найдено'}), 404
            update_equipment(conn, equipment_id, clean)
        return jsonify({'success': True, 'message': 'Оборудование обновлено'})
    except Exception as e:
        logger.exception('update_equipment_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>', methods=['DELETE'])
def delete_equipment_route(equipment_id):
    try:
        with db_connection() as conn:
            if not get_equipment_by_id(conn, equipment_id):
                return jsonify({'error': 'Оборудование не найдено'}), 404
            if equipment_referenced_by_incidents(conn, equipment_id):
                return jsonify({'error': 'Оборудование привязано к заявке Инцидента — сначала отвяжите его от заявки'}), 400
            delete_equipment(conn, equipment_id)
        # Фото — вне транзакции БД, ПОСЛЕ успешного удаления записи (тот
        # же порядок, что routes/engines.py::delete_engine ->
        # manager.py::delete_engine_photos_from_disk). Ошибки отдельных
        # файлов не мешают ответу — запись уже удалена, откатывать нечего.
        equipment_manager.delete_equipment_photos_from_disk(equipment_id)
        return jsonify({'success': True, 'message': 'Оборудование удалено'})
    except Exception as e:
        logger.exception('delete_equipment_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# Фото оборудования (modules/photo_manager/equipment_manager.py — ТЗ 3.3)
# ---------------------------------------------------------------------

@equipment_bp.route('/equipment/<int:equipment_id>/photos', methods=['GET'])
def get_equipment_photos_route(equipment_id):
    try:
        with db_connection() as conn:
            if not get_equipment_by_id(conn, equipment_id):
                return jsonify({'error': 'Оборудование не найдено'}), 404
        return jsonify(equipment_manager.get_equipment_photos(equipment_id))
    except Exception as e:
        logger.exception('get_equipment_photos_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>/photos', methods=['POST'])
def upload_equipment_photos_route(equipment_id):
    try:
        with db_connection() as conn:
            if not get_equipment_by_id(conn, equipment_id):
                return jsonify({'error': 'Оборудование не найдено'}), 404
        files = request.files.getlist('photos')
        return equipment_manager.upload_equipment_photos(equipment_id, files)
    except Exception as e:
        logger.exception('upload_equipment_photos_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>/photos/<filename>', methods=['PUT'])
def replace_equipment_photo_route(equipment_id, filename):
    try:
        with db_connection() as conn:
            if not get_equipment_by_id(conn, equipment_id):
                return jsonify({'error': 'Оборудование не найдено'}), 404
        file = request.files.get('photo')
        return equipment_manager.replace_equipment_photo(equipment_id, filename, file)
    except Exception as e:
        logger.exception('replace_equipment_photo_route failed')
        return jsonify({'error': str(e)}), 500


@equipment_bp.route('/equipment/<int:equipment_id>/photos/<filename>', methods=['DELETE'])
def delete_equipment_photo_route(equipment_id, filename):
    return equipment_manager.delete_equipment_photo(equipment_id, filename)


# ---------------------------------------------------------------------
# Экспорт в Excel (ТЗ раздел 3.6) — постраничная карточка с фото,
# лимит 100 записей за раз проверяется здесь (HTTP-слой), сама
# export_service ничего не ограничивает (тот же паттерн, что и у
# incident_ticket_routes.py::export_tickets_route).
# ---------------------------------------------------------------------

EQUIPMENT_EXPORT_MAX_IDS = 100


@equipment_bp.route('/equipment/export', methods=['POST'])
def export_equipment_route():
    try:
        data = request.json or {}
        ids = data.get('ids') or []
        if not ids:
            return jsonify({'error': 'Не выбрано ни одной записи оборудования'}), 400
        if len(ids) > EQUIPMENT_EXPORT_MAX_IDS:
            return jsonify({'error': f'Слишком много записей за раз (максимум {EQUIPMENT_EXPORT_MAX_IDS})'}), 400

        with db_connection() as conn:
            xlsx_bytes = export_service.export_equipment_to_xlsx(conn, [int(i) for i in ids])

        filename = f"equipment_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        logger.exception('export_equipment_route failed')
        return jsonify({'error': str(e)}), 500
