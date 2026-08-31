# PROJECT_CORE.md — Технический снимок проекта (инварианты)

> Создано автоматически. Не менять код — только этот файл. Объём: ~1-2 экрана.

---

## 1. Стек и архитектура

**Технологии:** Python 3.11+, Flask, SQLite (WAL, `PRAGMA foreign_keys=ON`), pandas/openpyxl (импорт), openpyxl + PIL (экспорт), jinja2 (templates), vanilla JS (static/js).

**Слои:** `templates` → `static/js` → `routes/` (blueprints) → `services/` / `repositories/` → `modules/db.py` (schema, connection) + `config/settings.py` (paths).

**Зарегистрированные blueprints** (`routes/__init__.py::create_blueprints`):

| Blueprint | url_prefix | Файл |
|---|---|---|
| auth_bp | `/api/auth` | `routes/auth.py` |
| engines_bp | `/api` | `routes/engines.py` |
| photos_bp | `/api` | `routes/photos.py` |
| import_bp | `/api` | `routes/import_routes.py` |
| export_bp | `/api` | `routes/export_routes.py` |
| backup_bp | `/api/backup` | `routes/backup_routes.py` |
| changelog_bp | `/api` | `routes/changelog.py` |
| status_bp | `/api` | `routes/status.py` |
| search_bp | `/api` | `routes/search.py` |
| pages_bp | (нет) | `routes/pages.py` |

**Файлы в `routes/`, не зарегистрированные в `__init__.py`:** все 10 файлов зарегистрированы — мёртвого кода нет.

---

## 2. Схема БД — только структура

Таблицы (из `modules/db.py::init_db`):

| Таблица | PK | FK / ON DELETE |
|---|---|---|
| `engines` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | — |
| `operating_modes` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | `engine_id → engines(id) ON DELETE CASCADE` |
| `maintenance_works` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | `engine_id → engines(id) ON DELETE CASCADE` |
| `changelog_entries` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | — |
| `wishlist_items` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | — |
| `users` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | — |
| `tokens` | `id INTEGER PRIMARY KEY AUTOINCREMENT` | `user_id → users(id) ON DELETE CASCADE` |

**Важно:** `ON DELETE CASCADE` прописан в схеме, но **на продакшен-БД (созданной до добавления CASCADE) он не работает**. Поэтому `repositories/engine_repo.py::delete()` удаляет дочерние записи явно (строки 235-237).

**Индексы:** `idx_modes_engine`, `idx_works_engine`, `idx_changelog_date`, по всем основным полям `engines` + `idx_tokens_hash`, `idx_tokens_user`.

**Auto-migration** (`_ensure_column`): добавляет `created_at`, `updated_at` в `engines` и `last_login`, `last_edit` в `users` при первом запуске новой версии. Backfill проставляет одинаковый timestamp всем старым записям.

---

## 3. Путевые/конфигурационные константы

Единственное определение — `config/settings.py` (строки 11-15):

```python
DB_PATH = str(BASE_DIR / 'engine_data.db')
MOTORS_FOLDER = str(BASE_DIR / 'motors')
PHOTOS_FOLDER = str(BASE_DIR / 'photos')
BACKUPS_FOLDER = str(BASE_DIR / 'backups')
BACKUP_STAGING_FOLDER = str(BASE_DIR / 'backup_staging')
```

**Дублирующие определения (точечный поиск по именам):**

| Константа | Определение 1 (каноническое) | Определение 2 (дубликат) | Примечание |
|---|---|---|---|
| `DB_PATH` | `config/settings.py:11` | `modules/backup_system/backup.py:35` (`DB_PATH = db_module.DB_PATH`) | Реэкспорт из `modules.db`, не новое значение |
| `PHOTOS_FOLDER` | `config/settings.py:13` | `modules/backup_system/backup.py:36` | Аналогично |
| `BACKUPS_FOLDER` | `config/settings.py:14` | `modules/backup_system/backup.py:37` | Аналогично |
| `BACKUP_STAGING_FOLDER` | `config/settings.py:15` | `modules/backup_system/backup.py:38` | Аналогично |
| `BACKUPS_FOLDER` | `config/settings.py:14` | `modules/backup_system/__init__.py:3` (реэкспорт) | Публичный API модуля бэкапа |
| `BACKUP_STAGING_FOLDER` | `config/settings.py:15` | `modules/backup_system/__init__.py:4` (реэкспорт) | Публичный API модуля бэкапа |

**Вывод:** дубликатов значений нет — везде реэкспорт из `modules.db` (который импортирует из `config.settings`). Единственный источник правды — `config/settings.py`.

---

## 4. Контракт имён файлов на диске (фото)

**Актуальная схема** (процитировано из `modules/photo_manager/manager.py:6-8`):

> СХЕМА ИМЕНОВАНИЯ: `ID{engine_id}_{n}.{ext}`, например `ID157_1.jpg` — первое фото двигателя с id=157. Связь фото→двигатель определяется исключительно через engine_id в имени файла, БД для поиска фото не нужна.

**Точки порождения схемы (upload/импорт):**
1. `modules/engine_parser/parser.py:209` — `extract_images_from_excel`: `photo_filename = f"ID{engine_id}_{idx+1}{ext}"`
2. `modules/photo_manager/manager.py:111` — `upload_engine_photos`: `photo_filename = f"ID{engine_id}_{next_idx + saved}{ext}"`

