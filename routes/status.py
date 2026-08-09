"""Маршрут статуса приложения: счётчики двигателей, размер БД, файлы в папке.

Вынесено из app.py.
"""
import os
import glob
from flask import Blueprint, jsonify

from modules.db import db_connection, DB_PATH, MOTORS_FOLDER

status_bp = Blueprint('status', __name__, url_prefix='/api')


@status_bp.route('/status', methods=['GET'])
def get_status():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    (SELECT COUNT(*) FROM engines) AS engine_count,
                    (SELECT COUNT(*) FROM operating_modes) AS modes_count,
                    (SELECT COUNT(*) FROM maintenance_works) AS works_count,
                    (SELECT COALESCE(SUM(photo_count), 0) FROM engines) AS photos_count
            ''')
            row = cursor.fetchone()
            engine_count, modes_count, works_count, photos_count = row

        motor_files = []
        if os.path.exists(MOTORS_FOLDER):
            for ext in ['*.xlsx', '*.xls']:
                motor_files.extend(glob.glob(os.path.join(MOTORS_FOLDER, ext)))

        db_size_bytes = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        if db_size_bytes >= 1024 * 1024:
            db_size_label = f"{db_size_bytes / (1024 * 1024):.1f} MB"
        else:
            db_size_label = f"{db_size_bytes / 1024:.1f} KB"

        return jsonify({
            'has_data': engine_count > 0,
            'engine_count': engine_count,
            'modes_count': modes_count,
            'works_count': works_count,
            'photos_count': photos_count,
            'files_in_folder': len(motor_files),
            'db_size_bytes': db_size_bytes,
            'db_size_label': db_size_label
        })
    except Exception as e:
        return jsonify({'has_data': False, 'error': str(e)})
