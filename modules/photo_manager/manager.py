# modules/photo_manager/manager.py
"""Единственный источник правды для файловых операций с фото двигателей:
дисковые пути, загрузка, удаление, замена (обрезка), отдача файлов и
полная чистка фото движка при его удалении.

СХЕМА ИМЕНОВАНИЯ: ID{engine_id}_{n}.{ext}, например ID157_1.jpg — первое
фото двигателя с id=157. Связь фото->двигатель определяется исключительно
через engine_id в имени файла, БД для поиска фото не нужна.

routes/photos.py — тонкая HTTP-обёртка над этим модулем, не дублирует
логику. routes/engines.py вызывает delete_engine_photos_from_disk() при
удалении двигателя.

PHOTOS_FOLDER читается динамически из modules.db при каждом вызове (а не
импортируется один раз при загрузке модуля), чтобы тестовый monkeypatch
`setattr(db_module, 'PHOTOS_FOLDER', ...)` был здесь виден — так же, как
раньше было устроено в routes/photos.py."""
import os
import re
import time
import uuid
import glob
from flask import send_file, jsonify

from config.settings import ALLOWED_PHOTO_EXT

# Cache for engine_photo_disk_paths: {engine_id: list of paths}
_photo_paths_cache = {}


def invalidate_photo_cache():
    """Clear the photo path cache. Call after photos folder replacement."""
    global _photo_paths_cache
    _photo_paths_cache.clear()


def _photos_folder():
    from modules import db as db_module
    return db_module.PHOTOS_FOLDER


def engine_photo_disk_paths(engine_id):
    """Список путей к файлам фото на диске для двигателя — реальное
    сканирование по маске ID{engine_id}_*.{ext}, источник истины —
    файловая система."""
    # Check cache first
    if engine_id in _photo_paths_cache:
        return _photo_paths_cache[engine_id]

    folder = _photos_folder()
    paths = []
    for ext in ALLOWED_PHOTO_EXT:
        pattern = f"ID{engine_id}_*.{ext.lstrip('.')}"
        paths.extend(glob.glob(os.path.join(folder, pattern)))
    sorted_paths = sorted(paths)
    _photo_paths_cache[engine_id] = sorted_paths
    return sorted_paths


def next_photo_index(engine_id):
    """Следующий свободный порядковый номер фото — по факту наличия файлов
    на диске (max существующего номера + 1), не по photo_count из БД."""
    max_idx = 0
    pattern = re.compile(rf'^ID{engine_id}_(\d+)\.')
    for p in engine_photo_disk_paths(engine_id):
        m = pattern.match(os.path.basename(p))
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def get_engine_photos(engine_id):
    """Возвращает список словарей {filename, path} для фото двигателя.
    БД не требуется — engine_id сам по себе достаточен для поиска на диске."""
    paths = engine_photo_disk_paths(engine_id)
    return [{'filename': os.path.basename(p), 'path': f'/api/photos/{os.path.basename(p)}'} for p in paths]


def get_photo(filename):
    """Отдаёт файл фото с заголовком no-cache (см. обоснование в app.py)."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    photo_path = os.path.join(_photos_folder(), filename)
    if os.path.exists(photo_path):
        response = send_file(photo_path)
        response.headers['Cache-Control'] = 'no-cache'
        return response
    return jsonify({'error': 'Photo not found'}), 404


def upload_engine_photos(conn, engine_id, files):
    """Сохраняет загруженные файлы фото и обновляет photo_count.
    files — список объектов FileStorage (request.files.getlist('photos'))."""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM engines WHERE id = ?', (engine_id,))
    if not cursor.fetchone():
        return jsonify({'error': 'Двигатель не найден'}), 404

    folder = _photos_folder()
    next_idx = next_photo_index(engine_id)

    saved = 0
    skipped = 0
    for f in files:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_PHOTO_EXT:
            skipped += 1
            continue
        photo_filename = f"ID{engine_id}_{next_idx + saved}{ext}"
        f.save(os.path.join(folder, photo_filename))
        saved += 1

    # Invalidate cache for this engine_id because we have added new photos
    if engine_id in _photo_paths_cache:
        del _photo_paths_cache[engine_id]
    new_count = len(engine_photo_disk_paths(engine_id))
    if saved:
        cursor.execute('UPDATE engines SET photo_count = ? WHERE id = ?', (new_count, engine_id))
        conn.commit()

    return jsonify({'success': True, 'uploaded': saved, 'skipped': skipped, 'photo_count': new_count})


def delete_engine_photo(conn, engine_id, filename):
    """Удаляет одно фото с диска и пересчитывает photo_count с диска
    (не декремент — самовосстанавливается при рассинхроне)."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    if not filename.startswith(f'ID{engine_id}_'):
        return jsonify({'error': 'Фото не принадлежит этому двигателю'}), 403
    photo_path = os.path.join(_photos_folder(), filename)
    if not os.path.exists(photo_path):
        return jsonify({'error': 'Фото не найдено'}), 404
    os.remove(photo_path)
    # Invalidate cache for this engine_id because we have deleted a photo
    if engine_id in _photo_paths_cache:
        del _photo_paths_cache[engine_id]
    new_count = len(engine_photo_disk_paths(engine_id))
    cursor = conn.cursor()
    cursor.execute('UPDATE engines SET photo_count = ? WHERE id = ?', (new_count, engine_id))
    conn.commit()

    return jsonify({'success': True, 'photo_count': new_count})


