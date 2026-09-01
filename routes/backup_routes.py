"""Маршруты бэкапа: создание, список, inspect-upload, restore, confirm-restore,
скачивание, удаление.

Вынесено из app.py. Делегирует логику в modules.backup_system.backup.
"""
import os
from flask import Blueprint, request, jsonify, send_file

from modules import db as db_module
from modules.backup_system import backup as backup_module

backup_bp = Blueprint('backup', __name__, url_prefix='/api/backup')


@backup_bp.route('/list', methods=['GET'])
def list_backups():
    try:
        backups = backup_module.list_backups()
        return jsonify(backups)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/create', methods=['POST'])
def create_backup():
    """Создаёт резервную копию и отдаёт ZIP-файлом (binary blob).

    Frontend (backupManager.js) вызывает response.blob() и парсит
    Content-Disposition для имени файла — поэтому роут возвращает
    send_file с as_attachment=True, а не JSON-метаданные."""
    try:
        result = backup_module.create_backup()
        path = result['path']
        filename = result['filename']
        return send_file(
            path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/inspect-upload', methods=['POST'])
def inspect_uploaded_backup():
    """Принимает загруженный zip во временный файл, читает manifest.json
    и сверяет SHA256-чексуммы. НЕ трогает рабочую БД."""
    try:
        # Принимаем файл по ключу 'file' (стандарт Flask) или 'backup' (frontend backupManager.js)
        f = request.files.get('file') or request.files.get('backup')
        if not f or not f.filename:
            return jsonify({'error': 'Файл не передан'}), 400
        if not f.filename.endswith('.zip'):
            return jsonify({'error': 'Только zip-файлы'}), 400

        # Сохраняем во staging
        staging_folder = db_module.BACKUP_STAGING_FOLDER
        os.makedirs(staging_folder, exist_ok=True)
        staging_path = os.path.join(staging_folder, f.filename)
        f.save(staging_path)

        result = backup_module.inspect_uploaded_backup(staging_path)
        # staging_id = имя файла в staging — frontend использует его для последующего confirm-restore
        result['staging_id'] = f.filename
        result['filename'] = f.filename
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    """Восстанавливает БД и фото из zip.

    Сначала сверяет чексуммы (inspect), затем атомарно применяет.
    Ищет файл в staging, а если там нет — в backups/."""
    try:
        safe = backup_module._safe_backup_filename(filename)
        if not safe:
            return jsonify({'error': 'Недопустимое имя файла'}), 400

        # Ищем zip: сначала в staging, затем в backups/
        staging_path = os.path.join(db_module.BACKUP_STAGING_FOLDER, safe)
        backups_path = os.path.join(db_module.BACKUPS_FOLDER, safe)
        file_path = None
        if os.path.exists(staging_path):
            file_path = staging_path
        elif os.path.exists(backups_path):
            file_path = backups_path
        if file_path is None:
            return jsonify({'error': 'Файл не найден в staging или backups'}), 404

        # Шаг 1: проверка чексумм — НЕ трогаем рабочую БД
        result = backup_module.inspect_uploaded_backup(file_path)
        if not result['valid']:
            return jsonify({
                'error': 'Чексуммы не совпадают. Восстановление отклонено.',
                'details': result['errors'],
            }), 422

        # Шаг 2: атомарное восстановление с rollback-точкой
        restore_result = backup_module.restore_backup(file_path)

        return jsonify({
            'success': True,
            'message': 'Восстановление завершено успешно',
            'restored_files': (restore_result or {}).get('restored_files', {}),
        })
    except RuntimeError as e:
        # Ошибка лока (другой restore уже выполняется)
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/confirm-restore', methods=['POST'])
def confirm_restore_uploaded_backup():
    """Подтверждение восстановления после staging.

    Повторно сверяет чексуммы (на всякий случай, если кто-то подменил
    файл в staging между inspect-upload и confirm-restore), затем
    атомарно применяет backup с rollback-точкой.
    """
    try:
        data = request.json or {}
        # Принимаем 'filename' (стандарт) или 'staging_id' (frontend backupManager.js)
        filename = data.get('filename') or data.get('staging_id') or request.form.get('filename')
        if not filename:
            return jsonify({'error': 'filename или staging_id обязателен'}), 400

        safe = backup_module._safe_backup_filename(filename)
        if not safe:
            return jsonify({'error': 'Недопустимое имя файла'}), 400

        staging_path = os.path.join(db_module.BACKUP_STAGING_FOLDER, safe)
        if not os.path.exists(staging_path):
            return jsonify({'error': 'Файл не найден в staging'}), 404

        # Повторная проверка чексумм — НЕ трогаем рабочую БД
        result = backup_module.inspect_uploaded_backup(staging_path)
        if not result['valid']:
            return jsonify({
                'error': 'Чексуммы не совпадают. Восстановление отклонено.',
                'details': result['errors'],
            }), 422

        # Атомарное восстановление с rollback-точкой + файловый лок
        restore_result = backup_module.restore_backup(staging_path)

        # Очищаем staging после успешного restore
        try:
            os.remove(staging_path)
        except OSError:
            pass

        return jsonify({
            'success': True,
            'message': 'Восстановление завершено успешно',
            'restored_files': (restore_result or {}).get('restored_files', {}),
        })
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/download/<filename>', methods=['GET'])
def download_backup(filename):
    try:
        path = backup_module.download_backup(filename)
        if not path:
            return jsonify({'error': 'Файл не найден'}), 404
        return send_file(path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/delete/<filename>', methods=['POST'])
def delete_backup(filename):
    try:
        ok = backup_module.delete_backup(filename)
        if not ok:
            return jsonify({'error': 'Файл не найден'}), 404
        return jsonify({'success': True, 'message': 'Бэкап удалён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Алиас для frontend: backupManager.js deleteBackupFile() отправляет
# DELETE /api/backup/<filename> (без сегмента /delete/).
# Сохраняем старый POST /api/backup/delete/<filename> для обратной совместимости.
@backup_bp.route('/<filename>', methods=['DELETE'])
def delete_backup_http_delete(filename):
    try:
        safe = backup_module._safe_backup_filename(filename)
        if not safe:
            return jsonify({'error': 'Недопустимое имя файла'}), 400
        ok = backup_module.delete_backup(safe)
        if not ok:
            return jsonify({'error': 'Файл не найден'}), 404
        return jsonify({'success': True, 'message': 'Бэкап удалён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
