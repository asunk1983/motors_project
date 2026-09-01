# modules/photo_manager/incident_manager.py
"""Фото-вложения заявок "Инцидентов" — та же дисковая схема, что и
modules/photo_manager/manager.py (двигатели), с отличиями:

- отдельная папка INCIDENT_PHOTOS_FOLDER ("PhotoI/"), а не PHOTOS_FOLDER —
  во избежание коллизий имён файлов между двумя разными сущностями,
  использующими одну и ту же схему именования ID{id}_{n}.ext;
- НЕТ синхронизации с колонкой в БД (в отличие от engines.photo_count) —
  incident_ticket ничего не хранит про количество фото, счётчик всегда
  считается с диска (ТЗ раздел 2.2: "без отдельной таблицы в БД").
- нет функции "заменить фото" (обрезка на месте) — в ТЗ для Инцидентов
  такого сценария нет (в отличие от карточки двигателя); добавить будет
  несложно по аналогии с manager.py::replace_engine_photo, если
  понадобится позже.

routes/incident_ticket_routes.py и routes/incident_photo_routes.py —
тонкие HTTP-обёртки, не дублируют логику (тот же принцип, что и
routes/photos.py для двигателей).
"""
import os
import re
import glob
from flask import send_file, jsonify

from config.settings import ALLOWED_PHOTO_EXT

_photo_paths_cache = {}


def invalidate_photo_cache():
    """Clear the photo path cache. Call after PhotoI/ folder replacement
    (например, при восстановлении из бэкапа, если бэкапы когда-нибудь
    начнут включать и эту папку)."""
    global _photo_paths_cache
    _photo_paths_cache.clear()


def _photos_folder():
    from modules import db as db_module
    return db_module.INCIDENT_PHOTOS_FOLDER


def ticket_photo_disk_paths(ticket_id):
    """Список путей к файлам фото на диске для заявки — реальное
    сканирование по маске ID{ticket_id}_*.{ext}, источник истины —
    файловая система."""
    if ticket_id in _photo_paths_cache:
        return _photo_paths_cache[ticket_id]

    folder = _photos_folder()
    paths = []
    for ext in ALLOWED_PHOTO_EXT:
        pattern = f"ID{ticket_id}_*.{ext.lstrip('.')}"
        paths.extend(glob.glob(os.path.join(folder, pattern)))
    sorted_paths = sorted(paths)
    _photo_paths_cache[ticket_id] = sorted_paths
    return sorted_paths


def next_photo_index(ticket_id):
    """Следующий свободный порядковый номер фото — по факту наличия
    файлов на диске (max существующего номера + 1)."""
    max_idx = 0
    pattern = re.compile(rf'^ID{ticket_id}_(\d+)\.')
    for p in ticket_photo_disk_paths(ticket_id):
        m = pattern.match(os.path.basename(p))
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def get_ticket_photos(ticket_id):
    """Список словарей {filename, path} для фото заявки. БД не требуется —
    ticket_id сам по себе достаточен для поиска на диске."""
    paths = ticket_photo_disk_paths(ticket_id)
    return [
        {'filename': os.path.basename(p), 'path': f'/api/incident-photos/{os.path.basename(p)}'}
        for p in paths
    ]