def delete_engine_photos_from_disk(engine_id):
    """Удаляет ВСЕ фото двигателя с диска — используется при удалении
    самого двигателя (routes/engines.py::delete_engine), ПОСЛЕ успешного
    удаления записи из БД. Не трогает БД (photo_count не обновляет —
    запись engines уже удалена к этому моменту). Возвращает количество
    удалённых файлов; ошибки удаления отдельных файлов не прерывают
    остальные — движок в БД уже удалён, максимум что можно сделать
    для "осиротевших" файлов — попытаться убрать все, залогировав то,
    что не получилось."""
    removed = 0
    errors = []
    for path in engine_photo_disk_paths(engine_id):
        try:
            os.remove(path)
            removed += 1
        except OSError as e:
            errors.append((path, str(e)))
    # Invalidate cache for this engine_id because we have deleted all photos
    if engine_id in _photo_paths_cache:
        del _photo_paths_cache[engine_id]
    return removed, errors


def _save_upload_atomically(file_storage, dest_path, retries=3, delay=0.15):
    """Сохраняет загруженный файл через временное имя + os.replace (атомарная
    подмена вместо прямой перезаписи dest_path), с несколькими попытками при
    переходной ошибке записи. На Windows перезапись файла, который в этот же
    момент читает другой запрос, может дать PermissionError/OSError — на
    Linux такое почти не встречается, но retry здесь безвреден и там же.
    os.replace() атомарен: до его успешного завершения старый файл остаётся
    нетронутым, поэтому неудачная попытка не оставляет диск в
    промежуточном/повреждённом состоянии."""
    tmp_path = f'{dest_path}.tmp{uuid.uuid4().hex[:8]}'
    last_err = None
    for attempt in range(retries):
        try:
            file_storage.stream.seek(0)
            file_storage.save(tmp_path)
            os.replace(tmp_path, dest_path)
            return
        except OSError as e:
            last_err = e
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            time.sleep(delay)
    raise last_err


def replace_engine_photo(engine_id, filename, file_storage):
    """Перезапись уже загруженного фото (используется обрезкой в карточке).
    photo_count не меняется — количество фото то же, меняется только
    содержимое (и, возможно, расширение) одного файла."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    folder = _photos_folder()
    old_path = os.path.join(folder, filename)
    if not os.path.exists(old_path):
        return jsonify({'error': 'Фото не найдено'}), 404

    if not filename.startswith(f'ID{engine_id}_'):
        return jsonify({'error': 'Фото не принадлежит этому двигателю'}), 403

    if not file_storage or not file_storage.filename:
        return jsonify({'error': 'Файл не передан'}), 400
    new_ext = os.path.splitext(file_storage.filename)[1].lower()
    if new_ext not in ALLOWED_PHOTO_EXT:
        return jsonify({'error': 'Недопустимый формат файла'}), 400

    name_no_ext, _old_ext = os.path.splitext(filename)
    new_filename = f'{name_no_ext}{new_ext}'
    new_path = os.path.join(folder, new_filename)
    _save_upload_atomically(file_storage, new_path)
    if new_path != old_path and os.path.exists(old_path):
        for attempt in range(3):
            try:
                os.remove(old_path)
                break
            except OSError:
                time.sleep(0.15)

    return jsonify({'success': True, 'filename': new_filename, 'path': f'/api/photos/{new_filename}'})