**Точки парсинга (поиск/удаление/замена):**
1. `modules/photo_manager/manager.py:53-54` — `engine_photo_disk_paths`: `pattern = f"ID{engine_id}_*.{ext.lstrip('.')}"` (glob по маске)
2. `modules/photo_manager/manager.py:64-68` — `next_photo_index`: regex `rf'^ID{engine_id}_(\d+)\.'` для извлечения номера

**Находка:** в `diag_photos.py:22` используется **старая схема** `pattern = f"{base}_img_*_{eid}.{ext.lstrip('.')}"` (через `normalize_base_name` из имени файла Excel). Это диагностический скрипт, не продакшн-код, но схема расходится.

---

## 5. Жизненный цикл ID записей

**Создание двигателя (поштучное, через UI):**
- `repositories/engine_repo.py:130-148` — `_next_free_id()`: ищет минимальный свободный id (1, либо первую «дыру», либо `max(id)+1`).
- Оборачивается в `BEGIN IMMEDIATE` (стр. 176) для атомарности при конкуренции.
- **Не использует AUTOINCREMENT** — id никогда не «убегает» вперёд количества записей.

**Массовый импорт (`routes/import_routes.py`):**
- `executemany` без указания id — отдаёт AUTOINCREMENT (строки 122-130).
- **Предположение:** импорт выполняется **только на пустую БД** (проверка строки 93: `existing_count > 0 → 400`).
- `first_id = last_insert_rowid() - len(all_engines) + 1` (стр. 130) корректен только при пустой таблице.

**Удаление:**
- `engine_repo.py::delete()` удаляет дочерние записи явно (CASCADE не работает на проде), затем сам двигатель.
- Фото на диске удаляет роут `routes/engines.py::delete_engine` через `photo_manager.delete_engine_photos_from_disk()` — **перед** удалением из БД (стр. 133-137). Если фото не удалились — транзакция БД не выполняется.

---

## 6. Обслуживание БД

**Очистка (`/api/clear` → `routes/import_routes.py::clear_database`):**
1. `DELETE FROM operating_modes`, `maintenance_works`, `engines`
2. `DELETE FROM sqlite_sequence WHERE name IN ('engines','operating_modes','maintenance_works')` — сброс AUTOINCREMENT
3. `PRAGMA wal_checkpoint(TRUNCATE)` + `VACUUM` — возврат места ФС (WAL требует checkpoint)
4. `shutil.rmtree(PHOTOS_FOLDER, ignore_errors=True)` + `os.makedirs(PHOTOS_FOLDER)` — полная чистка фото

**Журналирование:** `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL` (установлены в `modules/db.py:get_db_connection` строки 32-33).

---

## 7. Активные расхождения (только то, что есть СЕЙЧАС)

1. **Две независимые реализации схемы имён фото:**
   - Каноническая: `ID{engine_id}_{n}.{ext}` — `photo_manager`, `engine_parser` (импорт фото из Excel)
   - Устаревшая в `diag_photos.py:22`: `{base}_img_*_{eid}.{ext}` через `normalize_base_name` от имени Excel-файла. Диагностический скрипт, не влияет на продакшн, но схема расходится.

2. **Дублирующая логика получения путей фото (исправлена в export):**
   - В `services/export_service.py:209-221` (`_get_photo_paths`) **раньше была своя реализация** со старой схемой `engine_{id}_...`. Комментарий строк 212-217 фиксирует находку: теперь делегирует в `photo_manager.engine_photo_disk_paths` — единственный источник истины.

3. **ON DELETE CASCADE в схеме, но не работающий на проде:**
   - `engine_repo.py:225-227` явно комментирует: удаление дочерних записей вручную. Риск: если кто-то вызовет `DELETE FROM engines` напрямую (мимо репозитория) — дочерние записи останутся-сиротами.

4. **Константы без явных потребителей (проверено точечным поиском):**
   - `MOTORS_FOLDER` используется только в `app.py`, `import_routes.py`, `status.py`, `promote_and_cleanup.py`, тестах — все найдены.
   - `BACKUP_STAGING_FOLDER` — в `backup_routes.py`, `backup.py`, `backup_system/__init__.py`, `backup_service.py` — все найдены.
   - `ALLOWED_PHOTO_EXT` — в `parser.py`, `photo_manager`, `diag_photos.py`, `config/settings.py` — все найдены.

5. **Два способа назначения ID (поштучный vs массовый):**
   - Поштучный: явный поиск свободного id (`_next_free_id`).
   - Массовый: AUTOINCREMENT (на пустую БД).
   - Инвариант «max(id) ≤ count(*)» гарантирован только для поштучного пути. После импорта + поштучных созданий/удалений дыры могут появиться — `_next_free_id` их заполнит.

---

## 8. Сводка

- **Файлов проекта (Python, без тестов/кэша/venv):** ~45
- **Уникальных путевых констант:** 5 (`DB_PATH`, `MOTORS_FOLDER`, `PHOTOS_FOLDER`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER`) — все определены в `config/settings.py`
- **Найденных активных расхождений (раздел 7):** 5