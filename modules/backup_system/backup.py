# modules/backup_system/backup.py
"""Резервное копирование и восстановление: сборка zip (БД + фото + манифест),
сохранение на сервере с ограничением числа копий, применение zip-копии
(восстановление БД и фото), безопасная проверка имён файлов.

Манифест (manifest.json) теперь включает SHA256-чексуммы для engine_data.db
и каждого файла в photos/ — это позволяет проверить целостность архива на
этапах inspect-upload и confirm-restore, прежде чем трогать рабочую БД.

Восстановление (_apply_backup_zip) атомарно: сначала создаётся rollback-точка
(копия текущей engine_data.db), затем распаковка и sqlite3.backup() идут во
временные файлы/папку, и только после успешного завершения — атомарная замена
рабочих файлов (os.replace). При любой ошибке — откат на rollback-точку.

Для предотвращения race condition при параллельных restore-запросах
используется файловый лок (backup_restore.lock) с try/finally."""
import os
import json
import time
import sqlite3
import zipfile
import tempfile
import shutil
import hashlib
import uuid
from datetime import datetime
from io import BytesIO
import logging
from logging.handlers import RotatingFileHandler

from flask import jsonify
from modules import db as db_module
from modules.photo_manager import manager as photo_manager

DB_PATH = db_module.DB_PATH
PHOTOS_FOLDER = db_module.PHOTOS_FOLDER
INCIDENT_PHOTOS_FOLDER = db_module.INCIDENT_PHOTOS_FOLDER
EQUIPMENT_PHOTOS_FOLDER = db_module.EQUIPMENT_PHOTOS_FOLDER
BACKUPS_FOLDER = db_module.BACKUPS_FOLDER
BACKUP_STAGING_FOLDER = db_module.BACKUP_STAGING_FOLDER
MAX_BACKUPS_KEPT = 3

# Список фото-папок, которые участвуют в backup/restore. Префикс — это
# имя каталога верхнего уровня внутри zip-архива (и совпадает с именем
# самой папки на диске). Логика для всех трёх папок идентична:
# атомарная замена через rollback+replace (как и раньше для photos/).
PHOTO_FOLDERS = [
    ('photos', PHOTOS_FOLDER),
    ('PhotoI', INCIDENT_PHOTOS_FOLDER),
    ('PhotoE', EQUIPMENT_PHOTOS_FOLDER),
]

