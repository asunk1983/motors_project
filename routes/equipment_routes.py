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
import logging
from flask import Blueprint, request, jsonify

from modules.db import db_connection
from routes.auth import _require_admin
from repositories.equipment_repo import (
    list_equipment_types, get_equipment_type, create_equipment_type,
    equipment_type_in_use, delete_equipment_type,
    list_attribute_definitions, create_attribute_definition,
    attribute_definition_in_use, delete_attribute_definition,
    get_assigned_attributes, get_effective_attributes, set_type_attributes,
    get_equipment_by_id, list_equipment, create_equipment, update_equipment, delete_equipment,
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
        with db_connection() as conn:
            items = list_equipment(conn, equipment_type_id=equipment_type_id, search=search)
        return jsonify(items)
    except Exception as e:
        logger.exception('get_equipment_list failed')
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
            delete_equipment(conn, equipment_id)
        return jsonify({'success': True, 'message': 'Оборудование удалено'})
    except Exception as e:
        logger.exception('delete_equipment_route failed')
        return jsonify({'error': str(e)}), 500
