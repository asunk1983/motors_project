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
BACKUPS_FOLDER = db_module.BACKUPS_FOLDER
BACKUP_STAGING_FOLDER = db_module.BACKUP_STAGING_FOLDER
MAX_BACKUPS_KEPT = 3

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

    photo_files = []
    if os.path.exists(PHOTOS_FOLDER):
        photo_files = [f for f in os.listdir(PHOTOS_FOLDER)
                        if os.path.isfile(os.path.join(PHOTOS_FOLDER, f))]

    # --- Чексуммы ---
    # engine_data.db — хешируем уже полученный db_bytes (консистентный
    # снапшот через Online Backup API), а не файл на диске, чтобы чексумма
    # точно соответствовала тому, что попадает в архив.
    checksums = {
        'engine_data.db': _sha256_bytes(db_bytes),
    }
    # Фото — хешируем файлы на диске. Это те же байты, которые zf.write()
    # кладёт в архив, поэтому чексумма совпадает с содержимым архива.
    for fname in photo_files:
        try:
            checksums[f'photos/{fname}'] = _sha256_file(os.path.join(PHOTOS_FOLDER, fname))
        except OSError:
            _logger.warning('Failed to compute checksum for photo: %s', fname)

    manifest = {
        'app': 'engine-passports-backup',
        'manifest_version': 2,
        'created_at': datetime.now().isoformat(),
        'engine_count': engine_count,
        'photos_count_db': photos_count_db,
        'photos_count_files': len(photo_files),
        'checksums': checksums,
    }

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr('engine_data.db', db_bytes)
        for fname in photo_files:
            zf.write(os.path.join(PHOTOS_FOLDER, fname), arcname=f'photos/{fname}')
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
    """Пересчитывает SHA256 для engine_data.db и каждого файла photos/*
    внутри zip-архива и сверяет с manifest['checksums'].

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
        # photos/*
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

    === Атомарность и rollback ===
    1. Захват файлового лока (backup_restore.lock) — защита от параллельных
       restore-запросов (см. раздел «Race condition» ниже).
    2. Создаётся rollback-точка: копия текущей engine_data.db во временный
       файл. Если что-то пойдёт не так — БД восстанавливается из неё.
    3. Фото распаковываются во временную папку photos_new_<uuid>, а НЕ
       напрямую в PHOTOS_FOLDER — чтобы при ошибке старые фото не были
       удалены.
    4. engine_data.db из архива распаковывается во временный файл, затем
       sqlite3.backup() копирует его во ВТОРОЙ временный файл
       (engine_data.db.new), а НЕ в рабочую БД напрямую.
    5. Только если ВСЁ прошло успешно:
       - os.replace(rollback_db_path, DB_PATH)  — атомарная замена БД
       - os.replace(photos_new, PHOTOS_FOLDER)  — атомная замена папки фото
       - восстанавливаются пользователи/токены
    6. При ЛЮБОЙ ошибке — в except-блоке:
       - если БД уже была заменена (os.replace прошёл) — откатываем из
         rollback-точки
       - удаляем временную папку photos_new (старые фото остаются на месте)
       - удаляем engine_data.db.new

    === Race condition при параллельных restore ===
    Без файлового лока два параллельных /confirm-restore могли бы:
      a) оба создать rollback-копию одной и той же БД, второй перезаписал
         бы rollback-файл первого → у первого нет точки отката;
      b) одновременно удалить и перезаписать PHOTOS_FOLDER → один запрос
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
    photos_new_folder = None
    photos_rollback_folder = None
    new_db_path = None
    db_replaced = False
    photos_replaced = False
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

        # --- 2. Дампим пользователей/токены в JSON для диагностики ---
        if preserved_users or preserved_tokens:
            try:
                dump = {
                    'preserved_users': [list(u) for u in preserved_users],
                    'preserved_tokens': [list(t) for t in preserved_tokens],
                }
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                dump_path = os.path.join(BACKUPS_FOLDER, f'preserved_users_{ts}.json')
                with open(dump_path, 'w', encoding='utf-8') as df:
                    json.dump(dump, df, ensure_ascii=False, indent=2)
                _logger.info('Dumped preserved users/tokens to %s', dump_path)
            except Exception:
                _logger.exception('Failed to dump preserved users/tokens for diagnostics')

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

            # --- 4. Распаковка фото во ВРЕМЕННУЮ папку ---
            photos_new_folder = os.path.join(
                os.path.dirname(PHOTOS_FOLDER) or '.',
                f'photos_new_{uuid.uuid4().hex}'
            )
            os.makedirs(photos_new_folder, exist_ok=True)
            _logger.info('Unpacking photos to temporary folder: %s', photos_new_folder)

            for name in names:
                if name.startswith('photos/') and not name.endswith('/'):
                    target_name = os.path.basename(name)
                    if not target_name:
                        continue
                    with zf.open(name) as src, \
                         open(os.path.join(photos_new_folder, target_name), 'wb') as dst:
                        dst.write(src.read())

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

                # 7b. Замена папки фото (атомарно внутри одного тома)
                if os.path.exists(PHOTOS_FOLDER):
                    # ИСПРАВЛЕНО: раньше старая папка фото удалялась через
                    # rmtree ДО того, как было известно, что вся операция
                    # (включая последующее восстановление пользователей на
                    # шаге 8) точно завершится успешно. Если что-то падало
                    # после этой точки, откат БД срабатывал (см. except
                    # ниже), а откатить фото было уже нечем — они были
                    # безвозвратно удалены. Теперь старая папка не удаляется,
                    # а переименовывается в rollback-путь — как и для БД —
                    # и удаляется только после полного успеха всей функции
                    # (см. блок финального success ниже) либо возвращается
                    # на место при ошибке (см. except).
                    photos_rollback_folder = os.path.join(
                        os.path.dirname(PHOTOS_FOLDER) or '.',
                        f'photos_rollback_{uuid.uuid4().hex}'
                    )
                    os.replace(PHOTOS_FOLDER, photos_rollback_folder)
                    _logger.info('Moved current photos to rollback location: %s',
                                 photos_rollback_folder)
                os.replace(photos_new_folder, PHOTOS_FOLDER)
                photos_replaced = True
                photos_new_folder = None  # уже переименована
                # Invalidate photo manager cache after photos folder replacement
                photo_manager.invalidate_photo_cache()
                _logger.info('Atomically replaced photos folder: %s -> %s',
                             'photos_new_*', PHOTOS_FOLDER)

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

        # --- Успех: rollback-точка фото больше не нужна ---
        if photos_rollback_folder and os.path.exists(photos_rollback_folder):
            try:
                shutil.rmtree(photos_rollback_folder, ignore_errors=True)
                _logger.debug('Removed photos rollback point: %s', photos_rollback_folder)
            except Exception:
                _logger.exception('Failed to remove photos rollback point: %s', photos_rollback_folder)

        _logger.info('Restore completed successfully from %s', zip_path)
        return {
            'success': True,
            'message': 'Восстановление завершено успешно',
            'restored_files': manifest.get('photos_count_files', 0) if 'manifest' in locals() else 0
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
        # записи движков + чужие фото).
        if photos_replaced and photos_rollback_folder and os.path.exists(photos_rollback_folder):
            try:
                if os.path.exists(PHOTOS_FOLDER):
                    shutil.rmtree(PHOTOS_FOLDER, ignore_errors=True)
                os.replace(photos_rollback_folder, PHOTOS_FOLDER)
                _logger.info('Rollback: restored photos from %s to %s',
                             photos_rollback_folder, PHOTOS_FOLDER)
                photos_rollback_folder = None  # уже переименована обратно
            except Exception:
                _logger.exception(
                    'CRITICAL: Failed to rollback photos from %s — '
                    'manual intervention required', photos_rollback_folder
                )

        # Очищаем временные файлы/папки, которые могли остаться
        if new_db_path and os.path.exists(new_db_path):
            try:
                os.remove(new_db_path)
            except OSError:
                _logger.exception('Failed to remove leftover %s', new_db_path)

        if photos_new_folder and os.path.exists(photos_new_folder):
            try:
                shutil.rmtree(photos_new_folder, ignore_errors=True)
            except Exception:
                _logger.exception('Failed to remove leftover photos folder: %s', photos_new_folder)

        # Если фото были заменены, а БД — нет (или наоборот), состояние
        # может быть несогласованным. В этом случае логируем критическую
        # ошибку — администратору нужно вручную проверить целостность.
        # (Теперь это в первую очередь сигнал о том, что откат фото выше
        # тоже не удался — иначе photos_replaced был бы уже неактуален.)
        if photos_replaced and not db_replaced:
            _logger.critical(
                'Photos were replaced but DB was not — manual intervention required. '
                'DB rollback from %s may be needed.', rollback_db_path
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
    Возвращает dict: {'success': bool, 'message': str, 'restored_files': int}
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
