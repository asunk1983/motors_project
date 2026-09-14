"""Централизованные настройки проекта.

Раньше константы (DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, ...) дублировались
в modules/db.py и modules/engine_parser/parser.py. Теперь один источник правды.
app.py и модули импортируют отсюда: from config.settings import DB_PATH, ...
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default):
    """Путь из переменной окружения (для изоляции e2e-тестов).

    Все пути проекта можно переопределить переменными MOTORS_* (см.
    каждый _env-вызов ниже). Если переменная не задана — возвращается
    прежний дефолт, поэтому продовое поведение не меняется: systemd-юнит
    прода задаёт только PATH и FLASK_ENV, MOTORS_* в проде нигде не
    используется.
    """
    return os.environ.get(name, str(default))


DB_PATH = _env('MOTORS_DB_PATH', BASE_DIR / 'engine_data.db')
MOTORS_FOLDER = _env('MOTORS_MOTORS_FOLDER', BASE_DIR / 'motors')
PHOTOS_FOLDER = _env('MOTORS_PHOTOS_FOLDER', BASE_DIR / 'photos')
# Фото-вложения заявок "Инцидентов" — отдельная папка от PHOTOS_FOLDER
# (тот принадлежит двигателям, ID{engine_id}_{n}.ext) во избежание
# коллизий имён файлов между двумя разными сущностями с ID-неймингом.
INCIDENT_PHOTOS_FOLDER = _env('MOTORS_INCIDENT_PHOTOS_FOLDER', BASE_DIR / 'PhotoI')
# Фото номенклатуры оборудования (ТЗ "Инциденты + Оборудование", раздел 3.3) —
# та же логика обособления, что и у PhotoI.
EQUIPMENT_PHOTOS_FOLDER = _env('MOTORS_EQUIPMENT_PHOTOS_FOLDER', BASE_DIR / 'PhotoE')

# Список фото-папок, которые участвуют в backup/restore/clear_database.
# Перенесено сюда из modules/backup_system/backup.py — раньше жило только
# там, что противоречило конвенции "config/settings.py — единственный
# источник правды" (см. докстринг файла выше) и однажды уже приводило к
# багу: при добавлении EQUIPMENT_PHOTOS_FOLDER (PhotoE) в 2026-09-01
# clear_database() из routes/import_routes.py не узнал о новой папке и
# 5 дней молча не очищал её при сбросе БД (исправлено в 2026-09-04).
# Префикс — это имя каталога верхнего уровня внутри zip-архива бэкапа
# (совпадает с именем самой папки на диске).
#
# ВАЖНО: при добавлении новой *_PHOTOS_FOLDER константы выше — сразу
# добавляйте её и сюда, иначе backup/restore её подхватят (они уже
# устойчивы к этому), а вот clear_database() — нет, если где-то
# появится второй хардкод-список вместо использования этого.
PHOTO_FOLDERS = [
    ('photos', PHOTOS_FOLDER),
    ('PhotoI', INCIDENT_PHOTOS_FOLDER),
    ('PhotoE', EQUIPMENT_PHOTOS_FOLDER),
]

BACKUPS_FOLDER = _env('MOTORS_BACKUPS_FOLDER', BASE_DIR / 'backups')
BACKUP_STAGING_FOLDER = _env('MOTORS_BACKUP_STAGING_FOLDER', BASE_DIR / 'backup_staging')
CONFIG_DIR = _env('MOTORS_CONFIG_DIR', BASE_DIR / 'config')
FILE_USERS = _env('MOTORS_FILE_USERS', BASE_DIR / 'config' / 'users.json')
FILE_TOKENS = _env('MOTORS_FILE_TOKENS', BASE_DIR / 'config' / 'tokens.json')

# JSON-хранилища вкладки «Инфо»: e2e перенаправляет их во временную data-папку,
# чтобы тесты не писали в боевые data/changelog.json и data/wishlist.json.
DATA_DIR = _env('MOTORS_DATA_DIR', BASE_DIR / 'data')
CHANGELOG_JSON_PATH = str(Path(DATA_DIR) / 'changelog.json')
WISHLIST_JSON_PATH = str(Path(DATA_DIR) / 'wishlist.json')

ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# --- Импорт ---
MAX_WORKERS = 4
LOG_FILE = _env('MOTORS_LOG_FILE', BASE_DIR / 'app.log')
