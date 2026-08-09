"""Маршруты импорта и очистки данных.

Вынесено из app.py. Использует парсер из modules/engine_parser/parser.py
(функции parse_file_fast, extract_images_from_excel) и утилиту логирования
из utils/logging.py.
"""
import os
import glob
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify

from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER
from modules.engine_parser.parser import parse_file_fast, extract_images_from_excel
from utils.logging import log_message
from config.settings import MAX_WORKERS

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
    """Очистить БД: удалить все двигатели, режимы, работы и фото.
    Пользователи и токены сохраняются (чтобы админ мог снова зайти).

    ИСПРАВЛЕНО: раньше после DELETE файл engine_data.db не уменьшался —
    SQLite помечает страницы удалённых строк как свободные (freelist),
    но не отдаёт их обратно файловой системе, пока не выполнен VACUUM.
    На реальной БД проекта это давало ~36% файла "мёртвого" места после
    очистки. Плюс сбрасываем sqlite_sequence для очищенных таблиц, чтобы
    после полной очистки ID снова начинались с 1, а не продолжали расти
    от последнего значения AUTOINCREMENT (это нормальное поведение SQLite
    вне очистки, но при полном "СТИРАТЬ" разумно обнулить и счётчик)."""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM operating_modes')
            cursor.execute('DELETE FROM maintenance_works')
            cursor.execute('DELETE FROM engines')
            # Сброс автоинкремента только для очищенных таблиц —
            # changelog/wishlist/users/tokens не трогаем.
            cursor.execute(
                "DELETE FROM sqlite_sequence WHERE name IN "
                "('engines', 'operating_modes', 'maintenance_works')"
            )
            conn.commit()
            # WAL: обычный VACUUM не всегда достаточно освобождает место,
            # пока не сброшен write-ahead log в основной файл.
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.execute('VACUUM')

        # Удаляем все фотографии с диска
        if os.path.exists(PHOTOS_FOLDER):
            shutil.rmtree(PHOTOS_FOLDER, ignore_errors=True)
        os.makedirs(PHOTOS_FOLDER, exist_ok=True)

        return jsonify({'success': True, 'message': 'База данных и фото очищены'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
