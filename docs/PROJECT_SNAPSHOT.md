# PROJECT_SNAPSHOT — motors_project

> **Снимок архитектуры и состояния кода** на основе реального содержимого репозитория `c:\motors_project`.
> Документ описывает **как устроен** проект (что есть), **как запускается** (как поднять) и **как развивается** (как добавлять новое).
> Дата снимка: 2026-01-09.
> **Обновление 2026-09-15:** удалены описания вырезанных модулей «База знаний»/«Заявки» (`knowledge_*`, `ticket_*` — commit 758aa34).
> **Обновление 2026-09-16 (сверка с реальным репозиторием, commit 12a1697 / ветка main):** актуализировано дерево файлов и все ссылки на пути; добавлены реально существующие, но не описанные файлы (в т.ч. `modules/audit.py`, `repositories/audit_repo.py`, `routes/audit_routes.py`, `static/js/audit.js`, `utils/date.py`, `utils/logging.py`, `services/equipment_location_migration.py`, `scripts/`); удалены несуществующие пути (`static/js/app.js`, `state.js`, `api.js`, `services/import_service.py`, `schemas/incident_ticket_schema.py`, каталоги `photos_equipment/`/`photos_incidents/`/`uploads/`/`exports/`, `README.md`); пересчитаны цифры тестов (§13) и метрики (§16).

---

## Оглавление

