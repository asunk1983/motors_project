# PROJECT_SNAPSHOT.md — Технический снимок проекта Motors

**Дата создания:** 2026-08-05 09:38:00 (Europe/Moscow, UTC+3)
**Ветка git:** main
**SHA последнего коммита:** d0f25abd14ad46fd46bd49dacf90fde809a33529
**Git status:** чистый (нет незакоммиченных изменений)
**Рабочая директория:** C:\motors_project
**Python версия:** Python 3.11.9
**Виртуальное окружение:** C:\motors_project\.venv\Scripts\python.exe

---

## 0. Метаданные снимка

### Установленные пакеты (pip freeze)
```
Flask==3.0.3
Flask-Cors==4.0.1
openpyxl==3.1.5
pandas==2.2.2
Pillow==10.4.0
```

---

## 1. Полное дерево проекта

```
C:\motors_project
├── .clineignore
├── .gitignore
├── app.py
├── diag_modal.py
├── diag_photos.py
├── measurement.py
├── promote_and_cleanup.py
├── reset_admin_password.py
├── users_dump.sql
├── config/
│   └── settings.py
├── docs/
│   ├── e2e_failure_diagnosis.md
│   ├── e2e_scenarios.md
│   ├── e2e_test_results.md
│   ├── PROJECT_SNAPSHOT.md
│   ├── project_structure_snapshot.md
│   └── ui_audit.md
├── modules/
│   ├── __init__.py
│   ├── db.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── db_users.py
│   │   ├── file_users.py
│   │   ├── hashing.py
│   │   ├── tokens.py
│   │   └── decorators.py
│   ├── backup_system/
│   │   ├── __init__.py
│   │   └── backup.py
│   ├── engine_parser/
│   │   ├── __init__.py
│   │   └── parser.py
│   └── photo_manager/
│       ├── __init__.py
│       └── manager.py
├── repositories/
│   ├── __init__.py
│   ├── engine_repo.py
│   ├── mode_repo.py
│   └── work_repo.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── backup_routes.py
│   ├── changelog.py
│   ├── engines.py
│   ├── export_routes.py
│   ├── import_routes.py
│   ├── pages.py
│   ├── photos.py
│   ├── search.py
│   └── status.py
├── schemas/
│   ├── __init__.py
│   └── engine_schema.py
├── services/
│   ├── __init__.py
│   ├── backup_service.py
│   └── export_service.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js
│       ├── app.js
│       ├── auth.js
│       ├── backupManager.js
│       ├── catalog.js
│       ├── common.js
│       ├── engineCard.js
│       ├── engines.js
│       ├── exportManager.js
│       ├── importer.js
│       ├── locationTree.js
│       ├── print.js
│       ├── search.js
│       └── state.js
├── templates/
│   ├── index.html
│   └── print.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── helpers.py
│   │   ├── test_01_auth.py
│   │   ├── test_02_catalog.py
│   │   ├── test_03_add_engine.py
│   │   ├── test_04_detail.py
│   │   ├── test_05_photos.py
│   │   ├── test_06_import.py
│   │   ├── test_07_search.py
│   │   ├── test_08_settings.py
│   │   ├── test_09_backups.py
│   │   ├── test_10_info.py
│   │   └── test_11_misc.py
│   ├── test_backup_system/
│   │   └── test_backup.py
│   ├── test_repositories/
│   │   └── test_engine_repo.py
│   └── test_utils/
│       ├── test_date.py
│       ├── test_file_store.py
│       └── test_naming.py
└── utils/
    ├── __init__.py
    ├── date.py
    ├── file_store.py
    ├── logging.py
    └── naming.py
```

---

## 2. Обзор архитектуры

### Технологический стек
- **Backend:** Flask 3.0.3, Python 3.11
- **Database:** SQLite (WAL mode, foreign_keys=ON)
- **Frontend:** Vanilla JS (ES6 modules через глобальные переменные), CSS Grid/Flexbox
- **Excel/Import:** pandas + openpyxl
- **Images:** Pillow (для обрезки), openpyxl (извлечение из Excel)
- **Auth:** JWT-токены (SHA256), bcrypt-хеширование паролей

### Схема слоёв
```
templates/ (HTML) 
    → static/js/ (UI logic, state, API calls)
        → routes/ (Flask blueprints, HTTP layer)
            → repositories/ (SQL queries only)
            → services/ (business logic, orchestration)
            → modules/ (cross-cutting: db, auth, backup, photo_manager, engine_parser)
                → modules/db.py (DB connection, schema init)
```

### Зарегистрированные Flask Blueprints (routes/__init__.py)

| Blueprint | url_prefix | Исходный файл |
|-----------|------------|---------------|
| auth_bp | /api/auth | routes/auth.py |
| engines_bp | /api | routes/engines.py |
| photos_bp | /api | routes/photos.py |
| import_bp | /api | routes/import_routes.py |
| export_bp | /api | routes/export_routes.py |
| backup_bp | /api/backup | routes/backup_routes.py |
| changelog_bp | /api | routes/changelog.py |
| status_bp | /api | routes/status.py |
| search_bp | /api | routes/search.py |
| pages_bp | / | routes/pages.py |

**Порядок регистрации важен:** auth_bp регистрируется первым (before_app_request для загрузки текущего пользователя).

### Мёртвый код в routes/
Все файлы в routes/ зарегистрированы в routes/__init__.py. Незарегистрированных файлов нет.

---

## 3. База данных — полная схема

Все таблицы определены в `modules/db.py::init_db()` (строки 71-155).

### Таблица `engines`
| Поле | Тип | PK/AI | Назначение |
|------|-----|-------|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный ID двигателя |
| filename | TEXT | | Имя исходного Excel-файла |
| purpose | TEXT | | Назначение |
| workshop | TEXT | | Цех (числовое значение) |
| location | TEXT | | Место установки |
| engine_type | TEXT | | Тип двигателя |
| manufacturer | TEXT | | Производитель |
| serial_number | TEXT | | Заводской номер |
| bearing_front | TEXT | | Подшипник передний |
| bearing_rear | TEXT | | Подшипник задний |
| shaft_diameter | TEXT | | Диаметр вала |
| protection_class | TEXT | | Степень защиты |
| mounting_type | TEXT | | Тип крепления |
| temp_sensor | TEXT | | Датчик температуры |
| encoder | TEXT | | Энкодер |
| cooling | TEXT | | Охлаждение |
| note | TEXT | | Примечание |
| photo_count | INTEGER | DEFAULT 0 | Счётчик фото (синхронизируется с диском) |

**Индексы:** idx_engines_location, idx_engines_engine_type, idx_engines_manufacturer, idx_engines_serial_number, idx_engines_workshop, idx_engines_purpose

### Таблица `operating_modes`
| Поле | Тип | PK/AI | FK | Назначение |
|------|-----|-------|-----|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | | |
| engine_id | INTEGER | | REFERENCES engines(id) ON DELETE CASCADE | Ссылка на двигатель |
| frequency | TEXT | | | Частота (Гц) |
| power | TEXT | | | Мощность (кВт) |
| voltage | TEXT | | | Напряжение (В) |
| connection_type | TEXT | | | Тип подключения |
| current | TEXT | | | Ток (А) |
| rpm | TEXT | | | Обороты (об/мин) |

**Индекс:** idx_modes_engine (engine_id)

### Таблица `maintenance_works`
| Поле | Тип | PK/AI | FK | Назначение |
|------|-----|-------|-----|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | | |
| engine_id | INTEGER | | REFERENCES engines(id) ON DELETE CASCADE | Ссылка на двигатель |
| work_number | TEXT | | | Номер работы (порядковый) |
| date | TEXT | | | Дата (YYYY-MM-DD) |
| work_description | TEXT | | | Вид работ |
| isolation | TEXT | | | Сопротивление изоляции (МОм) |
| inspection | TEXT | | | Внешний осмотр |
| signature | TEXT | | | ФИО исполнителя |

**Индекс:** idx_works_engine (engine_id)

