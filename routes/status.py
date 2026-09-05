"""Маршрут статуса приложения: счётчики двигателей, размер БД, файлы в папке.
Вынесено из app.py.
"""
import os
import sys
import glob
import sqlite3
import subprocess
import flask
from flask import Blueprint, jsonify

from modules.db import db_connection, DB_PATH, MOTORS_FOLDER
from repositories import equipment_repo, incident_ticket_repo
from modules.photo_manager import equipment_manager, incident_manager

status_bp = Blueprint('status', __name__, url_prefix='/api')


# Читаем версию из version.txt в корне проекта (один раз при старте модуля)
_VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'version.txt')

def _read_app_version() -> str:
    """Возвращает версию из version.txt или fallback."""
    try:
        with open(_VERSION_FILE, 'r', encoding='utf-8') as f:
            v = f.read().strip()
            return v if v else 'unknown'
    except Exception:
        return 'unknown'


def _read_git_commit() -> str | None:
    """Возвращает короткий хэш текущего коммита или None, если git недоступен."""
    try:
        # cwd = корень проекта (родительская директория routes/)
        repo_root = os.path.dirname(os.path.dirname(__file__))
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


APP_VERSION = _read_app_version()
GIT_COMMIT = _read_git_commit()


@status_bp.route('/status', methods=['GET'])
def get_status():
    version_info = {
        'app_version': APP_VERSION,
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'sqlite_version': sqlite3.sqlite_version,
        'git_commit': GIT_COMMIT,
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

