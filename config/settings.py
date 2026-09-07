"""Централизованные настройки проекта.

Раньше константы (DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, ...) дублировались
в modules/db.py и modules/engine_parser/parser.py. Теперь один источник правды.
app.py и модули импортируют отсюда: from config.settings import DB_PATH, ...
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = str(BASE_DIR / 'engine_data.db')
MOTORS_FOLDER = str(BASE_DIR / 'motors')
PHOTOS_FOLDER = str(BASE_DIR / 'photos')
# Фото-вложения заявок "Инцидентов" — отдельная папка от PHOTOS_FOLDER
# (тот принадлежит двигателям, ID{engine_id}_{n}.ext) во избежание
# коллизий имён файлов между двумя разными сущностями с ID-неймингом.
INCIDENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoI')
# Фото номенклатуры оборудования (ТЗ "Инциденты + Оборудование", раздел 3.3) —
# та же логика обособления, что и у PhotoI.
EQUIPMENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoE')

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

BACKUPS_FOLDER = str(BASE_DIR / 'backups')
BACKUP_STAGING_FOLDER = str(BASE_DIR / 'backup_staging')
CONFIG_DIR = str(BASE_DIR / 'config')
FILE_USERS = str(BASE_DIR / 'config' / 'users.json')
FILE_TOKENS = str(BASE_DIR / 'config' / 'tokens.json')

ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# --- Импорт ---
MAX_WORKERS = 4
LOG_FILE = str(BASE_DIR / 'app.log')