### Таблица `changelog_entries`
| Поле | Тип | PK/AI | Назначение |
|------|-----|-------|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| entry_date | TEXT | NOT NULL | Дата записи (YYYY-MM-DD) |
| text | TEXT | NOT NULL | Текст изменения |
| created_at | TEXT | NOT NULL | ISO timestamp создания |

**Индекс:** idx_changelog_date (entry_date)

### Таблица `wishlist_items`
| Поле | Тип | PK/AI | Назначение |
|------|-----|-------|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| text | TEXT | NOT NULL | Текст пожелания |
| done | INTEGER | NOT NULL DEFAULT 0 | Флаг выполнения (0/1) |
| created_at | TEXT | NOT NULL | ISO timestamp |

### Таблица `users`
| Поле | Тип | PK/AI | Назначение |
|------|-----|-------|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| username | TEXT | UNIQUE NOT NULL | Логин |
| password_hash | TEXT | NOT NULL | bcrypt-хеш |
| role | TEXT | NOT NULL DEFAULT 'user' | user/admin/superadmin |
| created_at | TEXT | NOT NULL | ISO timestamp |
| last_login | TEXT | | Последний вход |
| last_edit | TEXT | | Последнее редактирование |

**Индексы:** idx_tokens_hash (token_hash), idx_tokens_user (user_id)

### Таблица `tokens`
| Поле | Тип | PK/AI | FK | Назначение |
|------|-----|-------|-----|------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | | |
| user_id | INTEGER | | REFERENCES users(id) ON DELETE CASCADE | Владелец токена |
| token_hash | TEXT | UNIQUE NOT NULL | SHA256 токена |
| created_at | TEXT | NOT NULL | Создан |
| expires_at | TEXT | | Истекает (опционально) |

---

### ON DELETE CASCADE — реальное поведение

**Важно:** В `modules/db.py` (строки 103, 116, 153) внешние ключи объявлены с `ON DELETE CASCADE`, но **на продакшен-БД (созданной до добавления CASCADE) каскад не работает**. Поэтому в `repositories/engine_repo.py::delete()` (строки 199-216) дочерние записи удаляются **явно** перед удалением двигателя:

```python
cur.execute('DELETE FROM operating_modes WHERE engine_id = ?', (engine_id,))
cur.execute('DELETE FROM maintenance_works WHERE engine_id = ?', (engine_id,))
cur.execute('DELETE FROM engines WHERE id = ?', (engine_id,))
```

---

## 4. Backend — карта роутов

### routes/engines.py (Blueprint: engines_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает | Repository/Service |
|--------------|---------|-----------|------------|-------------------|
| GET /engines | list_engines | search, search_field, sort_by, sort_order, workshop, location | JSON: список двигателей | engine_repo.get_all |
| GET /locations-tree | locations_tree | — | JSON: {workshop: {location: count}} | engine_repo.get_locations_tree |
| GET /engine/<id> | get_engine | engine_id (path) | JSON: engine + modes + works | engine_repo.get_with_details |
| POST /engine | create_engine | JSON body (engine + modes + works) | JSON: {success, id, message} | engine_repo.create, mode_repo.replace_all, work_repo.replace_all |
| PUT /engine/<id> | update_engine | engine_id (path), JSON body | JSON: {success, message} | engine_repo.update |
| DELETE /engine/<id> | delete_engine | engine_id (path) | JSON: {success, message} | engine_repo.delete + photo_manager.delete_engine_photos_from_disk |
| PUT /engine/<id>/modes | update_engine_modes | engine_id (path), JSON {modes: []} | JSON: {success, message} | mode_repo.replace_all |
| PUT /engine/<id>/works | update_engine_works | engine_id (path), JSON {works: []} | JSON: {success, message} | work_repo.replace_all |

### routes/photos.py (Blueprint: photos_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает | Module |
|--------------|---------|-----------|------------|--------|
| GET /engine/<id>/photos | get_engine_photos | engine_id (path) | JSON: [{filename, path}] | photo_manager.get_engine_photos |
| GET /photos/<filename> | get_photo | filename (path) | File (image) или JSON error | photo_manager.get_photo |
| POST /engine/<id>/photos | upload_engine_photos | engine_id (path), multipart files[] | JSON: {success, uploaded, skipped, photo_count} | photo_manager.upload_engine_photos |
| DELETE /engine/<id>/photos/<filename> | delete_engine_photo | engine_id, filename (path) | JSON: {success, photo_count} | photo_manager.delete_engine_photo |
| PUT /engine/<id>/photos/<filename> | replace_engine_photo | engine_id, filename (path), multipart photo | JSON: {success, filename, path} | photo_manager.replace_engine_photo |

### routes/import_routes.py (Blueprint: import_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| POST /import-folder | import_folder | — | JSON: {success, imported, total_photos, elapsed_time, file_reports, summary} |
| POST /clear | clear_database | — | JSON: {success, message} |

**import_folder:** 3 этапа — (1) параллельный парсинг Excel (ThreadPoolExecutor, MAX_WORKERS=4), (2) последовательная запись в БД в одной транзакции (executemany), (3) параллельное извлечение фото. **Важно:** импорт рассчитан на пустую БД (гарантия через /api/clear перед импортом).

### routes/export_routes.py (Blueprint: export_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| POST /engines/export | export_to_excel | JSON {ids: [int]} | xlsx blob (attachment) |

Делегирует в `services/export_service.export_to_xlsx(conn, ids)`.

### routes/backup_routes.py (Blueprint: backup_bp, url_prefix=/api/backup)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| GET /list | list_backups | — | JSON: список бэкапов с метаданными из manifest.json |
| POST /create | create_backup | — | ZIP file (attachment) |
| POST /inspect-upload | inspect_uploaded_backup | multipart file | JSON: {valid, manifest, errors, staging_id} |
| POST /restore/<filename> | restore_backup | filename (path) | JSON: {success, message, restored_files} |
| POST /confirm-restore | confirm_restore_uploaded_backup | JSON {filename|staging_id} | JSON: {success, message, restored_files} |
| GET /download/<filename> | download_backup | filename (path) | ZIP file (attachment) |
| POST /delete/<filename> | delete_backup | filename (path) | JSON: {success, message} |
| DELETE /<filename> | delete_backup_http_delete | filename (path) | JSON: {success, message} |

### routes/auth.py (Blueprint: auth_bp, url_prefix=/api/auth)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| POST /login | auth_login | JSON {username, password} | JSON: {success, token, user} |
| POST /logout | auth_logout | Bearer token | JSON: {success} |
| GET /me | auth_me | Bearer token | JSON: {id, username, role} |
| GET /admin/users | admin_list_users | Bearer token (admin) | JSON: список пользователей |
| POST /admin/users | admin_create_user | JSON {username, password, role} | JSON: {success, id} |
| DELETE /admin/users/<id> | admin_delete_user | user_id (path), Bearer token (admin) | JSON: {success} |
| POST /admin/users/<id>/password | admin_change_password | user_id, JSON {password} | JSON: {success} |
| POST /admin/users/<id>/revoke | admin_revoke_user | user_id, Bearer token (admin) | JSON: {success} |

### routes/search.py (Blueprint: search_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| GET /search-suggestions | search_suggestions | field, query | JSON: [string] |
| POST /engines/search | search_engines_advanced | JSON {conditions: [{field, operator, value, value2}]} | JSON: [engine objects] |

### routes/changelog.py (Blueprint: changelog_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| GET /changelog | get_changelog | — | JSON: [entries] |
| POST /changelog | create_changelog_entry | JSON {text, date} | JSON: {success, id} |
| DELETE /changelog/<id> | delete_changelog_entry | entry_id (path) | JSON: {success} |
| GET /wishlist | get_wishlist | — | JSON: [items] |
| POST /wishlist | create_wishlist_item | JSON {text} | JSON: {success, id} |
| PUT /wishlist/<id> | update_wishlist_item | item_id, JSON {done?, text?} | JSON: {success} |
| DELETE /wishlist/<id> | delete_wishlist_item | item_id (path) | JSON: {success} |

### routes/status.py (Blueprint: status_bp, url_prefix=/api)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| GET /status | get_status | — | JSON: {has_data, engine_count, modes_count, works_count, photos_count, files_in_folder, db_size_bytes, db_size_label} |

