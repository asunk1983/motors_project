# modules/photo_manager/equipment_manager.py
"""Фото номенклатуры оборудования — та же дисковая схема, что и
modules/photo_manager/manager.py (двигатели) и incident_manager.py
(заявки Инцидентов), с отличиями:

- отдельная папка EQUIPMENT_PHOTOS_FOLDER ("PhotoE/"), а не PHOTOS_FOLDER
  или INCIDENT_PHOTOS_FOLDER — во избежание коллизий имён файлов между
  тремя разными сущностями, использующими одну и ту же схему именования
  ID{id}_{n}.ext;
- НЕТ синхронизации с колонкой в БД (equipment ничего не хранит про
  количество фото — тот же принцип, что incident_ticket, см. ТЗ раздел
  3.3: "Не заводим отдельную таблицу... список файлов для карточки
  получается сканированием PhotoE/");
- нет функции "заменить фото" (обрезка на месте) — как и у
  incident_manager.py, для Оборудования такого сценария в ТЗ нет;
  добавить будет несложно по аналогии с manager.py::replace_engine_photo,
  если понадобится позже.

routes/equipment_photo_routes.py — тонкая HTTP-обёртка, не дублирует
логику (тот же принцип, что и routes/photos.py для двигателей,
routes/incident_photo_routes.py для заявок).
"""
import os
import re
import glob
from flask import send_file, jsonify

from config.settings import ALLOWED_PHOTO_EXT

_photo_paths_cache = {}


def invalidate_photo_cache():
    """Clear the photo path cache. Call after PhotoE/ folder replacement
    (например, при восстановлении из бэкапа, если бэкапы когда-нибудь
    начнут включать и эту папку)."""
    global _photo_paths_cache
    _photo_paths_cache.clear()


def _photos_folder():
    from modules import db as db_module
    return db_module.EQUIPMENT_PHOTOS_FOLDER


def equipment_photo_disk_paths(equipment_id):
    """Список путей к файлам фото на диске для оборудования — реальное
    сканирование по маске ID{equipment_id}_*.{ext}, источник истины —
    файловая система."""
    if equipment_id in _photo_paths_cache:
        return _photo_paths_cache[equipment_id]

    folder = _photos_folder()
    paths = []
    for ext in ALLOWED_PHOTO_EXT:
        pattern = f"ID{equipment_id}_*.{ext.lstrip('.')}"
        paths.extend(glob.glob(os.path.join(folder, pattern)))
    sorted_paths = sorted(paths)
    _photo_paths_cache[equipment_id] = sorted_paths
    return sorted_paths


def next_photo_index(equipment_id):
    """Следующий свободный порядковый номер фото — по факту наличия
    файлов на диске (max существующего номера + 1)."""
    max_idx = 0
    pattern = re.compile(rf'^ID{equipment_id}_(\d+)\.')
    for p in equipment_photo_disk_paths(equipment_id):
        m = pattern.match(os.path.basename(p))
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def get_equipment_photos(equipment_id):
    """Список словарей {filename, path} для фото оборудования. БД не
    требуется — equipment_id сам по себе достаточен для поиска на диске."""
    paths = equipment_photo_disk_paths(equipment_id)
    return [
        {'filename': os.path.basename(p), 'path': f'/api/equipment-photos/{os.path.basename(p)}'}
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


def upload_equipment_photos(equipment_id, files):
    """Сохраняет загруженные файлы фото оборудования. files — список
    объектов FileStorage (request.files.getlist('photos')). Существование
    самой записи оборудования в БД проверяет вызывающий route
    (equipment_repo.get_equipment_by_id) — этот модуль работает только с
    диском, БД не трогает вообще."""
    folder = _photos_folder()
    os.makedirs(folder, exist_ok=True)
    next_idx = next_photo_index(equipment_id)

    saved = 0
    skipped = 0
    for f in files:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_PHOTO_EXT:
            skipped += 1
            continue
        photo_filename = f"ID{equipment_id}_{next_idx + saved}{ext}"
        f.save(os.path.join(folder, photo_filename))
        saved += 1

    if equipment_id in _photo_paths_cache:
        del _photo_paths_cache[equipment_id]

    return jsonify({'success': True, 'uploaded': saved, 'skipped': skipped})


def delete_equipment_photo(equipment_id, filename):
    """Удаляет одно фото с диска."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    if not filename.startswith(f'ID{equipment_id}_'):
        return jsonify({'error': 'Фото не принадлежит этой записи оборудования'}), 403
    photo_path = os.path.join(_photos_folder(), filename)
    if not os.path.exists(photo_path):
        return jsonify({'error': 'Фото не найдено'}), 404
    os.remove(photo_path)
    if equipment_id in _photo_paths_cache:
        del _photo_paths_cache[equipment_id]
    return jsonify({'success': True})


def delete_equipment_photos_from_disk(equipment_id):
    """Удаляет ВСЕ фото оборудования с диска — вызывается роутом удаления
    оборудования ПОСЛЕ успешного удаления записи из БД (тот же паттерн,
    что manager.py::delete_engine_photos_from_disk у routes/engines.py и
    incident_manager.py::delete_ticket_photos_from_disk). Ошибки удаления
    отдельных файлов не прерывают остальные."""
    removed = 0
    errors = []
    for path in equipment_photo_disk_paths(equipment_id):
        try:
            os.remove(path)
            removed += 1
        except OSError as e:
            errors.append((path, str(e)))
    if equipment_id in _photo_paths_cache:
        del _photo_paths_cache[equipment_id]
    return removed, errors


def count_all_photos() -> int:
    """Общее количество файлов фото во ВСЕЙ PhotoE/ (не по конкретной
    записи) — ТЗ раздел 4 (дашборд-счётчики: equipment_photos_count).
    Простое сканирование по расширениям, тот же принцип, что
    equipment_photo_disk_paths(), но без фильтра по id."""
    folder = _photos_folder()
    if not os.path.isdir(folder):
        return 0
    count = 0
    for ext in ALLOWED_PHOTO_EXT:
        count += len(glob.glob(os.path.join(folder, f"*.{ext.lstrip('.')}")))
    return count
