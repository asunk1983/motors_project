# Карта проекта Motors

## 1. Обзор

**Стек:** Flask (Python 3.x), SQLite, openpyxl/pandas, vanilla ES6+ JS

**Точка входа:** `app.py` — создаёт Flask-приложение, регистрирует blueprints через `routes/__init__.py`, инициализирует БД через `modules/db.py::init_db()`

**Запуск:** `python app.py` (порт 5000) или через Flask dev server. Продакшен: production-ready WSGI.

---

## 2. Дерево проекта

```
motors_project/
├── app.py                              # Точка входа Flask
├── CLAUDE.md                           # Инструкции для агентов
├── audit_report.md                     # Отчёт аудита
├── config/
│   └── settings.py                     # Глобальные константы (пути, настройки)
├── routes/
│   ├── __init__.py                     # Фабрика blueprints для Flask
│   ├── auth.py                         # Авторизация (login/logout/admin)
│   ├── engines.py                      # CRUD двигателей, modes, works
│   ├── photos.py                       # Фото двигателей (upload/download/delete)
│   ├── backup_routes.py                # Бэкапы (create/list/restore/download/delete)
│   ├── import_routes.py                # Импорт Excel-паспортов
│   ├── export_routes.py                # Экспорт в Excel
│   ├── knowledge_routes.py             # База знаний (статьи, словари)
│   ├── equipment_routes.py             # CRUD оборудования, типы, атрибуты
│   ├── equipment_photo_routes.py       # Фото оборудования
│   ├── incident_ticket_routes.py       # Заявки Инцидентов (CRUD, фото, экспорт)
│   ├── incident_photo_routes.py        # Фото заявок Инцидентов
│   ├── ticket_routes.py                # Заявки, отказы, работы (общий)
│   ├── location_routes.py              # Дерево мест (location_node)
│   ├── crew_routes.py                  # Справочник людей
│   ├── search.py                       # Поисковые подсказки, расширенный поиск
│   ├── status.py                       # Дашборд-статус приложения
│   ├── changelog.py                    # Changelog и wishlist
│   └── pages.py                        # Статические страницы (index, print)
├── modules/
│   ├── db.py                           # SQLite-соединения, init БД, миграции
│   ├── auth.py                         # Авторизация (токены, пароли, пользователи)
│   ├── engine_parser/
│   │   └── parser.py                   # Парсинг Excel-паспортов
│   ├── photo_manager/
│   │   ├── manager.py                  # Фото двигателей (CRUD файлов)
│   │   ├── incident_manager.py         # Фото заявок Инцидентов
│   │   └── equipment_manager.py        # Фото оборудования
│   └── backup_system/
│       └── backup.py                   # Backup/restore с манифестом, чексуммами
├── repositories/
│   ├── __init__.py                     # Подсказка: репозитории = SQL только
│   ├── engine_repo.py                  # SQL для engines
│   ├── mode_repo.py                    # SQL для operating_modes
│   ├── work_repo.py                    # SQL для maintenance_works
│   ├── equipment_repo.py               # SQL для equipment, types, attributes
│   ├── location_repo.py                # SQL для location_node
│   ├── crew_repo.py                    # SQL для crew
│   ├── incident_ticket_repo.py         # SQL для incident_ticket
│   ├── incident_equipment_repo.py      # SQL для связей ticket↔equipment
│   ├── ticket_repo.py                  # SQL для ticket, failure, equipment_work
│   └── knowledge_repo.py               # SQL для dictionaries, articles
├── schemas/
│   ├── __init__.py                     # Подсказка: схемы валидации
│   ├── engine_schema.py                # Валидация engine, modes, works
│   ├── knowledge_schema.py             # Валидация article, dictionary
│   ├── equipment_schema.py             # Валидация equipment, types, attributes
│   └── ticket_schema.py                # Валидация ticket, failure, work
├── services/
│   ├── __init__.py                     # Подсказка: сервисы = бизнес-логика
│   ├── export_service.py               # Экспорт в Excel (openpyxl)
│   └── incident_service.py             # Бизнес-логика заявок Инцидентов
├── utils/
│   ├── date.py                         # Форматирование дат
│   ├── naming.py                       # Нормализация имён файлов
│   ├── file_store.py                   # JSON load/save
│   └── logging.py                      # log_message() с thread-safe записью
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── print.css
│   ├── ico/                            # SVG-иконки (27 файлов)
│   └── js/                             # Frontend-модули (21 файл)
├── templates/
│   ├── index.html                      # Главная страница
│   ├── print.html                      # Печать двигателя
│   ├── print_incident.html             # Печать заявки
│   └── print_equipment.html            # Печать оборудования
└── docs/
    └── project_map.md                  # Данный файл
```