### routes/pages.py (Blueprint: pages_bp, url_prefix=/)

| Метод + Путь | Функция | Параметры | Возвращает |
|--------------|---------|-----------|------------|
| GET / | index | — | templates/index.html |
| GET /print/<id> | print_engine_page | engine_id (path) | templates/print.html |
| GET /static/<path> | serve_static | path | static file |
| GET /test | test | — | JSON: {status: ok} |

---

## 5. Backend — repositories, services, modules

### repositories/engine_repo.py

| Функция | Сигнатура | Что делает | Вызывается из |
|---------|-----------|------------|---------------|
| _row_to_dict | (row) → dict | Преобразует sqlite3.Row в dict | Внутренне |
| get_by_id | (conn, engine_id: int) → dict\|None | Двигатель по ID (без modes/works) | routes/engines.py::get_engine, update_engine, delete_engine, create_engine (проверка) |
| get_with_details | (conn, engine_id: int) → dict\|None | Двигатель + modes + works + photo_count | routes/engines.py::get_engine, export_service.export_to_xlsx |
| get_modes_for_engine | (conn, engine_id: int) → list[dict] | Режимы работы двигателя | engine_repo.get_with_details |
| get_works_for_engine | (conn, engine_id: int) → list[dict] | Произведённые работы двигателя | engine_repo.get_with_details |
| get_all | (conn, limit=30, offset=0, sort='location_asc', search_field='all', search_query='', workshop=None, location=None) → list[dict] | Список с пагинацией, сортировкой, поиском, фильтром цех/место | routes/engines.py::list_engines |
| count_all | (conn, search_field='all', search_query='') → int | Общее количество для пагинации | (не используется напрямую в routes) |
| _next_free_id | (conn) → int | Находит минимальный свободный ID (1, или первая "дыра", или max+1) | engine_repo.create |
| create | (conn, data: dict) → int | Создаёт двигатель с явным ID из _next_free_id (BEGIN IMMEDIATE) | routes/engines.py::create_engine |
| update | (conn, engine_id: int, data: dict) → bool | Обновляет поля двигателя | routes/engines.py::update_engine |
| delete | (conn, engine_id: int) → bool | Удаляет двигатель + явно modes + works (каскад не работает на проде) | routes/engines.py::delete_engine |
| update_photo_count | (conn, engine_id: int, count: int) → None | Обновляет photo_count | photo_manager.upload_engine_photos, delete_engine_photo |
| get_by_filename | (conn, filename: str) → dict\|None | Поиск по filename (для импорта) | (не используется в routes) |
| get_locations_tree | (conn) → dict | {workshop: {location: count}} для дерева навигации | routes/engines.py::locations_tree |

### repositories/mode_repo.py

| Функция | Сигнатура | Что делает | Вызывается из |
|---------|-----------|------------|---------------|
| get_all | (conn, engine_id: int) → list[dict] | Все режимы двигателя | engine_repo.get_modes_for_engine |
| replace_all | (conn, engine_id: int, modes: list[dict]) → None | Полная замена (DELETE + INSERT) | routes/engines.py::create_engine, update_engine_modes |
| create | (conn, engine_id: int, mode: dict) → int | Один режим (lastrowid) | (не используется) |
| delete_all_for_engine | (conn, engine_id: int) → None | Удалить все режимы | (не используется) |

### repositories/work_repo.py

| Функция | Сигнатура | Что делает | Вызывается из |
|---------|-----------|------------|---------------|
| get_all | (conn, engine_id: int) → list[dict] | Все работы двигателя | engine_repo.get_works_for_engine |
| replace_all | (conn, engine_id: int, works: list[dict]) → None | Полная замена (DELETE + INSERT) | routes/engines.py::create_engine, update_engine_works |
| create | (conn, engine_id: int, work: dict) → int | Одна работа (lastrowid) | (не используется) |
| delete_all_for_engine | (conn, engine_id: int) → None | Удалить все работы | (не используется) |

### modules/photo_manager/manager.py

| Функция | Сигнатура | Что делает | Вызывается из |
|---------|-----------|------------|---------------|
| _photos_folder | () → str | Динамически читает PHOTOS_FOLDER из modules.db (для тестов monkeypatch) | Внутренне |
| engine_photo_disk_paths | (engine_id) → list[str] | Сканирует диск по маске ID{engine_id}_*.{ext} — источник истины | next_photo_index, get_engine_photos, upload_engine_photos, delete_engine_photo, delete_engine_photos_from_disk |
| next_photo_index | (engine_id) → int | Max существующего номера + 1 (по файлам на диске) | upload_engine_photos |
| get_engine_photos | (engine_id) → list[{filename, path}] | Список фото для фронтенда (path = /api/photos/{filename}) | routes/photos.py::get_engine_photos, engineCard.js (через API) |
| get_photo | (filename) → Response | Отдаёт файл с Cache-Control: no-cache | routes/photos.py::get_photo |
| upload_engine_photos | (conn, engine_id, files) → Response | Сохраняет файлы как ID{engine_id}_{n}.{ext}, обновляет photo_count | routes/photos.py::upload_engine_photos |
| delete_engine_photo | (conn, engine_id, filename) → Response | Удаляет одно фото, пересчитывает photo_count с диска | routes/photos.py::delete_engine_photo |
| delete_engine_photos_from_disk | (engine_id) → (removed: int, errors: list) | Удаляет ВСЕ фото двигателя с диска (после удаления из БД) | routes/engines.py::delete_engine |
| _save_upload_atomically | (file_storage, dest_path, retries=3, delay=0.15) → None | Атомарная запись через .tmp + os.replace с retry | replace_engine_photo |
| replace_engine_photo | (engine_id, filename, file_storage) → Response | Перезапись фото (обрезка), может сменить расширение | routes/photos.py::replace_engine_photo |

