"""Маршруты фотографий: получение, загрузка, удаление, замена.

Тонкая HTTP-обёртка — вся файловая логика в modules/photo_manager/manager.py
(единственный источник правды, чтобы не плодить дублирующиеся копии, как
было раньше). Здесь только разбор запроса и формирование ответа.
"""
from flask import Blueprint, request

from modules import db as db_module
from modules.photo_manager import manager as photo_manager

db_connection = db_module.db_connection

photos_bp = Blueprint('photos', __name__, url_prefix='/api')


@photos_bp.route('/engine/<int:engine_id>/photos', methods=['GET'])
def get_engine_photos(engine_id):
    try:
        return photo_manager.get_engine_photos(engine_id)
    except Exception:
        return [], 200


@photos_bp.route('/photos/<filename>', methods=['GET'])
def get_photo(filename):
    try:
        return photo_manager.get_photo(filename)
    except Exception as e:
        return {'error': str(e)}, 500


@photos_bp.route('/engine/<int:engine_id>/photos', methods=['POST'])
def upload_engine_photos(engine_id):
    try:
        files = request.files.getlist('photos')
        if not files:
            return {'error': 'Файлы не переданы'}, 400
        with db_connection() as conn:
            return photo_manager.upload_engine_photos(conn, engine_id, files)
    except Exception as e:
        return {'error': str(e)}, 500


@photos_bp.route('/engine/<int:engine_id>/photos/<filename>', methods=['DELETE'])
def delete_engine_photo(engine_id, filename):
    try:
        with db_connection() as conn:
            return photo_manager.delete_engine_photo(conn, engine_id, filename)
    except Exception as e:
        return {'error': str(e)}, 500


@photos_bp.route('/engine/<int:engine_id>/photos/<filename>', methods=['PUT'])
def replace_engine_photo(engine_id, filename):
    try:
        f = request.files.get('photo')
        return photo_manager.replace_engine_photo(engine_id, filename, f)
    except Exception as e:
        return {'error': str(e)}, 500
