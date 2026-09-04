"""Маршруты импорта и очистки данных.

Вынесено из app.py. Использует парсер из modules/engine_parser/parser.py
(функции parse_file_fast, extract_images_from_excel) и утилиту логирования
из utils/logging.py.
"""
import logging
import os
import glob
import time
import sqlite3
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify

from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER
from modules import db as db_module
from modules.engine_parser.parser import parse_file_fast, extract_images_from_excel
from utils.logging import log_message
from config.settings import MAX_WORKERS

logger = logging.getLogger(__name__)

import_bp = Blueprint('import', __name__, url_prefix='/api')


@import_bp.route('/import-folder', methods=['POST'])
def import_folder():
    log_message("=" * 70)
    log_message("ЗАПУСК ИМПОРТА")
    start_time = time.time()

    try:
        excel_files = []
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(glob.glob(os.path.join(MOTORS_FOLDER, ext)))

        if not excel_files:
            return jsonify({'success': False, 'error': f'В папке "{MOTORS_FOLDER}" нет Excel файлов.'}), 400

        # === ЭТАП 1: Параллельный парсинг Excel-файлов (CPU-bound + I/O) ===
        # ThreadPoolExecutor(4) — подходит, т.к. parse_file_fast в основном
        # читает файл (I/O) и парсит через pandas (частично CPU). ProcessPool
        # избыто тяжёл для 97 файлов небольшого размера.
        file_reports = []
        parsed_data = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(parse_file_fast, f, log_message): f for f in excel_files}
            for future in as_completed(futures):
                filepath = futures[future]
                filename = os.path.basename(filepath)
                try:
                    result = future.result()
                    if result['success']:
                        parsed_data.append(result)
                        file_reports.append({
                            'filename': filename,
                            'status': 'success',
                            'engine_id': None,
                            'modes_count': len(result['modes']),
                            'works_count': len(result['works']),
                            'photos_count': 0,
                        })
                    else:
                        file_reports.append({
                            'filename': filename,
                            'status': 'error',
                            'error': result.get('error', 'Неизвестная ошибка'),
                        })
                except Exception as e:
                    file_reports.append({
                        'filename': filename,
                        'status': 'error',
                        'error': str(e),
                    })

        if not parsed_data:
            return jsonify({
                'success': False,
                'error': 'Не удалось импортировать ни одного файла',
                'file_reports': file_reports,
                'summary': {
                    'total_files': len(excel_files),
                    'success_count': 0,
                    'error_count': len(file_reports),
                }
            }), 400

        # === ПРОВЕРКА: массовый импорт рассчитан только на пустую БД ===
        # ИСПРАВЛЕНО: вычисление first_id ниже (last_insert_rowid() минус
        # количество вставленных строк) корректно только если engines была
        # пуста до импорта. На непустой БД first_id получится неверным, и
        # все modes/works/фото привяжутся не к тем engine_id, что реально
        # присвоил автоинкремент. Раньше это предположение было зафиксировано
        # только в комментариях и не проверялось в коде.
        with db_connection() as conn:
            existing_count = conn.execute('SELECT COUNT(*) FROM engines').fetchone()[0]
        if existing_count > 0:
            return jsonify({
                'success': False,
                'error': (
                    f'В базе данных уже есть {existing_count} двигателей. '
                    'Массовый импорт поддерживается только на пустую БД — '
                    'сначала выполните очистку (/api/clear), затем повторите импорт.'
                ),
            }), 400

        # === ЭТАП 2: Последовательная запись в БД (один поток) ===
        # Вся запись в БД идёт в одном потоке с одной транзакцией. Это
        # исключает SQLite lock contention (даже в WAL-режиме несколько
        # writer'ов могут конфликтовать) и гарантирует атомарность: либо
        # все движители записаны, либо ни одного.
        #
        # _validate_mode_numeric_fields() сознательно НЕ применяется здесь.
        # Это массовый импорт легаси-данных из Excel (parse_operating_modes),
        # а не ручной ввод через веб-форму — отклонять весь файл целиком
        # из-за одной "грязной" ячейки было бы более серьёзным продуктовым
        # решением (пропускать только эту строку? весь файл? весь режим?),
        # которое требует отдельного обсуждения, а не тихого расширения
        # правила, введённого для ручных форм создания/редактирования.
        first_id = None
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('BEGIN TRANSACTION')

            all_engines = [d['engine_tuple'] for d in parsed_data]
            cursor.executemany("""INSERT INTO engines (filename, purpose, workshop, location, engine_type, manufacturer,
                serial_number, bearing_front, bearing_rear, shaft_diameter, protection_class,
                mounting_type, temp_sensor, encoder, cooling, note, photo_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", all_engines)

            cursor.execute('SELECT last_insert_rowid()')
            last_id = cursor.fetchone()[0]
            first_id = last_id - len(all_engines) + 1

            all_modes, all_works = [], []
            for idx, data in enumerate(parsed_data):
                engine_id = first_id + idx
                for mode in data['modes']:
                    all_modes.append((engine_id, mode['frequency'], mode['power'], mode['voltage'],
                                     mode['connection_type'], mode['current'], mode['rpm']))
                for work in data['works']:
                    all_works.append((engine_id, work['work_number'], work['date'], work['work_description'],
                                     work['isolation'], work['inspection'], work['signature']))

            if all_modes:
                cursor.executemany("""INSERT INTO operating_modes (engine_id, frequency, power, voltage, connection_type, current, rpm) VALUES (?, ?, ?, ?, ?, ?, ?)""", all_modes)
            if all_works:
                cursor.executemany("""INSERT INTO maintenance_works (engine_id, work_number, date, work_description, isolation, inspection, signature) VALUES (?, ?, ?, ?, ?, ?, ?)""", all_works)

            conn.commit()

        # === ЭТАП 3: Извлечение фото (параллельно, с защитой от ошибок) ===
        # Фото извлекаются ПАРАЛЛЕЛЬНО (I/O-bound — чтение из xlsx), но
        # ошибка одного файла не откатывает уже сохранённые данные движка:
        # try/except вокруг future.result(), а photo_count обновляется
        # только для успешно извлечённых.
        total_photos = 0
        photo_updates = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(extract_images_from_excel, data['file_path'], data['filename'],
                                 first_id + idx, log_message): (first_id + idx, idx)
                for idx, data in enumerate(parsed_data)
            }
            for future in as_completed(futures):
                engine_id, idx = futures[future]
                filename = parsed_data[idx]['filename']
                try:
                    count = future.result()
                    total_photos += count
                    if count > 0:
                        photo_updates.append((count, engine_id))
                    # Обновляем построчный отчёт
                    for report in file_reports:
                        if report['filename'] == filename:
                            report['photos_count'] = count
                            report['engine_id'] = engine_id
                            break
                except Exception as e:
                    # Ошибка фото не откатывает данные движка — он уже
                    # записан в БД на этапе 2. Просто логируем и продолжаем.
                    log_message(f"Ошибка извлечения фото для {filename}: {e}")
                    for report in file_reports:
                        if report['filename'] == filename:
                            report['photos_count'] = 0
                            report['engine_id'] = engine_id
                            report['photo_error'] = str(e)
                            break

        if photo_updates:
            with db_connection() as conn:
                conn.executemany('UPDATE engines SET photo_count = ? WHERE id = ?', photo_updates)
                conn.commit()

        elapsed_time = time.time() - start_time
        log_message(f"ИМПОРТ ЗАВЕРШЕН за {elapsed_time:.2f} сек. Фото: {total_photos}")

        success_count = sum(1 for r in file_reports if r['status'] == 'success')
        error_count = sum(1 for r in file_reports if r['status'] == 'error')

        return jsonify({
            'success': True,
            'imported': len(parsed_data),
            'total_photos': total_photos,
            'elapsed_time': round(elapsed_time, 2),
            'message': f'Импортировано {len(parsed_data)} файлов за {elapsed_time:.2f} сек. Фото: {total_photos}',
            'file_reports': file_reports,
            'summary': {
                'total_files': len(excel_files),
                'success_count': success_count,
                'error_count': error_count,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@import_bp.route('/clear', methods=['POST'])
def clear_database():
    """Полная очистка БД и всех фото-папок.

    Пересоздаёт файл engine_data.db с нуля через db_module.init_db() —
    это автоматически подхватывает новые таблицы, добавляемые в схему со
    временем (раньше clear_database() хардкодил DELETE FROM engines/
    operating_modes/maintenance_works и при добавлении новой таблицы эту
    функцию приходилось дополнять вручную — повторяет ту же историю, что
    и с restore в backup.py). Справочники (failure_mode, failure_cause,
    maintenance_action_type, equipment_type, attribute_definition,
    equipment_type_attribute) досеиваются init_db() автоматически.

    Сохраняются и возвращаются обратно:
      - users, tokens             — чтобы админ мог снова войти
      - changelog_entries         — история изменений
      - wishlist_items            — пожелания/идеи

    Теряются безвозвратно: engines, operating_modes, maintenance_works,
    вся подсистема инцидентов (incident_ticket* и связанные), номенклатура
    оборудования (equipment*), crew, location_node, knowledge_article*,
    failure, ticket, equipment_work.
    """
    try:
        # --- 1. Сохраняем данные, которые нужно вернуть в новую БД ---
        preserved_users = []
        preserved_tokens = []
        preserved_changelog = []
        preserved_wishlist = []
        if os.path.exists(db_module.DB_PATH):
            try:
                conn = sqlite3.connect(db_module.DB_PATH)
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT id, username, password_hash, role, created_at, '
                        'last_login, last_edit FROM users'
                    )
                    preserved_users = [tuple(row) for row in cursor.fetchall()]
                    cursor.execute(
                        'SELECT id, user_id, token_hash, created_at, expires_at '
                        'FROM tokens'
                    )
                    preserved_tokens = [tuple(row) for row in cursor.fetchall()]
                    # Весь контент как есть, включая seed-данные, если они
                    # там ещё есть. Если таблица уже пуста — после очистки
                    # она останется пустой (это ожидаемо).
                    cursor.execute(
                        'SELECT id, entry_date, text, created_at '
                        'FROM changelog_entries'
                    )
                    preserved_changelog = [tuple(row) for row in cursor.fetchall()]
                    cursor.execute(
                        'SELECT id, text, done, created_at FROM wishlist_items'
                    )
                    preserved_wishlist = [tuple(row) for row in cursor.fetchall()]
                finally:
                    conn.close()
                logger.info(
                    'Preserved before clear: %d users, %d tokens, '
                    '%d changelog, %d wishlist',
                    len(preserved_users), len(preserved_tokens),
                    len(preserved_changelog), len(preserved_wishlist),
                )
            except Exception:
                # Не угадываем — лучше упасть сразу, чем продолжить очистку
                # и потерять данные молча (та же история, что исправляли в
                # _apply_backup_zip для users/tokens).
                logger.exception('Failed to read preserved data before DB reset')
                return jsonify({
                    'success': False,
                    'error': 'Не удалось прочитать сохраняемые данные перед '
                             'очисткой БД. БД НЕ изменена.'
                }), 500

        # --- 2. Удаляем файл БД (с retry на Windows для PermissionError) ---
        db_path = db_module.DB_PATH
        for suffix in ('', '-wal', '-shm'):
            path = db_path + suffix
            if not os.path.exists(path):
                continue
            for attempt in range(5):
                try:
                    os.remove(path)
                    break
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.3)
                    else:
                        logger.exception('Cannot remove %s (file locked)', path)
                        return jsonify({
                            'success': False,
                            'error': 'Не удалось удалить ' + path +
                                     ' — файл занят другим процессом. '
                                     'Закройте приложения, использующие БД, '
                                     'и повторите.'
                        }), 500

        # --- 3. Пересоздаём схему БД через init_db() ---
        # init_db() создаст ВСЕ таблицы (CREATE TABLE IF NOT EXISTS) и
        # досеет справочники (failure_mode, failure_cause и т.п.), но
        # пустые. Для changelog — 5 дефолтных записей про обновления.
        db_module.init_db()

        # --- 4. Возвращаем preserved_* в новую БД ---
        try:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                # На случай если init_db() по какой-то причине не создал
                # нужные таблицы (теоретически не должно случиться, но
                # CREATE TABLE IF NOT EXISTS стоит копейки).
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        created_at TEXT NOT NULL,
                        last_login TEXT,
                        last_edit TEXT
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
                # init_db() уже создаёт changelog_entries/wishlist_items,
                # но для changelog досеивает 5 строк — стираем их перед
                # вставкой сохранённых. Если preserved_changelog пуст —
                # таблица останется пустой (по требованию).
                cursor.execute('DELETE FROM tokens')
                cursor.execute('DELETE FROM users')
                cursor.execute('DELETE FROM changelog_entries')
                cursor.execute('DELETE FROM wishlist_items')
                if preserved_users:
                    cursor.executemany(
                        'INSERT INTO users (id, username, password_hash, role, '
                        'created_at, last_login, last_edit) VALUES '
                        '(?, ?, ?, ?, ?, ?, ?)',
                        preserved_users,
                    )
                if preserved_tokens:
                    cursor.executemany(
                        'INSERT INTO tokens (id, user_id, token_hash, '
                        'created_at, expires_at) VALUES (?, ?, ?, ?, ?)',
                        preserved_tokens,
                    )
                if preserved_changelog:
                    cursor.executemany(
                        'INSERT INTO changelog_entries (id, entry_date, text, '
                        'created_at) VALUES (?, ?, ?, ?)',
                        preserved_changelog,
                    )
                if preserved_wishlist:
                    cursor.executemany(
                        'INSERT INTO wishlist_items (id, text, done, '
                        'created_at) VALUES (?, ?, ?, ?)',
                        preserved_wishlist,
                    )
                conn.commit()
            finally:
                conn.close()
            logger.info('Restored preserved data into fresh DB')
        except Exception:
            logger.exception('Failed to restore preserved data after DB reset')
            return jsonify({
                'success': False,
                'error': 'БД пересоздана, но не удалось вернуть сохранённых '
                         'пользователей/историю. Проверьте логи.'
            }), 500

        # --- 5. Очищаем все три фото-папки ---
        # Список импортируется из backup.py, чтобы не дублировать
        # константы. Локальный импорт — паттерн проекта (см.
        # modules/photo_manager/equipment_manager.py:42).
        from modules.backup_system.backup import PHOTO_FOLDERS
        for _prefix, folder_path in PHOTO_FOLDERS:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
            os.makedirs(folder_path, exist_ok=True)

        # Сброс кеша фото-менеджеров, чтобы они пересканировали диск.
        try:
            from modules.photo_manager import manager as photo_manager
            photo_manager.invalidate_photo_cache()
        except Exception:
            logger.exception('Failed to invalidate photo manager cache')

        logger.info('Database and all photo folders cleared')
        return jsonify({'success': True, 'message': 'База данных и фото очищены'})
    except Exception:
        logger.exception('clear_database failed')
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка при очистке. Подробности в логах.'
        }), 500