### modules/backup_system/backup.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| _build_backup_zip_bytes | (get_db_connection) → (bytes, manifest) | Консистентный снапшот БД (sqlite3.backup) + все фото + manifest.json с SHA256 |
| _save_backup_to_server | (zip_bytes, prefix) → (filename, path, size) | Сохраняет ZIP в BACKUPS_FOLDER |
| _enforce_backup_limit | (max_count=3) → None | Оставляет не более 3 бэкапов (FIFO по имени) |
| _verify_checksums | (zip_path, manifest) → (bool, error_msg) | Проверяет SHA256 engine_data.db и photos/* внутри ZIP |
| _atomic_replace | (src, dst, retries=5, delay=0.3) → None | os.replace с retry на Windows (WinError 5) |
| _acquire_restore_lock | (timeout=30) → lock_path\|None | Файловый лок backup_restore.lock (O_EXCL) |
| _release_restore_lock | (lock_path) → None | Удаляет файл-лок |
| _apply_backup_zip | (zip_path) → dict | **Атомарное восстановление:** rollback-точка → распаковка во временные файлы → sqlite3.backup в .new → os.replace DB + photos → восстановление users/tokens. При ошибке — откат на rollback. |
| _safe_backup_filename | (filename) → str\|None | Валидация имени (нет .., /, \, заканчивается на .zip) |
| create_backup | () → dict | Публичный API: создаёт бэкап, возвращает метаданные |
| list_backups | () → list[dict] | Список бэкапов с чтением manifest.json |
| inspect_uploaded_backup | (zip_path) → dict | Проверка чексумм загруженного ZIP (не трогает рабочую БД) |
| restore_backup | (zip_path) → dict | Атомарное восстановление с локом |
| download_backup | (filename) → str\|None | Путь к файлу для send_file |
| delete_backup | (filename) → bool | Удаление файла бэкапа |

### modules/engine_parser/parser.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| get_cell_safe | (arr, r, c) → str | Безопасное чтение ячейки numpy array |
| get_cell_val_safe | (arr, r, c) → str\|None | Безопасное чтение с strip |
| parse_engine_data | (arr, filename) → dict | Парсит характеристики двигателя из Excel (строки 9, 10, 13-15, 22-30) |
| parse_operating_modes | (arr) → list[dict] | Парсит режимы работы (колонки 50-69, строки 16-21) |
| parse_maintenance_works | (arr) → list[dict] | Парсит работы (строки 39+, колонки 13, 15, 19, 41, 45, 56) |
| extract_images_from_excel | (file_path, filename, engine_id, log_callback) → int | Извлекает фото из xl/media/ и openpyxl _images, сохраняет как ID{engine_id}_{n}.{ext} |
| parse_file_fast | (file_path, log_callback) → dict | Обёртка: парсит файл, возвращает engine_tuple, modes, works, file_path |

### modules/auth/auth.py (фасад, переэкспорт)

Переэкспортирует из подмодулей:
- **hashing:** hash_password, verify_password, hash_token, generate_token
- **db_users:** create_user, get_user_by_username, get_user_by_id, list_users, delete_user, update_user_password, update_last_login, count_users
- **file_users:** create_file_user, delete_file_user, update_file_user_password, update_file_user_last_login, _load_file_users, _save_file_users, _load_file_tokens, _save_file_tokens, _next_file_user_id, _migrate_negative_file_user_ids, FILE_USER_ID_OFFSET, FILE_USERS, FILE_TOKENS, CONFIG_DIR
- **tokens:** issue_token, get_user_from_token, revoke_token, revoke_all_for_user
- **decorators:** require_auth, require_admin, get_current_user, _extract_bearer_token

### modules/auth/db_users.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| create_user | (conn, username, password, role='user') → int | INSERT в users, возвращает lastrowid |
| get_user_by_username | (conn, username) → dict\|None | Сначала БД, затем файл (fallback) |
| get_user_by_id | (conn, user_id) → dict\|None | БД (id>0), затем файл (id>=FILE_USER_ID_OFFSET) |
| list_users | (conn) → list[dict] | Все пользователи (DB + file) с source |
| delete_user | (conn, user_id) → bool | DELETE FROM users (каскадно токены) |
| update_user_password | (conn, user_id, new_password) → bool | UPDATE password_hash + last_edit |
| update_last_login | (conn, user_id) → bool | UPDATE last_login |
| count_users | (conn) → int | COUNT(*) FROM users |

### modules/auth/file_users.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| _ensure_config | () → None | Создаёт CONFIG_DIR |
| _migrate_negative_file_user_ids | (users) → users | Чинит отрицательные id (legacy) → назначает >= FILE_USER_ID_OFFSET |
| _load_file_users | () → list[dict] | Читает config/users.json + миграция |
| _save_file_users | (users) → None | Пишет config/users.json |
| _load_file_tokens | () → list[dict] | Читает config/tokens.json |
| _save_file_tokens | (tokens) → None | Пишет config/tokens.json |
| _next_file_user_id | () → int | Max id + 1 или FILE_USER_ID_OFFSET |
| create_file_user | (username, password, role='user') → int | Создаёт в файле, возвращает id |
| delete_file_user | (user_id) → bool | Удаляет из файла |
| update_file_user_password | (user_id, new_password) → bool | Обновляет пароль в файле |
| update_file_user_last_login | (user_id) → bool | Обновляет last_login в файле |

**FILE_USER_ID_OFFSET = 1000000000** — файловые пользователи имеют id >= 1e9, чтобы не пересекаться с AUTOINCREMENT БД и проходить через Flask `<int:user_id>`.

### modules/auth/hashing.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| hash_password | (password: str) → str | bcrypt.hashpw |
| verify_password | (password: str, password_hash: str) → bool | bcrypt.checkpw |
| hash_token | (token: str) → str | SHA256 hex |
| generate_token | () → str | secrets.token_urlsafe(32) |

### modules/auth/tokens.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| issue_token | (conn, user_id) → str | Генерирует токен, сохраняет hash в tokens, возвращает plain token |
| get_user_from_token | (conn, token) → dict\|None | Находит пользователя по token_hash (БД + файл fallback) |
| revoke_token | (conn, token) → bool | DELETE FROM tokens WHERE token_hash = ? |
| revoke_all_for_user | (conn, user_id) → None | DELETE FROM tokens WHERE user_id = ? |

### modules/auth/decorators.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| _extract_bearer_token | () → str\|None | Из Authorization: Bearer или ?token= |
| get_current_user | () → dict\|None | Вызывает auth_module.get_user_from_token |
| require_auth | (f) → wrapper | 401 если нет пользователя |
| require_admin | (f) → wrapper | 403 если не admin/superadmin |

### services/export_service.py

| Функция | Сигнатура | Что делает |
|---------|-----------|------------|
| export_to_xlsx | (conn, engine_ids: list[int]) → bytes | Строит Workbook: для каждого двигателя — характеристики, режимы, работы, фото (openpyxl + PIL) |
| _get_photo_paths | (engine_id) → list[str] | **ДУБЛИРУЕТ ЛОГИКУ** photo_manager: ищет файлы по префиксу `engine_{engine_id}_` (СТАРАЯ СХЕМА!) |
| _col_letter | (col: int) → str | 1→A, 27→AA |

### services/backup_service.py

Тонкая обёртка над modules.backup_system.backup — делегирует все вызовы.

### modules/db.py

| Экспорт | Значение |
|---------|----------|
| DB_PATH | str(BASE_DIR / 'engine_data.db') |
| MOTORS_FOLDER | str(BASE_DIR / 'motors') |
| PHOTOS_FOLDER | str(BASE_DIR / 'photos') |
| BACKUPS_FOLDER | str(BASE_DIR / 'backups') |
| BACKUP_STAGING_FOLDER | str(BASE_DIR / 'backup_staging') |
| ENGINE_COLUMNS_ORDERED | список 17 колонок в порядке |
| ENGINE_COLUMNS | frozenset(ENGINE_COLUMNS_ORDERED) |
| MODE_COLUMNS | frozenset(6 колонок режимов) |
| get_db_connection | (db_path=None) → sqlite3.Connection (WAL, foreign_keys=ON) |
| db_connection | contextmanager для get_db_connection |
| init_db | (conn=None) → None — создаёт схему, индексы, авто-миграции, сидит admin + changelog |

---

### Содержимое ВСЕХ init.py (re-export списки)

#### modules/__init__.py
```python
# Пустой файл (нет __all__)
```

#### modules/auth/__init__.py
```python
# См. modules/auth/auth.py — __all__ с 88 именами (полный переэкспорт фасада)
```

#### modules/backup_system/__init__.py
```python
from modules.backup_system.backup import (
    create_backup, list_backups, inspect_uploaded_backup,
    restore_backup, download_backup, delete_backup
)
__all__ = ['create_backup', 'list_backups', 'inspect_uploaded_backup',
           'restore_backup', 'download_backup', 'delete_backup']
```

#### modules/engine_parser/__init__.py
```python
from modules.engine_parser.parser import (
    parse_engine_data, parse_operating_modes, parse_maintenance_works,
    extract_images_from_excel, parse_file_fast
)
__all__ = ['parse_engine_data', 'parse_operating_modes', 'parse_maintenance_works',
           'extract_images_from_excel', 'parse_file_fast']
```

#### modules/photo_manager/__init__.py
```python
from modules.photo_manager.manager import (
    engine_photo_disk_paths,
    next_photo_index,
    get_engine_photos,
    get_photo,
    upload_engine_photos,
    delete_engine_photo,
    delete_engine_photos_from_disk,
    replace_engine_photo,
)

__all__ = [
    'engine_photo_disk_paths',
    'next_photo_index',
    'get_engine_photos',
    'get_photo',
    'upload_engine_photos',
    'delete_engine_photo',
    'delete_engine_photos_from_disk',
    'replace_engine_photo',
]
```
**Важно:** __all__ синхронизирован с реальными определениями в manager.py (8 функций). Раньше расхождение вызывало ImportError при старте.

#### repositories/__init__.py
```python
# Пустой (нет __all__)
```

#### schemas/__init__.py
```python
from schemas.engine_schema import (
    validate_numeric_value,
    validate_mode_numeric_fields,
    validate_engine_payload,
    sanitize_engine_data,
)
__all__ = ['validate_numeric_value', 'validate_mode_numeric_fields',
           'validate_engine_payload', 'sanitize_engine_data']
```

#### services/__init__.py
```python
# Пустой (нет __all__)
```

#### utils/__init__.py
```python
# Пустой (нет __all__)
```

#### tests/__init__.py
```python
# Пустой
```

#### tests/e2e/__init__.py
```python
# Пустой
```

---

## 6. Backend — константы и конфигурация

### config/settings.py — точные строки определений

| Константа | Строка | Путь / вычисление |
|-----------|--------|-------------------|
| BASE_DIR | 9 | `Path(__file__).resolve().parent.parent` |
| DB_PATH | 11 | `str(BASE_DIR / 'engine_data.db')` |
| MOTORS_FOLDER | 12 | `str(BASE_DIR / 'motors')` |
| PHOTOS_FOLDER | 13 | `str(BASE_DIR / 'photos')` |
| BACKUPS_FOLDER | 14 | `str(BASE_DIR / 'backups')` |
| BACKUP_STAGING_FOLDER | 15 | `str(BASE_DIR / 'backup_staging')` |
| CONFIG_DIR | 16 | `str(BASE_DIR / 'config')` |
| FILE_USERS | 17 | `str(BASE_DIR / 'config' / 'users.json')` |
| FILE_TOKENS | 18 | `str(BASE_DIR / 'config' / 'tokens.json')` |
| ALLOWED_PHOTO_EXT | 20 | `{'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}` |
| MAX_WORKERS | 23 | `4` |
| LOG_FILE | 24 | `str(BASE_DIR / 'app.log')` |

### Локальные переопределения / дубликаты путей

| Константа | Файл:строка | Определение | Импортируется из |
|-----------|-------------|-------------|------------------|
| DB_PATH | modules/backup_system/backup.py:34 | `DB_PATH = db_module.DB_PATH` | modules.db |
| PHOTOS_FOLDER | modules/backup_system/backup.py:35 | `PHOTOS_FOLDER = db_module.PHOTOS_FOLDER` | modules.db |
| DB_PATH | modules/db.py:9 | `from config.settings import DB_PATH, ...` | config.settings |
| PHOTOS_FOLDER | modules/db.py:9 | `from config.settings import ..., PHOTOS_FOLDER, ...` | config.settings |
| PHOTOS_FOLDER | modules/engine_parser/parser.py:16 | `from config.settings import PHOTOS_FOLDER, ALLOWED_PHOTO_EXT` | config.settings |
| PHOTOS_FOLDER | modules/photo_manager/manager.py:25 | `from config.settings import ALLOWED_PHOTO_EXT` (PHOTOS_FOLDER читается динамически через modules.db) | config.settings (ALLOWED_PHOTO_EXT) |
| DB_PATH | routes/import_routes.py:14 | `from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER` | modules.db |
| PHOTOS_FOLDER | routes/import_routes.py:14 | `from modules.db import ..., PHOTOS_FOLDER, ...` | modules.db |
| DB_PATH | routes/status.py:9 | `from modules.db import db_connection, DB_PATH, MOTORS_FOLDER` | modules.db |
| PHOTOS_FOLDER | services/export_service.py:24 | `from config.settings import PHOTOS_FOLDER` | config.settings |
| PHOTOS_FOLDER | services/export_service.py:213 | `from config.settings import PHOTOS_FOLDER` | config.settings |
| DB_PATH | services/backup_service.py:9 | `from config.settings import DB_PATH, PHOTOS_FOLDER, ...` | config.settings |
| PHOTOS_FOLDER | services/backup_service.py:9 | `from config.settings import ..., PHOTOS_FOLDER, ...` | config.settings |
| DB_PATH | promote_and_cleanup.py:19 | `DB_PATH = Path(__file__).parent / 'engine_data.db'` | **ЛОКАЛЬНОЕ ПЕРЕОПРЕДЕЛЕНИЕ** (относительный путь) |
| DB_PATH | reset_admin_password.py:41 | `from modules.db import DB_PATH, ...` | modules.db |
| DB_PATH | temp/temp_selftest.py:16 | `TEST_DB_PATH = ROOT / 'temp_test_engine_data.db'` | Тестовый локальный |
| PHOTOS_FOLDER | temp/temp_selftest.py:18 | `TEST_PHOTOS_FOLDER = ROOT / 'temp_test_photos'` | Тестовый локальный |

### Таблица: Константа | Единственное место определения | Кто импортирует | Дублирующие определения

| Константа | Единственное определение | Импортируют (реально, по Select-String) | Дубликаты / другие имена |
|-----------|--------------------------|------------------------------------------|--------------------------|
| DB_PATH | config/settings.py:11 | modules.db, modules.backup_system.backup, routes.status, routes.import_routes, services.backup_service, reset_admin_password, promote_and_cleanup (локально), temp/* (тесты) | promote_and_cleanup.py:19 — `Path(__file__).parent / 'engine_data.db'` (относительный) |
| PHOTOS_FOLDER | config/settings.py:13 | modules.db, modules.backup_system.backup, modules.engine_parser.parser, routes.import_routes, services.export_service (2 раза), services.backup_service, app.py, diag_photos.py | — |
| MOTORS_FOLDER | config/settings.py:12 | modules.db, routes.import_routes, routes.status, app.py | — |
| BACKUPS_FOLDER | config/settings.py:14 | modules.db, modules.backup_system.backup, services.backup_service, app.py | — |
| BACKUP_STAGING_FOLDER | config.settings.py:15 | modules.db, modules.backup_system.backup, routes.backup_routes, app.py | — |
| ALLOWED_PHOTO_EXT | config/settings.py:20 | modules.db, modules.engine_parser.parser, modules.photo_manager.manager, diag_photos.py | — |
| FILE_USER_ID_OFFSET | modules/auth/file_users.py:12 | modules.auth.file_users, modules.auth.auth (реэкспорт), modules.auth.db_users (через fallback) | — |

---

## 7. Контракт имён файлов на диске (фото)

### Актуальная схема (modules/photo_manager/manager.py, строки 6-8, 33-42, 96)
```
ID{engine_id}_{n}.{ext}
Пример: ID157_1.jpg — первое фото двигателя с id=157
```
**Связь фото→двигатель определяется исключительно через engine_id в имени файла. БД для поиска фото не нужна.**

### Все места, где схема ПОРОЖДАЕТСЯ (upload, импорт)

| Место | Файл:функция | Строка генерации имени |
|-------|--------------|------------------------|
| Загрузка фото в карточке | photo_manager.upload_engine_photos | 96: `photo_filename = f"ID{engine_id}_{next_idx + saved}{ext}"` |
| Извлечение фото при импорте Excel | engine_parser.extract_images_from_excel | 209: `photo_filename = f"ID{engine_id}_{idx+1}{ext}"` |
| Извлечение фото через openpyxl | engine_parser.extract_images_from_excel | 234: `photo_filename = f"ID{engine_id}_{idx+1}.png"` |

### Все места, где схема ПАРСИТСЯ (поиск, удаление, замена)

| Место | Файл:функция | Использование |
|-------|--------------|---------------|
| Сканирование фото двигателя | photo_manager.engine_photo_disk_paths | 40: `pattern = f"ID{engine_id}_*.{ext.lstrip('.')}"` |
| Следующий индекс | photo_manager.next_photo_index | 49: `pattern = re.compile(rf'^ID{engine_id}_(\d+)\.')` |
| Удаление одного фото | photo_manager.delete_engine_photo | 113: `if not filename.startswith(f'ID{engine_id}_'):` |
| Удаление всех фото при удалении двигателя | photo_manager.delete_engine_photos_from_disk | 137: `for path in engine_photo_disk_paths(engine_id):` |
| Замена фото (обрезка) | photo_manager.replace_engine_photo | 185: `if not filename.startswith(f'ID{engine_id}_'):` |
| Экспорт фото (СТАРАЯ СХЕМА!) | export_service._get_photo_paths | 218: `prefix = f'engine_{engine_id}_'` — **НЕ СОВПАДАЕТ** с актуальной! |

### НАХОДКА: Дублирование логики именования
**Две независимые схемы именования:**
1. **Актуальная:** `ID{engine_id}_{n}.{ext}` — в photo_manager, engine_parser
2. **Устаревшая в export_service:** `engine_{engine_id}_{n}.{ext}` (строка 218)

Это приведёт к тому, что экспорт в Excel **не найдёт фото** для двигателей, загруженных через актуальный путь. Требует исправления export_service._get_photo_paths на использование photo_manager.engine_photo_disk_paths.

---

## 8. Жизненный цикл ID записей (engines)

### Назначение ID при создании
**Файл:** `repositories/engine_repo.py::create()` (строки 145-172) + `_next_free_id()` (строки 124-142)

```python
def _next_free_id(conn) -> int:
    # 1. Если id=1 свободен — вернуть 1
    # 2. Иначе найти первую "дыру": MIN(id+1) WHERE NOT EXISTS (id+1)
    # 3. Если дыр нет — max(id)+1
```
**ID выбирается явно как минимальный свободный, а не отдаётся AUTOINCREMENT** (строка 148-150 комментария). Оборачивается в `BEGIN IMMEDIATE` для атомарности.

### Массовый импорт (import_routes.py)
**Отдельный путь через `executemany`** (строки 104-128). **НЕ использует _next_free_id**. Рассчитан на **пустую БД** (гарантия: /api/clear перед импортом сбрасывает sqlite_sequence). ID назначаются последовательно через `last_insert_rowid()` после батча.

### При удалении записи
**ID переиспользуется** — `_next_free_id` найдёт "дыру" и вернёт удалённый ID. Фото на диске удаляются **после** успешного удаления из БД (routes/engines.py:127-134), поэтому осиротевших фото не остаётся — следующий двигатель с тем же ID создаст файлы с нуля (`ID{id}_1.ext`).

### Проверка предположений импорта
- Предположение: "импорт всегда на пустую БД" — **проверяется неявно** через вызов /api/clear перед импортом (фронтенд вызывает clear, потом import-folder).
- В коде import_routes.py **нет явной проверки** что БД пуста перед executemany.

---

## 9. Обслуживание БД

### Очистка БД (/api/clear) — routes/import_routes.py::clear_database (строки 196-233)

```python
with db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('DELETE FROM operating_modes')
    cursor.execute('DELETE FROM maintenance_works')
    cursor.execute('DELETE FROM engines')
    # Сброс автоинкремента ТОЛЬКО для очищенных таблиц
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('engines', 'operating_modes', 'maintenance_works')")
    conn.commit()
    # WAL checkpoint + VACUUM
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    conn.execute('VACUUM')

# Удаление фото с диска
if os.path.exists(PHOTOS_FOLDER):
    shutil.rmtree(PHOTOS_FOLDER, ignore_errors=True)
os.makedirs(PHOTOS_FOLDER, exist_ok=True)
```

**Важно:** 
- Дочерние записи удаляются **явно** (не полагается на CASCADE)
- `sqlite_sequence` сбрасывается → ID начнут с 1 после очистки
- `PRAGMA wal_checkpoint(TRUNCATE)` + `VACUUM` — освобождает место на диске (раньше файл не уменьшался)
- Фото удаляются через `shutil.rmtree` (рекурсивно, ignore_errors=True)

### Журналирование (WAL)
Включается в `modules/db.py::get_db_connection()` (строка 32):
```python
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA foreign_keys=ON')
```

---

## 10. Frontend — файлы и назначение

| Файл | Назначение |
|------|------------|
| static/js/common.js | Общие утилиты: escapeHtml, debounce, DETAIL_CHAR_FIELDS, DETAIL_NUMERIC_FIELDS, _formatRuDate, showToast |
| static/js/catalog.js | Каталог: таблица/карточки, пагинация, сортировка, поиск, экспорт, выбор двигателей, навигация |
| static/js/locationTree.js | Дерево "Цех → Место установки" (боковая панель), фильтрация каталога |
| static/js/engineCard.js | Детальная модалка: характеристики, фото (галерея, добавление, обрезка), режимы, работы, печать, удаление |
| static/js/engines.js | Глобальные переменные состояния (allEngines, currentSort, currentPage, activeWorkshop, activeLocation, selectedEngineIds, currentEngineId, currentEngineData, currentPhotos, detailEditMode, detailMode, photoCacheBust, detailPhotoFiles, pendingPhotoFiles, cropState) + функции формы добавления, автодополнение |
| static/js/importer.js | Вкладка импорт: прогресс-бар, лог, подтверждение очистки БД |
| static/js/exportManager.js | Экспорт выбранных (UI для exportSelected) |
| static/js/backupManager.js | Вкладка бэкапы: создание, список, загрузка, восстановление (2-этапный: inspect → confirm) |
| static/js/search.js | Расширенный поиск: построение условий, отправка на /api/engines/search, отображение результатов |
| static/js/auth.js | Авторизация: login/logout, токен в localStorage, админ-панель пользователей |
| static/js/api.js | apiFetch — обёртка над fetch с авторизацией (Bearer token из localStorage) |
| static/js/state.js | (пустой/минимальный) |
| static/js/app.js | (пустой/минимальный) |
| static/js/print.js | Печатная страница: рендер паспорта из API данных |

---

## 11. Frontend — глобальные переменные

| Имя | Где объявлена | Читают/пишут | Назначение |
|-----|---------------|--------------|------------|
| allEngines | engines.js:1 | catalog.js (loadEngines, renderTable, renderCards), engineCard.js (navigateEngine), search.js | Единый массив текущих двигателей для каталога/поиска/дерева — все источники пишут в неё перед рендером |
| currentSort | engines.js:2 | catalog.js (loadEngines, sortTable), engines.js | Текущая сортировка {field, order} |
| currentPage | engines.js:3 | catalog.js (renderTable, prevPage, nextPage, loadEngines), locationTree.js | Текущая страница пагинации |
| activeWorkshop | locationTree.js:4 | catalog.js (loadEngines — через typeof check), locationTree.js | Активный цех из дерева (null = все) |
| activeLocation | locationTree.js:5 | catalog.js (loadEngines), locationTree.js | Активное место установки (null = все в цехе) |
| selectedEngineIds | engines.js:4 | catalog.js (toggleEngineSelection, toggleSelectAll, clearSelection, updateExportButton), engineCard.js (deleteCurrentEngine → clearSelection) | Set ID выбранных для экспорта |
| currentEngineId | engines.js:5 | engineCard.js (showDetail, navigateEngine, saveDetailEdit, saveModesInline, saveWorksOnly, deleteCurrentEngine, photo ops) | ID открытой карточки |
| currentEngineData | engines.js:6 | engineCard.js (renderDetailContent, saveDetailEdit, addModeRowInline, removeModeRowInline, saveModesInline, addWorkRowInline, removeWorkRowInline, saveWorksOnly) | Данные текущего двигателя (кэш) |
| currentPhotos | engines.js:7 | engineCard.js (renderDetailContent, openPhotoModalWithNav, navigatePhotoModal, submitDetailPhotoAdd, removeDetailPhoto, applyCrop) | Фото текущего двигателя |
| detailEditMode | engines.js:8 | engineCard.js (renderDetailContent, toggleDetailMode, toggleDetailEdit, cancelDetailEdit, saveDetailEdit) | Флаг режима редактирования карточки |
| detailMode | engines.js:9 | engineCard.js (showDetail, renderDetailContent, toggleDetailMode) | 'view' \| 'edit' |
| photoCacheBust | engines.js:10 | engineCard.js (renderDetailContent, submitDetailPhotoAdd, removeDetailPhoto, openPhotoModal, navigatePhotoModal, applyCrop) | Timestamp для cache-busting фото |
| detailPhotoFiles | engines.js:11 | engineCard.js (openPhotoAddModal, renderDetailPhotoPreview, removeDetailPendingPhoto, submitDetailPhotoAdd, openCropModal) | File[] для загрузки в карточке |
| pendingPhotoFiles | engines.js:12 | engines.js (форма добавления), engineCard.js (openCropModal) | File[] для формы добавления нового двигателя |
| cropState | engineCard.js:610 | engineCard.js (openCropModal, _cropFilesArray, _openCropStage, _renderCropSelection, _cropPointerDown/Move/Up, applyCrop, _applyCropFile, _applyCropExisting) | Состояние кропа (list, index, filename, objectUrl, image, displayScale, sel, drag) |

---

## 12. Frontend — ключевые функции (вызываемые извне)

| Функция | Файл | Что делает | Откуда вызывается |
|---------|------|------------|-------------------|
| loadEngines | catalog.js | Загружает список через API, рендерит таблицу/карточки | DOMContentLoaded, switchTab, refreshTable, sortTable, debouncedLoadEngines, locationTree.js (toggleTreeWorkshop, selectTreeLocation, resetLocationFilter) |
| renderTable | catalog.js | Рендерит таблицу с пагинацией | loadEngines, toggleView, prevPage, nextPage |
| renderCards | catalog.js | Рендерит карточный вид | loadEngines, toggleView |
| toggleView | catalog.js | Переключает таблица/карточки | onclick в HTML (viewTableBtn, viewCardsBtn) |
| showDetail | engineCard.js | Открывает модалку карточки, загружает данные + фото | onclick в таблице/карточке, navigateEngine, editEngine |
| closeDetail | engineCard.js | Закрывает модалку с анимацией | modal-close кнопка, click-outside (engines.js), deleteCurrentEngine |
| navigateEngine | catalog.js | НавигацияPrev/Next в модалке | toolbar кнопки в карточке |
| editEngine | catalog.js | Открывает карточку в режиме редактирования | onclick edit кнопки в таблице/карточке |
| deleteEngine | catalog.js | Удаляет двигатель через API, обновляет списки | onclick delete кнопки, engineCard.js::deleteCurrentEngine |
| toggleDetailMode | engineCard.js | Переключает view/edit в карточке | toolbar кнопки в карточке |
| saveDetailEdit | engineCard.js | Сохраняет характеристики (PUT /api/engine/:id) | кнопка "Сохранить" в карточке |
| saveModesInline | engineCard.js | Сохраняет режимы (PUT /api/engine/:id/modes) | кнопка "Сохранить режимы" |
| saveWorksOnly | engineCard.js | Сохраняет работы (PUT /api/engine/:id/works) | кнопка "Сохранить работы" |
| addModeRowInline / removeModeRowInline | engineCard.js | Добавляет/удаляет строку режимов в карточке | кнопки в таблице режимов |
| addWorkRowInline / removeWorkRowInline | engineCard.js | Добавляет/удаляет строку работ в карточке | кнопки в таблице работ |
| openPhotoAddModal / closePhotoAddModal | engineCard.js | Модалка добавления фото в карточке | кнопка "Добавить" в секции фото |
| submitDetailPhotoAdd | engineCard.js | Загружает фото (POST /api/engine/:id/photos) | кнопка "Загрузить" в модалке фото |
| removeDetailPhoto | engineCard.js | Удаляет фото (DELETE /api/engine/:id/photos/:filename) | кнопка "−" на миниатюре |
| openCropModal / closeCropModal / applyCrop | engineCard.js | Обрезка фото (canvas) — для новых и существующих | кнопка "✂️" на миниатюре/в превью |
| printEngineCard | engineCard.js | Открывает /print/:id в новой вкладке | кнопка "Печать" в toolbar |
| importFiles | importer.js | Запускает импорт с прогресс-баром | кнопка "Импортировать все файлы" |
| confirmClearDatabase | importer.js | Подтверждение "СТИРАТЬ" → POST /api/clear | кнопка "Очистить БД" |
| createBackup | backupManager.js | Создаёт бэкап (GET /api/backup/create → blob) | кнопка "Создать резервную копию" |
| inspectUploadedBackup | backupManager.js | POST /api/backup/inspect-upload | загрузка файла в input |
| confirmRestoreUploadedBackup | backupManager.js | POST /api/backup/confirm-restore | кнопка "Восстановить" после inspect |
| searchEngines | search.js | POST /api/engines/search с условиями | кнопка "Найти", Enter в полях |
| authInit / login / logout | auth.js | Авторизация, токен в localStorage | DOMContentLoaded, форма логина, кнопка "Выйти" |
| apiFetch | api.js | fetch с Authorization: Bearer | везде где нужны API вызовы |

---

## 13. UI-компоненты → файлы

| Визуальный блок | HTML (templates/) | JS управление | CSS секция |
|-----------------|-------------------|---------------|------------|
| Таблица каталога | index.html:105-123 | catalog.js (renderTable) | .data-table, .table-wrapper |
| Карточки каталога | index.html:125 | catalog.js (renderCards) | .equipment-grid, .equipment-card |
| Детальная модалка | index.html:410-422 | engineCard.js (showDetail, renderDetailContent) | .modal, .modal-lg, .modal-content |
| Форма добавления | index.html:140-252 | engines.js (saveEngine, addModeRow, addWorkRow, resetForm) | .engine-form, .form-grid, .sub-table |
| Дерево цехов | index.html:64-70 | locationTree.js (loadLocationTree, renderLocationTree) | .tree-panel, .tree-workshop-group |
| Тулбар поиска | index.html:73-103 | catalog.js (loadEngines, debouncedLoadEngines, sortTable) | .toolbar, .search-input, .sort-select |
| Вкладки (Каталог/Добавить/Импорт/Поиск/Настройки/Инфо/Админ) | index.html:18-38 | catalog.js (switchTab) | .tab-btn, .tab-content |
| Логин | index.html:52-55 | auth.js (authInit, login, logout) | .topbar-user |
| Модалка фото (добавление) | index.html:424-443 | engineCard.js (openPhotoAddModal, submitDetailPhotoAdd) | .modal, #photoAddModal |
| Модалка обрезки | index.html:449-472 | engineCard.js (openCropModal, applyCrop, canvas logic) | .modal, #photoCropModal, .crop-stage |
| Модалка просмотра фото | index.html:475-483 | engineCard.js (openPhotoModal, navigatePhotoModal) | .photo-modal, #photoModal |
| Печатная страница | print.html | print.js (renderPrintPage) | @media print, .print-page |
| Настройки/Бэкапы | index.html:313-347 | backupManager.js, catalog.js (loadSettings) | .settings-container, .backups-list |
| Расширенный поиск | index.html:293-310 | search.js (addCondition, searchEngines) | .search-filters, .search-results |
| Админ-панель | index.html:358-380 | auth.js (adminListUsers, adminCreateUser, ...) | .admin-container, .admin-users-list |

---

## 14. Тестовая инфраструктура

### Структура tests/
```
tests/
├── conftest.py              # Фикстуры: app, client, db_connection, auth_token
├── test_utils/
│   ├── test_date.py         # format_ru_date, is_valid_iso_date
│   ├── test_naming.py       # normalize_base_name
│   └── test_file_store.py   # (пустой/заглушка)
├── test_repositories/
│   └── test_engine_repo.py  # CRUD engines, modes, works, photo_count
├── test_backup_system/
│   └── test_backup.py       # create/list/inspect/restore backup, чексуммы, лок
└── e2e/
    ├── conftest.py          # browser, base_url, auth fixtures
    ├── helpers.py           # wait_for, fill_form, select_option
    ├── test_01_auth.py      # Login, logout, token persistence
    ├── test_02_catalog.py   # Table/cards, pagination, sort, search, tree filter
    ├── test_03_add_engine.py # Create engine with modes/works/photos
    ├── test_04_detail.py    # Detail modal, edit, modes/works inline, photos
    ├── test_05_photos.py    # Upload, delete, crop, replace
    ├── test_06_import.py    # Import folder, clear DB
    ├── test_07_search.py    # Advanced search conditions
    ├── test_08_settings.py  # Stats, backup create/download
    ├── test_09_backups.py   # Restore, inspect, confirm-restore
    ├── test_10_info.py      # Changelog, wishlist
    └── test_11_misc.py      # Print page, export, navigation
```

### Команда запуска
```bash
# Unit/integration
.venv\Scripts\python.exe -m pytest tests/ -v

# E2E (требует запущенного сервера на :5000)
.venv\Scripts\python.exe -m pytest tests/e2e/ -v --base-url=http://localhost:5000
```

### Количество сценариев
- Unit: ~25 тестов
- E2E: 11 файлов × ~3-5 сценариев = ~40 сценариев

---

## 15. Карта использования (Select-String по всему репозиторию)

### photo_manager / PHOTOS_FOLDER / DB_PATH / engine_photo_disk_paths / normalize_base_name
*(Результат первого Select-String — см. раздел 0 метаданных, полный вывод в логе терминала)*

**Ключевые находки:**
- `photo_manager` импортируется в: routes/photos.py, routes/engines.py, repositories/engine_repo.py (комментарий), modules/photo_manager/__init__.py
- `PHOTOS_FOLDER` определяется в config/settings.py, читается через modules.db во всех модулях
- `DB_PATH` — аналогично, но есть локальное переопределение в promote_and_cleanup.py
- `engine_photo_disk_paths` — только в photo_manager/manager.py + __init__.py + repositories/engine_repo.py (комментарий) + routes/engines.py (вызов delete_engine_photos_from_disk)
- `normalize_base_name` — только в utils/naming.py + tests/test_utils/test_naming.py (не используется в продакшн-коде!)

### Дополнительные Select-String для констант с множественными потребителями

#### ALLOWED_PHOTO_EXT
```
config/settings.py:20 — определение
modules/db.py:9 — импорт
modules/engine_parser/parser.py:16 — импорт
modules/photo_manager/manager.py:25 — импорт
diag_photos.py:4 — импорт
```

#### FILE_USER_ID_OFFSET
```
modules/auth/file_users.py:12 — определение (1000000000)
modules/auth/auth.py:50 — реэкспорт в __all__
modules/auth/db_users.py:70 — используется в get_user_by_id (fallback для file users)
```

#### MAX_WORKERS
```
config/settings.py:23 — определение (4)
routes/import_routes.py:17, 43, 137 — ThreadPoolExecutor(max_workers=MAX_WORKERS) (3 места)
```

#### ENGINE_COLUMNS_ORDERED / ENGINE_COLUMNS / MODE_COLUMNS
```
modules/db.py:11-17 — определения
repositories/engine_repo.py:6 — импорт ENGINE_COLUMNS_ORDERED
repositories/mode_repo.py:5 — импорт MODE_COLUMNS
schemas/engine_schema.py:6 — импорт обоих
routes/search.py:7 — импорт всех трёх
```

---

## 16. Найденные расхождения (без исправлений)

1. **Две схемы именования фото на диске**
   - Актуальная: `ID{engine_id}_{n}.{ext}` (photo_manager, engine_parser)
   - Устаревшая в export_service._get_photo_paths: `engine_{engine_id}_{n}.{ext}` (строка 218)
   - **Результат:** экспорт в Excel не найдёт фото для двигателей, загруженных через актуальный путь.

2. **Локальное переопределение DB_PATH**
   - promote_and_cleanup.py:19 — `DB_PATH = Path(__file__).parent / 'engine_data.db'` (относительный путь)
   - Остальной код использует config.settings.DB_PATH (абсолютный через BASE_DIR)
   - Риск: если скрипт запускать не из корня проекта — откроет не ту БД.

3. **normalize_base_name определена, но не используется в продакшене**
   - utils/naming.py:10 — функция существует
   - Select-String по всему репо показывает использование **только в тестах** (tests/test_utils/test_naming.py)
   - parser.py и photo_manager используют свою инлайн-логику генерации имён.

4. **ON DELETE CASCADE в схеме БД не работает на проде**
   - modules/db.py строки 103, 116, 153 — объявлено CASCADE
   - repositories/engine_repo.py::delete() строки 212-214 — явное удаление modes/works
   - Комментарий в коде подтверждает: "на продакшен-БД (созданной до добавления CASCADE) он не работает"

5. **Массовый импорт не проверяет пустоту БД**
   - import_routes.py::import_folder использует executemany без проверки что engines пуста
   - Предположение "импорт на пустую БД" зафиксировано в комментариях и /api/clear, но не валидируется в коде.

6. **Дублирование логики получения путей фото**
   - photo_manager.engine_photo_disk_paths — каноническая
   - export_service._get_photo_paths — дублирует с другой схемой именования
   - diag_photos.py — собственная логика сканирования

7. **modules/__init__.py пустой, но modules/auth/__init__.py — фасад с 88 именами**
   - Несогласованность: некоторые модули имеют __all__, некоторые пустые.

8. **export_service импортирует PHOTOS_FOLDER напрямую из config.settings, а не через modules.db**
   - services/export_service.py:24 и 213 — `from config.settings import PHOTOS_FOLDER`
   - Остальные модули читают через modules.db (динамически для тестов)
   - Нарушает паттерн "динамическое чтение для monkeypatch в тестах".

9. **reset_admin_password.py импортирует из modules.db, но также имеет свою логику путей**
   - Строка 41: `from modules.db import DB_PATH, db_connection, PHOTOS_FOLDER, ...`
   - Но строка 27: комментарий про extract_images_from_excel — смешанные подходы.

10. **В tests/ есть temp/ с дублирующими определениями путей**
    - temp/temp_selftest.py:16-18, 52-53 — TEST_DB_PATH, TEST_PHOTOS_FOLDER + прямое присваивание в модули
    - Это тестовый код, но создаёт путаницу при поиске определений.

---

## 17. Известные особенности и история инцидентов

1. **Пути к данным (photos/motors/backups) должны идти только через config.settings** — раньше были относительные литералы, приводившие к тому, что `shutil.rmtree` стирал не ту папку.

2. **allEngines — единая точка результата для каталога/поиска/дерева**, все три источника обязаны писать в неё перед рендером.

3. **.suggest-dropdown — position: fixed с ручным позиционированием через JS (не absolute)** из-за `overflow:hidden` у модалок.

4. **/api/clear требует подтверждения "СТИРАТЬ" на фронтенде** — защита от повторения инцидента с потерей фото.