# Настройка логгера для операций бэкапа/восстановления. Пишем в
# BACKUPS_FOLDER/backup_restore.log, чтобы иметь отдельный файл для
# диагностики проблем восстановления (например, WinError 32).
_logger = logging.getLogger('backup_restore')
if not _logger.handlers:
    try:
        if not os.path.exists(BACKUPS_FOLDER):
            os.makedirs(BACKUPS_FOLDER, exist_ok=True)
        handler_path = os.path.join(BACKUPS_FOLDER, 'backup_restore.log')
        handler = RotatingFileHandler(handler_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        _logger.setLevel(logging.DEBUG)
    except Exception:
        # Не фатальная ошибка: если не удалось создать файл логов,
        # просто продолжим и будем логировать в стандартный лог.
        _logger = logging.getLogger('backup_restore')


def _sha256_bytes(data):
    """Возвращает hex-строку SHA256 для байтового буфера."""
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path):
    """Возвращает hex-строку SHA256 для файла на диске (потоково, чтобы
    не держать большие файлы полностью в памяти)."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _build_backup_zip_bytes(get_db_connection):
    """Возвращает (zip_bytes, manifest_dict) — консистентный снапшот БД +
    все файлы фото. НЕ копирует engine_data.db напрямую (см. get_db_connection:
    там включён PRAGMA journal_mode=WAL) — свежие закоммиченные изменения
    какое-то время живут в отдельном engine_data.db-wal, и голый файловый
    copy может либо "не увидеть" их, либо скопировать файл в момент записи.
    Правильный способ — sqlite3 Online Backup API (Connection.backup()),
    он корректно учитывает WAL независимо от того, останавливать сервер
    или нет.

    В манифест дополнительно записываются SHA256-чексуммы для engine_data.db
    и каждого файла photos/* — для последующей проверки целостности при
    восстановлении (inspect-upload / confirm-restore)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM engines')
        engine_count = cursor.fetchone()[0]
        cursor.execute('SELECT COALESCE(SUM(photo_count), 0) FROM engines')
        photos_count_db = cursor.fetchone()[0]

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
        os.close(tmp_fd)
        try:
            dest_conn = sqlite3.connect(tmp_path)
            conn.backup(dest_conn)
            dest_conn.close()
            with open(tmp_path, 'rb') as f:
                db_bytes = f.read()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # --- Фото по всем фото-папкам (photos/, PhotoI/, PhotoE/) ---
    # Словарь {prefix: [filenames, ...]} — единый проход для чексумм и для
    # записи в zip. Каждая папка обрабатывается симметрично: если её нет
    # на диске — список пуст, чексумм для неё не будет, в zip файлы не
    # попадут. Восстановление в этом случае создаст пустую папку.
    photo_files_by_prefix = {}
    for prefix, folder in PHOTO_FOLDERS:
        files = []
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder)
                     if os.path.isfile(os.path.join(folder, f))]
        photo_files_by_prefix[prefix] = files

    # --- Чексуммы ---
    # engine_data.db — хешируем уже полученный db_bytes (консистентный
    # снапшот через Online Backup API), а не файл на диске, чтобы чексумма
    # точно соответствовала тому, что попадает в архив.
    checksums = {
        'engine_data.db': _sha256_bytes(db_bytes),
    }
    # Фото — хешируем файлы на диске. Это те же байты, которые zf.write()
    # кладёт в архив, поэтому чексумма совпадает с содержимым архива.
    for prefix, folder in PHOTO_FOLDERS:
        for fname in photo_files_by_prefix[prefix]:
            try:
                checksums[f'{prefix}/{fname}'] = _sha256_file(os.path.join(folder, fname))
            except OSError:
                _logger.warning('Failed to compute checksum for %s/%s', prefix, fname)

    manifest = {
        'app': 'engine-passports-backup',
        'manifest_version': 2,
        'created_at': datetime.now().isoformat(),
        'engine_count': engine_count,
        'photos_count_db': photos_count_db,
        'photos_count_files': len(photo_files_by_prefix.get('photos', [])),
        'photoi_count_files': len(photo_files_by_prefix.get('PhotoI', [])),
        'photoe_count_files': len(photo_files_by_prefix.get('PhotoE', [])),
        'checksums': checksums,
    }

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr('engine_data.db', db_bytes)
        for prefix, folder in PHOTO_FOLDERS:
            for fname in photo_files_by_prefix[prefix]:
                zf.write(os.path.join(folder, fname), arcname=f'{prefix}/{fname}')
    return buf.getvalue(), manifest


def _save_backup_to_server(zip_bytes, prefix='backup'):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{prefix}_{ts}.zip'
    path = os.path.join(BACKUPS_FOLDER, filename)
    with open(path, 'wb') as f:
        f.write(zip_bytes)
    size = os.path.getsize(path)
    return filename, path, size


def _enforce_backup_limit(max_count=MAX_BACKUPS_KEPT):
    """Оставляет не более max_count резервных копий в BACKUPS_FOLDER,
    удаляя более старые по принципу FIFO (первым создан — первым удалён).
    Имя файла — '{prefix}_{YYYYMMDD_HHMMSS}.zip' (см. _save_backup_to_server),
    поэтому обычная строковая сортировка совпадает с хронологической и не
    нужно читать manifest/mtime каждого файла отдельно."""
    if not os.path.exists(BACKUPS_FOLDER):
        return
    files = sorted(f for f in os.listdir(BACKUPS_FOLDER) if f.endswith('.zip'))
    excess = len(files) - max_count
    for fname in files[:max(0, excess)]:
        try:
            os.remove(os.path.join(BACKUPS_FOLDER, fname))
        except OSError:
            pass


def _verify_checksums(zip_path, manifest):
    """Пересчитывает SHA256 для engine_data.db и каждого файла из
    manifest['checksums'] (photos/*, PhotoI/*, PhotoE/* — общий цикл по
    всем ключам, без хардкода префикса) внутри zip-архива и сверяет с
    manifest['checksums'].

    Возвращает (True, None) при совпадении, (False, error_msg) при
    несовпадении или если чексуммы отсутствуют в манифесте.

    Эта функция НЕ трогает рабочую БД и рабочие фото — она читает только
    из zip-архива, поэтому безопасна для вызова на этапах inspect-upload
    и confirm-restore."""
    checksums = manifest.get('checksums')
    if not checksums:
        # Манифест без чексумм (старые бэкапы, manifest_version < 2) —
        # нельзя гарантировать целостность, отклоняем.
        return False, 'В манифесте отсутствуют чексуммы (checksums). ' \
                       'Это старый формат резервной копии (manifest_version < 2). ' \
                       'Восстановление отклонено для безопасности.'

    mismatches = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = set(zf.namelist())
        # engine_data.db
        if 'engine_data.db' in checksums:
            if 'engine_data.db' not in names:
                mismatches.append('engine_data.db: файл отсутствует в архиве')
            else:
                actual = _sha256_bytes(zf.read('engine_data.db'))
                expected = checksums['engine_data.db']
                if actual != expected:
                    mismatches.append(
                        f'engine_data.db: ожидалась {expected}, получена {actual}'
                    )
        # photos/*, PhotoI/*, PhotoE/* — общий цикл по всем ключам
        for arcname, expected in checksums.items():
            if arcname == 'engine_data.db':
                continue
            if arcname not in names:
                mismatches.append(f'{arcname}: файл отсутствует в архиве')
                continue
            actual = _sha256_bytes(zf.read(arcname))
            if actual != expected:
                mismatches.append(
                    f'{arcname}: ожидалась {expected}, получена {actual}'
                )

    if mismatches:
        return False, 'Чексуммы не совпадают (архив повреждён или изменён):\n' + \
                       '\n'.join(f'  - {m}' for m in mismatches)

    return True, None


def _atomic_replace(src, dst, retries=5, delay=0.3):
    """Атомарная замена файла src → dst с retry на Windows.

    На Windows os.replace иногда падает с PermissionError [WinError 5],
    если целевой файл недавно был открыт SQLite (даже после conn.close()
    дескриптор может ещё держаться ОС). Повторяем несколько раз с паузой.
    На Linux/Unix поведение идентично — os.replace атомарен внутри тома."""
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt < retries - 1:
                _logger.debug('os.replace retry %d/%d: %s -> %s',
                              attempt + 2, retries, src, dst)
                time.sleep(delay)
            else:
                raise
    # Достигнуть сюда невозможно, но на всякий случай:
    os.replace(src, dst)


def _acquire_restore_lock(timeout=30, retry_interval=0.2):
    """Пытается атомарно создать файл-лок backup_restore.lock в BACKUPS_FOLDER.
    Использует O_EXCL (через os.O_CREAT | os.O_EXCL) — если файл уже существует,
    значит другой restore-поток уже захватил лок. Ждёт с таймаутом.

    Возвращает путь к файлу-локу при успехе, или None при таймауте.
    Освобождается через _release_restore_lock()."""
    lock_path = os.path.join(BACKUPS_FOLDER, 'backup_restore.lock')
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f'{os.getpid()}\n'.encode())
            os.close(fd)
            _logger.info('Acquired restore lock: %s', lock_path)
            return lock_path
        except FileExistsError:
            time.sleep(retry_interval)
    _logger.warning('Timed out waiting for restore lock: %s', lock_path)
    return None


def _release_restore_lock(lock_path):
    """Освобождает файл-лок, созданный _acquire_restore_lock()."""
    if lock_path and os.path.exists(lock_path):
        try:
            os.remove(lock_path)
            _logger.info('Released restore lock: %s', lock_path)
        except OSError:
            _logger.exception('Failed to release restore lock: %s', lock_path)


def _apply_backup_zip(zip_path):
    """Восстанавливает БД и фото из ранее собранного backup-zip (см.
    _build_backup_zip_bytes). Сохраняет текущие пользователи и токены,
    чтобы восстановление данных не удаляло учётные записи.

    В архиве участвуют ТРИ фото-папки: photos/ (двигатели), PhotoI/
    (инциденты), PhotoE/ (оборудование). Логика для них полностью
    симметрична: каждая папка заменяется атомарно через rollback+replace.
    Если в архиве для какой-то папки нет ни одного файла — после restore
    она станет пустой (но существующей), даже если до restore на диске
    в ней что-то лежало. Это требование согласованности с id-записей в БД
    (файлы ID{id}_* привязаны к id, который после restore может означать
    совсем другую запись, чем до restore — лишние файлы на диске дадут
    рассинхрон).

    === Атомарность и rollback ===
    1. Захват файлового лока (backup_restore.lock) — защита от параллельных
       restore-запросов (см. раздел «Race condition» ниже).
    2. Создаётся rollback-точка: копия текущей engine_data.db во временный
       файл. Если что-то пойдёт не так — БД восстанавливается из неё.
    3. Фото по всем фото-папкам распаковываются во временные папки
       <folder>_new_<uuid>, а НЕ напрямую в рабочие папки — чтобы при
       ошибке старые фото не были удалены.
    4. engine_data.db из архива распаковывается во временный файл, затем
       sqlite3.backup() копирует его во ВТОРОЙ временный файл
       (engine_data.db.new), а НЕ в рабочую БД напрямую.
    5. Только если ВСЁ прошло успешно:
       - os.replace(rollback_db_path, DB_PATH)  — атомарная замена БД
       - os.replace(<folder>_new, <folder>)    — атомная замена каждой
         из трёх фото-папок (photos/, PhotoI/, PhotoE/)
       - восстанавливаются пользователи/токены
    6. При ЛЮБОЙ ошибке — в except-блоке:
       - если БД уже была заменена (os.replace прошёл) — откатываем из
         rollback-точки
       - для каждой уже заменённой фото-папки — возвращаем её
         rollback-версию обратно
       - удаляем временные папки <folder>_new (если остались)
       - удаляем engine_data.db.new

    === Race condition при параллельных restore ===
    Без файлового лока два параллельных /confirm-restore могли бы:
      a) оба создать rollback-копию одной и той же БД, второй перезаписал
         бы rollback-файл первого → у первого нет точки отката;
      b) одновременно удалить и перезаписать фото-папки → один запрос
         получил бы 404/битый файл;
      c) одновременно вызвать sqlite3.backup() в DB_PATH → конфликт WAL.
    Файловый лок (backup_restore.lock) последовательно сериализует все
    restore-операции: второй запрос ждёт (до 30 сек), пока первый не
    освободит лок в finally. Это не идеально (блокирует параллельность),
    но для restore-операций, которые редки и длительны, это правильная
    торговля: консистентность важнее параллелизма."""
    lock_path = _acquire_restore_lock()
    if lock_path is None:
        raise RuntimeError(
            'Не удалось захватить лок восстановления (backup_restore.lock) '
            'в течение 30 секунд. Возможно, другой запрос restore уже выполняется. '
            'Повторите попытку позже.'
        )

    rollback_db_path = None
    new_db_path = None
    db_replaced = False
    # Состояние по каждой фото-папке (photos/, PhotoI/, PhotoE/).
    # Структура единая для всех трёх:
    #   new_folder      — путь к временной папке <folder>_new_<uuid>,
    #                     куда извлекаются файлы из zip (создаётся пустой,
    #                     если в архиве для данного префикса файлов нет);
    #   rollback_folder — путь к <folder>_rollback_<uuid> (текущая папка,
    #                     переименованная перед заменой);
    #   replaced        — True, если замена os.replace уже выполнена;
    #   count_in_zip    — количество файлов, реально извлечённых в
    #                     new_folder (используется для restored_files —
    #                     manifest в этой функции не читается).
    photo_state = {
        prefix: {
            'new_folder': None,
            'rollback_folder': None,
            'replaced': False,
            'count_in_zip': 0,
        }
        for prefix, _folder in PHOTO_FOLDERS
    }
    try:
        _logger.info('Starting restore from zip: %s', zip_path)

        # --- 1. Сохраняем пользователей/токены из текущей БД ---
        preserved_users = []
        preserved_tokens = []
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                try:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT id, username, password_hash, role, created_at FROM users'
                    )
                    preserved_users = [tuple(row) for row in cursor.fetchall()]
                    cursor.execute(
                        'SELECT id, user_id, token_hash, created_at, expires_at FROM tokens'
                    )
                    preserved_tokens = [tuple(row) for row in cursor.fetchall()]
                finally:
                    conn.close()
                _logger.info('Preserved %d users and %d tokens from existing DB',
                             len(preserved_users), len(preserved_tokens))
            except Exception as e:
                # ИСПРАВЛЕНО: раньше эта ошибка только логировалась, и
                # восстановление продолжалось с пустыми preserved_users/
                # preserved_tokens. Ниже (шаг 8) восстановление пользователей
                # выполняется ТОЛЬКО если эти списки не пусты — значит при
                # сбое чтения (например, "database is locked") учётные
                # записи из бэкапа молча оставались как есть, а текущие
                # пользователи/токены терялись без единой явной ошибки.
                # Теперь отказываем в восстановлении ДО того, как что-либо
                # тронуто (rollback-точка ещё не создана, файлы не заменены).
                _logger.exception('Failed to read existing users/tokens from %s', DB_PATH)
                raise RuntimeError(
                    'Не удалось прочитать текущих пользователей и токены перед '
                    'восстановлением из бэкапа. Восстановление отменено, чтобы '
                    f'не потерять учётные записи. Причина: {e}'
                ) from e

        # --- 3. Создаём rollback-точку: копия текущей БД ---
        if os.path.exists(DB_PATH):
            rollback_fd, rollback_db_path = tempfile.mkstemp(suffix='.db.rollback')
            os.close(rollback_fd)
            shutil.copy2(DB_PATH, rollback_db_path)
            _logger.info('Created rollback point: %s', rollback_db_path)
        else:
            _logger.info('No existing DB to create rollback point — fresh install')

        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            if 'engine_data.db' not in names:
                raise ValueError(
                    'В архиве нет engine_data.db — это не резервная копия этого приложения'
                )

            # --- 4. Распаковка фото во ВРЕМЕННЫЕ папки (по одной на каждую
            # из PHOTO_FOLDERS). Если в архиве для какого-то префикса нет
            # ни одного файла — соответствующая <folder>_new_<uuid> остаётся
            # пустой (создаётся через os.makedirs(exist_ok=True)). На шаге 7b
            # такая пустая папка заменит текущую папку на диске — это и есть
            # требуемое "полная замена, даже если в бэкапе пусто".
            for prefix, folder in PHOTO_FOLDERS:
                new_folder = os.path.join(
                    os.path.dirname(folder) or '.',
                    f'{os.path.basename(folder)}_new_{uuid.uuid4().hex}'
                )
                os.makedirs(new_folder, exist_ok=True)
                photo_state[prefix]['new_folder'] = new_folder
                _logger.info('Unpacking %s/* to temporary folder: %s', prefix, new_folder)

            for name in names:
                if name.endswith('/'):
                    continue
                # Определяем, какой фото-папке принадлежит запись, по
                # префиксу <prefix>/. Если префикс не из PHOTO_FOLDERS
                # (например, manifest.json или engine_data.db) — пропускаем.
                matched_prefix = None
                for prefix, _folder in PHOTO_FOLDERS:
                    if name.startswith(f'{prefix}/'):
                        matched_prefix = prefix
                        break
                if matched_prefix is None:
                    continue
                target_name = os.path.basename(name)
                if not target_name:
                    continue
                with zf.open(name) as src, \
                     open(os.path.join(photo_state[matched_prefix]['new_folder'],
                                       target_name), 'wb') as dst:
                    dst.write(src.read())
                # Считаем количество реально извлечённых файлов для
                # restored_files (т.к. manifest в этой функции не читается).
                photo_state[matched_prefix]['count_in_zip'] = (
                    photo_state[matched_prefix].get('count_in_zip', 0) + 1
                )

            # --- 5. Распаковка engine_data.db во временный файл ---
            tmp_db_fd, tmp_db_path = tempfile.mkstemp(suffix='.db.extract')
            os.close(tmp_db_fd)
            _logger.info('Extracting engine_data.db to %s', tmp_db_path)
            try:
                with zf.open('engine_data.db') as src, open(tmp_db_path, 'wb') as dst:
                    dst.write(src.read())
            except Exception:
                _logger.exception('Failed to extract engine_data.db from zip: %s', zip_path)
                raise
            finally:
                # tmp_db_path удаляется в конце try/finally ниже
                pass

            try:
                # --- 6. sqlite3.backup() из распакованной БД во ВТОРОЙ
                # временный файл (engine_data.db.new), а НЕ в рабочую БД.
                # Таким образом, если backup() упадёт на полпути, рабочая
                # БД не пострадает — она будет заменена только после
                # успешного завершения.
                new_db_path = DB_PATH + '.new'
                _logger.info('Running sqlite3.backup() from %s to %s', tmp_db_path, new_db_path)

                src_conn = sqlite3.connect(tmp_db_path)
                dest_conn = sqlite3.connect(new_db_path)
                try:
                    src_conn.backup(dest_conn)
                finally:
                    src_conn.close()
                    dest_conn.close()
                _logger.info('SQLite backup finished successfully')

                # --- 7. Всё прошло успешно — атомарная замена ---
                # 7a. Замена БД (с retry на Windows — os.replace может падать
                #     с WinError 5, если файл недавно был открыт SQLite)
                _atomic_replace(new_db_path, DB_PATH)
                new_db_path = None  # уже переименован
                db_replaced = True
                _logger.info('Atomically replaced DB: %s -> %s', 'engine_data.db.new', DB_PATH)

                # 7b. Замена фото-папок (атомарно внутри одного тома).
                # Логика симметрична для photos/, PhotoI/, PhotoE/:
                #   - если текущая папка существует — переименовываем её
                #     в <folder>_rollback_<uuid>;
                #   - os.replace(<folder>_new_<uuid>, <folder>).
                # Если в архиве для префикса не было ни одного файла,
                # соответствующая <folder>_new_<uuid> пуста — но os.replace
                # всё равно атомарно подменит текущую папку пустой. Это и
                # есть требуемое "полная замена, даже если в бэкапе пусто".
                # ИСПРАВЛЕНО: раньше старая папка фото удалялась через
                # rmtree ДО того, как было известно, что вся операция
                # (включая последующее восстановление пользователей на
                # шаге 8) точно завершится успешно. Если что-то падало
                # после этой точки, откат БД срабатывал (см. except
                # ниже), а откатить фото было уже нечем — они были
                # безвозвратно удалены. Теперь старая папка не удаляется,
                # а переименовывается в rollback-путь — как и для БД — и
                # удаляется только после полного успеха всей функции
                # (см. блок финального success ниже) либо возвращается
                # на место при ошибке (см. except).
                any_photo_replaced = False
                for prefix, folder in PHOTO_FOLDERS:
                    if os.path.exists(folder):
                        rollback_folder = os.path.join(
                            os.path.dirname(folder) or '.',
                            f'{os.path.basename(folder)}_rollback_{uuid.uuid4().hex}'
                        )
                        os.replace(folder, rollback_folder)
                        photo_state[prefix]['rollback_folder'] = rollback_folder
                        _logger.info('Moved current %s folder to rollback location: %s',
                                     prefix, rollback_folder)
                    os.replace(photo_state[prefix]['new_folder'], folder)
                    photo_state[prefix]['replaced'] = True
                    photo_state[prefix]['new_folder'] = None  # уже переименована
                    any_photo_replaced = True
                    _logger.info('Atomically replaced %s folder: %s_new_* -> %s',
                                 prefix, prefix, folder)
                # Invalidate photo manager cache after photos folder replacement
                if any_photo_replaced:
                    photo_manager.invalidate_photo_cache()

            finally:
                # Убираем временный файл с распакованной БД
                if os.path.exists(tmp_db_path):
                    try:
                        os.remove(tmp_db_path)
                    except OSError:
                        _logger.exception('Failed to remove extracted DB temp file: %s', tmp_db_path)

        # --- 8. Восстанавливаем пользователей/токены в новую БД ---
        if preserved_users or preserved_tokens:
            try:
                conn = sqlite3.connect(DB_PATH)
                try:
                    cursor = conn.cursor()
                    # Ensure users/tokens tables exist in the restored DB. Some
                    # backups may come from older app versions without these
                    # tables; создаём их, чтобы можно было восстановить
                    # учётные записи.
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            role TEXT NOT NULL DEFAULT 'user',
                            created_at TEXT NOT NULL
                        )
                    ''')
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS tokens (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            token_hash TEXT UNIQUE NOT NULL,
                            created_at TEXT NOT NULL,
                            expires_at TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                        )
                    ''')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_hash ON tokens(token_hash)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id)')
                    _logger.debug('Ensured users/tokens tables exist in restored DB')
                    cursor.execute('DELETE FROM tokens')
                    cursor.execute('DELETE FROM users')
                    if preserved_users:
                        cursor.executemany(
                            'INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                            preserved_users
                        )
                    if preserved_tokens:
                        cursor.executemany(
                            'INSERT INTO tokens (id, user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?)',
                            preserved_tokens
                        )
                    conn.commit()
                finally:
                    conn.close()
                _logger.info('Restored preserved users/tokens into %s', DB_PATH)
            except Exception as e:
                # ИСПРАВЛЕНО: раньше эта ошибка только логировалась, и
                # функция ниже писала "Restore completed successfully" —
                # т.е. восстановление объявлялось успешным, даже если
                # текущие пользователи/токены так и не попали обратно в
                # уже подменённую БД (например, из-за UNIQUE-конфликта
                # username с пользователем из бэкапа). Теперь пробрасываем
                # исключение наверх: оно попадёт в except ниже, который
                # откатит БД на rollback-точку (созданную ДО подмены и
                # содержащую корректных текущих пользователей) — вместо
                # того чтобы молча оставить учётки в неопределённом
                # состоянии при формальном "успехе" операции.
                _logger.exception('Failed to restore preserved users/tokens into %s', DB_PATH)
                raise RuntimeError(
                    'Данные и фото восстановлены из бэкапа, но не удалось вернуть '
                    'обратно текущие учётные записи пользователей. Выполняется '
                    f'откат к состоянию до восстановления. Причина: {e}'
                ) from e

        # --- Успех: rollback-точки фото-папок больше не нужны ---
        for prefix, folder in PHOTO_FOLDERS:
            rb = photo_state[prefix]['rollback_folder']
            if rb and os.path.exists(rb):
                try:
                    shutil.rmtree(rb, ignore_errors=True)
                    _logger.debug('Removed %s rollback point: %s', prefix, rb)
                except Exception:
                    _logger.exception('Failed to remove %s rollback point: %s', prefix, rb)

        _logger.info('Restore completed successfully from %s', zip_path)
        # restored_files — dict с разбивкой по папкам плюс total для
        # backward-compat со старыми клиентами, которые ждали число.
        # Снимок счётчиков берём из photo_state[prefix]['count_in_zip'] —
        # это количество файлов, реально извлечённых в <folder>_new_<uuid>
        # на шаге 4 (manifest из zip в этой функции не читается).
        restored_by_prefix = {
            prefix: photo_state[prefix]['count_in_zip']
            for prefix, _folder in PHOTO_FOLDERS
        }
        restored_total = sum(restored_by_prefix.values())
        return {
            'success': True,
            'message': 'Восстановление завершено успешно',
            'restored_files': {
                **restored_by_prefix,
                'total': restored_total,
            },
        }

    except Exception:
        # === ОТКАТ НА ROLLBACK-TOЧКУ ===
        _logger.exception('Restore failed — initiating rollback')

        # Если БД уже была заменена (os.replace прошёл), откатываем из
        # rollback-точки. Если замена не удалась (db_replaced == False),
        # рабочая БД не тронута — откат не нужен.
        if db_replaced and rollback_db_path and os.path.exists(rollback_db_path):
            try:
                shutil.copy2(rollback_db_path, DB_PATH)
                _logger.info('Rollback: restored DB from %s to %s', rollback_db_path, DB_PATH)
            except Exception:
                _logger.exception('CRITICAL: Failed to rollback DB from %s', rollback_db_path)

        # ИСПРАВЛЕНО: аналогично БД, откатываем и фото — если старые фото
        # были перемещены в rollback-папку (см. шаг 7b), возвращаем их на
        # место вместо того, чтобы оставлять диск с фото из бэкапа при
        # откаченной на старое состояние БД (несогласованность: старые
        # записи движков + чужие фото). Логика симметрична для всех трёх
        # фото-папок (photos/, PhotoI/, PhotoE/).
        for prefix, folder in PHOTO_FOLDERS:
            if not photo_state[prefix]['replaced']:
                continue
            rb = photo_state[prefix]['rollback_folder']
            if not rb or not os.path.exists(rb):
                continue
            try:
                if os.path.exists(folder):
                    shutil.rmtree(folder, ignore_errors=True)
                os.replace(rb, folder)
                _logger.info('Rollback: restored %s from %s to %s', prefix, rb, folder)
                photo_state[prefix]['rollback_folder'] = None  # уже переименована обратно
            except Exception:
                _logger.exception(
                    'CRITICAL: Failed to rollback %s from %s — '
                    'manual intervention required', prefix, rb
                )

        # Очищаем временные файлы/папки, которые могли остаться
        if new_db_path and os.path.exists(new_db_path):
            try:
                os.remove(new_db_path)
            except OSError:
                _logger.exception('Failed to remove leftover %s', new_db_path)

        # Временные <folder>_new_<uuid> для всех трёх фото-папок.
        for prefix, _folder in PHOTO_FOLDERS:
            nf = photo_state[prefix]['new_folder']
            if nf and os.path.exists(nf):
                try:
                    shutil.rmtree(nf, ignore_errors=True)
                except Exception:
                    _logger.exception('Failed to remove leftover %s folder: %s', prefix, nf)

        # Если хотя бы одна фото-папка была заменена, а БД — нет (или
        # наоборот), состояние может быть несогласованным. Логируем
        # критическую ошибку — администратору нужно вручную проверить
        # целостность. (Это в первую очередь сигнал о том, что откат фото
        # выше тоже не удался — иначе replaced-флаги были бы уже неактуальны.)
        replaced_prefixes = [p for p, _ in PHOTO_FOLDERS if photo_state[p]['replaced']]
        if replaced_prefixes and not db_replaced:
            _logger.critical(
                'Photo folders %s were replaced but DB was not — manual intervention required. '
                'DB rollback from %s may be needed.', replaced_prefixes, rollback_db_path
            )

        raise  # пробрасываем исключение наверх

    finally:
        # --- Очистка rollback-точки ---
        if rollback_db_path and os.path.exists(rollback_db_path):
            try:
                os.remove(rollback_db_path)
                _logger.debug('Removed rollback point: %s', rollback_db_path)
            except OSError:
                _logger.exception('Failed to remove rollback point: %s', rollback_db_path)

        # --- Освобождение лока ---
        _release_restore_lock(lock_path)


def _safe_backup_filename(filename):
    if not filename or '..' in filename or '/' in filename or '\\' in filename or not filename.endswith('.zip'):
        return None
    return filename


# =====================================================================
# PUBLIC API — вызывается из routes/backup_routes.py и services/backup_service.py
# =====================================================================

def create_backup():
    """Создаёт бэкап engine_data.db + photos/ + manifest.json (с чексуммами).

    Возвращает dict: {'filename': ..., 'path': ..., 'size': ..., 'manifest': ...}
    """
    zip_bytes, manifest = _build_backup_zip_bytes(db_module.db_connection)
    filename, path, size = _save_backup_to_server(zip_bytes)
    _enforce_backup_limit()
    return {
        'filename': filename,
        'path': path,
        'size': size,
        'manifest': manifest,
    }


def list_backups():
    """Список файлов бэкапов в BACKUPS_FOLDER (от новых к старых).

    Для каждого архива читает manifest.json и включает метаданные
    (created_at, engine_count, photos_count_db, photos_count_files),
    чтобы frontend не нужно было пересчитывать их заново.
    """
    if not os.path.exists(BACKUPS_FOLDER):
        return []
    files = sorted(
        [f for f in os.listdir(BACKUPS_FOLDER) if f.endswith('.zip')],
        reverse=True
    )
    result = []
    for f in files:
        full = os.path.join(BACKUPS_FOLDER, f)
        entry = {
            'filename': f,
            'size': os.path.getsize(full),
            'modified': datetime.fromtimestamp(os.path.getmtime(full)).isoformat(),
        }
        # Читаем manifest.json из zip — это быстрая операция (один файл),
        # не требует распаковки engine_data.db или photos/*.
        try:
            with zipfile.ZipFile(full, 'r') as zf:
                names = zf.namelist()
                if 'manifest.json' in names:
                    manifest = json.loads(zf.read('manifest.json'))
                    entry['created_at'] = manifest.get('created_at')
                    entry['engine_count'] = manifest.get('engine_count')
                    entry['photos_count_db'] = manifest.get('photos_count_db')
                    entry['photos_count_files'] = manifest.get('photos_count_files')
                    entry['manifest_version'] = manifest.get('manifest_version')
        except Exception:
            pass
        result.append(entry)
    return result


def inspect_uploaded_backup(zip_path):
    """Читает manifest.json из загруженного zip и сверяет чексуммы.

    Возвращает dict: {'valid': bool, 'manifest': dict, 'errors': [str, ...]}
    """
    errors = []
    manifest = None
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            if 'manifest.json' not in names:
                return {'valid': False, 'manifest': None,
                        'errors': ['manifest.json не найден в архиве']}
            manifest = json.loads(zf.read('manifest.json'))
        # _verify_checksums возвращает (ok: bool, error_msg: str|None)
        ok, error_msg = _verify_checksums(zip_path, manifest)
        if not ok:
            errors.append(error_msg)
    except Exception as e:
        return {'valid': False, 'manifest': None,
                'errors': [f'Ошибка чтения архива: {e}']}
    return {'valid': len(errors) == 0, 'manifest': manifest, 'errors': errors}


def restore_backup(zip_path):
    """Атомарно восстанавливает engine_data.db и photos/ из zip.

    Использует rollback point + файловый lock.
    Возвращает dict: {'success': bool, 'message': str,
                      'restored_files': dict с разбивкой по папкам
                      ({'photos': N, 'PhotoI': M, 'PhotoE': K, 'total': N+M+K})}
    """
    return _apply_backup_zip(zip_path)


def download_backup(filename):
    """Возвращает абсолютный путь к файлу бэкапа или None."""
    safe = _safe_backup_filename(filename)
    if not safe:
        return None
    path = os.path.join(BACKUPS_FOLDER, safe)
    if not os.path.exists(path):
        return None
    return path


def delete_backup(filename):
    """Удаляет файл бэкапа. Возвращает True если удалён."""
    safe = _safe_backup_filename(filename)
    if not safe:
        return False
    path = os.path.join(BACKUPS_FOLDER, safe)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True
