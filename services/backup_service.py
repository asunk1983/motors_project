"""Сервис бэкапов.

Делегирует работу модулю modules/backup_system/backup.py, но добавляет
слоистую абстракцию: сервис знает о пути к файлам и staging-папке,
а backup.py — о деталях zip/SQLite Online Backup API.
"""
import logging

from config.settings import DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER

logger = logging.getLogger(__name__)


def create_backup() -> dict:
    """Создать резервную копию.

    Возвращает dict: {'filename': ..., 'path': ..., 'size': ..., 'manifest': ...}
    """
    from modules.backup_system import backup as backup_module
    return backup_module.create_backup()


def list_backups() -> list[dict]:
    """Список доступных бэкапов в backups/."""
    from modules.backup_system import backup as backup_module
    return backup_module.list_backups()


def inspect_uploaded_backup(zip_path: str) -> dict:
    """Проверить загруженный zip: manifest.json + чексуммы.

    Возвращает {valid: bool, manifest: dict, errors: [str, ...]}.
    НЕ трогает рабочую БД.
    """
    from modules.backup_system import backup as backup_module
    return backup_module.inspect_uploaded_backup(zip_path)


def restore_backup(zip_path: str) -> dict:
    """Атомарно восстановить БД и фото из zip.

    - Сначала копирует текущую engine_data.db во временный файл (rollback point)
    - Извлекает engine_data.db и photos/ из zip во staging
    - Пересчитывает чексуммы и сверяет с manifest.json
    - Если всё ОК — заменяет рабочие файлы
    - При ошибке — откатывает на rollback point

    Возвращает {success: bool, error: str (опцIONALно)}.
    """
    from modules.backup_system import backup as backup_module
    return backup_module.restore_backup(zip_path)


def download_backup(filename: str) -> str:
    """Получить путь к файлу бэкапа для скачивания."""
    from modules.backup_system import backup as backup_module
    return backup_module.download_backup(filename)


def delete_backup(filename: str) -> bool:
    """Удалить файл бэкапа."""
    from modules.backup_system import backup as backup_module
    return backup_module.delete_backup(filename)