def get_photo(filename):
    """Отдаёт файл фото с заголовком no-cache (см. тот же паттерн в
    manager.py::get_photo и обоснование в app.py)."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    photo_path = os.path.join(_photos_folder(), filename)
    if os.path.exists(photo_path):
        response = send_file(photo_path)
        response.headers['Cache-Control'] = 'no-cache'
        return response
    return jsonify({'error': 'Photo not found'}), 404


def upload_ticket_photos(ticket_id, files):
    """Сохраняет загруженные файлы фото заявки. files — список объектов
    FileStorage (request.files.getlist('photos')). Существование самой
    заявки в БД проверяет вызывающий route (incident_ticket_repo.get_by_id)
    — этот модуль работает только с диском, БД не трогает вообще."""
    folder = _photos_folder()
    os.makedirs(folder, exist_ok=True)
    next_idx = next_photo_index(ticket_id)

    saved = 0
    skipped = 0
    for f in files:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_PHOTO_EXT:
            skipped += 1
            continue
        photo_filename = f"ID{ticket_id}_{next_idx + saved}{ext}"
        f.save(os.path.join(folder, photo_filename))
        saved += 1

    if ticket_id in _photo_paths_cache:
        del _photo_paths_cache[ticket_id]

    return jsonify({'success': True, 'uploaded': saved, 'skipped': skipped})


def replace_ticket_photo(ticket_id, filename, file):
    """Перезаписывает уже существующее фото на диске — используется при
    обрезке (crop) в UI, тот же паттерн, что
    equipment_manager.py::replace_equipment_photo для оборудования и
    manager.py::replace_engine_photo для двигателей.

    file — объект FileStorage (request.files['photo']), содержащий уже
    обрезанный canvas.toBlob()-результат. Если его расширение не
    совпадает с исходным, файл пересохраняется под тем же базовым именем,
    но с новым расширением, а старый файл — удаляется."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    if not filename.startswith(f'ID{ticket_id}_'):
        return jsonify({'error': 'Фото не принадлежит этой заявке'}), 403

    folder = _photos_folder()
    old_path = os.path.join(folder, filename)
    if not os.path.exists(old_path):
        return jsonify({'error': 'Фото не найдено'}), 404

    if not file or not file.filename:
        return jsonify({'error': 'Файл не передан'}), 400

    new_ext = os.path.splitext(file.filename)[1].lower()
    if new_ext not in ALLOWED_PHOTO_EXT:
        return jsonify({'error': 'Недопустимый формат файла'}), 400

    base_name = filename[:filename.rfind('.')]
    new_filename = base_name + new_ext
    new_path = os.path.join(folder, new_filename)

    # Временный файл + os.replace() — атомарная запись, тот же приём, что
    # и в equipment_manager.py::replace_equipment_photo.
    tmp_path = new_path + '.tmp'
    file.save(tmp_path)
    os.replace(tmp_path, new_path)

    if new_filename != filename:
        try:
            os.remove(old_path)
        except OSError:
            pass

    if ticket_id in _photo_paths_cache:
        del _photo_paths_cache[ticket_id]

    return jsonify({'success': True, 'filename': new_filename})


def delete_ticket_photo(ticket_id, filename):
    """Удаляет одно фото с диска."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    if not filename.startswith(f'ID{ticket_id}_'):
        return jsonify({'error': 'Фото не принадлежит этой заявке'}), 403
    photo_path = os.path.join(_photos_folder(), filename)
    if not os.path.exists(photo_path):
        return jsonify({'error': 'Фото не найдено'}), 404
    os.remove(photo_path)
    if ticket_id in _photo_paths_cache:
        del _photo_paths_cache[ticket_id]
    return jsonify({'success': True})


def delete_ticket_photos_from_disk(ticket_id):
    """Удаляет ВСЕ фото заявки с диска — вызывается services/incident_service
    после успешного удаления самой заявки из БД (тот же паттерн, что
    manager.py::delete_engine_photos_from_disk у routes/engines.py).
    Ошибки удаления отдельных файлов не прерывают остальные."""
    removed = 0
    errors = []
    for path in ticket_photo_disk_paths(ticket_id):
        try:
            os.remove(path)
            removed += 1
        except OSError as e:
            errors.append((path, str(e)))
    if ticket_id in _photo_paths_cache:
        del _photo_paths_cache[ticket_id]
    return removed, errors


def count_all_photos() -> int:
    """Общее количество файлов фото во ВСЕЙ PhotoI/ (не по конкретной
    заявке) — ТЗ раздел 4 (дашборд-счётчики: incident_photos_count)."""
    folder = _photos_folder()
    if not os.path.isdir(folder):
        return 0
    count = 0
    for ext in ALLOWED_PHOTO_EXT:
        count += len(glob.glob(os.path.join(folder, f"*.{ext.lstrip('.')}")))
    return count
