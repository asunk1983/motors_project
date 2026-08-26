"""Маршрут статуса приложения: счётчики двигателей, размер БД, файлы в папке.
Вынесено из app.py.
"""
import os
import sys
import glob
import sqlite3
import flask
from flask import Blueprint, jsonify

from modules.db import db_connection, DB_PATH, MOTORS_FOLDER
from repositories import equipment_repo, incident_ticket_repo
from modules.photo_manager import equipment_manager, incident_manager

status_bp = Blueprint('status', __name__, url_prefix='/api')

APP_VERSION = '2.0'


@status_bp.route('/status', methods=['GET'])
def get_status():
    version_info = {
        'app_version': APP_VERSION,
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'sqlite_version': sqlite3.sqlite_version,
    }
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

        # Дашборд-счётчики Инцидентов/Оборудования (ТЗ раздел 4) — та же
        # db_connection(), что и выше, отдельным блоком: не хотим уронить
        # уже существующий ответ, если в новых модулях что-то пойдёт не
        # так (см. except ниже — сначала пробуем полный ответ, при сбое
        # именно этого блока отдаём хотя бы то, что было раньше).
        try:
            with db_connection() as conn:
                equipment_count = equipment_repo.count_all(conn)
                incident_count = incident_ticket_repo.count_all(conn)
                incident_open_count = incident_ticket_repo.count_by_status(conn, 'in_progress')
            equipment_photos_count = equipment_manager.count_all_photos()
            incident_photos_count = incident_manager.count_all_photos()
        except Exception:
            # Инциденты/Оборудование ещё не готовы (например, БД не
            # мигрирована) — не должны ронять уже рабочий /api/status
            # для двигателей.
            equipment_count = incident_count = incident_open_count = 0
            equipment_photos_count = incident_photos_count = 0

        return jsonify({
            'has_data': engine_count > 0,
            'engine_count': engine_count,
            'modes_count': modes_count,
            'works_count': works_count,
            'photos_count': photos_count,
            'files_in_folder': len(motor_files),
            'db_size_bytes': db_size_bytes,
            'db_size_label': db_size_label,
            'equipment_count': equipment_count,
            'equipment_photos_count': equipment_photos_count,
            'incident_count': incident_count,
            'incident_open_count': incident_open_count,
            'incident_photos_count': incident_photos_count,
            **version_info,
        })
    except Exception as e:
        return jsonify({'has_data': False, 'error': str(e), **version_info})