1. [Общее описание и стек](#1-общее-описание-и-стек)
2. [Структура каталогов](#2-структура-каталогов)
3. [Запуск и окружение](#3-запуск-и-окружение)
4. [Слой данных: SQLite + репозитории](#4-слой-данных-sqlite--репозитории)
5. [Сервисный слой и утилиты](#5-сервисный-слой-и-утилиты)
6. [HTTP-роуты (Flask Blueprints)](#6-http-роуты-flask-blueprints)
7. [Аутентификация и авторизация](#7-аутентификация-и-авторизация)
8. [Бэкапы: создание, инспекция, восстановление](#8-бэкапы-создание-инспекция-восстановление)
9. [Импорт / Экспорт](#9-импорт--экспорт)
10. [Парсер xlsx-каталога и нормализация имён фото](#10-парсер-xlsx-каталога-и-нормализация-имён-фото)
11. [Frontend: HTML + vanilla JS (модули)](#11-frontend-html--vanilla-js-модули)
12. [UI-табы и состояние каталога](#12-ui-табы-и-состояние-каталога)
13. [Тестирование: pytest + Playwright e2e](#13-тестирование-pytest--playwright-e2e)
14. [Известные ограничения и решения](#14-известные-ограничения-и-решения)
15. [Как добавить новую функциональность (рецепты)](#15-как-добавить-новую-функциональность-рецепты)
16. [Точки расширения и TODO](#16-точки-расширения-и-todo)

---

## 1. Общее описание и стек

**Назначение.** Веб-приложение «motors_project» — каталог электродвигателей предприятия с функциями:
- учёт карточек двигателей (характеристики, режимы работы, ремонты);
- прикрепление фотографий к карточкам;
- поиск/фильтрация по любым полям;
- импорт каталога из Excel-файла (`*.xlsx`) с автоприкреплением фотографий по имени;
- ручной и автоматический экспорт/импорт JSON-снимков состояния;
- резервное копирование БД + фото в zip с манифестом и SHA-256 чексуммами;
- учёт инцидентов (заявки) и обслуживание оборудования (`crew`, `equipment`, `equipment_placement`) с фото-связями;
- журнал изменений и wishlist — теперь JSON-файлы `data/changelog.json` / `data/wishlist.json` (таблиц `changelog_entries`/`wishlist_items` в схеме больше нет; миграция — `scripts/migrate_changelog_to_json.py`, `scripts/migrate_wishlist_to_json.py`);
- журнал аудита правок (таблица `audit_log`, `modules/audit.py`, `repositories/audit_repo.py`, API `/api/audit/*`, UI — таб «Аудит» в `static/js/audit.js`);
- аутентификация по логину/паролю, токены, роли (`admin` / `user`).

**Стек.**

| Слой        | Технология                                                   |
|-------------|--------------------------------------------------------------|
| Backend     | Python 3, Flask (Blueprints), SQLite (стандартный модуль)    |
| HTTP-клиент | встроенные запросы из JS через `fetch`; Bearer-токен подставляет `apiFetch()` из `static/js/auth.js` |
| Frontend    | Vanilla JS (классические `<script src>`, без ES-модулей и сборки), HTML, CSS (без фреймворков) |
| Excel       | `openpyxl`                                                   |
| Архивация   | стандартный `zipfile` + `sqlite3` Online Backup API          |
| Тесты       | `pytest` — 592 unit/route-теста (591 passed, 1 skipped); `playwright` — 81 e2e (Chrome headless, запускается на изолированном Flask-сервере) |

**Ключевые принципы архитектуры (как они видны в коде):**
- **Repository pattern** — SQL изолирован в `repositories/`, сервисы и роуты работают с функциями-репозиториями.
- **Сервисный слой** (`services/`) оркеструет репозитории и инкапсулирует файловые/zip-операции.
- **Тонкие роуты** (`routes/`) — принимают запрос, вызывают сервис/репозиторий, сериализуют ответ.
- **Frontend без сборки** — браузер сам подгружает обычные скрипты по `<script src="/static/js/...">` (перечень — в `templates/index.html`, строки 976–993); ES-модулей и сборщика нет, функции живут в глобальной области видимости.
- **Атомарность бэкапов** — staging-папка + rollback point, чтобы можно было безопасно восстановиться.
- **Декомпозиция по фичам** — каждая фича в своих подпапках (`modules/`, `routes/`, `repositories/`, `schemas/`).

---

## 2. Структура каталогов

Реальная структура (сокращённо):

```
c:\motors_project\
+- app.py                              # Flask-приложение, точка входа
+- config\settings.py                  # Пути и константы (DB_PATH, PHOTOS_FOLDER, PHOTO_FOLDERS, ...)
+- engine_data.db                      # БД SQLite — в КОРНЕ проекта (не в data\)
+- data\                               # JSON-хранилища вкладки «Инфо»: changelog.json, wishlist.json (+ .bak)
+- backups\                            # готовые zip-бэкапы
+- backup_staging\                     # временная зона для restore (см. §8)
+- photos\                             # фото двигателей: photos/<engine_id>/<base_name>.<ext>
+- PhotoE\                             # фото оборудования (equipment_id)
+- PhotoI\                             # фото инцидентов (ID<ticket_id>_<n>.<ext>)
+- motors\                             # папка импорта (MOTORS_FOLDER)
+- scripts\                            # служебные скрипты (миграции JSON, диагностика аудита)
+- diag_photos.py, diag_modal.py, measurement.py, test_mode_repo.py   # разовые диагностические скрипты
+- requirements.txt, version.txt, summary.txt, index.html, mockup.html
+- push-deploy.bat/.sh, rollback-remote.sh                            # деплой на прод
+- modules\
|  +- db.py                            # get_db_connection, db_connection (context manager), init_db
|  +- audit.py                         # log_creation / log_deletion / log_field_changes (журнал аудита)
|  +- auth\                            # ПАКЕТ (не auth.py): auth.py — фасад, hashing, db_users, file_users, tokens, decorators
|  +- engine_parser\
|  |  +- parser.py                     # parse_file_fast, parse_engine_data, parse_operating_modes, parse_maintenance_works, extract_images_from_excel
|  +- photo_manager\
|  |  +- manager.py                    # фото двигателей: upload_engine_photos, delete_engine_photo, engine_photo_disk_paths
|  |  +- equipment_manager.py          # фото оборудования (PhotoE)
|  |  +- incident_manager.py           # фото инцидентов (PhotoI)
|  +- backup_system\
|     +- backup.py                     # create_backup, list_backups, inspect_uploaded_backup, restore_backup, download_backup, delete_backup
+- repositories\                       # тонкий слой SQL (см. §4)
|  +- engine_repo.py, mode_repo.py, work_repo.py
|  +- location_repo.py, audit_repo.py
|  +- crew_repo.py, equipment_repo.py, incident_equipment_repo.py
|  +- equipment_placement_repo.py, incident_ticket_repo.py
+- routes\                             # Flask Blueprints (см. §6)
|  +- auth.py, engines.py, search.py
|  +- equipment_routes.py, equipment_photo_routes.py
|  +- incident_ticket_routes.py, incident_photo_routes.py
|  +- backup_routes.py, import_routes.py, export_routes.py
|  +- location_routes.py
|  +- pages.py, status.py, photos.py
|  +- changelog.py, crew_routes.py, audit_routes.py
+- schemas\                            # лёгкие валидаторы (функции, без dataclass-обязательств)
|  +- engine_schema.py, equipment_schema.py
+- services\
|  +- export_service.py                # экспорт каталога/оборудования/инцидентов в XLSX
|  +- incident_service.py              # бизнес-логика инцидентов
|  +- backup_service.py                # тонкий фасад над modules.backup_system
|  +- equipment_location_migration.py  # миграция старых текстовых мест в дерево location_node
+- utils\
|  +- naming.py                        # normalize_base_name (единый источник правды)
|  +- file_store.py                    # load_json / save_json
|  +- date.py                          # format_ru_date, is_valid_iso_date
|  +- logging.py                       # log_message
+- static\
|  +- js\                              # 21 файл, подключаются как обычные скрипты в index.html (976–993)
|  |  +- common.js                     # общие хелперы: escapeHtml/escapeAttr/debounce/showToast/formatRuDateTime/attachEntitySuggest/initPanelResizer
|  |  +- auth.js                       # токен в localStorage, apiFetch() с Authorization: Bearer, login/logout, вкладка Админ
|  |  +- catalog.js                    # таблица каталога, сортировка, пагинация, switchTab()
|  |  +- engines.js                    # глобалы каталога: allEngines, currentPage, pageSize, currentSort, selectedEngineIds
|  |  +- engineCard.js                 # детальная карточка + галерея фото + обрезка (canvas)
|  |  +- locationTree.js               # дерево Цех→Место на Каталоге (activeWorkshop/activeLocation)
|  |  +- importer.js                   # импорт xlsx + очистка БД (/api/clear), поиск фото
|  |  +- exportManager.js              # экспорт выбранного, кэш «последних экспортов»
|  |  +- search.js                     # расширенный поиск (заменяет allEngines)
|  |  +- equipment.js, equipmentLocationTree.js, equipmentPrint.js
|  |  +- incidents.js, incidentCrew.js, incidentLocations.js, incidentLocationTree.js, incidentPrint.js
|  |  +- backup.js, info.js            # бэкапы + вкладка «Инфо» (changelog/wishlist/о системе)
|  |  +- audit.js                      # таб «Аудит»: журнал правок (/api/audit/log)
|  |  +- print.js                      # страницы печати (двигатель/оборудование/заявка)
|  +- css\                             # style.css, print.css
|  +- ico\                             # 34 svg-иконки UI
+- templates\
|  +- index.html                       # единая SPA-HTML страница (табы #tab-*)
|  +- print.html, print_equipment.html, print_incident.html   # печатные страницы
+- tests\
|  +- conftest.py                      # фикстуры db_conn (in-memory SQLite), file_users_env
|  +- test_repositories\               # 159 тестов по всем *_repo.py
|  +- test_routes\, test_services\, test_audit\, test_auth\, test_photo_manager\, test_engine_parser\, test_backup_system\, test_utils\
|  +- e2e\
|  |  +- conftest.py                   # Playwright: Chrome headless, свой Flask-сервер на изолированной runtime-БД
|  |  +- helpers.py                    # make_engine, login_ui, switch_tab, wait_toast
|  |  +- test_01_auth.py ... test_11_misc.py
+- docs\                               # эта и другие документации (HANDOFF.md, TEST_PLAN.md, tests.md, server_reference.md, ...)
+- requirements.txt
```

---

## 3. Запуск и окружение

**Зависимости** (`.venv`, `pip freeze` — 26 пакетов; `requirements.txt` присутствует): Flask 3.1.3, flask-cors, Werkzeug, openpyxl 3.1.5, pandas/numpy, pillow, pytest 9.1.1, playwright 1.62.0 (Python 3.14.6).

**Переменные окружения:**
- `MOTORS_*` — переопределение всех путей проекта (используется e2e-тестами для изоляции; в проде не задаётся). Полный список — в `tests/e2e/conftest.py` (`_RUNTIME_REL`): `MOTORS_DB_PATH`, `MOTORS_MOTORS_FOLDER`, `MOTORS_PHOTOS_FOLDER`, `MOTORS_INCIDENT_PHOTOS_FOLDER`, `MOTORS_EQUIPMENT_PHOTOS_FOLDER`, `MOTORS_BACKUPS_FOLDER`, `MOTORS_BACKUP_STAGING_FOLDER`, `MOTORS_CONFIG_DIR`, `MOTORS_FILE_USERS`, `MOTORS_FILE_TOKENS`, `MOTORS_DATA_DIR`, `MOTORS_LOG_FILE`.
- `FLASK_ENV` — стандартная для Flask.
- `E2E_BASE_URL` — **не существует** (прежняя версия документа ошибалась): e2e поднимает собственный Flask-сервер на свободном порту (`make_server('127.0.0.1', 0, app)`) и берёт `base_url` из фикстуры `live_server`.

**Пути в `config/settings.py` (единственный источник правды):**
- `DB_PATH` — `engine_data.db` **в корне проекта** (не в `data/`).
- `MOTORS_FOLDER` — `motors/` (папка импорта).
- `PHOTOS_FOLDER` — `photos/` (двигатели).
- `INCIDENT_PHOTOS_FOLDER` — `PhotoI/`.
- `EQUIPMENT_PHOTOS_FOLDER` — `PhotoE/`.
- `PHOTO_FOLDERS` — список `[('photos', …), ('PhotoI', …), ('PhotoE', …)]` для backup/restore/clear_database.
- `BACKUPS_FOLDER` — `backups/`; `BACKUP_STAGING_FOLDER` — `backup_staging/` (временная зона при restore).
- `CONFIG_DIR` — `config/`; `FILE_USERS` — `config/users.json`; `FILE_TOKENS` — `config/tokens.json`.
- `DATA_DIR` — `data/`; `CHANGELOG_JSON_PATH` — `data/changelog.json`; `WISHLIST_JSON_PATH` — `data/wishlist.json`.
- `ALLOWED_PHOTO_EXT`, `MAX_WORKERS = 4`, `LOG_FILE` — `app.log`.
- Каталогов/констант `UPLOADS_FOLDER`, `EXPORTS_FOLDER`, `PHOTOS_EQUIPMENT_FOLDER`, `PHOTOS_INCIDENTS_FOLDER`, `CHANGELOG_FILE`, `WISHLIST_FILE` в коде нет.

**Команды (Windows, venv проекта):**

```bash
# Установка
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Запуск приложения
.venv\Scripts\python.exe app.py
# -> http://localhost:5000

# Unit/route тесты
.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e
# (на 2026-09-16: 591 passed, 1 skipped, 592 собрано, ~57 с)

# E2E (Playwright; браузеры должны быть установлены: `playwright install chrome`)
.venv\Scripts\python.exe -m pytest tests/e2e -q
# (на 2026-09-16: 81 passed, ~158 с)
# Поднимать app.py вручную НЕ нужно — фикстура live_server сама стартует
# изолированное приложение на свободном порту с временной runtime-БД.
# Результаты пишутся в docs/e2e_test_results.md (+ tests/e2e/.results.json)
```

**Инициализация БД.** При первом запуске `init_db()` создаёт все таблицы (см. §4) идемпотентно (`CREATE TABLE IF NOT EXISTS`).
Миграции — через ручные `ALTER TABLE` при необходимости (см. §4 про auto-migration).

---

## 4. Слой данных: SQLite + репозитории

### 4.1. Соединение с БД

`modules/db.py`:
- `get_db_connection()` — открывает соединение с `row_factory=sqlite3.Row` (чтобы `.fetchall()` возвращал dict-like).
- `db_connection()` — context manager. Сам открывает и коммитит; в случае исключения откатывает.
- `init_db(conn=None)` — создаёт все таблицы (`CREATE TABLE IF NOT EXISTS`). `conn=None` означает production-режим (откроет свой), `conn=<sqlite3.Connection>` — тестовый режим (использует переданное соединение).

### 4.2. Схема (таблицы)

Из `modules/db.py` и комментариев к `init_db()`:

| Таблица | Назначение | Ключевые поля |
|---|---|---|
| `engines` | Карточка двигателя | `id`, `filename` (откуда импортирован), `purpose`, `workshop`, `location`, `engine_type`, `manufacturer`, `serial_number`, подшипники (`bearing_front`/`bearing_rear`), `shaft_diameter`, `protection_class`, `mounting_type`, `temp_sensor`, `encoder`, `cooling`, `note`, `photo_count`, `status` (`work`/`archived`), `created_at`, `updated_at` |
| `operating_modes` | Режимы работы | FK `engine_id` (CASCADE) |
| `maintenance_works` | Ремонты/ТО | FK `engine_id` (CASCADE), `status` |
| `changelog_entries` | Журнал изменений | `entry_date`, `text`, `created_at` |
| `wishlist_items` | Пожелания/идеи | `text`, `done` |
| `users` | Пользователи | `username` UNIQUE, `password_hash`, `role` (`admin`/`user`), `last_login`, `last_edit` |
| `tokens` | Сессионные токены | `user_id`, `token_hash` UNIQUE, `expires_at` |
| `crew` | Бригады | … |
| `equipment` | Оборудование (не двигатели) | … |
| `incident_equipment` | Связь инцидент-оборудование | … |
| `incident_link` | Связи между инцидентами | … |
| `incident_ticket` | Тикеты инцидентов | … |

### 4.3. Auto-migration

В коде присутствует паттерн `_ensure_column(cursor, table, column, definition)` — новый столбец добавляется одной строкой рядом с определением таблицы, без её пересоздания. Пример из `db.py`:
> `_ensure_column(cursor, 'users', 'crew_id', 'INTEGER REFERENCES crew(id)')`

То есть добавление нового столбца = одна строка `_ensure_column(...)` рядом с таблицей, без пересоздания.

### 4.4. Репозитории

Каждый файл в `repositories/` — набор чистых функций `fn(conn, *args, **kwargs) -> Row | list[Row] | bool`. Никаких глобальных состояний, всё через `conn`. Это позволяет легко тестировать.

**`engine_repo.py` (основной):**
- `get_by_id(conn, engine_id) -> Row | None`
- `get_with_details(conn, engine_id) -> Row | None` — двигатель + `modes` + `works`.
- `get_all(conn, limit, offset, search_field, search_query, sort_by, sort_dir) -> list[Row]`
- `count_all(conn, search_field, search_query) -> int`
- `create(conn, data) -> int` (новый `id`)
- `update(conn, engine_id, data) -> bool`
- `delete(conn, engine_id) -> bool` (каскадно снесёт modes/works — `ON DELETE CASCADE` в БД)
- `update_photo_count(conn, engine_id, count)`
- `get_by_filename(conn, filename)`
- `get_modes_for_engine(conn, engine_id)`, `get_works_for_engine(conn, engine_id)`

**`mode_repo.py` / `work_repo.py`:**
- `replace_all(conn, engine_id, items)` — атомарная замена всех режимов/работ двигателя (единственный путь записи, используемый роутами).
- `get_all(conn, engine_id)`, `create(...)`, `delete_all_for_engine(...)` — точечные операции (`create` роутами не вызывается).

**`location_repo.py`** — дерево мест (`location_node`), не плоский справочник:
- `list_all()`, `get_children()`, `get_by_id()`, `get_breadcrumb()/get_breadcrumb_text()`, `search()`.
- `create()`, `update()`, `move()`, `delete()`, `get_subtree_ids()`.
- Защита от разрушения дерева: `has_children()`, `is_referenced()`.

**`incident_*`, `crew_repo`, `equipment_repo`, `equipment_placement_repo`:**
- Аналогичный набор CRUD-операций для соответствующих сущностей (`equipment_repo` — самый крупный: ~29 функций, включая типы, определения атрибутов, `get_effective_attributes`, `get_stock_summary`).

**`audit_repo.py`:**
- `list_entries(conn, entity_type=None, entity_id=None, ...)` — выборка журнала аудита с подстановкой человекочитаемых подписей (`_resolve_location_label`, `_attach_value_labels`).
- `list_entity_types(conn)` — уникальные `entity_type` из `audit_log`.

### 4.5. Схемы (`schemas/`)

Лёгкая функциональная валидация входных данных (`engine_schema.py`, `equipment_schema.py`) — отдельный шаг между роутом и репозиторием, без Pydantic/dataclass. Реально в пакете всего **два** файла (плюс `__init__.py`): функции вида `validate_engine_payload`, `sanitize_engine_data`, `validate_equipment_payload`, `sanitize_equipment_data`, `validate_equipment_type_payload`, `validate_attribute_definition_payload`. Файла `incident_ticket_schema.py` не существует (прежняя версия документа упоминала его и `incident_equipment_repo.py` ошибочно — второй лежит в `repositories/`).

---

## 5. Сервисный слой и утилиты

### 5.1. Утилиты

**`utils/naming.py`** — единый источник правды для нормализации имён фото:
```python
def normalize_base_name(filename: str, engine_id: int | None = None) -> str:
    base_name = os.path.splitext(filename or '')[0] or f'engine_{engine_id}'
    base_name = re.sub(r'[<>:\"/\\|?*]', '_', base_name)
    return base_name
```
**Важно:** в комментарии явно указано, что длина **не обрезается** — это сохраняет обратную совместимость с уже существующими файлами в `photos/`. Раньше эта функция дублировалась в `parser.py` и `photo_manager/`.

**`utils/file_store.py`** — обёртки над JSON-файлами:
- `load_json(path, default=[])`, `save_json(path, data)`.
- Раньше `load_file_users`/`load_file_tokens`/`save_file_users`/`save_file_tokens` дублировались в `auth.py` — теперь всё в одном месте.

**`utils/date.py`** — `format_ru_date`, `is_valid_iso_date`.

**`utils/logging.py`** — `log_message` (единая запись в `LOG_FILE`).

### 5.2. Сервисы

**`services/export_service.py`** — экспорт в XLSX (не JSON!): `export_to_xlsx` (каталог двигателей), `export_equipment_to_xlsx`, `export_incidents_to_xlsx`; встраивает фото в лист через `_place_photos`.

**`services/incident_service.py`** — бизнес-логика инцидентов: `create_ticket`, `update_ticket`, `delete_ticket`, `add_equipment_link`/`remove_equipment_link`, `move_location`, `delete_location`, `delete_crew`.

**`services/equipment_location_migration.py`** — одноразовая миграция старых текстовых мест оборудования в дерево `location_node`: `find_or_create_node`, `find_or_create_root_node`, `migrate_equipment_locations`.

**`services/backup_service.py`** — фасад над `modules/backup_system/backup.py`:
- `create_backup()`, `list_backups()`, `inspect_uploaded_backup(zip_path)`,
  `restore_backup(zip_path)`, `download_backup(filename)`, `delete_backup(filename)`.
- Сам ничего не делает, кроме делегирования; нужен, чтобы отделить «знание о путях» от «знания о zip+SQLite Online Backup API».

**Импорт xlsx** отдельного сервиса НЕ имеет (прежняя версия документа упоминала несуществующий `services/import_service.py`): логика импорта живёт прямо в `routes/import_routes.py` (парсинг — `modules/engine_parser/parser.py`, привязка фото — `modules/photo_manager/manager.py`).

---

## 6. HTTP-роуты (Flask Blueprints)

Все роуты — Blueprint'ы, регистрируются в `app.py`. Ниже — что каждый делает.

| Blueprint (`routes/`) | Префикс (предп.) | Назначение |
|---|---|---|
| `pages.py` | (без префикса) | `/` (SPA `index.html`), `/print/<engine_id>`, `/print/incident/<id>`, `/print/equipment/<id>`, `/static/<path>`, `/test`. |
| `auth.py` | `/api/auth` | `/login`, `/logout`, `/me`, `/admin/users*` (список/создание/PATCH/DELETE/пароль/revoke). |
| `engines.py` | `/api` | `/engines`, `/engine/<id>`, `/engine`, `/engine/<id>/status`, `/engine/<id>/modes`, `/engine/<id>/works`, `/locations-tree`. |
| `search.py` | `/api` | `/search-suggestions`, `/engines/search`. |
| `equipment_routes.py` | `/api` | `/equipment*`, `/equipment-types*`, `/attribute-definitions*`, `/equipment/<id>/placements*`, `/equipment/<id>/photos*`, `/equipment/export`. |
| `equipment_photo_routes.py` | `/api/equipment-photos` | Отдача файлов фото оборудования (`/<path:filename>`). |
| `incident_ticket_routes.py` | `/api/incident-tickets` | Заявки инцидентов, связи с оборудованием, фото, `/export`. |
| `incident_photo_routes.py` | `/api/incident-photos` | Отдача файлов фото инцидентов. |
| `backup_routes.py` | `/api/backup` | `/list`, `/create`, `/inspect-upload`, `/restore/<filename>`, `/confirm-restore`, `/download/<filename>`, `/delete/<filename>`. |
| `import_routes.py` | `/api` | `/import-folder` (xlsx+фото), `/clear` (сброс БД). |
| `export_routes.py` | `/api` | `/engines/export` (XLSX). |
| `location_routes.py` | `/api/locations` | Дерево мест: список, create, `/search`, `/children`, `/<id>/breadcrumb`, `/<id>/move`, delete. |
| `changelog.py` | `/api` | `/changelog` (read-only, из `data/changelog.json`), `/wishlist` (GET/POST/PUT/DELETE, JSON-файл). |
| `crew_routes.py` | `/api/crew` | Справочник людей: список/создание/`/search`/update/delete. |
| `photos.py` | `/api` | `/engine/<id>/photos*`, `/photos/<filename>`. |
| `status.py` | `/api` | `/status` (версия, git-commit, счётчики). |
| `audit_routes.py` | `/api/audit` | `/log`, `/entity-types` — журнал аудита (таб «Аудит»). |

**Шаблон обработчика** (тонкий роут; `@require_auth` — иллюстрация прежнего стиля, в актуальном коде защита идёт через `before_app_request` в `routes/auth.py`):
```python
@bp.route("/<id>", methods=["GET"])
def get_engine(id):
    with db_connection() as conn:
        engine = engine_repo.get_with_details(conn, id)
    if not engine:
        return jsonify({"error": "not found"}), 404
    return jsonify(_serialize(engine))
```

Стандартные HTTP-коды: 200/201/204 — успех; 400 — невалидный ввод; 401 — неавторизован; 403 — нет прав; 404 — не найдено; 409 — конфликт; 500 — внутренняя.

---

## 7. Аутентификация и авторизация

**`modules/auth/`** — пакет (не одиночный `modules/auth.py`):
- `hashing.py` — `hash_password`/`verify_password` (werkzeug), `hash_token` (SHA-256), `generate_token` (`secrets.token_urlsafe(32)`).
- `db_users.py` — CRUD пользователей в таблице `users`, с fallback на файл.
- `file_users.py` — альтернативное хранилище `config/users.json` / `config/tokens.json` (id файл-пользователей ≥ `FILE_USER_ID_OFFSET`).
- `tokens.py` — `issue_token`, `get_user_from_token`, `revoke_token`, `revoke_all_for_user`; в БД хранится `token_hash`, не сам токен.
- `decorators.py` — `require_auth` / `require_admin` / `get_current_user` (**в текущем коде НЕ используются**: реальная защита — `before_app_request` в `routes/auth.py::load_current_user`).
- `auth.py` — фасад, реэкспортирующий всё перечисленное.

**Поток логина:**
1. Клиент шлёт `POST /api/auth/login` с `{username, password}`.
2. Сервер проверяет пароль, генерирует токен, сохраняет `token_hash` в `tokens`, возвращает `{token, user}`.
3. Клиент сохраняет токен (frontend — `static/js/auth.js::apiFetch()` централизованно подставляет `Authorization: Bearer`).
4. `last_login` обновляется.

**Роли** (в `routes/auth.py` допускаются 4 значения: `user`, `admin`, `superadmin`, `reader`):
- `superadmin` — всё, включая создание/изменение пользователей с ролями `admin`/`superadmin` (`_require_superadmin`).
- `admin` — админские операции (`_is_admin_role` = `admin` или `superadmin`): табы «Настройки», «Админ», «Аудит».
- `user` — базовые CRUD по доменным сущностям.
- `reader` — read-only: запись разрешена только для путей из `_READER_ALLOWED_WRITE_PATHS`.

**Защита:** централизованный `before_app_request` (`routes/auth.py::load_current_user`) + собственные хелперы `routes/auth.py::_is_admin_role` / `_require_admin` / `_require_superadmin`. Декораторы `require_auth`/`require_admin` из `modules/auth/decorators.py` в роутах не применяются.

---

## 8. Бэкапы: создание, инспекция, восстановление

Реализовано в `modules/backup_system/backup.py`, фасад — `services/backup_service.py`, HTTP — `routes/backup_routes.py`.

### 8.1. Формат бэкапа

`*.zip` со структурой:
```
backup_YYYYMMDD_HHMMSS.zip
+- manifest.json
+- engine_data.db
+- photos/
   +- <engine_id>/
      +- <base_name>.<ext>
   +- ...
+- checksums.txt      (sha256 каждого файла)
```

`manifest.json` содержит метаданные: `created_at`, `app_version`, `db_path`, `files: [...]`, `total_size`, плюс, вероятно, `engine_count`.

### 8.2. Создание (`create_backup`)

1. Через SQLite Online Backup API (`conn.backup(...)`) делается атомарный снимок БД в файл в `backup_staging/`.
2. Копируются фото из всех папок списка `PHOTO_FOLDERS` — `photos/`, `PhotoI/`, `PhotoE/` (имена каталогов внутри zip совпадают с именами папок).
3. Считаются SHA-256 чексуммы.
4. Пишется `manifest.json`.
5. Всё пакуется в zip в `backups/`.
6. Staging-папка чистится.

### 8.3. Инспекция (`inspect_uploaded_backup`)

- Открывает zip, читает `manifest.json`.
- Проверяет наличие всех файлов из манифеста.
- Сверяет SHA-256.
- **Не трогает рабочую БД.** Возвращает `{valid: bool, manifest: ..., errors: [...]}`.
- Используется на UI перед restore («уверены ли вы, что хотите восстановить?»).

### 8.4. Восстановление (`restore_backup`)

Атомарный процесс с rollback:
1. Копируется текущий `engine_data.db` в `backup_staging/engine_data.db.rollback`.
2. Извлекается содержимое zip в `backup_staging/restore/`.
3. Пересчитываются чексуммы, сверяются с `manifest.json`.
4. Если ОК:
   - рабочая `engine_data.db` заменяется на извлечённую;
   - `photos/` заменяются (с сохранением/объединением — нужно смотреть код; обычно merge).
5. Если ошибка — откат на `.rollback` файл.
6. Возвращает `{success: bool, error: str}`.

### 8.5. Скачивание и удаление

- `download_backup(filename) -> str` — путь к файлу для `send_file`.
- `delete_backup(filename) -> bool` — `os.remove` под безопасной проверкой пути (anti-traversal).

---

## 9. Импорт / Экспорт

### 9.1. Импорт xlsx

- Эндпоинт: `POST /api/import-folder` (см. `routes/import_routes.py`).
- Отдельного сервиса нет — вся логика импорта в `routes/import_routes.py`.
- Парсер: `modules/engine_parser/parser.py` (читает `openpyxl`).
- Алгоритм:
  1. Открыть xlsx, пройти по строкам.
  2. Для каждой строки собрать dict характеристик, валидировать (`schemas/engine_schema.py`).
  3. Создать `engines` (через `engine_repo.create`).
  4. Создать режимы (`mode_repo.replace_all`) и работы (`work_repo.replace_all`).
  5. Пройтись по фото: имя файла → `normalize_base_name` → искать engine, у которого в `filename` или в `serial_number`/`engine_type` совпадает база → прикрепить (см. §10).

### 9.2. Экспорт XLSX

- Эндпоинты: `POST /api/engines/export` (`routes/export_routes.py`), `POST /api/equipment/export` (`routes/equipment_routes.py`), `POST /api/incident-tickets/export`.
- Сервис: `services/export_service.py` — `export_to_xlsx`, `export_equipment_to_xlsx`, `export_incidents_to_xlsx` (фото встраиваются в лист).
- JSON-снимок состояния как пользовательская фича отсутствует (прежняя версия документа описывала несуществующий JSON-экспорт).

### 9.3. Импорт JSON

Такого эндпоинта нет (прежняя версия документа предполагала `POST /api/import/json` — в коде его не существует). JSON-файлы используются только как внутренние хранилища: `data/changelog.json` (read-only через API) и `data/wishlist.json` (CRUD). Чтение/запись — встроенный `json` прямо в `routes/changelog.py`; `utils/file_store.py` (`load_json`/`save_json`) в production **не используется**.

---

## 10. Парсер xlsx-каталога и нормализация имён фото

### 10.1. Парсер

`modules/engine_parser/parser.py` (296 строк):
- `parse_file_fast(file_path, log_callback=None)` — основная точка входа: читает `openpyxl`, разбирает строки и сразу пишет в БД (её вызывает `routes/import_routes.py`).
- `parse_engine_data(arr, filename)` — характеристики двигателя из строки листа.
- `parse_operating_modes(arr)` — режимы (колонки 50..70, строки 16..21).
- `parse_maintenance_works(arr)` — работы, начиная со строки 39, до пустых строк.
- `extract_images_from_excel(file_path, filename, engine_id, log_callback=None)` — вытаскивает вложенные фото из xlsx.
- `get_cell_safe` / `get_cell_val_safe` — безопасное чтение ячеек.

### 10.2. Нормализация имён фото

Когда оператор складывает xlsx и папку с фото, ожидается что имя файла фото (без расширения) совпадает с одним из идентификаторов двигателя — обычно `serial_number` или `engine_type` (модель).

Алгоритм в `routes/import_routes.py` (отдельного `import_service.py` нет):
```
candidate_base = normalize_base_name(photo_filename)   # utils/naming.py
for engine in imported_engines:
    for key in (engine["serial_number"], engine["engine_type"]):
        if normalize_base_name(key) == candidate_base:
            attach(photo_path, engine_id)
            break
```

Это и есть основная «магия», которая избавляет оператора от ручной привязки.

**Почему имена не обрезаются:** в `utils/naming.py` явно сказано:
> «НЕ обрезаем до 100 символов — это нарушило бы обратную совместимость с существующими фото в photos/».

### 10.3. Фото на диске

Структура `photos/`:
```
photos/<engine_id>/<base_name>.<ext>
```

`modules/photo_manager/manager.py` (двигатели):
- `upload_engine_photos(engine_id, files)` — сохраняет с нормализованным именем (`_save_upload_atomically`).
- `delete_engine_photo(engine_id, filename)` — удаляет файл и обновляет `engines.photo_count`.
- `delete_engine_photos_from_disk(engine_id)` — вызывается при удалении двигателя.
- `engine_photo_disk_paths(engine_id)`, `get_engine_photos(engine_id)`, `get_photo(...)`, `replace_engine_photo(...)`, `next_photo_index(...)`, `invalidate_photo_cache()`.

Аналогичные наборы — `equipment_manager.py` (`equipment_photo_disk_paths`, `PhotoE/`) и `incident_manager.py` (`ticket_photo_disk_paths`, `PhotoI/`) + `count_all_photos()` в обоих.

---

## 11. Frontend: HTML + vanilla JS (модули)

### 11.1. Точка входа

`templates/index.html` (1064 строки) — единственная SPA-страница с табами `#tab-*`. Подключает **обычные** (не модульные) скрипты в фиксированном порядке — строки 976–993:
```html
<script src="/static/js/common.js?v=20260911"></script>
<script src="/static/js/engines.js"></script>
<script src="/static/js/catalog.js?v=20260910"></script>
... (locationTree, engineCard, importer, exportManager, backup, info, search, auth, equipment,
     equipmentLocationTree, incidentLocations, incidentLocationTree, incidentCrew, incidents, audit)
<script> ... </script>
```
ES-модулей (`type="module"`) и сборщика нет: все функции — глобальные, файлов `app.js`, `state.js`, `api.js` в проекте нет (они были в ранней версии проекта; прежняя версия этого документа описывала их ошибочно).

### 11.2. Файлы JS (`static/js/`, 21 файл)

| Файл | Строк | Ответственность |
|---|---|---|
| `common.js` | 573 | Утилиты: `escapeHtml`, `escapeAttr`, `debounce`, `highlightMatch`, `formatRuDateTime`, `toggleModalMaximize`, `showToast`, `attachEntitySuggest`, `initPanelResizer`, `initColumnToggleCombobox`. |
| `auth.js` | 582 | Токен в `localStorage` (`getAuthToken`/`setAuthToken`/`clearAuth`), `apiFetch()` с `Authorization: Bearer`, `parseJsonResponse`, `authInit`, вкладка «Админ» (пользователи, смена пароля/бригады). |
| `catalog.js` | 645 | Таблица каталога, сортировка, пагинация, `updateStats`, `loadSettings`, **`switchTab(tabId)`** (строка 60). |
| `engines.js` | 255 | Глобалы каталога: `allEngines` (строка 4), `currentPage`, `pageSize`, `currentSort`, `currentEngineId`, `currentPhotos`, `selectedEngineIds` (строка 30). |
| `engineCard.js` | 1350 | Детальная карточка двигателя, фото-галерея, обрезка фото (canvas), печатная форма. |
| `locationTree.js` | 169 | Дерево «Цех → Место» на Каталоге (`activeWorkshop`/`activeLocation` — строки 4–5). |
| `importer.js` | 80 | Импорт xlsx и полный сброс БД (`/api/clear` с подтверждением). |
| `exportManager.js` | 190 | Экспорт выбранного в XLSX, список последних экспортов. |
| `search.js` | 455 | Расширенный поиск (`SEARCH_FIELDS`, `OPERATORS_TEXT/NUMBER`), перезаписывает `allEngines` (оригинал — в `originalAllEngines`). |
| `equipment.js` | 1867 | Вкладка «Оборудование»: список, конструктор типов/атрибутов, ЗИП, модалка карточки. |
| `equipmentLocationTree.js` | 211 | Дерево мест оборудования (`location_node`). |
| `equipmentPrint.js` | 152 | Печать карточки оборудования. |
| `incidentLocations.js` | 390 | Справочник мест инцидентов + пикер/визард создания узлов. |
| `incidentLocationTree.js` | 155 | Дерево инцидентов. |
| `incidentCrew.js` | 264 | Справочник людей (тег-инпут). |
| `incidents.js` | 783 | Вкладка «Инциденты»: журнал, карточка заявки, связи, фото, экспорт. |
| `incidentPrint.js` | 135 | Печать заявки. |
| `backup.js` | 173 | Вкладка «Настройки → Бэкапы»: список, создание, скачивание, restore. |
| `info.js` | 178 | Вкладка «Инфо»: changelog/wishlist (JSON), системная информация. |
| `audit.js` | 244 | Таб «Аудит»: журнал правок (`/api/audit/log`), фильтры, пагинация. |
| `print.js` | 173 | Печать карточки двигателя. |

### 11.3. API-обёртка (`auth.js::apiFetch`)

```js
const token = localStorage.getItem('motors_auth_token');
if (token) headers['Authorization'] = 'Bearer ' + token;
fetch(url, { headers, ... })
```
Возвращает распарсенный JSON либо бросает осмысленную ошибку; на 401 — `clearAuth()` и показ экрана логина.

### 11.4. Toast

`showToast(message, type)` (`common.js`) создаёт элемент `.toast` с автозакрытием. Используется во всех формах для обратной связи.

### 11.5. CSS

`static/css/style.css` и `static/css/print.css` — стили табов, модалок, форм, toast, кнопок и печатных страниц. Без препроцессоров.

---

## 12. UI-табы и состояние каталога

В `index.html` и в JS-файлах выделяются следующие глобальные идентификаторы (поиск по `allEngines|currentSort|currentPage|activeWorkshop|activeLocation|selectedEngineIds`):

- **`allEngines`** — кеш всех двигателей, загруженных с сервера (`engines.js:4`; перезаписывается поиском в `search.js`).
- **`currentSort`** — текущий ключ сортировки (`engines.js:5`, `{field, order}`).
- **`currentPage`** / **`pageSize`** — пагинация каталога (`engines.js:2-3`).
- **`activeWorkshop`** / **`activeLocation`** — фильтры по цеху/месту из дерева (`locationTree.js:4-5`).
- **`selectedEngineIds`** — `Set` выбранных id для bulk-экспорта (`engines.js:30`).
- **`activeTab`** — в `catalog.js:40` это DOM-элемент активной кнопки таба (`document.querySelector('.tab-btn.active')`), отдельной глобальной переменной `currentTab` в коде нет (прежняя версия документа упоминала её ошибочно).

**Переключение табов:** клик по `.tab-btn[data-tab="<name>"]` → `switchTab(tabId)` (`catalog.js:60`); содержимое таба `#tab-<name>` получает `display: block`, остальные — `none`. Активный таб запоминается в `localStorage` и восстанавливается при загрузке (`auth.js::restoreActiveTab()`).

**Согласованность состояния:** при операциях с данными (создание/удаление/редактирование) `loadEngines()` перечитывает каталог с сервера и обновляет `allEngines`, после чего таблица перерисовывается.

---

## 13. Тестирование: pytest + Playwright e2e

### 13.1. Unit / route / service тесты (pytest)

Прогон 2026-09-16 (`.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e`):

```
591 passed, 1 skipped in 56.65s      # собрано 592 теста
```

Единственный skip — `tests/test_backup_system/test_backup.py:216` («Windows-specific os.replace lock issue — fix in production, not blocking»).

Разбивка по каталогам (592 собранных теста):

| Каталог | Тестов |
|---|---|
| `tests/test_repositories/` | 159 |
| `tests/test_routes/` | 183 |
| `tests/test_photo_manager/` | 81 |
| `tests/test_auth/` | 52 |
| `tests/test_services/` | 33 |
| `tests/test_audit/` | 28 |
| `tests/test_utils/` | 27 |
| `tests/test_backup_system/` | 16 |
| `tests/test_engine_parser/` | 13 |

Файлы (топ по количеству): `test_routes/test_equipment_routes.py` — 63, `test_repositories/test_equipment_repo.py` — 37, `test_services/test_incident_service.py` — 33, `test_photo_manager/test_manager.py` — 31, `test_repositories/test_incident_ticket_repo.py` — 31, `test_routes/test_incident_ticket_routes.py` — 30, `test_routes/test_auth_routes.py` — 28, `test_routes/test_engines.py` — 26.

- Фикстуры — `tests/conftest.py`: `db_conn` (in-memory SQLite, `init_db(conn)`) и `file_users_env` (изолированные `users.json`/`tokens.json`).
- Конфигурационного файла pytest (`pytest.ini`, `pyproject.toml`, `setup.cfg`) в проекте **нет** — pytest работает на дефолтных настройках, discovery идёт от корня.
- Пример: `tests/test_repositories/test_engine_repo.py` (325 строк, 23 теста) — `get_by_id`, `get_with_details`, `get_all` (пагинация, поиск), `create`, `update`, `delete` (ручной каскад modes/works), `update_photo_count`, `get_by_filename`, плюс тесты гонки миграций.
- Аудит покрыт отдельно: `tests/test_audit/` (`test_audit.py`, `test_audit_repo.py`, `test_audit_routes.py` — 28 тестов) и `tests/test_repositories/test_engine_repo_audit.py`.

### 13.2. E2E (`tests/e2e/`)

Прогон 2026-09-16 (`.venv\Scripts\python.exe -m pytest tests/e2e -q`):

```
81 passed, 199 warnings in 157.55s
```

- `conftest.py` (463 строки) — инфраструктура Playwright:
  - **Браузер: безголовый Chromium Playwright** — `pw.chromium.launch(headless=True, args=["--window-size=1300,820", "--no-first-run"])` (строки 176–182). `headless=True` — **подтверждено кодом**; параметр `channel="chrome"` в запуске **НЕ используется** (упоминание `channel="chrome"` осталось только в docstring conftest и в генерируемом заголовке `docs/e2e_test_results.md` — это устаревший текст, не реальная настройка).
  - Изоляция от прода: на уровне модуля задаются `MOTORS_*`-переменные (`_RUNTIME_REL`) на `tempfile.mkdtemp()`, `import app` происходит только внутри фикстуры `live_server`; сама фикстура поднимает `make_server("127.0.0.1", 0, app, threaded=True)` → свой порт, своя БД.
  - Один браузер на сессию, для каждого теста — отдельный контекст (изоляция `localStorage`/cookies).
  - Тестовые пользователи: `e2e_test_admin`, `e2e_test_user` — создаются в начале сессии, удаляются в teardown.
  - Префикс `MARKER = "E2E_TESTS"` для тестовых сущностей.
  - Сбор диагностики: ошибки консоли, JS-исключения, сетевые ответы `>= 400`, скриншот при падении (`tests/e2e/screenshots/`).
  - Сессионная фикстура `storage_state` — логинит admin через реальную UI-форму один раз.
  - Результаты агрегируются в `docs/e2e_test_results.md` (таблица + totals) и `tests/e2e/.results.json`; порядок групп — `GROUP_ORDER` в `_write_results()` (11 групп).
- `helpers.py` (298 строк) — переиспользуемые функции: `make_engine/make_mode/make_work`, `login_ui/logout_ui/switch_tab/wait_toast`, `engine_id_by_serial/delete_engine_by_serial`, `create_engine_direct`, `fill_detail_fields/open_engine_card/close_detail/open_detail_edit/save_detail_card`, `make_test_png`, `upload_detail_photo`, `set_local_storage`, `accept_dialogs/prompt_accept`.
- Тестовые модули и сценарии (81):
  - `test_01_auth.py` — 12, `test_02_catalog.py` — 11, `test_03_add_engine.py` — 9, `test_04_detail.py` — 10, `test_05_photos.py` — 6, `test_06_import.py` — 3, `test_07_search.py` — 6, `test_08_settings.py` — 6, `test_09_backups.py` — 4, `test_10_info.py` — 9, `test_11_misc.py` — 5.

### 13.3. Как запускать

```bash
# unit/route/service (без e2e)
.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e

# только e2e
.venv\Scripts\python.exe -m pytest tests/e2e -q

# всё
.venv\Scripts\python.exe -m pytest -q
```

**Перед e2e поднимать приложение НЕ нужно** — фикстура `live_server` сама запускает изолированный Flask-сервер на свободном порту с временной runtime-БД (и удаляет её после прогона). Нужны только установленные браузеры Playwright (`playwright install chromium`).

---

## 14. Известные ограничения и решения

Эти ограничения зафиксированы прямо в комментариях кода и важно о них помнить при расширении.

1. **`normalize_base_name` не обрезает имя до 100 символов** (`utils/naming.py`).
   *Причина:* обратная совместимость с фото в `photos/`. Не вводите обрезку — поломаете старые пути.

2. **Сохранение обратной совместимости JSON-файлов.**
   `auth.py` раньше имел дубли `load_file_users`/`save_file_users`/... — теперь всё в `utils/file_store.py`. При добавлении новых полей в `users.json` используйте `default=[]` и миграционные шаги.

3. **E2E запускается в невидимом браузере** — `tests/e2e/conftest.py:176-182`: `pw.chromium.launch(headless=True, args=["--window-size=1300,820", "--no-first-run"])`.
   Проверено 2026-09-16: значение `headless=True` (подтверждено кодом). `channel="chrome"` в launch не передаётся — используется Chromium из Playwright, поэтому нужен `playwright install chromium`, а не Chrome. Отдельное согласование режима не требуется.

4. **Бэкапы атомарны через staging + rollback**, не через прямое копирование поверх.
   Любой новый формат бэкапа должен сохранять эту гарантию.

5. **Тестовые пользователи e2e** (`e2e_test_admin`, `e2e_test_user`) удаляются в teardown, **но не удаляются, если `id == 1`** (защита встроенного админа). Не меняйте этот инвариант.

6. **Все таблицы создаются через `CREATE TABLE IF NOT EXISTS`** — то есть `init_db` идемпотентен. Изменения схемы — только через `_ensure_column`.

---

## 15. Как добавить новую функциональность (рецепты)

### 15.1. Новое поле в карточке двигателя

1. **БД:** добавить столбец через `_ensure_column(cursor, 'engines', '<col>', '<TYPE>')` рядом с `CREATE TABLE engines` в `modules/db.py`.
2. **Репозиторий:** расширить `engine_repo.create/update/get_*` — включить новое поле в `INSERT`/`UPDATE`/`SELECT`.
3. **Схема:** добавить поле в `schemas/engine_schema.py` для валидации.
4. **Парсер:** если поле приходит из xlsx — добавить маппинг в `modules/engine_parser/parser.py`.
5. **Роут:** убедиться, что в `routes/engines.py` поле прокидывается (часто достаточно прозрачной сериализации).
6. **UI:** добавить инпут в форму (`templates/index.html`) и ячейку в `engines.js`/`engineCard.js`.

### 15.2. Новая сущность (например, «Датчики»)

1. **`modules/db.py`:** новая `CREATE TABLE IF NOT EXISTS sensor (...)`.
2. **`repositories/sensor_repo.py`:** функции `get_by_id`, `get_all`, `create`, `update`, `delete`.
3. **`schemas/sensor_schema.py`:** валидатор.
4. **`routes/sensor_routes.py`:** Blueprint, регистрация в `app.py`.
5. **`static/js/sensor.js`:** UI-рендеринг.
6. **Тесты:** `tests/test_repositories/test_sensor_repo.py` + при необходимости `tests/e2e/test_NN_sensor.py`.

### 15.3. Новый таб в UI

1. В `index.html` добавить `<button class="tab-btn" data-tab="sensor">` и `<section id="tab-sensor">…</section>`.
2. В конкретном `*.js`-файле таба (или в `catalog.js::switchTab`) — обработчик переключения, lazy-init.
3. Если таб только для админа — скрыть кнопку (`style="display:none"`) и показать её в `auth.js::applyRoleUI()`.
4. E2E: добавить сценарий в новый `tests/e2e/test_NN_*.py`, использовать `switch_tab(page, "sensor")` и `wait_toast(...)`.

### 15.4. Новый эндпоинт бэкапа

1. В `modules/backup_system/backup.py` (или отдельный файл рядом) — функция.
2. Зарегистрировать в фасаде `services/backup_service.py`.
3. Добавить маршрут в `routes/backup_routes.py` (защита админских операций — проверка роли в самом роуте, как в остальных `routes/*`).
4. UI — кнопка в табе «Настройки/Бэкапы», `fetch` + `toast`.
5. E2E — клик, проверка toast, проверка появления файла в `backups/`.

### 15.5. Правка формата бэкапа (с сохранением совместимости)

- Никогда не удалять поля из `manifest.json` (только добавлять с дефолтами).
- Чтение — tolerant: отсутствующие поля = дефолт.
- Тесты на `inspect_uploaded_backup` со старым и новым манифестом.

---

## 16. Точки расширения и TODO

Эти места в коде уже обозначены как «на перспективу» или явно требуют доработки.

| Где | Что | Идея |
|---|---|---|
| `static/js/engines.js`, `locationTree.js` | Глобальные `currentSort`/`activeWorkshop`/... — много плоских переменных. | По мере роста — выделить `catalogFilters`, `tablePagination` в подобъекты (ES-модулей в проекте нет, всё в глобальной области). |
| `routes/import_routes.py` | Стратегия сопоставления фото с двигателем — по точному совпадению нормализованного имени. | Добавить fuzzy-match по `serial_number` или `engine_type` с приоритетами. |
| `tests/e2e/` | 11 тестовых модулей, 81 сценарий; группы жёстко перечислены в `GROUP_ORDER` (`conftest.py::_write_results`). | При добавлении группы >11 — расширить `GROUP_ORDER`. |
| `routes/photos.py` и `modules/photo_manager/manager.py` | Фото двигателей хранятся по `<engine_id>/...`, но при переимпорте xlsx с тем же `serial_number` могут дублироваться. | Добавить дедупликацию по хешу содержимого. |
| `repositories/equipment_repo.py` | Оборудование связано с двигателями только косвенно (через заявки инцидентов). | При необходимости — жёсткая связь `equipment.engine_id` (через `_ensure_column`). |
| `templates/index.html` | Единая SPA-страница на 1064 строки, раздувается при росте функциональности. | Разнести по partials (через `<template>` и клонирование), либо перейти к per-tab страницам. |
| `modules/backup_system/backup.py` | Снимок фото делается полным копированием. | Добавить инкрементальные бэкапы (по `mtime`/`hash`). |
| `static/js/auth.js` | `Authorization` берётся из `localStorage`. | При росте требований к безопасности — httpOnly cookie + CSRF. |
| `tests/` | Покрытие: 592 unit/route + 81 e2e, всё зелёное (2026-09-16). | Расширять по мере добавления новых функций репозиториев/роутов. |
| `docs/e2e_test_results.md`, `tests/e2e/conftest.py` | В генерируемом заголовке и в docstring написано `channel="chrome"`, хотя фактически используется bundled Chromium Playwright (`pw.chromium.launch(headless=True)`). | Привести текст в соответствие с кодом (правка не входит в текущую задачу). |

---

## Приложение А. Соответствие "файл → роль"

| Слой | Где живет |
|---|---|
| Точка входа | `app.py` |
| Конфигурация | `config/settings.py` |
| БД (схема + соединение) | `modules/db.py` |
| Аутентификация | `modules/auth/` (пакет), `routes/auth.py` |
| Доменные модули | `modules/audit.py`, `modules/engine_parser/`, `modules/photo_manager/`, `modules/backup_system/` |
| SQL (Repository) | `repositories/*_repo.py` (11 файлов) |
| Валидация | `schemas/engine_schema.py`, `schemas/equipment_schema.py` |
| Бизнес-логика | `services/*.py` (backup, export, incident, equipment_location_migration) |
| HTTP | `routes/*.py` (17 blueprint'ов) |
| Служебные скрипты | `scripts/` (миграции JSON, диагностика аудита) |
| Утилиты | `utils/naming.py`, `utils/file_store.py`, `utils/date.py`, `utils/logging.py` |
| UI (серверные шаблоны) | `templates/index.html`, `templates/print*.html` |
| UI (скрипты/стили) | `static/js/*.js` (21), `static/css/*`, `static/ico/*.svg` |
| Тесты | `tests/test_repositories/`, `tests/test_routes/`, `tests/test_services/`, `tests/test_audit/`, `tests/test_auth/`, `tests/test_photo_manager/`, `tests/test_engine_parser/`, `tests/test_backup_system/`, `tests/test_utils/`, `tests/e2e/` |
| Документация | `docs/*.md` (`README.md` в проекте отсутствует) |

## Приложение Б. Глобальное состояние фронта

Найдено в `static/js/` (файлов `state.js`/`app.js`/`api.js` в проекте нет):

- `allEngines` — массив всех двигателей (клиентский кеш; `engines.js:4`).
- `currentSort` — `{field, order}` (`engines.js:5`).
- `currentPage` / `pageSize` — пагинация каталога (`engines.js:2-3`).
- `activeWorkshop` / `activeLocation` — фильтры по цеху/месту (`locationTree.js:4-5`).
- `selectedEngineIds` — `Set` id выбранных двигателей (для bulk-операций, `engines.js:30`).
- `activeTab` — DOM-элемент активной кнопки таба (`catalog.js:40`); сам выбранный таб хранится в `localStorage` под ключом `motors_active_tab` (`auth.js::restoreActiveTab`).
- `motors_auth_token` (localStorage) — токен авторизации; `motors_auth_user` — JSON пользователя; `motors_theme` — тема.

## Приложение В. Команды на каждый день

```bash
# Поднять приложение
.venv\Scripts\python.exe app.py

# Прогнать unit/route/service тесты (592 теста)
.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e

# Прогнать e2e (81 сценарий; app.py поднимать НЕ нужно — свой сервер в фикстуре)
.venv\Scripts\python.exe -m pytest tests/e2e -q

# Посмотреть отчёт e2e
type docs\e2e_test_results.md

# Создать бэкап вручную (через API)
curl -X POST -H "Authorization: Bearer <admin_token>" http://localhost:5000/api/backup/create

# Восстановить из бэкапа (через UI, кнопка "Восстановить" сначала показывает inspect)
```

---

*Конец снимка. Документ сгенерирован на основе прямого чтения исходников `c:\motors_project`. При расхождениях — опирайтесь на код, а не на этот документ; правки приветствуются.*
