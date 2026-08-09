"""Маршруты двигателей: CRUD + modes + works.

Вынесено из app.py. Использует repositories/ и schemas/.
"""
import logging
from flask import Blueprint, request, jsonify

from modules.db import db_connection
from modules.photo_manager import manager as photo_manager
from repositories.engine_repo import (
    get_by_id, get_with_details, get_all, count_all, get_locations_tree,
    create as engine_create, update as engine_update,
    delete as engine_delete, update_photo_count,
)
from repositories.mode_repo import replace_all as replace_modes
from repositories.work_repo import replace_all as replace_works
from schemas.engine_schema import validate_engine_payload, sanitize_engine_data

logger = logging.getLogger(__name__)
engines_bp = Blueprint('engines', __name__, url_prefix='/api')


@engines_bp.route('/engines', methods=['GET'])
def list_engines():
    try:
        search = request.args.get('search', '')
        search_field = request.args.get('search_field', 'all')
        sort_by = request.args.get('sort_by', 'location')
        sort_order = request.args.get('sort_order', 'ASC').upper()
        # workshop/location — точный фильтр от дерева навигации (не LIKE).
        # request.args.get возвращает None, если параметра нет в URL вообще
        # (фильтр не активен), и '' если передан пустой (узел "Без цеха").
        workshop = request.args.get('workshop', None)
        location = request.args.get('location', None)

        # Собираем внутренний параметр сортировки из sort_by + sort_order
        # (front отправляет их отдельными параметрами, а repository
        #  оживает единый токен вроде 'location_asc').
        sort_order = sort_order if sort_order in ('ASC', 'DESC') else 'ASC'
        sort = f'{sort_by}_{sort_order.lower()}'

        with db_connection() as conn:
            engines = get_all(conn, limit=10000, offset=0, sort=sort,
                              search_field=search_field, search_query=search,
                              workshop=workshop, location=location)

        return jsonify(engines)
    except Exception as e:
        logger.exception('list_engines failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/locations-tree', methods=['GET'])
def locations_tree():
    try:
        with db_connection() as conn:
            tree = get_locations_tree(conn)
        return jsonify(tree)
    except Exception as e:
        logger.exception('locations_tree failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine/<int:engine_id>', methods=['GET'])
def get_engine(engine_id):
    try:
        with db_connection() as conn:
            engine = get_with_details(conn, engine_id)
        if not engine:
            return jsonify({'error': 'Двигатель не найден'}), 404
        return jsonify(engine)
    except Exception as e:
        logger.exception('get_engine failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine', methods=['POST'])
def create_engine():
    try:
        data = request.json or {}
        is_valid, err = validate_engine_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_engine_data(data)
        with db_connection() as conn:
            engine_id = engine_create(conn, clean)
            if data.get('modes'):
                replace_modes(conn, engine_id, data['modes'])
            if data.get('works'):
                replace_works(conn, engine_id, data['works'])

        return jsonify({'success': True, 'id': engine_id, 'message': 'Двигатель создан'})
    except Exception as e:
        logger.exception('create_engine failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine/<int:engine_id>', methods=['PUT'])
def update_engine(engine_id):
    try:
        data = request.json or {}
        is_valid, err = validate_engine_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_engine_data(data)
        with db_connection() as conn:
            if not get_by_id(conn, engine_id):
                return jsonify({'error': 'Двигатель не найден'}), 404
            engine_update(conn, engine_id, clean)
            # Единая точка сохранения карточки: характеристики + режимы +
            # работы одним запросом (см. engineCard.js::saveDetailEdit).
            # 'modes'/'works' в data — полная замена списка (DELETE+INSERT,
            # как и было у отдельных /modes и /works). Проверяем через
            # 'in', а не truthy — иначе отправка пустого списка (пользователь
            # удалил все строки и сохранил) не сотрёт старые записи.
            if 'modes' in data:
                replace_modes(conn, engine_id, data['modes'])
            if 'works' in data:
                replace_works(conn, engine_id, data['works'])

        return jsonify({'success': True, 'message': 'Двигатель обновлён'})
    except Exception as e:
        logger.exception('update_engine failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine/<int:engine_id>', methods=['DELETE'])
def delete_engine(engine_id):
    try:
        # Сначала пытаемся удалить фотографии с диска
        removed, errors = photo_manager.delete_engine_photos_from_disk(engine_id)
        if errors:
            # Если не удалось удалить некоторые фотографии, не удаляем запись из БД
            logger.warning('Не удалось удалить часть фото двигателя %s: %s', engine_id, errors)
            return jsonify({'error': 'Не удалось удалить фотографии двигателя'}), 500

        # Если фотографии успешно удалены, удаляем запись из БД
        with db_connection() as conn:
            if not get_by_id(conn, engine_id):
                # Двигатель уже был удален (возможно, конкурентным запросом)
                return jsonify({'error': 'Двигатель не найден'}), 404
            engine_delete(conn, engine_id)

        return jsonify({'success': True, 'message': 'Двигатель удалён'})
    except Exception as e:
        logger.exception('delete_engine failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine/<int:engine_id>/modes', methods=['PUT'])
def update_engine_modes(engine_id):
    try:
        data = request.json or {}
        modes = data.get('modes', [])
        for mode in modes:
            err = validate_engine_payload({'modes': [mode]})[1]
            if err:
                return jsonify({'error': err}), 400

        with db_connection() as conn:
            if not get_by_id(conn, engine_id):
                return jsonify({'error': 'Двигатель не найден'}), 404
            replace_modes(conn, engine_id, modes)

        return jsonify({'success': True, 'message': 'Режимы работы обновлены'})
    except Exception as e:
        logger.exception('update_engine_modes failed')
        return jsonify({'error': str(e)}), 500


@engines_bp.route('/engine/<int:engine_id>/works', methods=['PUT'])
def update_engine_works(engine_id):
    try:
        data = request.json or {}
        works = data.get('works', [])
        for work in works:
            err = validate_engine_payload({'works': [work]})[1]
            if err:
                return jsonify({'error': err}), 400

        with db_connection() as conn:
            if not get_by_id(conn, engine_id):
                return jsonify({'error': 'Двигатель не найден'}), 404
            replace_works(conn, engine_id, works)

        return jsonify({'success': True, 'message': 'Произведённые работы обновлены'})
    except Exception as e:
        logger.exception('update_engine_works failed')
        return jsonify({'error': str(e)}), 500
