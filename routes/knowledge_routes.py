"""Маршруты базы знаний: справочники (failure_mode/failure_cause) + статьи.

Использует repositories/knowledge_repo.py и schemas/knowledge_schema.py.
Стиль — как в routes/engines.py.
"""
import logging
from flask import Blueprint, request, jsonify

from modules.db import db_connection
from routes.auth import _require_superadmin
from repositories.knowledge_repo import (
    list_failure_modes, list_failure_causes,
    create_failure_mode, create_failure_cause,
    failure_mode_in_use, failure_cause_in_use,
    delete_failure_mode, delete_failure_cause,
    get_article_by_id, list_articles, create_article, update_article, delete_article,
)
from schemas.knowledge_schema import (
    validate_article_payload, sanitize_article_data,
    validate_dictionary_payload, sanitize_dictionary_data,
)

logger = logging.getLogger(__name__)
knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api')


# База знаний (статьи + управление справочниками) пока не привязана к
# двигателям и не нужна большинству сотрудников — доступ строго superadmin
# (не admin, см. _require_superadmin в routes/auth.py). Один общий guard
# на весь blueprint, а не per-route проверка.
#
# ИСКЛЮЧЕНИЕ: чтение самих справочников failure_mode/failure_cause (не
# управление ими, не статьи) — открыто всем. Эти два GET нужны ЛЮБОМУ
# пользователю при подтверждении заявки как отказа (routes/ticket_routes.py
# ::confirm_failure_route), а тикеты — открытый всем функционал. Закрыть
# их вместе с остальной базой знаний значило бы сломать создание заявок
# всем, кроме superadmin.
_PUBLIC_DICTIONARY_READ_PATHS = ('/api/knowledge/failure-modes', '/api/knowledge/failure-causes')


@knowledge_bp.before_request
def _knowledge_require_superadmin():
    if request.method == 'GET' and request.path in _PUBLIC_DICTIONARY_READ_PATHS:
        return None
    return _require_superadmin()


# ---------------------------------------------------------------------
# Справочники
# ---------------------------------------------------------------------

@knowledge_bp.route('/knowledge/failure-modes', methods=['GET'])
def get_failure_modes():
    try:
        with db_connection() as conn:
            modes = list_failure_modes(conn)
        return jsonify(modes)
    except Exception as e:
        logger.exception('get_failure_modes failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/failure-modes', methods=['POST'])
def create_failure_mode_route():
    try:
        data = request.json or {}
        is_valid, err = validate_dictionary_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_dictionary_data(data)
        with db_connection() as conn:
            mode_id = create_failure_mode(conn, clean['code'], clean['name'], clean.get('description'))

        return jsonify({'success': True, 'id': mode_id, 'message': 'Режим отказа создан'})
    except Exception as e:
        logger.exception('create_failure_mode_route failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/failure-modes/<int:mode_id>', methods=['DELETE'])
def delete_failure_mode_route(mode_id):
    try:
        with db_connection() as conn:
            if failure_mode_in_use(conn, mode_id):
                return jsonify({'error': 'Режим отказа используется в записях ТО или статьях — удаление запрещено'}), 400
            deleted = delete_failure_mode(conn, mode_id)
        if not deleted:
            return jsonify({'error': 'Режим отказа не найден'}), 404
        return jsonify({'success': True, 'message': 'Режим отказа удалён'})
    except Exception as e:
        logger.exception('delete_failure_mode_route failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/failure-causes', methods=['GET'])
def get_failure_causes():
    try:
        with db_connection() as conn:
            causes = list_failure_causes(conn)
        return jsonify(causes)
    except Exception as e:
        logger.exception('get_failure_causes failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/failure-causes', methods=['POST'])
def create_failure_cause_route():
    try:
        data = request.json or {}
        is_valid, err = validate_dictionary_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_dictionary_data(data)
        with db_connection() as conn:
            cause_id = create_failure_cause(conn, clean['code'], clean['name'], clean.get('description'))

        return jsonify({'success': True, 'id': cause_id, 'message': 'Причина создана'})
    except Exception as e:
        logger.exception('create_failure_cause_route failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/failure-causes/<int:cause_id>', methods=['DELETE'])
def delete_failure_cause_route(cause_id):
    try:
        with db_connection() as conn:
            if failure_cause_in_use(conn, cause_id):
                return jsonify({'error': 'Причина используется в записях ТО или статьях — удаление запрещено'}), 400
            deleted = delete_failure_cause(conn, cause_id)
        if not deleted:
            return jsonify({'error': 'Причина не найдена'}), 404
        return jsonify({'success': True, 'message': 'Причина удалена'})
    except Exception as e:
        logger.exception('delete_failure_cause_route failed')
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------
# Статьи базы знаний
# ---------------------------------------------------------------------

@knowledge_bp.route('/knowledge/articles', methods=['GET'])
def get_articles():
    try:
        symptom_query = request.args.get('search', '')
        equipment_type_id = request.args.get('equipment_type', type=int)
        with db_connection() as conn:
            articles = list_articles(conn, symptom_query=symptom_query, equipment_type_id=equipment_type_id)
        return jsonify(articles)
    except Exception as e:
        logger.exception('get_articles failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/article/<int:article_id>', methods=['GET'])
def get_article(article_id):
    try:
        with db_connection() as conn:
            article = get_article_by_id(conn, article_id)
        if not article:
            return jsonify({'error': 'Статья не найдена'}), 404
        return jsonify(article)
    except Exception as e:
        logger.exception('get_article failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/article', methods=['POST'])
def create_article_route():
    try:
        data = request.json or {}
        is_valid, err = validate_article_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_article_data(data)
        with db_connection() as conn:
            article_id = create_article(conn, clean)

        return jsonify({'success': True, 'id': article_id, 'message': 'Статья создана'})
    except Exception as e:
        logger.exception('create_article_route failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/article/<int:article_id>', methods=['PUT'])
def update_article_route(article_id):
    try:
        data = request.json or {}
        is_valid, err = validate_article_payload(data)
        if not is_valid:
            return jsonify({'error': err}), 400

        clean = sanitize_article_data(data)
        with db_connection() as conn:
            if not get_article_by_id(conn, article_id):
                return jsonify({'error': 'Статья не найдена'}), 404
            update_article(conn, article_id, clean)

        return jsonify({'success': True, 'message': 'Статья обновлена'})
    except Exception as e:
        logger.exception('update_article_route failed')
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/knowledge/article/<int:article_id>', methods=['DELETE'])
def delete_article_route(article_id):
    try:
        with db_connection() as conn:
            if not get_article_by_id(conn, article_id):
                return jsonify({'error': 'Статья не найдена'}), 404
            delete_article(conn, article_id)

        return jsonify({'success': True, 'message': 'Статья удалена'})
    except Exception as e:
        logger.exception('delete_article_route failed')
        return jsonify({'error': str(e)}), 500