---

## 3. Карта модулей

| Пакет | Роль | Слой | Взаимодействия |
|-------|------|------|----------------|
| **config/** | Централизованные настройки | Data/Configuration | modules/, routes/, utils/ |
| **routes/** | HTTP-интерфейс (blueprints) | Presentation | modules/, repositories/, schemas/, services/ |
| **modules/** | Бизнес-логика | Business | config/, repositories/ |
| **services/** | Оркестрация (экспорт, incident) | Business | repositories/, modules/ |
| **repositories/** | SQL-запросы | Data Access | (ничего) |
| **schemas/** | Валидация DTO | Business (Validation) | используется routes/ |
| **utils/** | Вспомогательные функции | Infrastructure | config/, logging |

**Правила взаимодействия:**
- Routes → Schemas (валидация) → Repositories (SQL) → Modules (file ops)
- Routes → Services (если есть) → Repositories + Modules
- Repositories принимают `sqlite3.Connection` (DI), без бизнес-логики
- Modules photo_manager работают напрямую с файловой системой


## 4. Карта "функция → файлы"

### 4.1 Авторизация (auth)

**Основные файлы:**
- `routes/auth.py` — маршруты (login, logout, refresh-token, admin CRUD)
- `modules/auth.py` — ядро (verify_password, get_user_by_username, create_user, revoke_token)
- `config/settings.py` — FILE_USERS, FILE_TOKENS, DB_PATH
- `utils/file_store.py` — load_json/save_json для users.json

**Вспомогательные:**
- `config/users.json` — пользовательские учётные записи
- `config/tokens.json` — токены доступа

**Не трогать:**
- `config/settings.py` (только пути)

---


### 4.2 Управление двигателями (engines)

**Основные файлы:**
- `routes/engines.py` — CRUD, list, locations-tree
- `repositories/engine_repo.py` — SQL: get_by_id, get_with_details, create, update, delete, get_locations_tree, count_all, _next_free_id
- `schemas/engine_schema.py` — validate_engine_payload, sanitize_engine_data
- `modules/db.py` — ENGINE_COLUMNS_ORDERED, ENGINE_COLUMNS

**Вспомогательные:**
- `routes/photos.py` — photo_count обновляется при загрузке фото
- `modules/photo_manager/manager.py` — delete_engine_photos_from_disk (при удалении двигателя)

**Не трогать:**
- `repositories/mode_repo.py`, `repositories/work_repo.py` (только SQL)

---

### 4.3 Фото двигателей

**Основные файлы:**
- `routes/photos.py` — HTTP-обёртка (upload, delete, replace, get)
- `modules/photo_manager/manager.py` — файловая логика (upload_engine_photos, delete_engine_photo, replace_engine_photo)

**Вспомогательные:**
- `config/settings.py` — PHOTOS_FOLDER, ALLOWED_PHOTO_EXT
- `repositories/engine_repo.py` — update_photo_count

**Не трогать:**
- `routes/engines.py` (только вызывает delete_engine_photos_from_disk)

---

### 4.4 Бэкапы и восстановление

**Основные файлы:**
- `routes/backup_routes.py` — list, create, inspect-upload, restore, download, delete
- `modules/backup_system/backup.py` — create_backup, restore_backup, inspect_uploaded_backup, list_backups, _build_backup_zip_bytes, _apply_backup_zip

**Вспомогательные:**
- `config/settings.py` — BACKUPS_FOLDER, BACKUP_STAGING_FOLDER
- `modules/db.py` — DB_PATH, PHOTOS_FOLDER

**Не трогать:**
- `routes/photos.py` (только использует BACKUP_STAGING_FOLDER)

---

### 4.5 Импорт Excel-паспортов

**Основные файлы:**
- `routes/import_routes.py` — import_folder (параллельный импорт)
- `modules/engine_parser/parser.py` — parse_file_fast, parse_engine_data, extract_images_from_excel

**Вспомогательные:**
- `config/settings.py` — MOTORS_FOLDER, PHOTOS_FOLDER, MAX_WORKERS
- `modules/db.py` — db_connection, ENGINE_COLUMNS_ORDERED
- `utils/logging.py` — log_message

**Не трогать:**
- `routes/export_routes.py`

---

### 4.6 Экспорт в Excel

**Основные файлы:**
- `routes/export_routes.py` — /engines/export
- `services/export_service.py` — export_to_xlsx (с печатными настройками)

**Вспомогательные:**
- `repositories/engine_repo.py` — get_with_details
- `modules/photo_manager/manager.py` — get_engine_photos

**Не трогать:**
- `routes/import_routes.py`

---

### 4.7 База знаний

**Основные файлы:**
- `routes/knowledge_routes.py` — articles, failure_modes, failure_causes (только superadmin)
- `repositories/knowledge_repo.py` — SQL для словарей, статей

**Вспомогательные:**
- `schemas/knowledge_schema.py` — валидация

**Не трогать:**
- `routes/incident_ticket_routes.py` (чтение dictionaries открыто)

---

### 4.8 Оборудование (equipment)

**Основные файлы:**
- `routes/equipment_routes.py` — CRUD оборудования, типы, атрибуты, stock summary, экспорт
- `repositories/equipment_repo.py` — SQL для equipment, equipment_type, attribute_definition

**Вспомогательные:**
- `routes/location_routes.py` — location_node для equipment.location_node_id
- `routes/equipment_photo_routes.py` — фото оборудования
- `modules/photo_manager/equipment_manager.py` — файловая логика

**Не трогать:**
- `routes/equipment_photo_routes.py` (только GET)

---

### 4.9 Заявки Инцидентов (incident-tickets)

**Основные файлы:**
- `routes/incident_ticket_routes.py` — CRUD, confirm_failure, экспорт
- `repositories/incident_ticket_repo.py` — SQL для incident_ticket
- `repositories/incident_equipment_repo.py` — связи ticket↔equipment
- `services/incident_service.py` — create_ticket, update_ticket, delete_crew, move_location

**Вспомогательные:**
- `routes/crew_routes.py` — crew (инициаторы/исполнители)
- `routes/location_routes.py` — места
- `modules/photo_manager/incident_manager.py` — фото заявок

**Не трогать:**
- `routes/ticket_routes.py` (другой модуль заявок)

---

### 4.10 Места (location tree)

**Основные файлы:**
- `routes/location_routes.py` — CRUD location_node, search, move
- `repositories/location_repo.py` — SQL, get_subtree_ids, is_referenced

**Вспомогательные:**
- `routes/engines.py` — workshop/location (старый формат, мигрируется)
- `routes/equipment_routes.py` — location_node_id

**Не трогать:**
- `repositories/incident_ticket_repo.py` (только reads location)

---

### 4.11 Справочник людей (crew)

**Основные файлы:**
- `routes/crew_routes.py` — CRUD crew
- `repositories/crew_repo.py` — SQL, is_referenced

**Вспомогательные:**
- `routes/incident_ticket_routes.py` — initiator_ids, executor_ids

**Не трогать:**
- `repositories/incident_ticket_repo.py` (только reads)

---

### 4.12 Поиск

**Основные файлы:**
- `routes/search.py` — /search-suggestions, extended engine search
- `modules/db.py` — ENGINE_COLUMNS, MODE_COLUMNS

**Вспомогательные:**
- `repositories/engine_repo.py` — get_all с поиском

**Не трогать:**
- `services/` (поиск напрямую в SQL)

---

### 4.13 Статус приложения

**Основные файлы:**
- `routes/status.py` — /status (счётчики, версии, размер БД)
- `repositories/engine_repo.py` — count_all

**Вспомогательные:**
- `repositories/equipment_repo.py` — count_all
- `repositories/incident_ticket_repo.py` — count_all, count_by_status
- `modules/photo_manager/equipment_manager.py` — count_all_photos
- `modules/photo_manager/incident_manager.py` — count_all_photos


## 5. Граф зависимостей между функциональными областями

```
auth (routes/auth.py)
    │
    ├── config/settings.py (FILE_USERS, FILE_TOKENS, DB_PATH)
    ├── modules/db.py (db_connection)
    └── modules/auth.py (get_user_by_token, verify_password)

engines + photos
    ├── routes/engines.py ─┐
    │                     ├── repositories/engine_repo.py
    │                     ├── schemas/engine_schema.py
    │                     └── modules/db.py (ENGINE_COLUMNS)
    │
    └── routes/photos.py ─ modules/photo_manager/manager.py
                               └── config/settings.py (PHOTOS_FOLDER)

backup
    ├── routes/backup_routes.py
    │       ├── modules/backup_system/backup.py
    │       └── modules/db.py (DB_PATH, PHOTOS_FOLDER)
    │
    └── modules/photo_manager/ (для фото в бэкапе)

import + export
    ├── routes/import_routes.py
    │       ├── modules/engine_parser/parser.py
    │       ├── config/settings.py (MOTORS_FOLDER, PHOTOS_FOLDER)
    │       └── utils/logging.py
    │
    └── routes/export_routes.py ─ services/export_service.py

knowledge
    ├── routes/knowledge_routes.py
    │       ├── repositories/knowledge_repo.py
    │       └── schemas/knowledge_schema.py
    │
    └── routes/auth.py::_require_superadmin

equipment
    ├── routes/equipment_routes.py
    │       ├── repositories/equipment_repo.py
    │       ├── schemas/equipment_schema.py
    │       └── services/export_service.py (export_equipment_to_xlsx)
    │
    ├── routes/equipment_photo_routes.py ─ modules/photo_manager/equipment_manager.py
    │                                        └── config/settings.py (EQUIPMENT_PHOTOS_FOLDER)
    │
    └── routes/location_routes.py (location_node_id)

incident-tickets
    ├── routes/incident_ticket_routes.py
    │       ├── repositories/incident_ticket_repo.py
    │       ├── repositories/incident_equipment_repo.py
    │       ├── services/incident_service.py
    │       └── routes/auth.py::_require_superadmin
    │
    ├── routes/crew_routes.py (инициаторы/исполнители)
    └── routes/location_routes.py (location_node_id)

location
    ├── routes/location_routes.py
    │       └── repositories/location_repo.py
    │
    └── USED BY: equipment, incident-tickets

crew
    ├── routes/crew_routes.py
    │       └── repositories/crew_repo.py
    │
    └── USED BY: incident-tickets (initiators/executors)

search
    └── routes/search.py ─ modules/db.py (ENGINE_COLUMNS, MODE_COLUMNS)

status
    └── routes/status.py ─ все репозитории + photo_managers
```

**Общие модули, затрагивающие несколько фич:**
- `config/settings.py` — пути к папкам (PHOTOS_FOLDER, BACKUPS_FOLDER, MOTORS_FOLDER, INCIDENT_PHOTOS_FOLDER, EQUIPMENT_PHOTOS_FOLDER)
- `modules/db.py` — db_connection, ENGINE_COLUMNS*, MODE_COLUMNS
- `routes/auth.py` — auth_bp.before_app_request защищает POST/PUT/DELETE
- `repositories/location_repo.py` — location_node используется equipment и incident-tickets

---
## 6. Признаки для определения нужных файлов

| Ключевое слово/сущность | Скорее всего нужны файлы |
|------------------------|--------------------------|
| "фото", "photo" | `modules/photo_manager/manager.py`, `routes/photos.py`, `config/settings.py::PHOTOS_FOLDER` |
| "бэкап", "backup" | `modules/backup_system/backup.py`, `routes/backup_routes.py`, `config/settings.py::BACKUPS_FOLDER` |
| "двигатель", "engine" | `routes/engines.py`, `repositories/engine_repo.py`, `schemas/engine_schema.py`, `modules/photo_manager/manager.py` |
| "заявка", "ticket", "incident" | `routes/incident_ticket_routes.py`, `repositories/incident_ticket_repo.py`, `services/incident_service.py` |
| "оборудование", "equipment" | `routes/equipment_routes.py`, `repositories/equipment_repo.py`, `schemas/equipment_schema.py` |
| "место", "location" | `routes/location_routes.py`, `repositories/location_repo.py` |
| "человек", "crew" | `routes/crew_routes.py`, `repositories/crew_repo.py` |
| "режим", "mode" | `repositories/mode_repo.py`, используется через `routes/engines.py` |
| "работа", "work" | `repositories/work_repo.py`, используется через `routes/engines.py` |
| "импорт", "import" | `routes/import_routes.py`, `modules/engine_parser/parser.py` |
| "экспорт", "export" | `routes/export_routes.py`, `services/export_service.py` |
| "поиск" | `routes/search.py`, `modules/db.py::ENGINE_COLUMNS` |
| "авторизация", "auth", "логин" | `routes/auth.py`, `modules/auth.py` |
| "знания", "article", "knowledge" | `routes/knowledge_routes.py`, `repositories/knowledge_repo.py` |

---

## 7. Известные технические долги и хрупкие места

### 7.1 Дублирование констант

- `config/settings.py` — единый источник путей
- `modules/db.py` — ENGINE_COLUMNS_ORDERED, ENGINE_COLUMNS, MODE_COLUMNS
- `modules/photo_manager/manager.py::_photos_folder()` — читает PHOTOS_FOLDER динамически из modules.db (для тестового monkeypatch)
- **При изменении пути к фото:** править только `config/settings.py`

### 7.2 Миграция workshop/location → location_node

- Старый формат: `workshop` + `location` как колонки в engines
- Новый формат: `location_node` с иерархией (shared между equipment и incident-tickets)
- При удалении двигателя: `photo_manager.delete_engine_photos_from_disk()` вызывается ДО `engine_delete()`

### 7.3 Каскадное удаление в SQLite

- `repositories/engine_repo.py::delete()` — дочерние записи (modes, works) удаляются ЯВНО
- Это гарантирует целостность данных при старой продакшен-БД без FK CASCADE

### 7.4 Атомарность фото-операций

- `modules/photo_manager/manager.py::_save_upload_atomically()` — временный файл + `os.replace()`
- На Windows нужен retry из-за PermissionError
- При замене фото (`replace_engine_photo`) старый файл удаляется после успешной записи

### 7.5 Бэкап-лок

- `modules/backup_system/backup.py` — использует `backup_restore.lock`
- restore выполняется только один раз в момент времени

### 7.6 Права доступа

- `routes/auth.py::before_app_request` — проверка авторизации для всех /api/
- `reader` role: доступ только к GET
- Исключения: `_AUTH_EXEMPT_WRITE_PATHS`, `_READER_ALLOWED_WRITE_PATHS`

### 7.7 Экспорт в Excel - печать

- `services/export_service.py`
- `fitToWidth=1` + `fitToHeight=0` + `fitToPage=True` — критично для печати
- Без `fitToPage=True` Excel игнорирует `fitToWidth`

### 7.8 Поиск по кириллице

- SQLite `LIKE ... COLLATE NOCASE` не работает с кириллицей
- Поиск делается в Python через `str.lower()`
- Безопасно при небольшом количестве записей

### 7.9 Два разных модуля заявок

- `routes/ticket_routes.py` — старый модуль (ticket, failure, equipment_work)
- `routes/incident_ticket_routes.py` — новый модуль Инцидентов
- Не путать: это РАЗНЫЕ сущности

---

## Как запросить больше контекста при правке

1. Изменение `config/settings.py` → запросить все файлы, импортирующие константы
2. Изменение `modules/db.py::ENGINE_COLUMNS_*` → запросить все repositories и schemas
3. Изменение `modules/backup_system/backup.py` → запросить `backup_routes.py`, все photo_manager модули
4. Изменение схемы имён файлов фото → запросить все `*_manager.py`, `backup.py`