5. **Схема именования фото менялась:** старая `{base}img{n}{engine_id}.ext` → новая `ID{engine_id}_{n}.ext` (актуальная на момент снимка — см. раздел 7).

6. **Логика ID движков:** переход от чистого AUTOINCREMENT к переиспользованию минимального свободного ID при удалении (см. раздел 8) — актуальное поведение зафиксировано в `repositories/engine_repo.py::_next_free_id` и `create`.

7. **modules/photo_manager/__init__.py должен явно перечислять только те имена, которые РЕАЛЬНО определены в manager.py** — расхождение здесь уже приводило к падению приложения при старте (ImportError).

---

## 18. Итоговая сводка

| Метрика | Значение |
|---------|----------|
| Количество файлов проекта (исходный код, без .git/venv/tests/temp/docs) | ~65 |
| Количество модулей (папок с __init__.py) | 12 (modules, modules/auth, modules/backup_system, modules/engine_parser, modules/photo_manager, repositories, routes, schemas, services, static, static/js, utils, tests, tests/e2e, tests/test_repositories, tests/test_utils, tests/test_backup_system) |
| Количество файлов с путевыми константами | 18 (config/settings.py + 17 импортирующих) |
| Количество уникальных путевых констант | 10 (DB_PATH, PHOTOS_FOLDER, MOTORS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, CONFIG_DIR, FILE_USERS, FILE_TOKENS, ALLOWED_PHOTO_EXT, MAX_WORKERS) |
| Количество мест их использования (импортов) | ~45 (по Select-String) |
| Количество найденных дублей/расхождений (раздел 16) | 10 |
| Количество init.py с явными re-export списками | 6 (modules/auth, modules/backup_system, modules/engine_parser, modules/photo_manager, schemas, utils — пустой) |
| Из них синхронизированы с реальным содержимым модуля | 5 (modules/auth — фасад, modules/backup_system, modules/engine_parser, modules/photo_manager, schemas) |
| Несинхронизированные | 1 (utils/__init__.py пустой, но naming.py экспортирует функцию) |

---

**Отчёт создан:** docs/PROJECT_SNAPSHOT.md  
**Проанализировано файлов:** ~65 исходных файлов  
**Найдено констант:** 10 уникальных путевых + 3 конфигурационных  
**Найдено функций:** ~80 публичных функций в repositories/services/modules  
**Найдено дублей/расхождений:** 10