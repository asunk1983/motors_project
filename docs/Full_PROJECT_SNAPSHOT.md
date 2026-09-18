# Full Project Snapshot — Motors

> Документ создан автоматическим аудитом. Единственная цель — дать другой ИИ-сессии полный контекст проекта без повторного сканирования кода.

## 0. Метаданные снимка

- **Дата и время создания:** 2026-09-01 (по локальному времени Windows)
- **Дата сверки с репозиторием:** 2026-09-16
- **Рабочая директория проекта (абсолютный путь):** `C:\motors_project`
- **Текущая ветка git:** `main`
- **SHA последнего коммита (на 2026-09-16):** `12a1697ebc0581fd4d6a3a82bc44960cc4a115da`
  (в первой версии документа был указан `7003563d8a6123eea68e1d7776e4212e2efadf1d`)
- **Незакоммиченные изменения (`git status --porcelain`) на 2026-09-16:**
  - `M .gitignore`
  - `M summary.txt`
  - `M docs/PROJECT_SNAPSHOT.md`
  - `M docs/Full_PROJECT_SNAPSHOT.md`

- **Python:** `Python 3.14.6`
- **Пути к интерпретаторам (`where.exe python`):**
  - `C:\Users\KIPIA\AppData\Local\Microsoft\WindowsApps\python.exe`
  - `C:\Users\KIPIA\AppData\Local\Python\bin\python.exe`
- **Используемый venv:** `.venv\Scripts\python.exe` (Python 3.14.6)
- **`requirements.txt`:** присутствует в корне проекта (в первой версии документа было указано «отсутствует» — неверно).

### Состав `.venv` (`pip freeze`):

| Пакет | Версия |
| --- | --- |
| blinker | 1.9.0 |
| click | 8.4.2 |
| colorama | 0.4.6 |
| et_xmlfile | 2.0.0 |
| Flask | 3.1.3 |
| flask-cors | 6.0.5 |
| greenlet | 3.5.4 |
| iniconfig | 2.3.0 |
| itsdangerous | 2.2.0 |
| Jinja2 | 3.1.6 |
| MarkupSafe | 3.0.3 |
| numpy | 2.5.1 |
| openpyxl | 3.1.5 |
| packaging | 26.2 |
| pandas | 3.0.3 |
| pillow | 12.3.0 |
| playwright | 1.62.0 |
| pluggy | 1.6.0 |
| pyee | 13.0.1 |
| Pygments | 2.20.0 |
| pytest | 9.1.1 |
| python-dateutil | 2.9.0.post0 |
| six | 1.17.0 |
| typing_extensions | 4.16.0 |
| tzdata | 2026.3 |
| Werkzeug | 3.1.8 |

`version.txt`: `1.0.5` (только 1 строка).

> **Обновление 2026-09-16:** расхождение «`version.txt` vs `APP_VERSION`» устранено в коде — `routes/status.py:22-51` теперь читает версию из `version.txt` (`_read_app_version()`), хардкода `'2.0'` больше нет. `/api/status` дополнительно отдаёт `git_commit` (`_read_git_commit()`, `git rev-parse --short HEAD`).
> **Обновление 2026-09-18:** тесты — 611 unit/route (1 skip) + 83 e2e, все зелёные (было 592+81 на 16.09; расхождение в 83 против прежних 82 e2e — из-за нового e2e-теста обрезки фото `test_45_crop_photo` (коммит ab6ebd6), а 82 против 81 на 16.09 — из-за e2e-тестов смены роли в `test_01_auth.py` (коммит c09fa0b); коммит 257bf70 — фикс гонки ожидания загрузки фото, счётчик тестов он не менял). Добавлена смена роли пользователя в админке (PATCH /api/auth/admin/users/<id>): роль superadmin через эту функцию не назначается и не снимается никем — только при создании пользователя; защита от самоблокировки. Добавлен модуль tests/descriptions.py — русские описания тестов в живом выводе `pytest -v` (маркер scn, докстринг, либо автогенерация из имени). Добавлен run_tests.bat для локального прогона с логом в docs/.


## 1. Полное дерево проекта

Полный список файлов проекта (**219** файлов; без `__pycache__`, `.venv`, `.git`, `.pytest_cache`, каталогов данных `motors`, `photos`, `PhotoE`, `PhotoI`, `backups`, `backup_staging`, каталога артефактов `tests/e2e/screenshots`, и без расширений `.db`/`.log`/`.pyc`). Сверено с диском 2026-09-16:

```
C:\motors_project\.clinerules
C:\motors_project\__clinerules
C:\motors_project\.gitignore
C:\motors_project\app.py
C:\motors_project\config\settings.py
C:\motors_project\config\tokens.json
C:\motors_project\config\users.json
C:\motors_project\data\changelog.json
C:\motors_project\data\wishlist.json
C:\motors_project\data\wishlist.json.bak
C:\motors_project\deploy_log.txt
C:\motors_project\diag_modal.py
C:\motors_project\diag_photos.py
C:\motors_project\docs\e2e_test_results.md
C:\motors_project\docs\Full_PROJECT_SNAPSHOT.md
C:\motors_project\docs\git_diff_clear_database_review.txt
C:\motors_project\docs\HANDOFF.md
C:\motors_project\docs\PROJECT_SNAPSHOT.md
C:\motors_project\docs\server_reference.md
C:\motors_project\docs\TEST_PLAN.md
C:\motors_project\docs\tests.md
C:\motors_project\import_log.txt
C:\motors_project\index.html
C:\motors_project\measurement.py
C:\motors_project\mockup.html
C:\motors_project\modules\__init__.py
C:\motors_project\modules\audit.py
C:\motors_project\modules\auth\__init__.py
C:\motors_project\modules\auth\auth.py
C:\motors_project\modules\auth\db_users.py
C:\motors_project\modules\auth\decorators.py
C:\motors_project\modules\auth\file_users.py
C:\motors_project\modules\auth\hashing.py
C:\motors_project\modules\auth\tokens.py
C:\motors_project\modules\backup_system\__init__.py
C:\motors_project\modules\backup_system\backup.py
C:\motors_project\modules\db.py
C:\motors_project\modules\engine_parser\__init__.py
C:\motors_project\modules\engine_parser\parser.py
C:\motors_project\modules\photo_manager\__init__.py
C:\motors_project\modules\photo_manager\equipment_manager.py
C:\motors_project\modules\photo_manager\incident_manager.py
C:\motors_project\modules\photo_manager\manager.py
C:\motors_project\push-deploy.bat
C:\motors_project\push-deploy.sh
C:\motors_project\requirements.txt
C:\motors_project\rollback-remote.sh
C:\motors_project\summary.txt
C:\motors_project\test_mode_repo.py
C:\motors_project\version.txt
C:\motors_project\Новый текстовый документ.cmd
C:\motors_project\repositories\__init__.py
C:\motors_project\repositories\audit_repo.py
C:\motors_project\repositories\crew_repo.py
C:\motors_project\repositories\engine_repo.py
C:\motors_project\repositories\equipment_placement_repo.py
C:\motors_project\repositories\equipment_repo.py
C:\motors_project\repositories\incident_equipment_repo.py
C:\motors_project\repositories\incident_ticket_repo.py
C:\motors_project\repositories\location_repo.py
C:\motors_project\repositories\mode_repo.py
C:\motors_project\repositories\work_repo.py
C:\motors_project\routes\__init__.py
C:\motors_project\routes\audit_routes.py
C:\motors_project\routes\auth.py
C:\motors_project\routes\backup_routes.py
C:\motors_project\routes\changelog.py
C:\motors_project\routes\crew_routes.py
C:\motors_project\routes\engines.py
C:\motors_project\routes\equipment_photo_routes.py
C:\motors_project\routes\equipment_routes.py
C:\motors_project\routes\export_routes.py
C:\motors_project\routes\import_routes.py
C:\motors_project\routes\incident_photo_routes.py
C:\motors_project\routes\incident_ticket_routes.py
C:\motors_project\routes\location_routes.py
C:\motors_project\routes\pages.py
C:\motors_project\routes\photos.py
C:\motors_project\routes\search.py
C:\motors_project\routes\status.py
C:\motors_project\schemas\__init__.py
C:\motors_project\schemas\engine_schema.py
C:\motors_project\schemas\equipment_schema.py
C:\motors_project\scripts\add_changelog_entry.py
C:\motors_project\scripts\diag_audit_log.py
C:\motors_project\scripts\diag_audit_missing_entities.py
C:\motors_project\scripts\diag_schema_mismatch.py
C:\motors_project\scripts\migrate_changelog_to_json.py
C:\motors_project\scripts\migrate_wishlist_to_json.py
C:\motors_project\services\__init__.py
C:\motors_project\services\backup_service.py
C:\motors_project\services\equipment_location_migration.py
C:\motors_project\services\export_service.py
C:\motors_project\services\incident_service.py
C:\motors_project\static\css\print.css
C:\motors_project\static\css\style.css
C:\motors_project\static\ico\*.svg  (34 файла иконок)
C:\motors_project\static\js\audit.js
C:\motors_project\static\js\auth.js
C:\motors_project\static\js\backup.js
C:\motors_project\static\js\catalog.js
C:\motors_project\static\js\common.js
C:\motors_project\static\js\engineCard.js
C:\motors_project\static\js\engines.js
C:\motors_project\static\js\equipment.js
C:\motors_project\static\js\equipmentLocationTree.js
C:\motors_project\static\js\equipmentPrint.js
C:\motors_project\static\js\exportManager.js
C:\motors_project\static\js\importer.js
C:\motors_project\static\js\incidentCrew.js
C:\motors_project\static\js\incidentLocations.js
C:\motors_project\static\js\incidentLocationTree.js
C:\motors_project\static\js\incidentPrint.js
C:\motors_project\static\js\incidents.js
C:\motors_project\static\js\info.js
C:\motors_project\static\js\locationTree.js
C:\motors_project\static\js\print.js
C:\motors_project\static\js\search.js
C:\motors_project\templates\index.html
C:\motors_project\templates\print.html
C:\motors_project\templates\print_equipment.html
C:\motors_project\templates\print_incident.html
C:\motors_project\tests\__init__.py
C:\motors_project\tests\conftest.py
C:\motors_project\tests\e2e\__init__.py
C:\motors_project\tests\e2e\.results.json
C:\motors_project\tests\e2e\conftest.py
C:\motors_project\tests\e2e\helpers.py
C:\motors_project\tests\e2e\test_01_auth.py
C:\motors_project\tests\e2e\test_02_catalog.py
C:\motors_project\tests\e2e\test_03_add_engine.py
C:\motors_project\tests\e2e\test_04_detail.py
C:\motors_project\tests\e2e\test_05_photos.py
C:\motors_project\tests\e2e\test_06_import.py
C:\motors_project\tests\e2e\test_07_search.py
C:\motors_project\tests\e2e\test_08_settings.py
C:\motors_project\tests\e2e\test_09_backups.py
C:\motors_project\tests\e2e\test_10_info.py
C:\motors_project\tests\e2e\test_11_misc.py
C:\motors_project\tests\test_audit\__init__.py
C:\motors_project\tests\test_audit\test_audit.py
C:\motors_project\tests\test_audit\test_audit_repo.py
C:\motors_project\tests\test_audit\test_audit_routes.py
C:\motors_project\tests\test_auth\__init__.py
C:\motors_project\tests\test_auth\test_db_users.py
C:\motors_project\tests\test_auth\test_decorators.py
C:\motors_project\tests\test_auth\test_hashing.py
C:\motors_project\tests\test_auth\test_tokens.py
C:\motors_project\tests\test_backup_system\__init__.py
C:\motors_project\tests\test_backup_system\test_backup.py
C:\motors_project\tests\test_engine_parser\test_parser.py
C:\motors_project\tests\test_photo_manager\__init__.py
C:\motors_project\tests\test_photo_manager\test_equipment_manager.py
C:\motors_project\tests\test_photo_manager\test_incident_manager.py
C:\motors_project\tests\test_photo_manager\test_manager.py
C:\motors_project\tests\test_repositories\__init__.py
C:\motors_project\tests\test_repositories\test_crew_repo.py
C:\motors_project\tests\test_repositories\test_engine_repo.py
C:\motors_project\tests\test_repositories\test_engine_repo_audit.py
C:\motors_project\tests\test_repositories\test_equipment_placement_repo.py
C:\motors_project\tests\test_repositories\test_equipment_repo.py
C:\motors_project\tests\test_repositories\test_incident_equipment_repo.py
C:\motors_project\tests\test_repositories\test_incident_ticket_repo.py
C:\motors_project\tests\test_repositories\test_location_repo.py
C:\motors_project\tests\test_repositories\test_mode_repo.py
C:\motors_project\tests\test_repositories\test_work_repo.py
C:\motors_project\tests\test_routes\test_auth_routes.py
C:\motors_project\tests\test_routes\test_crew_routes.py
C:\motors_project\tests\test_routes\test_engines.py
C:\motors_project\tests\test_routes\test_equipment_photo_routes.py
C:\motors_project\tests\test_routes\test_equipment_routes.py
C:\motors_project\tests\test_routes\test_import_routes.py
C:\motors_project\tests\test_routes\test_incident_photo_routes.py
C:\motors_project\tests\test_routes\test_incident_ticket_routes.py
C:\motors_project\tests\test_routes\test_photos.py
C:\motors_project\tests\test_services\test_incident_service.py
C:\motors_project\tests\test_utils\__init__.py
C:\motors_project\tests\test_utils\test_date.py
C:\motors_project\tests\test_utils\test_file_store.py
C:\motors_project\tests\test_utils\test_logging.py
C:\motors_project\tests\test_utils\test_naming.py
C:\motors_project\utils\__init__.py
C:\motors_project\utils\date.py
C:\motors_project\utils\file_store.py
C:\motors_project\utils\logging.py
C:\motors_project\utils\naming.py
```

Сводка количества файлов по категориям (на 2026-09-16, всего **219**):

| Категория | Кол-во файлов |
| --- | --- |
| Корень проекта (все файлы, кроме каталогов) | 19 |
| `config/` | 3 |
| `data/` | 3 |
| `docs/` | 8 |
| `modules/` | 18 |
| `repositories/` | 11 |
| `routes/` | 18 |
| `schemas/` | 3 |
| `scripts/` | 6 |
| `services/` | 5 |
| `static/css/` | 2 |
| `static/ico/` | 34 |
| `static/js/` | 21 |
| `templates/` | 4 |
| `tests/` (unit + e2e, без `__pycache__` и без `screenshots/`) | 59 |
| `utils/` | 5 |
| **Всего файлов проекта** | **219** |

> В первой версии документа было **147** файлов и отсутствовали разделы `scripts/`, `data/`, `docs/*` (кроме двух снапшотов), `tests/test_audit|test_auth|test_engine_parser|test_photo_manager|test_services`, `tests/e2e/conftest.py`, `modules/audit.py`, `repositories/audit_repo.py`, `repositories/equipment_placement_repo.py`, `routes/audit_routes.py`, `static/js/audit.js`/`backup.js`/`info.js`.

Служебные артефакты аудита `docs/_tree.txt`, `docs/_static.txt`, `docs/_templates.txt`, `docs/_tests.txt`, `docs/_usage_scan.txt`, упоминавшиеся в первой версии документа, **на диске отсутствуют** (уже удалены) — все цифры раздела 15 пересчитаны заново 2026-09-16.

## 2. Обзор архитектуры

### Технологический стек

- **Backend:** Python 3.14 + Flask 3.1.3 (`flask-cors==6.0.5`), `sqlite3` (stdlib, WAL mode, `foreign_keys=ON`), `pandas==3.0.3` + `openpyxl==3.1.5` для парсинга Excel, `Pillow==12.3.0` для фото, `werkzeug==3.1.8` для хэширования паролей (pbkdf2/scrypt).
- **Frontend:** Vanilla JavaScript (ES6+) без фреймворков, прямая работа с DOM. Шрифты Google Fonts (`Inter`, `JetBrains Mono`). Свой CSS design system на `custom properties`. Подключение скриптов через `<script src>` в `index.html` (без сборщика).
- **Тесты:** `pytest==9.1.1`. E2E на Playwright (`playwright==1.62.0` + `pyee==13.0.1`).
- **Хранение фото:** дисковое (НЕ через БД) — `photos/`, `PhotoI/`, `PhotoE/`. Имя файла — `ID{owner_id}_{n}.{ext}` (см. раздел 7).
- **Авторизация:** opaque-токены (Bearer). Хранение токенов в таблице `tokens` для DB-пользователей, в `config/tokens.json` для файловых пользователей (id ≥ `FILE_USER_ID_OFFSET=1000000000`). CSRF не используется.

### Слои (схема потока запроса)

```
templates/ (index.html, print*.html)
        ↓ подключаются <script src="..."> (обычные скрипты, НЕ ES-модули)
static/js/  (auth, common, catalog, engines, engineCard, locationTree, importer, exportManager,
             backup, info, search, equipment, equipmentLocationTree, equipmentPrint,
             incidents, incidentCrew, incidentLocations, incidentLocationTree, incidentPrint,
             audit, print — 21 файл; см. раздел 10)
        ↓ fetch /api/...
routes/    (Flask blueprints — тонкая HTTP-обёртка, parse payload, status codes)
        ↓ ↓ оркестрация через services/
services/  (бизнес-логика: export_service, backup_service, incident_service, equipment_location_migration)
        ↓ ↓ только SQL
repositories/ (тонкий слой SQL: engine_repo, mode_repo, work_repo, equipment_repo, location_repo,
              crew_repo, incident_ticket_repo, incident_equipment_repo)
        ↓ ↓ sqlite3.Connection через context manager
modules/db.py  (db_connection(), get_db_connection(), init_db() — управление PRAGMA + auto-migrations)
        ↓ ↓ 
SQLite файл engine_data.db + дисковые папки photos/ PhotoI/ PhotoE/ backups/ backup_staging/
```

### Зарегистрированные blueprints (`routes/__init__.py`)

Все blueprint-ы собираются в `create_blueprints()` (`routes/__init__.py:9`) и регистрируются через `register_blueprints(app)`. `auth_bp` регистрируется первым — до остальных.

| Blueprint | url_prefix | Имя в `create_blueprints` | Исходный файл |
| --- | --- | --- | --- |
| `auth_bp` | `/api/auth` | `auth_bp` | `routes/auth.py` |
| `engines_bp` | `/api` | `engines_bp` | `routes/engines.py` |
| `equipment_bp` | `/api` | `equipment_bp` | `routes/equipment_routes.py` |
| `equipment_photo_bp` | `/api/equipment-photos` | `equipment_photo_bp` | `routes/equipment_photo_routes.py` |
| `location_bp` | `/api/locations` | `location_bp` | `routes/location_routes.py` |
| `crew_bp` | `/api/crew` | `crew_bp` | `routes/crew_routes.py` |
| `incident_ticket_bp` | `/api/incident-tickets` | `incident_ticket_bp` | `routes/incident_ticket_routes.py` |
| `incident_photo_bp` | `/api/incident-photos` | `incident_photo_bp` | `routes/incident_photo_routes.py` |
| `photos_bp` | `/api` | `photos_bp` | `routes/photos.py` |
| `import_bp` | `/api` | `import_bp` | `routes/import_routes.py` |
| `export_bp` | `/api` | `export_bp` | `routes/export_routes.py` |
| `backup_bp` | `/api/backup` | `backup_bp` | `routes/backup_routes.py` |
| `changelog_bp` | `/api` | `changelog_bp` | `routes/changelog.py` |
| `status_bp` | `/api` | `status_bp` | `routes/status.py` |
| `search_bp` | `/api` | `search_bp` | `routes/search.py` |
| `pages_bp` | (без префикса) | `pages_bp` | `routes/pages.py` |
| `audit_bp` | `/api/audit` | `audit_bp` | `routes/audit_routes.py` |

### Проверка: файлы `.py` в `routes/`, которые НЕ зарегистрированы

| Файл в `routes/` | Зарегистрирован как blueprint? | Комментарий |
| --- | --- | --- |
| `routes/__init__.py` | (фабрика) | — |
| `routes/audit_routes.py` | ✅ `audit_bp` | `/api/audit/*` |
| `routes/auth.py` | ✅ `auth_bp` | `/api/auth/*` |
| `routes/backup_routes.py` | ✅ `backup_bp` | `/api/backup/*` |
| `routes/changelog.py` | ✅ `changelog_bp` | `/api/changelog`, `/api/wishlist` |
| `routes/crew_routes.py` | ✅ `crew_bp` | `/api/crew/*` |
| `routes/engines.py` | ✅ `engines_bp` | `/api/engines`, `/api/engine/*`, `/api/locations-tree` |
| `routes/equipment_photo_routes.py` | ✅ `equipment_photo_bp` | `/api/equipment-photos/<path>` |
| `routes/equipment_routes.py` | ✅ `equipment_bp` | `/api/equipment*`, `/api/equipment-types*`, `/api/attribute-definitions*` |
| `routes/export_routes.py` | ✅ `export_bp` | `/api/engines/export`, `/api/equipment/export` |
| `routes/import_routes.py` | ✅ `import_bp` | `/api/import-folder`, `/api/clear` |
| `routes/incident_photo_routes.py` | ✅ `incident_photo_bp` | `/api/incident-photos/<path>` |
| `routes/incident_ticket_routes.py` | ✅ `incident_ticket_bp` | `/api/incident-tickets/*` |
| `routes/location_routes.py` | ✅ `location_bp` | `/api/locations/*` |
| `routes/pages.py` | ✅ `pages_bp` | `/`, `/print/<id>`, `/print/incident/<id>`, `/print/equipment/<id>`, `/static/<path>`, `/test` |
| `routes/photos.py` | ✅ `photos_bp` | `/api/photos/<filename>`, `/api/engine/<id>/photos*` |
| `routes/search.py` | ✅ `search_bp` | `/api/search-suggestions`, `/api/engines/search` |
| `routes/status.py` | ✅ `status_bp` | `/api/status` |

**Итог:** все 17 `.py` файлов в `routes/` (кроме `__init__.py`) зарегистрированы как blueprint. Мёртвого кода в `routes/` НЕТ.

## 3. База данных — полная схема

> **Обновление 2026-09-16 (сверка с `modules/db.py`, 519 строк):** таблицы `changelog_entries` и `wishlist_items` в схеме **отсутствуют** (журнал изменений и wishlist переведены в JSON — `data/changelog.json`, `data/wishlist.json`; миграция — `scripts/migrate_changelog_to_json.py`, `scripts/migrate_wishlist_to_json.py`), таблицы `incident_ticket_link` тоже нет (`incident_ticket_repo.py::_ensure_link_table_dropped` её дропает). Появились/не были описаны: `audit_log` и `equipment_placement`. Все таблицы в **актуальной** БД (17 штук): `engines`, `operating_modes`, `maintenance_works`, `users`, `tokens`, `audit_log`, `equipment_type`, `attribute_definition`, `equipment_type_attribute`, `equipment`, `equipment_placement`, `location_node`, `crew`, `incident_ticket`, `incident_ticket_initiator`, `incident_ticket_executor`, `incident_ticket_equipment`.
>
> Фактические номера строк `CREATE TABLE` в `modules/db.py` (на 2026-09-16, сдвинулись относительно первой версии документа): `engines` 102, `operating_modes` 129, `maintenance_works` 148, `users` 162, `tokens` 173, `audit_log` 200, `equipment_type` 231, `attribute_definition` 240, `equipment_type_attribute` 254, `equipment` 269, `equipment_placement` 314, `location_node` 347, `crew` 365, `incident_ticket` 383, `incident_ticket_initiator` 417, `incident_ticket_executor` 424, `incident_ticket_equipment` 431.

Схема определена в `modules/db.py` (одна функция `init_db()`, строка 76 — до конца файла). PRAGMA устанавливаются в `get_db_connection()`:

```
PRAGMA journal_mode=WAL
PRAGMA synchronous=NORMAL
PRAGMA foreign_keys=ON
```

Поддержка тестов: `db_connection(':memory:')` создаёт соединение с in-memory SQLite (для unit-тестов).

### Таблица 1: `engines` (`modules/db.py:71-95`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | Идентификатор двигателя |
| `filename` | TEXT | — | Имя исходного Excel-файла (импорт) |
| `purpose` | TEXT | — | Назначение двигателя |
| `workshop` | TEXT | — | Цех (старый текстовый формат, дублирует `location_node`) |
| `location` | TEXT | — | Место установки (старый текстовый формат) |
| `engine_type` | TEXT | — | Тип двигателя (например "АИР112М4У2") |
| `manufacturer` | TEXT | — | Производитель |
| `serial_number` | TEXT | — | Заводской номер |
| `bearing_front` | TEXT | — | Передний подшипник |
| `bearing_rear` | TEXT | — | Задний подшипник |
| `shaft_diameter` | TEXT | — | Диаметр вала |
| `protection_class` | TEXT | — | Степень защиты |
| `mounting_type` | TEXT | — | Тип крепления |
| `temp_sensor` | TEXT | — | Датчик температуры |
| `encoder` | TEXT | — | Энкодер |
| `cooling` | TEXT | — | Охлаждение |
| `note` | TEXT | — | Примечание |
| `photo_count` | INTEGER | DEFAULT 0 | Кэшированное количество фото (см. раздел 8) |
| `status` | TEXT | NOT NULL DEFAULT 'work' | Эксплуатационное состояние: `work`/`reserve`/`repair` (auto-migration `db.py:453`) |
| `created_at` | TEXT | — | ISO-дата создания (auto-migration `db.py:445`) |
| `updated_at` | TEXT | — | ISO-дата изменения (auto-migration `db.py:446`) |

Индексы: `idx_engines_updated_at`, `idx_engines_created_at`, `idx_engines_status`, плюс динамические `idx_engines_{col}` для полей ENGINE_COLUMNS_ORDERED.

ON DELETE CASCADE: не определён (сама `engines` не имеет внешнего ключа, см. ниже примечание про каскад).

### Таблица 2: `operating_modes` (`modules/db.py:96-108`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | Идентификатор записи |
| `engine_id` | INTEGER | FK→`engines(id)` ON DELETE CASCADE | Ссылка на двигатель |
| `frequency` | TEXT | — | Частота (Гц) |
| `power` | TEXT | — | Мощность (кВт) |
| `voltage` | TEXT | — | Напряжение (В) — может быть "220-240" |
| `connection_type` | TEXT | — | Тип подключения |
| `current` | TEXT | — | Ток (А) |
| `rpm` | TEXT | — | Обороты (об/мин) |

Индекс: `idx_modes_engine`.

> **Замечание о каскаде:** `ON DELETE CASCADE` записано в CREATE TABLE, но **на продакшен-БД (созданной до добавления CASCADE) не работает** — `repositories/engine_repo.py::delete()` удаляет дочерние строки вручную в одной транзакции (см. раздел 16).

### Таблица 3: `maintenance_works` (`modules/db.py:109-122`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | Идентификатор |
| `engine_id` | INTEGER | FK→`engines(id)` ON DELETE CASCADE | Ссылка на двигатель |
| `work_number` | TEXT | — | Номер работы |
| `date` | TEXT | — | Дата работы |
| `work_description` | TEXT | — | Вид работ |
| `isolation` | TEXT | — | Сопротивление изоляции (ГОм) |
| `inspection` | TEXT | — | Внешний осмотр |
| `signature` | TEXT | — | ФИО исполнителя |
| `status` | TEXT | NOT NULL DEFAULT 'work' | Состояние (auto-migration `db.py:460`) |

Индекс: `idx_works_engine`. ON DELETE CASCADE — тот же нюанс, что у `operating_modes`.

### Таблицы 4–5 (УДАЛЕНЫ): `changelog_entries`, `wishlist_items`

На 2026-09-16 этих таблиц в схеме **нет**. Журнал изменений и wishlist вкладки «Инфо» хранятся в JSON-файлах (`data/changelog.json`, `data/wishlist.json`); чтение/запись выполняет сам `routes/changelog.py` встроенным модулем `json` (пути — `config.settings.CHANGELOG_JSON_PATH`/`WISHLIST_JSON_PATH`), а НЕ `utils/file_store.py` (он в production не используется). Доступ по API `/api/changelog` (read-only), `/api/wishlist` (CRUD). Перенос выполняют одноразовые скрипты `scripts/migrate_changelog_to_json.py` и `scripts/migrate_wishlist_to_json.py` (создание записей вручную — `scripts/add_changelog_entry.py`).

### Таблица 6: `users` (`modules/db.py:162`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `username` | TEXT | UNIQUE NOT NULL | Логин |
| `password_hash` | TEXT | NOT NULL | werkzeug hash (pbkdf2/scrypt) |
| `role` | TEXT | NOT NULL DEFAULT 'user' | `user` / `admin` / `superadmin` / `reader` |
| `created_at` | TEXT | NOT NULL | ISO-дата |
| `last_login` | TEXT | (auto-migration `db.py:443`) | — |
| `last_edit` | TEXT | (auto-migration `db.py:444`) | — |

Seed: создаётся пользователь `admin` с паролем `admin123`, роль `admin` (`db.py:513-517`).

### Таблица 7: `tokens` (`modules/db.py:150-159`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `user_id` | INTEGER | NOT NULL, FK→`users(id)` ON DELETE CASCADE | Ссылка на пользователя |
| `token_hash` | TEXT | UNIQUE NOT NULL | SHA-256 от токена |
| `created_at` | TEXT | NOT NULL | — |
| `expires_at` | TEXT | (опц.) | — |

Индексы: `idx_tokens_hash`, `idx_tokens_user`.

### Таблица 8: `equipment_type` (`modules/db.py:222-230`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `code` | TEXT | NOT NULL UNIQUE | Код (UPPER_SNAKE_CASE) |
| `name` | TEXT | NOT NULL | Название |
| `parent_type_id` | INTEGER | FK→`equipment_type(id)` | Иерархия (как у Maximo Classifications) |
| `description` | TEXT | (опц.) | — |
| `min_stock_qty` | INTEGER | (auto-migration `db.py:492`, опц.) | Норма запаса (ТЗ 3.7) |

Индексы: `idx_equipment_type_parent` и динамически `idx_equipment_type_id`.

### Таблица 9: `attribute_definition` (`modules/db.py:231-244`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `key` | TEXT | NOT NULL UNIQUE | lower_snake_case |
| `label` | TEXT | NOT NULL | Подпись |
| `group_name` | TEXT | (опц.) | Группировка в карточке |
| `value_type` | TEXT | NOT NULL DEFAULT 'text', CHECK IN ('text','number','select','boolean','textarea') | — |
| `unit` | TEXT | (опц.) | Единица измерения |
| `options_json` | TEXT | (опц.) | JSON со списком вариантов для `value_type='select'` |
| `default_value` | TEXT | (опц.) | — |
| `weight` | INTEGER | NOT NULL DEFAULT 0 | Порядок отображения |

### Таблица 10: `equipment_type_attribute` (`modules/db.py:245-253`) — M2M

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `equipment_type_id` | INTEGER | NOT NULL, FK→`equipment_type(id)` ON DELETE CASCADE | — |
| `attribute_definition_id` | INTEGER | NOT NULL, FK→`attribute_definition(id)` ON DELETE CASCADE | — |
| `is_required` | INTEGER | NOT NULL DEFAULT 0 | — |
| `weight_override` | INTEGER | (опц.) | — |
| `show_in_list` | INTEGER | NOT NULL DEFAULT 0 (auto-migration `db.py:485`) | Показывать в таблице номенклатуры |

PK: `(equipment_type_id, attribute_definition_id)`. Индекс: `idx_eta_type`.

### Таблица 11: `equipment` (`modules/db.py:254-272`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `equipment_type_id` | INTEGER | NOT NULL, FK→`equipment_type(id)` | — |
| `name` | TEXT | NOT NULL | Наименование |
| `article` | TEXT | (опц.) | Артикул |
| `manufacturer` | TEXT | (опц.) | — |
| `serial_number` | TEXT | (опц.) | — |
| `workshop` | TEXT | (опц.) | Старый текстовый цех (для миграции) |
| `location` | TEXT | (опц.) | Старое текстовое место |
| `firmware_version` | TEXT | (опц.) | — |
| `criticality` | INTEGER | CHECK BETWEEN 1 AND 5 (опц.) | Критичность |
| `installed_at` | TEXT | (опц.) | Дата установки |
| `specs_json` | TEXT | (опц.) | JSON со значениями атрибутов типа |
| `note` | TEXT | (опц.) | — |
| `created_at` | TEXT | NOT NULL | — |
| `updated_at` | TEXT | NOT NULL | — |
| `location_node_id` | INTEGER | FK→`location_node(id)` (auto-migration `db.py:479`) | Новый формат места |

Индексы: `idx_equipment_type`, `idx_equipment_workshop`, `idx_equipment_location_node`.

> Схема хранит спецификации equipment через `specs_json` (TEXT с JSON) — реализация по образцу NetBox Custom Fields. Парсинг через `json.loads(d['options_json'])` в `repositories/equipment_repo.py::list_attribute_definitions`.

### Таблица 12: `location_node` (`modules/db.py:361-371`) — общее дерево мест

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `parent_id` | INTEGER | FK→`location_node(id)` (опц.) | Корень дерева — NULL |
| `name` | TEXT | NOT NULL | Имя узла |
| `node_type` | TEXT | CHECK IN ('workshop','installation','unit','zone','warehouse','other') | — |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | — |

UNIQUE: `UNIQUE(parent_id, name)`. Индексы: `idx_location_parent`, `idx_location_name`.

> Примечание автора: `UNIQUE(parent_id, name)` не защищает корневые узлы от дублей (`NULL != NULL` в SQLite).

### Таблица 13: `crew` (`modules/db.py:381-389`) — справочник людей Инцидентов

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `full_name` | TEXT | NOT NULL | ФИО |
| `position` | TEXT | (опц.) | Должность |
| `workshop` | TEXT | (опц.) | Цех |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | — |

Индекс: `idx_crew_name`.

### Таблица 14: `incident_ticket` (`modules/db.py:392-404`) — заявка Инцидента

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `location_node_id` | INTEGER | NOT NULL, FK→`location_node(id)` | — |
| `problem` | TEXT | NOT NULL | Описание проблемы |
| `solution` | TEXT | (опц.) | Решение |
| `priority` | TEXT | NOT NULL DEFAULT 'medium' | CHECK IN ('low','medium','high') |
| `status` | TEXT | NOT NULL DEFAULT 'in_progress' | CHECK IN ('in_progress','resolved','rejected') |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | — |
| `closed_at` | TEXT | (опц.) | — |
| `created_by_user_id` | INTEGER | NOT NULL, FK→`users(id)` | — |
| `updated_at` | TEXT | (auto-migration в `repositories/incident_ticket_repo.py::_ensure_updated_at_column`) | — |

Индексы: `idx_incident_status`, `idx_incident_location`.

### Таблица 15: `incident_ticket_initiator` (`modules/db.py:408-414`) — M2M

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `ticket_id` | INTEGER | NOT NULL, FK→`incident_ticket(id)` ON DELETE CASCADE | — |
| `crew_id` | INTEGER | NOT NULL, FK→`crew(id)` | — |

PK: `(ticket_id, crew_id)`.

### Таблица 16: `incident_ticket_executor` (`modules/db.py:415-421`) — M2M

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `ticket_id` | INTEGER | NOT NULL, FK→`incident_ticket(id)` ON DELETE CASCADE | — |
| `crew_id` | INTEGER | NOT NULL, FK→`crew(id)` | — |

PK: `(ticket_id, crew_id)`.

### Таблица 17: `incident_ticket_equipment` (`modules/db.py:422-428`) — M2M

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `ticket_id` | INTEGER | NOT NULL, FK→`incident_ticket(id)` ON DELETE CASCADE | — |
| `equipment_id` | INTEGER | NOT NULL, FK→`equipment(id)` | — |

PK: `(ticket_id, equipment_id)`.

### Таблица 18 (УДАЛЕНА): `incident_ticket_link`

Таблицы ссылок заявки в схеме больше **нет** (2026-09-16): `repositories/incident_ticket_repo.py::_ensure_link_table_dropped` дропает её при первом обращении (появилась FK-миграция на «без users-FK», см. `_ensure_no_users_fk`). Ссылки-«линки» заявок в UI/API не поддерживаются.

### Таблица 19: `audit_log` (`modules/db.py:200`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `entity_type` | TEXT | NOT NULL | Тип сущности: `'engine'`, `'equipment'`, `'incident_ticket'`, … |
| `entity_id` | INTEGER | NOT NULL | id сущности |
| `field_name` | TEXT | NOT NULL | Какое поле изменилось (одна строка = одно поле) |
| `old_value` | TEXT | (опц.) | Прежнее значение |
| `new_value` | TEXT | (опц.) | Новое значение |
| `changed_by_user_id` | INTEGER | (опц.) | id пользователя |
| `changed_by_display_name` | TEXT | (опц.) | Денормализованное имя на момент правки |
| `changed_at` | TEXT | NOT NULL | Время правки |

Индекс: `idx_audit_log_entity(entity_type, entity_id, changed_at)`.

> Запись ведёт `modules/audit.py` (`log_creation`, `log_deletion`, `log_field_changes`) из репозиториев (`engine_repo`, `equipment_repo`, `incident_ticket_repo`); чтение — `repositories/audit_repo.py` (`list_entries`, `list_entity_types`) через `GET /api/audit/log` и `GET /api/audit/entity-types`; UI — таб «Аудит» (`static/js/audit.js`).

### Таблица 20: `equipment_placement` (`modules/db.py:314`)

| Колонка | Тип | PK/AUTOINC | Назначение |
| --- | --- | --- | --- |
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `equipment_id` | INTEGER | NOT NULL, FK→`equipment(id)` ON DELETE CASCADE | Оборудование |
| `location_node_id` | INTEGER | NOT NULL, FK→`location_node(id)` | Место установки (узел дерева) |
| `designation` | TEXT | (опц.) | Схемное обозначение (уникально в пределах места) |
| `note` | TEXT | (опц.) | Примечание |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | — |

Индексы: `idx_equipment_placement_equipment`, `idx_equipment_placement_location`. CRUD — `repositories/equipment_placement_repo.py`, API — `/api/equipment/<id>/placements*`.

> **Фото Инцидентов НЕ имеют таблицы в БД** — они хранятся на диске в папке `PhotoI/` с маской `ID{ticket_id}_{n}.{ext}`. Аналогично для оборудования — `PhotoE/`.

### Сводная таблица: ON DELETE поведение FK

| FK | ON DELETE | Реально работает на прод-БД? | Источник |
| --- | --- | --- | --- |
| `operating_modes.engine_id → engines.id` | CASCADE | **НЕТ** (старая БД) — `engine_repo.delete()` удаляет вручную | `repositories/engine_repo.py:243-247` |
| `maintenance_works.engine_id → engines.id` | CASCADE | **НЕТ** (старая БД) — `engine_repo.delete()` удаляет вручную | `repositories/engine_repo.py:244-246` |
| `tokens.user_id → users.id` | CASCADE | ✅ да (таблица новая) | `db.py:157` |
| `equipment_type_attribute.equipment_type_id` | CASCADE | ✅ да | `db.py:247` |
| `equipment_type_attribute.attribute_definition_id` | CASCADE | ✅ да | `db.py:248` |
| `equipment.equipment_type_id` | (не указано) | n/a | — |
| `location_node.parent_id` | (не указано) | n/a (см. `repositories/location_repo.py::has_children` для защиты) | — |
| `incident_ticket.location_node_id` | (не указано) | n/a (см. `repositories/location_repo.py::is_referenced` для защиты) | — |
| `incident_ticket.created_by_user_id → users.id` | (не указано) | n/a | — |
| `incident_ticket_initiator/executor/equipment.ticket_id` | CASCADE | ✅ да | `db.py:417,424,431` |
| `incident_ticket_equipment.equipment_id` | (не указано) | n/a | — |
| `equipment_placement.equipment_id` | CASCADE | ✅ да | `db.py:316` |
| `equipment_placement.location_node_id` | (не указано) | n/a (защита — `location_repo.is_referenced`) | `db.py:317` |
| `incident_ticket_link.ticket_id` | — | **таблицы больше нет** (дропается `_ensure_link_table_dropped`) | — |

> **Требует уточнения:** для таблиц `equipment`, `equipment_type` отсутствуют явные ON DELETE CASCADE/RESTRICT. SQLite БЕЗ `PRAGMA foreign_keys=ON` молча игнорирует FK. В коде `get_db_connection()` явно включает `PRAGMA foreign_keys=ON`, но если кто-то забудет его установить (например, через прямой `sqlite3.connect()` в обход `db_connection`) — связи не будут enforced. Из диагностических скриптов напрямую `sqlite3.connect(DB_PATH)` использует `diag_photos.py:6` (файла `promote_and_cleanup.py` в проекте уже нет — см. раздел 17.12).

## 4. Backend — карта роутов

Все эндпоинты приложения. Метод + путь → файл → имя функции-обработчика → параметры → что возвращает → какой repository/service/module вызывает → краткое описание.

### `routes/auth.py` (auth_bp, `/api/auth`)

| Метод/путь | Функция | Параметры | Возврат | Сервис | Описание |
| --- | --- | --- | --- | --- | --- |
| `before_app_request` | `load_current_user` | — | `None` или 401/403 JSON | `modules.auth.tokens.get_user_from_token` | Парсит токен из Bearer/Query, кладёт `request.current_user`. На не-GET: 401 без токена, 403 для `reader` (кроме `/api/engines/search`) |
| `POST /api/auth/login` | `auth_login` | body `{username, password}` | `{success, token, role, user}` или `{error}`, 401 | `modules.auth.auth.get_user_by_username`, `verify_password`, `issue_token` | Логин |
| `POST /api/auth/logout` | `auth_logout` | — | `{success}` или `{error}` | `modules.auth.tokens.revoke_token` | Эксемпт-write (см. `_AUTH_EXEMPT_WRITE_PATHS`) |
| `GET /api/auth/me` | `auth_me` | — | user dict | `auth_module.get_user_by_id` | Текущий пользователь |
| `POST /api/auth/admin/users` | `admin_create_user` | body `{username, password, role}` | `{success, id}` или `{error}`, 400/403/409/500 | `auth_module.create_file_user` | Создать файл-пользователя. Только superadmin может давать admin/superadmin |
| `DELETE /api/auth/admin/users/<int:user_id>` | `admin_delete_user` | path `user_id` | `{success}` или 400/403/404 | `auth_module.delete_user` / `delete_file_user` | Нельзя удалить себя; admin-ов может удалять только superadmin |
| `POST /api/auth/admin/users/<int:user_id>/password` | `admin_change_password` | path `user_id`, body `{password}` | `{success}` или 400/404 | `update_user_password` / `update_file_user_password` | Сменить пароль |
| `POST /api/auth/admin/users/<int:user_id>/revoke` | `admin_revoke_user` | path `user_id` | `{success}` | `revoke_all_for_user` | Сбросить все сессии |

### `routes/engines.py` (engines_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Сервис | Описание |
| --- | --- | --- | --- | --- | --- |
| `GET /api/engines` | `list_engines` | query: `search, search_field, sort_by, sort_order, workshop, location, status` | список engines | `repositories.engine_repo.get_all` | Каталог двигателей |
| `GET /api/locations-tree` | `locations_tree` | — | `{workshop: {location: count}}` | `engine_repo.get_locations_tree` | Дерево цехов для боковой панели |
| `GET /api/engine/<int:engine_id>` | `get_engine` | path `engine_id` | engine dict с modes/works/photo_count | `engine_repo.get_with_details` | Карточка |
| `POST /api/engine` | `create_engine` | body engine dict | `{success, id, message}` или `{error}`, 400 | `engine_repo.create`, `sanitize_engine_data`, `validate_engine_payload` | Создать |
| `PUT /api/engine/<int:engine_id>` | `update_engine` | path `engine_id`, body | `{success, message}` или 404 | `engine_repo.update` | Обновить |
| `DELETE /api/engine/<int:engine_id>` | `delete_engine` | path `engine_id` | `{success, message}` или 500/404 | `modules.photo_manager.manager.delete_engine_photos_from_disk`, `engine_repo.delete` | Сначала фото, потом БД |
| `PATCH /api/engine/<int:engine_id>/status` | `set_engine_status` | body `{status}` | `{success, status, message}` или 400/404 | `engine_repo.update_status` | Смена эксплуат. статуса |
| `PUT /api/engine/<int:engine_id>/modes` | `update_engine_modes` | body `{modes: [...]}` | `{success, message}` или 400/404 | `mode_repo.replace_all` | Полная замена режимов |
| `PUT /api/engine/<int:engine_id>/works` | `update_engine_works` | body `{works: [...]}` | `{success, message}` или 400/404 | `work_repo.replace_all` | Полная замена работ |

### `routes/photos.py` (photos_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Сервис | Описание |
| --- | --- | --- | --- | --- | --- |
| `GET /api/engine/<int:engine_id>/photos` | `get_engine_photos` | path `engine_id` | `[{'filename', 'path'}]` или `[]` | `modules.photo_manager.manager.get_engine_photos` | Список фото |
| `GET /api/photos/<filename>` | `get_photo` | path `filename` | файл (no-cache) | `manager.get_photo` | Отдать файл |
| `POST /api/engine/<int:engine_id>/photos` | `upload_engine_photos` | multipart `photos` | dict из `manager.upload_engine_photos` | `manager.upload_engine_photos` | Загрузить |
| `DELETE /api/engine/<int:engine_id>/photos/<filename>` | `delete_engine_photo` | path | JSON | `manager.delete_engine_photo` | Удалить одно фото |
| `PUT /api/engine/<int:engine_id>/photos/<filename>` | `replace_engine_photo` | multipart `photo` | JSON | `manager.replace_engine_photo` | Заменить (обрезка) |

### `routes/equipment_routes.py` (equipment_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/equipment-types` | `get_equipment_types` | — | список типов | плоский список + parent_name |
| `POST /api/equipment-types` | `create_equipment_type_route` | body | 200/400/500 (admin+) | создать тип |
| `DELETE /api/equipment-types/<int:type_id>` | `delete_equipment_type_route` | path | 200/404/500 | удалить (если не in_use) |
| `GET /api/attribute-definitions` | `get_attribute_definitions` | — | список | — |
| `POST /api/attribute-definitions` | `create_attribute_definition_route` | body | 200/400/500 (admin+) | — |
| `DELETE /api/attribute-definitions/<int:attr_id>` | `delete_attribute_definition_route` | path | 200/404/500 | — |
| `GET /api/equipment-types/<int:type_id>/attributes` | `get_type_attributes_route` | path | `{type, assigned: [...], effective: [...]}` | effective наследует атрибуты родителя |
| `PUT /api/equipment-types/<int:type_id>/attributes` | `set_type_attributes_route` | body `{attribute_ids: [...]}` | 200/400 (admin+) | — |
| `PATCH /api/equipment-types/<int:type_id>/min-stock` | `update_min_stock_route` | body `{min_stock_qty}` | 200/400/404 (admin+) | — |
| `GET /api/equipment` | `list_equipment` | query: `type, location_subtree, search, attributes` | плоский список | — |
| `GET /api/equipment/<int:equipment_id>` | `get_equipment_route` | path | dict | с details |
| `POST /api/equipment` | `create_equipment_route` | body | `{success, id}` | — |
| `PUT /api/equipment/<int:equipment_id>` | `update_equipment_route` | path, body | 200/404 | — |
| `DELETE /api/equipment/<int:equipment_id>` | `delete_equipment_route` | path | 200/400/404 | через `equipment_repo.delete_equipment` |
| `GET /api/equipment/location-counts` | `get_equipment_location_counts_route` | — | `{location_node_id: count}` | — |
| `GET /api/equipment/stock-summary` | `get_stock_summary_route` | — | список | ЗИП |
| `GET /api/equipment/<int:equipment_id>/photos` | `get_equipment_photos_route` | path | список | — |
| `POST /api/equipment/<int:equipment_id>/photos` | `upload_equipment_photos_route` | multipart | JSON | — |
| `PUT /api/equipment/<int:equipment_id>/photos/<filename>` | `replace_equipment_photo_route` | multipart | JSON | — |
| `DELETE /api/equipment/<int:equipment_id>/photos/<filename>` | `delete_equipment_photo_route` | path | JSON | — |
| `POST /api/equipment/export` | `export_equipment_route` | body `{ids}` | xlsx blob | POST с лимитом 100 |

### `routes/equipment_photo_routes.py` (equipment_photo_bp, `/api/equipment-photos`)

| Метод/путь | Функция | Параметры | Возврат | Сервис | Описание |
| --- | --- | --- | --- | --- | --- |
| `GET /api/equipment-photos/<path:filename>` | `get_equipment_photo_route` | path `filename` | файл | `equipment_manager.get_photo` | Отдача файлов фото оборудования (read-only) |

### `routes/location_routes.py` (location_bp, `/api/locations`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/locations` | `list_locations_route` | — | плоский список узлов | — |
| `POST /api/locations` | `create_location_route` | body `{name, node_type, parent_id?}` | 200/400 | — |
| `GET /api/locations/search` | `search_locations_route` | query `q` | список с `path` | — |
| `GET /api/locations/children` | `children_locations_route` | query `parent_id` | дети | — |
| `GET /api/locations/<int:node_id>/breadcrumb` | `breadcrumb_location_route` | path | путь от корня | — |
| `PUT /api/locations/<int:node_id>` | `update_location_route` | path, body | 200/400/404 | — |
| `PATCH /api/locations/<int:node_id>/move` | `move_location_route` | path, body `{parent_id}` | 200/400/404 | защита от цикла |
| `DELETE /api/locations/<int:node_id>` | `delete_location_route` | path | 200/400/404 | защита: есть дети / используется |

### `routes/crew_routes.py` (crew_bp, `/api/crew`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/crew` | `list_crew_route` | — | плоский список | — |
| `POST /api/crew` | `create_crew_route` | body `{full_name, position?, workshop?}` | `{success, id}` | — |
| `GET /api/crew/search` | `search_crew_route` | query `q` | список | — |
| `PUT /api/crew/<int:crew_id>` | `update_crew_route` | path, body | 200/400/404 | — |
| `DELETE /api/crew/<int:crew_id>` | `delete_crew_route` | path | 200/400/404 | через `incident_service.delete_crew` (проверка ссылок) |

### `routes/incident_ticket_routes.py` (incident_ticket_bp, `/api/incident-tickets`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/incident-tickets` | `list_tickets_route` | query `status, priority, location_node_id` | список | — |
| `POST /api/incident-tickets` | `create_ticket_route` | body | `{success, id}` | через `incident_service.create_ticket` |
| `GET /api/incident-tickets/<int:ticket_id>` | `get_ticket_route` | path | dict с photos/links | — |
| `PATCH /api/incident-tickets/<int:ticket_id>` | `update_ticket_route` | path, body | 200/400/404 | — |
| `DELETE /api/incident-tickets/<int:ticket_id>` | `delete_ticket_route` | path | 200/404 | superadmin only |
| `GET /api/incident-tickets/location-counts` | `get_location_counts_route` | — | `{node_id: count, 'unassigned': count}` | — |
| `POST /api/incident-tickets/<int:ticket_id>/links` | `add_link_route` | body `{url, caption?}` | `{success, id}` | — |
| `GET /api/incident-tickets/<int:ticket_id>/links` | `get_links_route` | path | список | — |
| `DELETE /api/incident-tickets/links/<int:link_id>` | `delete_link_route` | path | 200/404 | — |
| `POST /api/incident-tickets/<int:ticket_id>/equipment` | `add_equipment_route` | body `{equipment_id}` | 200/400/404 | — |
| `DELETE /api/incident-tickets/<int:ticket_id>/equipment/<int:equipment_id>` | `remove_equipment_route` | path | 200/404 | — |
| `GET /api/incident-tickets/<int:ticket_id>/photos` | `list_ticket_photos_route` | path | список | — |
| `POST /api/incident-tickets/<int:ticket_id>/photos` | `upload_ticket_photos_route` | multipart | JSON | — |
| `DELETE /api/incident-tickets/<int:ticket_id>/photos/<filename>` | `delete_ticket_photo_route` | path | JSON | — |
| `POST /api/incident-tickets/export` | `export_tickets_route` | body `{ids}` | xlsx blob | лимит 100 |

### `routes/incident_photo_routes.py` (incident_photo_bp, `/api/incident-photos`)

| Метод/путь | Функция | Параметры | Возврат | Сервис | Описание |
| --- | --- | --- | --- | --- | --- |
| `GET /api/incident-photos/<path:filename>` | `get_incident_photo_route` | path | файл | `incident_manager.get_photo` | read-only |

### `routes/backup_routes.py` (backup_bp, `/api/backup`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/backup/list` | `list_backups` | — | список бэкапов с manifest | — |
| `POST /api/backup/create` | `create_backup` | — | zip blob (attachment) | — |
| `POST /api/backup/inspect-upload` | `inspect_uploaded_backup` | multipart `file` или `backup` | `{valid, manifest, errors, staging_id, filename}` | — |
| `POST /api/backup/restore/<filename>` | `restore_backup` | path | `{success, message, restored_files}` или 409 | ищет в staging, потом backups/ |
| `POST /api/backup/confirm-restore` | `confirm_restore_uploaded_backup` | body `{filename}` или `{staging_id}` | `{success, restored_files}` или 422/409 | повторная проверка чексумм |
| `GET /api/backup/download/<filename>` | `download_backup` | path | файл | — |
| `POST /api/backup/delete/<filename>` | `delete_backup` | path | 200/404 | обратная совместимость |
| `DELETE /api/backup/<filename>` | `delete_backup_http_delete` | path | 200/404 | алиас для frontend (DELETE) |

### `routes/changelog.py` (changelog_bp, `/api`)

> **Обновление 2026-09-16:** changelog стал **read-only** — `POST /api/changelog` и `DELETE /api/changelog/<id>` удалены из кода (см. docstring `routes/changelog.py:5-7`); новые записи добавляются скриптом `scripts/add_changelog_entry.py`. Данные читаются из `data/changelog.json` (не из БД) — сортировка `entry_date DESC, id DESC`.

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/changelog` | `get_changelog` | — | список записей из `data/changelog.json` | read-only (запись через API удалена) |
| ~~`POST /api/changelog`~~ | — | — | — | **удалён из кода** |
| ~~`DELETE /api/changelog/<int:entry_id>`~~ | — | — | — | **удалён из кода** |
| `GET /api/wishlist` | `get_wishlist` | — | список пожеланий из `data/wishlist.json` | сортировка: невыполненные сверху |
| `POST /api/wishlist` | `create_wishlist_item` | body `{text}` | `{success, item}` | создать пожелание |
| `PUT /api/wishlist/<int:item_id>` | `update_wishlist_item` | path, body `{done?, text?}` | `{success, item}` / 404 | изменить |
| `DELETE /api/wishlist/<int:item_id>` | `delete_wishlist_item` | path | `{success}` / 404 | удалить |

> Файлы JSON читаются/пишутся встроенным `json` прямо в `routes/changelog.py` (`_load_wishlist`, `_save_wishlist`), а НЕ через `utils/file_store.py`; пути берутся из `config.settings.CHANGELOG_JSON_PATH` / `WISHLIST_JSON_PATH`.

### `routes/status.py` (status_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/status` | `get_status` | — | `{engine_count, modes_count, works_count, photos_count, files_in_folder, db_size_bytes, db_size_label, equipment_count, equipment_photos_count, incident_count, incident_open_count, incident_photos_count, app_version, python_version, flask_version, sqlite_version, has_data}` | дашборд-счётчики |

### `routes/search.py` (search_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /api/search-suggestions` | `search_suggestions` | query `field, query` | `[строка]` | подсказки для autocomplet` |
| `POST /api/engines/search` | `advanced_search` | body `{conditions: [{field, operator, value, value2?}]}` | список engines | расширенный поиск по whitelisted колонкам |

### `routes/import_routes.py` (import_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `POST /api/import-folder` | `import_folder` | — | `{success, imported, total_photos, elapsed_time, file_reports: [...], summary: {...}}` | массовый импорт Excel из `MOTORS_FOLDER` через `ThreadPoolExecutor(MAX_WORKERS=4)` |
| `POST /api/clear` | `clear_database` | — | `{success, message}` | удалить все engines/modes/works, сбросить `sqlite_sequence`, VACUUM, `shutil.rmtree(PHOTOS_FOLDER)` |

### `routes/export_routes.py` (export_bp, `/api`)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `POST /api/engines/export` | `export_to_excel` | body `{ids: [int]}` | xlsx blob (макс 100) | вызывает `services.export_service.export_to_xlsx` |

### `routes/pages.py` (pages_bp, без префикса)

| Метод/путь | Функция | Параметры | Возврат | Описание |
| --- | --- | --- | --- | --- |
| `GET /` | `index` | — | `templates/index.html` | SPA |
| `GET /print/<int:engine_id>` | `print_engine_page` | path | `templates/print.html` | id парсится в `print.js` на клиенте |
| `GET /print/incident/<int:ticket_id>` | `print_incident_page` | path | `templates/print_incident.html` | id парсится в `incidentPrint.js` |
| `GET /print/equipment/<int:equipment_id>` | `print_equipment_page` | path | `templates/print_equipment.html` | id парсится в `equipmentPrint.js` |
| `GET /static/<path:path>` | `serve_static` | path | файл из `static/` | — |
| `GET /test` | `test` | — | `{status: 'ok', message: 'Сервер работает!'}` | healthcheck |

## 5. Backend — repositories, services, modules

Для каждой публичной функции — полная СИГНАТУРА (имя + параметры с дефолтами), одна строка что делает, и кто её вызывает.

### `repositories/engine_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | `sqlite3.Row → dict` | (private) |
| `get_by_id` | `(conn, engine_id: int)` | SELECT по id (без modes/works) | `routes/engines.py::delete_engine` (проверка существования); в тестах `tests/test_repositories/test_engine_repo.py` |
| `get_with_details` | `(conn, engine_id: int)` | двигатель + modes + works | `routes/engines.py::get_engine`, `services/export_service.py::export_to_xlsx` |
| `get_modes_for_engine` | `(conn, engine_id: int)` | список modes | `engine_repo.get_with_details` (через `repositories.mode_repo.get_all`) |
| `get_works_for_engine` | `(conn, engine_id: int)` | список works | `engine_repo.get_with_details` (через `repositories.work_repo.get_all`) |
| `get_all` | `(conn, limit=30, offset=0, sort='location_asc', search_field='all', search_query='', workshop=None, location=None, status=None)` | список с пагинацией/сортировкой/поиском/фильтрами | `routes/engines.py::list_engines`, `tests/test_repositories/test_engine_repo.py` |
| `count_all` | `(conn)` | `SELECT COUNT(*) FROM engines` | тесты |
| `create` | `(conn, data: dict)` → `int` | INSERT + явный поиск минимального свободного id (см. раздел 8) | `routes/engines.py::create_engine` |
| `update` | `(conn, engine_id: int, data: dict)` → `bool` | UPDATE по `ENGINE_COLUMNS_ORDERED` + `updated_at=now()` | `routes/engines.py::update_engine` |
| `delete` | `(conn, engine_id: int)` → `bool` | DELETE modes + DELETE works + DELETE engine (явно, без опоры на CASCADE на старой БД) | `routes/engines.py::delete_engine` |
| `update_photo_count` | `(conn, engine_id: int, count: int)` → `None` | UPDATE photo_count | (на момент снимка никто не вызывает в routes — поиск; см. раздел 16) |
| `update_status` | `(conn, engine_id: int, status: str)` → `bool` | UPDATE status | `routes/engines.py::set_engine_status` |
| `get_by_filename` | `(conn, filename: str)` | SELECT по filename (для импорта) | тесты |
| `get_locations_tree` | `(conn)` | `{workshop: {location: count}}` | `routes/engines.py::locations_tree` |
| `VALID_STATUSES` | `= ('work', 'reserve', 'repair')` | whitelist для статусов | `routes/engines.py::set_engine_status`, `schemas.engine_schema.validate_work_status` |

### `repositories/mode_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | private | — |
| `get_all` | `(conn, engine_id: int)` | SELECT modes | `engine_repo.get_modes_for_engine` |
| `replace_all` | `(conn, engine_id: int, modes: list[dict])` | DELETE ALL + executemany INSERT | `routes/engines.py::update_engine_modes` |
| `create` | `(conn, engine_id: int, mode: dict)` → `int` | INSERT одного режима | (на момент снимка нет вызывающих из роутов) |
| `delete_all_for_engine` | `(conn, engine_id: int)` | DELETE modes для двигателя | (не вызывается в routes) |

### `repositories/work_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | private | — |
| `get_all` | `(conn, engine_id: int)` | SELECT works | `engine_repo.get_works_for_engine` |
| `replace_all` | `(conn, engine_id: int, works: list[dict])` | DELETE + executemany INSERT | `routes/engines.py::update_engine_works` |
| `create` | `(conn, engine_id: int, work: dict)` → `int` | INSERT одной работы | (нет вызывающих) |
| `delete_all_for_engine` | `(conn, engine_id: int)` | DELETE works для двигателя | (нет вызывающих) |
| `WORK_COLUMNS` | `frozenset(['work_number','date','work_description','isolation','inspection','signature','status'])` | whitelist колонок | `replace_all`, `create` |

### `repositories/equipment_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | private | — |
| `list_equipment_types` | `(conn)` | плоский список типов с `parent_name` | `routes/equipment_routes.py::get_equipment_types` |
| `get_equipment_type` | `(conn, type_id: int)` | SELECT по id | guard, проверка использования |
| `create_equipment_type` | `(conn, code, name, parent_type_id=None, description=None)` → `int` | INSERT типа | `routes/equipment_routes.py::create_equipment_type_route` |
| `equipment_type_in_use` | `(conn, type_id: int)` → `bool` | проверка: есть записи equipment ИЛИ дочерние типы | `routes/equipment_routes.py::delete_equipment_type_route` |
| `delete_equipment_type` | `(conn, type_id: int)` → `bool` | DELETE M2M + DELETE тип | `routes/equipment_routes.py::delete_equipment_type_route` |
| `list_attribute_definitions` | `(conn)` | список + парсинг `options_json` | `routes/equipment_routes.py::get_attribute_definitions` |
| `create_attribute_definition` | `(conn, data: dict)` → `int` | INSERT | `routes/equipment_routes.py::create_attribute_definition_route` |
| `attribute_definition_in_use` | `(conn, attr_id)` → `bool` | проверка | `routes/equipment_routes.py::delete_attribute_definition_route` |
| `delete_attribute_definition` | `(conn, attr_id)` → `bool` | DELETE | `routes/equipment_routes.py::delete_attribute_definition_route` |
| `get_assigned_attributes` | `(conn, type_id)` | список атрибутов M2M типа | `routes/equipment_routes.py::get_type_attributes_route` |
| `get_effective_attributes` | `(conn, type_id)` | assigned + inherited от родителя | `routes/equipment_routes.py::get_type_attributes_route`, `static/js/equipmentPrint.js` |
| `set_type_attributes` | `(conn, type_id, attribute_ids)` | DELETE + INSERT M2M | `routes/equipment_routes.py::set_type_attributes_route` |
| `get_equipment_by_id` | `(conn, equipment_id)` | SELECT по id | `routes/equipment_routes.py::get_equipment_route` |
| `list_equipment` | `(conn, type_id=None, ...)` | список оборудования | `routes/equipment_routes.py::list_equipment` |
| `create_equipment` | `(conn, data: dict)` → `int` | INSERT | `routes/equipment_routes.py::create_equipment_route` |
| `update_equipment` | `(conn, equipment_id, data)` → `bool` | UPDATE | `routes/equipment_routes.py::update_equipment_route` |
| `delete_equipment` | `(conn, equipment_id)` → `bool` | DELETE | `routes/equipment_routes.py::delete_equipment_route` |
| `get_equipment_location_counts` | `(conn)` | { node_id: count } (свои, без суммы поддерева) | `routes/equipment_routes.py::get_equipment_location_counts_route`, `static/js/equipmentLocationTree.js` |
| `get_show_in_list_attributes` | `(conn, type_id=None)` | колонки для динамической таблицы | `routes/equipment_routes.py::list_equipment` |
| `get_stock_summary` | `(conn)` | сводка ЗИП | `routes/equipment_routes.py::get_stock_summary_route` |
| `update_equipment_type_min_stock_qty` | `(conn, type_id, min_stock_qty)` → `bool` | UPDATE | `routes/equipment_routes.py::update_min_stock_route` |
| `count_all` | `(conn)` → `int` | дашборд-счётчик | `routes/status.py::get_status` |
| `equipment_referenced_by_incidents` | `(conn, equipment_id)` → `bool` | guard удаления | `routes/equipment_routes.py::delete_equipment_route` |

### `repositories/incident_ticket_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_ensure_updated_at_column` | `(conn)` | auto-migration колонки `updated_at` | внутри `list_all`, `get_by_id`, `update` |
| `list_all` | `(conn, status=None, priority=None, location_node_id=None)` → `list[dict]` | список заявок с breadcrumb + ФИО | `routes/incident_ticket_routes.py::list_tickets_route`, `static/js/incidents.js` |
| `get_by_id` | `(conn, ticket_id)` → `dict\|None` | заявка + initiators + executors + links + photos | `routes/incident_ticket_routes.py::get_ticket_route`, `services/export_service.py::export_incidents_to_xlsx` |
| `create` | `(conn, location_node_id, problem, created_by_user_id, solution=None, priority='medium', status='in_progress', closed_at=None)` → `int` | INSERT | `services/incident_service.create_ticket` |
| `update` | `(conn, ticket_id, location_node_id=None, problem=None, solution=None, priority=None, status=None, closed_at=None)` → `bool` | UPDATE | `services/incident_service.update_ticket` |
| `delete` | `(conn, ticket_id)` → `bool` | DELETE | `services/incident_service.delete_ticket` |
| `set_initiators` | `(conn, ticket_id, crew_ids)` | DELETE + executemany INSERT | `services/incident_service` (create/update) |
| `set_executors` | `(conn, ticket_id, crew_ids)` | то же для исполнителей | `services/incident_service` (create/update) |
| `get_links` | `(conn, ticket_id)` → list | список ссылок | `routes/incident_ticket_routes.py::get_links_route` |
| `add_link` | `(conn, ticket_id, url, caption=None)` → `int` | INSERT | `routes/incident_ticket_routes.py::add_link_route` |
| `delete_link` | `(conn, link_id)` → `bool` | DELETE | `routes/incident_ticket_routes.py::delete_link_route` |
| `get_location_counts` | `(conn)` → `dict` | `{node_id: count, 'unassigned': count}` | `routes/incident_ticket_routes.py::get_location_counts_route` |
| `count_all` | `(conn)` → `int` | дашборд | `routes/status.py::get_status` |
| `count_by_status` | `(conn, status)` → `int` | дашборд | `routes/status.py::get_status` |

### `repositories/incident_equipment_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `get_relations` | `(conn, ticket_id)` → `list[dict]` | список связанного оборудования | внутри `incident_ticket_repo.get_by_id` (через JOIN в основном запросе) |
| `add_relation` | `(conn, ticket_id, equipment_id)` | INSERT OR IGNORE | `services/incident_service.add_equipment_link` |
| `remove_relation` | `(conn, ticket_id, equipment_id)` → `bool` | DELETE | `services/incident_service.remove_equipment_link` |

### `repositories/location_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `VALID_NODE_TYPES` | `set('workshop','installation','unit','zone','warehouse','other')` | whitelist node_type | `routes/location_routes.py` |
| `list_all` | `(conn)` → `list[dict]` | плоский список всех узлов | `routes/location_routes.py::list_locations_route`, `static/js/equipmentLocationTree.js`, `static/js/incidentLocationTree.js` |
| `get_children` | `(conn, parent_id)` → `list[dict]` | дети узла | `routes/location_routes.py::children_locations_route` |
| `search` | `(conn, query, limit=20)` → `list[dict]` | регистронезависимый поиск на Python + breadcrumb | `static/js/incidentLocations.js` (через `/api/locations/search`) |
| `get_breadcrumb` | `(conn, node_id)` → `list[dict]` | путь от корня | `routes/location_routes.py::breadcrumb_location_route` |
| `get_by_id` | `(conn, node_id)` → `dict\|None` | SELECT | `routes/location_routes.py`, `services/incident_service`, `services/equipment_location_migration`, `equipment_repo.get_stock_summary` |
| `create` | `(conn, name, node_type, parent_id=None)` → `int` | INSERT | `services/equipment_location_migration`, `routes/location_routes.py` |
| `update` | `(conn, node_id, name=None, node_type=None)` → `bool` | UPDATE | `routes/location_routes.py::update_location_route` |
| `get_subtree_ids` | `(conn, node_id)` → `list[int]` | все id узла и потомков (recursive CTE) | `equipment_repo.get_stock_summary`, `location_repo._is_descendant` |
| `_is_descendant` | `(conn, node_id, candidate_ancestor_id)` → `bool` | проверка на цикл | `location_repo.move` |
| `move` | `(conn, node_id, new_parent_id)` → `(bool, str\|None)` | смена родителя + guard | `routes/location_routes.py::move_location_route`, `services/incident_service.move_location` |
| `has_children` | `(conn, node_id)` → `bool` | есть ли дети | `location_repo.delete` |
| `is_referenced` | `(conn, node_id)` → `bool` | используется в incident_ticket или equipment | `location_repo.delete` |
| `delete` | `(conn, node_id)` → `(bool, str\|None)` | DELETE с guards | `routes/location_routes.py::delete_location_route`, `services/incident_service.delete_location` |

### `repositories/crew_repo.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `list_all` | `(conn)` → `list[dict]` | плоский список | `routes/crew_routes.py::list_crew_route`, `static/js/incidentCrew.js` |
| `get_by_id` | `(conn, crew_id)` → `dict\|None` | SELECT | `services/incident_service` |
| `search` | `(conn, query, limit=20)` → `list[dict]` | регистронезависимый поиск | `static/js/incidentCrew.js` |
| `create` | `(conn, full_name, position=None, workshop=None)` → `int` | INSERT | `routes/crew_routes.py`, `static/js/incidentCrew.js` (через /api/crew) |
| `update` | `(conn, crew_id, full_name=None, position=None, workshop=None)` → `bool` | UPDATE | `routes/crew_routes.py::update_crew_route` |
| `is_referenced` | `(conn, crew_id)` → `bool` | guard удаления | `crew_repo.delete` |
| `delete` | `(conn, crew_id)` → `(bool, str\|None)` | DELETE с guard | `routes/crew_routes.py::delete_crew_route` (через `incident_service.delete_crew`) |

### `services/backup_service.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `create_backup` | `()` → `dict` | делегирует в `modules.backup_system.backup.create_backup` | **никто в routes** (используется напрямую `modules/backup_system/backup.py`) |
| `list_backups` | `()` → `list[dict]` | делегирует | **никто** |
| `inspect_uploaded_backup` | `(zip_path: str)` → `dict` | делегирует | **никто** |
| `restore_backup` | `(zip_path: str)` → `dict` | делегирует | **никто** |
| `download_backup` | `(filename: str)` → `str` | делегирует | **никто** |
| `delete_backup` | `(filename: str)` → `bool` | делегирует | **никто** |

> **Находка:** `services/backup_service.py` — dead layer. `routes/backup_routes.py` импортирует `backup` напрямую из `modules/backup_system`. См. раздел 16.

### `services/equipment_location_migration.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `find_or_create_node` | `(conn, name, parent_id, node_type)` → `int` | find-or-create узла | `migrate_equipment_locations`, `find_or_create_root_node` |
| `find_or_create_root_node` | `(conn, name, node_type='workshop')` → `int` | обёртка для корня | `migrate_equipment_locations` |
| `migrate_equipment_locations` | `(conn)` → `dict` | одноразовая миграция equipment.workshop/location → equipment.location_node_id | только `if __name__ == '__main__'` (точка ручного запуска `python -m services.equipment_location_migration`) |
| `__main__` | — | запускает миграцию | (пользователь вручную) |

### `services/export_service.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `export_to_xlsx` | `(conn, ids: list[int])` → `bytes` | экспорт выбранных двигателей в xlsx с фото | `routes/export_routes.py::export_to_excel` |
| `export_incidents_to_xlsx` | `(conn, ticket_ids: list[int])` → `bytes` | плоский экспорт заявок Инцидентов | `routes/incident_ticket_routes.py::export_tickets_route` |
| `export_equipment_to_xlsx` | `(conn, ids: list[int])` → `bytes` | экспорт оборудования в xlsx | `routes/equipment_routes.py::export_equipment_route` |

Также файл содержит много приватных хелперов: `_col_letter`, `_set_wrapped_row_height`, `_build_engine_pages`, `_trp`, `_col_letter_from_index`, константы `INCIDENT_EXPORT_COLUMNS`, `INCIDENT_PRIORITY_LABEL`, `INCIDENT_STATUS_LABEL`, константы страницы (`PAGE_MARGIN_LR`, `PAGE_HEIGHT_PT`, `PAGE_SAFETY_BUFFER_PT`, `FONT_NAME`, `ROW_H_TITLE` и т.д.) — все используются внутри `export_to_xlsx`.

### `services/incident_service.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_now` | `()` → `str` | текущее время в формате ISO | внутри модуля |
| `_resolve_closed_at` | `(old_status, new_status, old_closed_at, explicit_closed_at)` → `str\|None` | правило для `closed_at` при смене статуса | `incident_service.update_ticket` |
| `create_ticket` | `(conn, *, location_node_id, problem, created_by_user_id, solution=None, priority='medium', status='in_progress', initiator_ids=None, executor_ids=None, closed_at=None)` → `(int\|None, str\|None)` | бизнес-валидация + INSERT | `routes/incident_ticket_routes.py::create_ticket_route` |
| `update_ticket` | `(conn, ticket_id, *, location_node_id=None, problem=None, solution=None, priority=None, status=None, initiator_ids=None, executor_ids=None, closed_at=None, closed_at_explicitly_set=False)` → `(bool, str\|None)` | UPDATE с валидацией | `routes/incident_ticket_routes.py::update_ticket_route` |
| `delete_ticket` | `(conn, ticket_id)` → `(bool, str\|None)` | DELETE | `routes/incident_ticket_routes.py::delete_ticket_route` |
| `add_equipment_link` | `(conn, ticket_id, equipment_id)` → `(bool, str\|None)` | добавить связь | `routes/incident_ticket_routes.py::add_equipment_route` |
| `remove_equipment_link` | `(conn, ticket_id, equipment_id)` → `(bool, str\|None)` | удалить связь | `routes/incident_ticket_routes.py::remove_equipment_route` |
| `move_location` | `(conn, node_id, new_parent_id)` → `(bool, str\|None)` | тонкая обёртка над `location_repo.move` | (на момент снимка нет вызывающих в routes) |
| `delete_location` | `(conn, node_id)` → `(bool, str\|None)` | тонкая обёртка над `location_repo.delete` | (на момент снимка нет вызывающих) |
| `delete_crew` | `(conn, crew_id)` → `(bool, str\|None)` | проксирование на `crew_repo.delete` | `routes/crew_routes.py::delete_crew_route` |
| `VALID_PRIORITIES` | `set('low','medium','high')` | whitelist | внутри модуля |
| `VALID_STATUSES` | `set('in_progress','resolved','rejected')` | whitelist | внутри модуля |

### `modules/db.py`

| Функция / константа | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `ENGINE_COLUMNS_ORDERED` | `list[str]` | упорядоченный список колонок `engines` | `repositories/engine_repo`, `schemas/engine_schema`, `static/js/search.js` |
| `ENGINE_COLUMNS` | `frozenset` | то же, но frozenset | `repositories/engine_repo`, `routes/search.py` |
| `MODE_COLUMNS` | `frozenset('frequency','power','voltage','connection_type','current','rpm')` | колонки режима | `repositories/mode_repo`, `schemas/engine_schema`, `routes/search.py` |
| `get_db_connection` | `(db_path=None)` → `Connection` | sqlite3.connect + PRAGMA (WAL, synchronous=NORMAL, foreign_keys=ON), row_factory=sqlite3.Row | `db_connection`, `repositories/*` |
| `db_connection` | `(db_path=None)` → contextmanager `Connection` | обёртка над `get_db_connection` для `with db_connection() as conn:` | повсеместно (routes, services, repositories, tests) |
| `_ensure_column` | `(cursor, table, column, definition)` | авто-миграция: добавляет колонку, если её ещё нет | `init_db` (для engines.created_at/updated_at/status, users.last_login/last_edit, maintenance_works.status, equipment.location_node_id, equipment_type_attribute.show_in_list, equipment_type.min_stock_qty) |
| `init_db` | `(conn=None)` | вся схема + сидинг (admin-пользователь, справочники, 5 записей changelog) | `app.py::if __name__ == '__main__'`, `tests/conftest.py::db_conn` |

> `modules/db.py` дополнительно реэкспортирует константы путей: `DB_PATH`, `MOTORS_FOLDER`, `PHOTOS_FOLDER`, `INCIDENT_PHOTOS_FOLDER`, `EQUIPMENT_PHOTOS_FOLDER`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER`, `ALLOWED_PHOTO_EXT` — все они `from config.settings import …` (строки 9).

### `modules/auth/auth.py` (фасад)

Переэкспортирует **всё** из подмодулей `hashing`, `db_users`, `file_users`, `tokens`, `decorators`. Никакой собственной логики. Содержимое `__all__`: `hash_password`, `verify_password`, `hash_token`, `generate_token`, `create_user`, `get_user_by_username`, `get_user_by_id`, `list_users`, `delete_user`, `update_user_password`, `update_last_login`, `count_users`, `create_file_user`, `delete_file_user`, `update_file_user_password`, `update_file_user_last_login`, `_load_file_users`, `_save_file_users`, `_load_file_tokens`, `_save_file_tokens`, `_next_file_user_id`, `_migrate_negative_file_user_ids`, `FILE_USER_ID_OFFSET`, `FILE_USERS`, `FILE_TOKENS`, `CONFIG_DIR`, `issue_token`, `get_user_from_token`, `revoke_token`, `revoke_all_for_user`, `require_auth`, `require_admin`, `get_current_user`, `_extract_bearer_token`.

### `modules/auth/hashing.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `hash_password` | `(password: str)` → `str` | `werkzeug.security.generate_password_hash` | `db_users.create_user`, `file_users.create_file_user` |
| `verify_password` | `(password: str, password_hash: str)` → `bool` | `werkzeug.security.check_password_hash` | `routes/auth.py::auth_login` |
| `hash_token` | `(token: str)` → `str` | SHA-256 от токена | `tokens.issue_token`, `tokens.get_user_from_token`, `tokens.revoke_token` |
| `generate_token` | `()` → `str` | `secrets.token_urlsafe(32)` | `tokens.issue_token` |

### `modules/auth/db_users.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | private | — |
| `create_user` | `(conn, username, password, role='user')` → `int` | INSERT в `users` | `routes/auth.py` через `auth_module.create_user`, `modules/db.py::init_db` (admin/admin123) |
| `get_user_by_username` | `(conn, username)` → `dict\|None` | DB + fallback в файл | `routes/auth.py::auth_login` |
| `get_user_by_id` | `(conn, user_id)` → `dict\|None` | DB + fallback в файл | `routes/auth.py::auth_me`, `admin_change_password`, `admin_delete_user` |
| `list_users` | `(conn)` → list | DB + file | `routes/auth.py` (через JS `loadAdminUsers`) |
| `delete_user` | `(conn, user_id)` → `bool` | DELETE | `routes/auth.py::admin_delete_user` |
| `update_user_password` | `(conn, user_id, new_password)` → `bool` | UPDATE password_hash | `routes/auth.py::admin_change_password` |
| `update_last_login` | `(conn, user_id)` → `bool` | UPDATE last_login | (нет вызывающих) |
| `count_users` | `(conn)` → `int` | SELECT COUNT(*) | (нет вызывающих) |

### `modules/auth/file_users.py`

| Функция / константа | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `FILE_USER_ID_OFFSET` | `= 1000000000` | offset для file-пользователей | `tokens.issue_token`, `tokens.get_user_from_token`, `_migrate_negative_file_user_ids` |
| `_ensure_config` | `()` | создаёт CONFIG_DIR если нет | `_load_file_users`, `_save_file_users`, `_load_file_tokens`, `_save_file_tokens` |
| `_migrate_negative_file_user_ids` | `(users)` → users list | миграция отрицательных id → FILE_USER_ID_OFFSET | `_load_file_users` |
| `_load_file_users` | `()` → list | чтение `config/users.json` + миграция | `db_users.get_user_by_username`, `db_users.get_user_by_id`, `db_users.list_users` |
| `_save_file_users` | `(users)` | запись `config/users.json` | `create_file_user`, `delete_file_user`, `update_file_user_password`, `_migrate_negative_file_user_ids` |
| `_load_file_tokens` | `()` → list | чтение `config/tokens.json` | `tokens.issue_token`, `tokens.get_user_from_token`, `tokens.revoke_token` |
| `_save_file_tokens` | `(tokens)` | запись `config/tokens.json` | `tokens.issue_token`, `tokens.revoke_token` |
| `_next_file_user_id` | `()` → `int` | следующий свободный id | `create_file_user` |
| `create_file_user` | `(username, password, role='user')` → `int` | создать файл-пользователя | `routes/auth.py::admin_create_user` |
| `delete_file_user` | `(user_id)` → `bool` | DELETE | `routes/auth.py::admin_delete_user` |
| `update_file_user_password` | `(user_id, new_password)` → `bool` | UPDATE | `routes/auth.py::admin_change_password` |
| `update_file_user_last_login` | `(user_id)` → `bool` | UPDATE last_login | (нет вызывающих) |

### `modules/auth/tokens.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_row_to_dict` | `(row)` | private | — |
| `issue_token` | `(conn, user_id, expires_in_days=None)` → `str` | для DB-пользователей сохраняет в таблицу `tokens`, для файловых — в `config/tokens.json` | `routes/auth.py::auth_login` |
| `get_user_from_token` | `(conn, token)` → `dict\|None` | DB tokens + fallback file tokens, проверка expires_at | `routes/auth.py::get_current_user`, `modules/auth/decorators.py::get_current_user` |
| `revoke_token` | `(conn, token)` → `bool` | DELETE в tokens (DB) + удаление из file tokens | `routes/auth.py::auth_logout` |
| `revoke_all_for_user` | `(conn, user_id)` | DELETE tokens для user_id | `routes/auth.py::admin_revoke_user` |

### `modules/auth/decorators.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_extract_bearer_token` | `()` → `str\|None` | парсит Authorization: Bearer или ?token= | `get_current_user` |
| `get_current_user` | `()` → `dict\|None` | user по токену из текущего запроса | (определён в decorators, но **на момент снимка НЕ используется в routes напрямую**; routes/auth.py имеет свою копию; см. раздел 16) |
| `require_auth` | декоратор | 401 если нет токена | (на момент снимка НЕ используется в проекте) |
| `require_admin` | декоратор | 401/403 для не-admin | (на момент снимка НЕ используется; в routes/auth.py есть `_require_admin`/`_require_superadmin`) |

### `modules/engine_parser/parser.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `get_cell_safe` | `(arr, r, c)` → `str` | безопасное чтение значения ячейки (pandas DataFrame → str) | `parse_engine_data`, `parse_maintenance_works` |
| `get_cell_val_safe` | `(arr, r, c)` → `str\|None` | то же, возвращает None вместо "" | `parse_operating_modes`, `parse_maintenance_works` |
| `parse_engine_data` | `(arr, filename)` → `dict` | парсит характеристики из фиксированных координат (ячейки `10,41` для цеха/места, `13,50..30,50` для характеристик) | `parse_file_fast` |
| `parse_operating_modes` | `(arr)` → `list[dict]` | парсит режимы из колонок 50..70 на строках 16..21 | `parse_file_fast` |
| `parse_maintenance_works` | `(arr)` → `list[dict]` | парсит работы, начиная со строки 39, останавливается по пустым строкам | `parse_file_fast` |
| `extract_images_from_excel` | `(file_path, engine_id, log=None)` → `int` | достаёт изображения из Excel через zipfile или openpyxl, сохраняет с именами `ID{engine_id}_{idx+1}.png` | `routes/import_routes.py::import_folder` |
| `parse_file_fast` | `(file_path, log_callback=None)` → `dict` | главная функция пакетного импорта — читает Excel, парсит, возвращает dict с `success, engine_tuple, modes, works, file_path` | `routes/import_routes.py::import_folder` (через ThreadPoolExecutor) |

### `modules/photo_manager/manager.py` (двигатели)

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_photo_paths_cache` | `dict` | кэш путей | внутри модуля |
| `invalidate_photo_cache` | `()` | очистить кэш | (на момент снимка не вызывается из routes; есть заготовка для restore) |
| `_photos_folder` | `()` → `str` | динамически берёт `db_module.PHOTOS_FOLDER` (нужно для тестового monkeypatch) | внутри модуля |
| `engine_photo_disk_paths` | `(engine_id)` → `list[str]` | glob `PHOTOS_FOLDER/ID{engine_id}_*.{ext}` | внутри модуля + `routes/photos.py` |
| `next_photo_index` | `(engine_id)` → `int` | max(существующий) + 1 по regex `ID{engine_id}_(\d+)\.` | внутри модуля |
| `get_engine_photos` | `(engine_id)` → `[{'filename','path'}]` | список фото с URL `/api/photos/...` | `routes/photos.py::get_engine_photos` |
| `get_photo` | `(filename)` → файл или JSON 400/404 | отдать файл с no-cache | `routes/photos.py::get_photo` |
| `upload_engine_photos` | `(conn, engine_id, files)` → `{success, uploaded, skipped, photo_count}` | сохранить File-ы с именами `ID{engine_id}_{n}.{ext}` (n продолжается), обновить `engines.photo_count` | `routes/photos.py::upload_engine_photos` |
| `delete_engine_photo` | `(conn, engine_id, filename)` → JSON | проверка `filename.startswith(f'ID{engine_id}_')`, удаление + обновление photo_count | `routes/photos.py::delete_engine_photo` |
| `delete_engine_photos_from_disk` | `(engine_id)` → `(removed, errors)` | удалить ВСЕ фото двигателя | `routes/engines.py::delete_engine` |
| `replace_engine_photo` | `(engine_id, filename, file_storage)` → `{success, filename, path}` | атомарная перезапись через `_save_upload_atomically` + удаление старого файла при смене расширения | `routes/photos.py::replace_engine_photo` |
| `_save_upload_atomically` | `(file_storage, dest_path, retries=3, delay=0.15)` | временное имя + os.replace (атомарная подмена) | `replace_engine_photo` |
| `ALLOWED_PHOTO_EXT` | `{'.png','.jpg','.jpeg','.gif','.bmp','.webp'}` | whitelist | внутри модуля + `modules/db.py` (реэкспорт) |

### `modules/photo_manager/incident_manager.py` (заявки Инцидентов)

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_photo_paths_cache` | `dict` | кэш путей | — |
| `invalidate_photo_cache` | `()` | очистить кэш | (нет вызывающих) |
| `_photos_folder` | `()` → `str` | `db_module.INCIDENT_PHOTOS_FOLDER` | внутри модуля |
| `ticket_photo_disk_paths` | `(ticket_id)` → `list[str]` | glob `INCIDENT_PHOTOS_FOLDER/ID{ticket_id}_*.{ext}` | внутри модуля |
| `next_photo_index` | `(ticket_id)` → `int` | max + 1 | внутри модуля |
| `get_ticket_photos` | `(ticket_id)` → `[{'filename','path'}]` | список с URL `/api/incident-photos/...` | `routes/incident_ticket_routes.py::get_ticket_route`, `routes/incident_ticket_routes.py::list_ticket_photos_route` |
| `get_photo` | `(filename)` → файл или JSON 400/404 | отдать с no-cache | `routes/incident_photo_routes.py::get_incident_photo_route` |
| `upload_ticket_photos` | `(ticket_id, files)` → JSON | сохранить с именами `ID{ticket_id}_{n}.{ext}` | `routes/incident_ticket_routes.py::upload_ticket_photos_route` |
| `delete_ticket_photo` | `(ticket_id, filename)` → JSON | проверка prefix + delete | `routes/incident_ticket_routes.py::delete_ticket_photo_route` |
| `delete_ticket_photos_from_disk` | `(ticket_id)` → `(removed, errors)` | удалить ВСЕ фото | (нет вызывающих; см. раздел 16) |
| `count_all_photos` | `()` → `int` | дашборд | `routes/status.py::get_status` |

### `modules/photo_manager/equipment_manager.py` (оборудование)

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `_photo_paths_cache` | `dict` | кэш путей | — |
| `invalidate_photo_cache` | `()` | очистить кэш | (нет вызывающих) |
| `_photos_folder` | `()` → `str` | `db_module.EQUIPMENT_PHOTOS_FOLDER` | внутри модуля |
| `equipment_photo_disk_paths` | `(equipment_id)` → `list[str]` | glob `EQUIPMENT_PHOTOS_FOLDER/ID{equipment_id}_*.{ext}` | внутри модуля |
| `next_photo_index` | `(equipment_id)` → `int` | max + 1 | внутри модуля |
| `get_equipment_photos` | `(equipment_id)` → `[{'filename','path'}]` | список с URL `/api/equipment-photos/...` | `routes/equipment_routes.py::get_equipment_photos_route` |
| `get_photo` | `(filename)` → файл или JSON 400/404 | отдать с no-cache | `routes/equipment_photo_routes.py::get_equipment_photo_route` |
| `upload_equipment_photos` | `(equipment_id, files)` → JSON | сохранить с именами `ID{equipment_id}_{n}.{ext}` | `routes/equipment_routes.py::upload_equipment_photos_route` |
| `replace_equipment_photo` | `(equipment_id, filename, file)` → `{success, filename}` | атомарная замена + удаление старого | `routes/equipment_routes.py::replace_equipment_photo_route` |
| `delete_equipment_photo` | `(equipment_id, filename)` → JSON | prefix check + delete | `routes/equipment_routes.py::delete_equipment_photo_route` |
| `delete_equipment_photos_from_disk` | `(equipment_id)` → `(removed, errors)` | удалить ВСЕ фото | (нет вызывающих) |
| `count_all_photos` | `()` → `int` | дашборд | `routes/status.py::get_status` |

### `modules/backup_system/backup.py`

Только самые важные функции (файл 769 строк):

| Функция / константа | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `MAX_BACKUPS_KE` | `= 3` | лимит копий | `_enforce_backup_limit` |
| `_sha256_bytes` | `(data: bytes)` → `hex` | SHA-256 байтов | `_verify_checksums`, `_build_backup_zip_bytes` |
| `_sha256_file` | `(path)` → `hex` | SHA-256 файла потоково | `_build_backup_zip_bytes` |
| `_build_backup_zip_bytes` | `(get_db_connection)` → `(zip_bytes, manifest)` | sqlite3 Online Backup API + zip с manifest.json (SHA256 каждого файла photos/) | `create_backup` |
| `create_backup` | `()` → `dict` | сборка zip, сохранение в BACKUPS_FOLDER, проверка лимита | `routes/backup_routes.py::create_backup` |
| `_enforce_backup_limit` | `(max_count=MAX_BACKUPS_KE)` | удалить самые старые | `create_backup` |
| `_apply_backup_zip` | `(zip_path)` → `dict` | атомарное восстановление с rollback и файловым локом `backup_restore.lock` | `restore_backup` |
| `_safe_backup_filename` | `(filename)` → `str\|None` | regex проверка безопасности | `routes/backup_routes.py` |
| `list_backups` | `()` → `list[dict]` | чтение BACKUPS_FOLDER, manifest из каждого zip | `routes/backup_routes.py::list_backups` |
| `inspect_uploaded_backup` | `(zip_path)` → `dict` | чтение manifest + SHA256 проверка | `routes/backup_routes.py::inspect_uploaded_backup`, `confirm_restore_uploaded_backup` |
| `restore_backup` | `(zip_path)` → `dict` | обёртка для `_apply_backup_zip` | `routes/backup_routes.py::restore_backup`, `confirm_restore_uploaded_backup` |
| `download_backup` | `(filename)` → `str\|None` | путь к файлу | `routes/backup_routes.py::download_backup` |
| `delete_backup` | `(filename)` → `bool` | удаление | `routes/backup_routes.py::delete_backup`, `delete_backup_http_delete` |

### `utils/date.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `format_ru_date` | `(iso_date: str)` → `str` | `YYYY-MM-DD → DD.MM.YYYY` | тесты + фронт (`static/js/common.js::_formatRuDate`) |
| `is_valid_iso_date` | `(date_str)` → `bool` | regex `^\d{4}-\d{2}-\d{2}$` | тесты |

### `utils/file_store.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `load_json` | `(path, default=None)` | безопасная загрузка JSON | **на момент снимка не вызывается из production** (только тесты) |
| `save_json` | `(path, data)` | запись с mkdir | **на момент снимка не вызывается из production** |

### `utils/logging.py`

| Функция / константа | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `log_lock` | `threading.Lock` | блокировка для логов | внутри `log_message` |
| `log_message` | `(message)` | запись в `LOG_FILE` (cp1251-safe) | `routes/import_routes.py::import_folder` |

### `utils/naming.py`

| Функция | Сигнатура | Что делает | Кто вызывает |
| --- | --- | --- | --- |
| `normalize_base_name` | `(filename: str, engine_id: int \| None = None)` → `str` | нормализация имени | **на момент снимка не вызывается из production** (см. раздел 16) |

### Содержимое всех `__init__.py` (для контроля импортов)

| Файл | Содержимое |
| --- | --- |
| `routes/__init__.py` | фабрика blueprint-ов через `create_blueprints()` + `register_blueprints(app)` |
| `modules/__init__.py` | пустой (только `# -*- coding: utf-8 -*-`) |
| `modules/auth/__init__.py` | `from . import auth` |
| `modules/auth/auth.py` | реэкспорт из hashing/db_users/file_users/tokens/decorators (большой `__all__`) |
| `modules/backup_system/__init__.py` | реэкспорт из `backup`: `BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, MAX_BACKUPS_KE, _build_backup_zip_bytes, _save_backup_to_server, _enforce_backup_limit, _apply_backup_zip, _safe_backup_filename` |
| `modules/engine_parser/__init__.py` | реэкспорт `get_cell_safe, get_cell_val_safe, parse_engine_data, parse_operating_modes, parse_maintenance_works, parse_file_fast` |
| `modules/photo_manager/__init__.py` | реэкспорт ТОЛЬКО из `manager.py`: `ALLOWED_PHOTO_EXT, engine_photo_disk_paths, next_photo_index, get_engine_photos, get_photo, upload_engine_photos, delete_engine_photo, delete_engine_photos_from_disk, replace_engine_photo, _save_upload_atomically` |
| `repositories/__init__.py` | только docstring |
| `schemas/__init__.py` | только docstring |
| `services/__init__.py` | только docstring |
| `tests/__init__.py`, `tests/test_backup_system/__init__.py`, `tests/test_repositories/__init__.py`, `tests/test_utils/__init__.py`, `tests/e2e/__init__.py` | пустые |
| `utils/__init__.py` | только docstring |

> **Важное замечание:** `modules/photo_manager/__init__.py` реэкспортирует ТОЛЬКО из `manager.py` (двигатели). Функции `incident_manager.py` и `equipment_manager.py` доступны только как `from modules.photo_manager.incident_manager import ...`. `routes/incident_ticket_routes.py` и `routes/equipment_routes.py` импортируют их явно.

## 6. Backend — константы и конфигурация

### Константы из `config/settings.py`

Точные строки определения (как в файле):

| Константа | Точная строка определения | Через что вычисляется |
| --- | --- | --- |
| `BASE_DIR` | `BASE_DIR = Path(__file__).resolve().parent.parent` | `pathlib.Path` от `config/settings.py` |
| `DB_PATH` | `DB_PATH = str(BASE_DIR / 'engine_data.db')` | BASE_DIR + 'engine_data.db' |
| `MOTORS_FOLDER` | `MOTORS_FOLDER = str(BASE_DIR / 'motors')` | BASE_DIR + 'motors' |
| `PHOTOS_FOLDER` | `PHOTOS_FOLDER = str(BASE_DIR / 'photos')` | BASE_DIR + 'photos' |
| `INCIDENT_PHOTOS_FOLDER` | `INCIDENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoI')` | BASE_DIR + 'PhotoI' |
| `EQUIPMENT_PHOTOS_FOLDER` | `EQUIPMENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoE')` | BASE_DIR + 'PhotoE' |
| `BACKUPS_FOLDER` | `BACKUPS_FOLDER = str(BASE_DIR / 'backups')` | BASE_DIR + 'backups' |
| `BACKUP_STAGING_FOLDER` | `BACKUP_STAGING_FOLDER = str(BASE_DIR / 'backup_staging')` | BASE_DIR + 'backup_staging' |
| `CONFIG_DIR` | `CONFIG_DIR = str(BASE_DIR / 'config')` | BASE_DIR + 'config' |
| `FILE_USERS` | `FILE_USERS = str(BASE_DIR / 'config' / 'users.json')` | BASE_DIR + 'config/users.json' |
| `FILE_TOKENS` | `FILE_TOKENS = str(BASE_DIR / 'config' / 'tokens.json')` | BASE_DIR + 'config/tokens.json' |
| `ALLOWED_PHOTO_EXT` | `ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}` | (set, не вычисляется) |
| `MAX_WORKERS` | `MAX_WORKERS = 4` | (int, не вычисляется) |
| `LOG_FILE` | `LOG_FILE = str(BASE_DIR / 'app.log')` | BASE_DIR + 'app.log' |

### Полная таблица использования констант

Кто импортирует каждую константу пути — пересобрано 2026-09-16 напрямую по коду (`Select-String`/чтение файлов; прежний лог `docs/_usage_scan.txt` на диске отсутствует):

| Константа | Единственное место определения | Кто импортирует (файлы) |
| --- | --- | --- |
| `DB_PATH` | `config/settings.py:25` | `modules/db.py:9` (реэкспорт), `modules/backup_system/backup.py:35` (через `db_module`), `services/backup_service.py:9`, `diag_photos.py:6`, `routes/import_routes.py` (через `db_module.DB_PATH`) |
| `MOTORS_FOLDER` | `config/settings.py:26` | `modules/db.py:9` (реэкспорт), `app.py:15`, `routes/import_routes.py:14` |
| `PHOTOS_FOLDER` | `config/settings.py:27` | `modules/db.py:9` (реэкспорт), `modules/backup_system/backup.py:36` (через `db_module`), `services/backup_service.py:9`, `routes/import_routes.py:14`, `diag_photos.py:4`, `modules/photo_manager/manager.py` (через `db_module`) |
| `INCIDENT_PHOTOS_FOLDER` | `config/settings.py:31` | `modules/db.py:9` (реэкспорт), `modules/backup_system/backup.py:37`, `modules/photo_manager/incident_manager.py` (через `db_module.INCIDENT_PHOTOS_FOLDER`), в списке `PHOTO_FOLDERS` (`settings.py:52`) |
| `EQUIPMENT_PHOTOS_FOLDER` | `config/settings.py:34` | `modules/db.py:9` (реэкспорт), `modules/backup_system/backup.py:38`, `modules/photo_manager/equipment_manager.py` (через `db_module.EQUIPMENT_PHOTOS_FOLDER`), в списке `PHOTO_FOLDERS` (`settings.py:53`) |
| `PHOTO_FOLDERS` | `config/settings.py:50` | `modules/db.py:9` (реэкспорт), `routes/import_routes.py:364-365` (`clear_database`) |
| `BACKUPS_FOLDER` | `config/settings.py:56` | `app.py:15`, `modules/backup_system/backup.py:39` (через `db_module`), `services/backup_service.py:9`, `routes/backup_routes.py` (через `db_module`) |
| `BACKUP_STAGING_FOLDER` | `config/settings.py:57` | `app.py:15`, `modules/backup_system/backup.py:40` (через `db_module`), `services/backup_service.py:9`, `routes/backup_routes.py` (через `db_module`) |
| `CONFIG_DIR` | `config/settings.py:58` | `modules/auth/file_users.py:10` (использование — строки 16-17) |
| `FILE_USERS` | `config/settings.py:59` | `modules/auth/file_users.py:10`, реэкспорт в `modules/auth/auth.py:55` |
| `FILE_TOKENS` | `config/settings.py:60` | `modules/auth/file_users.py:10`, реэкспорт в `modules/auth/auth.py:56` |
| `DATA_DIR`, `CHANGELOG_JSON_PATH`, `WISHLIST_JSON_PATH` | `config/settings.py:64-66` | `routes/changelog.py:22-24` (импорт под алиасами) |
| `ALLOWED_PHOTO_EXT` | `config/settings.py:68` | `modules/db.py:9` (реэкспорт), `modules/photo_manager/manager.py:25`, `incident_manager.py:25`, `equipment_manager.py:28`, `diag_photos.py:4` |
| `MAX_WORKERS` | `config/settings.py:71` | `routes/import_routes.py:17` |
| `LOG_FILE` | `config/settings.py:72` | `utils/logging.py` |

### Другие/дублирующие определения той же константы

Из `Select-String` по всему репозиторию:

| Константа/паттерн | Где ещё определено или упоминается |
| --- | --- |
| `BASE_DIR` | `config/settings.py:10` — ЕДИНСТВЕННОЕ место. В `app.py:15` есть только `from config.settings import ...` (без `BASE_DIR`). |
| `PHOTOS_FOLDER` | `config/settings.py:27` — ЕДИНСТВЕННОЕ место. Все остальные потребители импортируют из `config.settings` или через `db_module.PHOTOS_FOLDER`. |
| `DB_PATH` | `config/settings.py:25` — ЕДИНСТВЕННОЕ место. Используется во всех остальных файлах через импорт. |
| `FILE_USERS`, `FILE_TOKENS`, `CONFIG_DIR` | только `config/settings.py:58-60` + реэкспорт через `modules/auth/auth.py`. Нет дубликатов. |
| `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER` | только `config/settings.py:56-57` + `modules/backup_system/backup.py` (импорт из `db_module`) + `app.py`. Нет дубликатов. |
| `MAX_WORKERS` | `config/settings.py:71` — ЕДИНСТВЕННОЕ место. Используется только в `routes/import_routes.py`. |
| `LOG_FILE` | `config/settings.py:72` — ЕДИНСТВЕННОЕ место. Используется только в `utils/logging.py`. |

### Локальные определения, дублирующие config.settings

- `modules/backup_system/backup.py:35-38` — локально импортируются `DB_PATH`, `PHOTOS_FOLDER`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER` через `db_module.DB_PATH` и т.п. Это **НЕ дубликат**, а проксирование для читаемости.
- `services/backup_service.py:9` — аналогично через прямой импорт из `config.settings`. НЕ дубликат.

> **Находка:** других локальных переопределений путей нигде в проекте нет. Все пути идут только через `config.settings` (напрямую или через `db.py`/`services/backup_service.py`). См. также раздел 16 — про постоянство путей и историю инцидентов с `shutil.rmtree`.

## 7. Контракт имён файлов на диске

### Текущая схема

**`ID{owner_id}_{n}.{ext}`**, где `owner_id` — это `engine_id` для двигателей, `ticket_id` для заявок Инцидентов, `equipment_id` для оборудования. `{n}` — порядковый номер (начиная с 1). `{ext}` — расширение из `ALLOWED_PHOTO_EXT`.

Точные строки реализации:

**Двигатели (`modules/photo_manager/manager.py`):**

```
# строка 6-8 — docstring с описанием схемы
СХЕМА ИМЕНОВАНИЯ: ID{engine_id}_{n}.{ext}, например ID157_1.jpg — первое фото двигателя с id=157

# строка 53 — формирование маски при поиске существующих файлов
pattern = f"ID{engine_id}_*.{ext.lstrip('.')}"

# строка 64 — regex для извлечения номера
pattern = re.compile(rf'^ID{engine_id}_(\d+)\.')

# строка 113 — формат при загрузке (через parser.extract_images_from_excel)
photo_filename = f"ID{engine_id}_{idx+1}.png"
```

**Заявки Инцидентов (`modules/photo_manager/incident_manager.py`):**

```
# строка 53 — маска для поиска
pattern = f"ID{ticket_id}_*.{ext.lstrip('.')}"

# строка 64 — regex
pattern = re.compile(rf'^ID{ticket_id}_(\d+)\.')

# строка 113 — сохранение
photo_filename = f"ID{ticket_id}_{next_idx + saved}{ext}"
```

**Оборудование (`modules/photo_manager/equipment_manager.py`):**

```
# строка 56 — маска для поиска
pattern = f"ID{equipment_id}_*.{ext.lstrip('.')}"

# строка 67 — regex
pattern = re.compile(rf'^ID{equipment_id}_(\d+)\.')
```

### Старая схема (историческая)

В коде упоминается: `{base}img{n}{engine_id}.ext` → новая `ID{engine_id}{n}.ext` (см. раздел 17). В текущем коде нет упоминания старого формата имён файлов — старая схема осталась только в тексте комментариев/документации. См. раздел 17.

### Точки порождения схемы (где создаются файлы)

| Файл | Функция | Строка | Что делает |
| --- | --- | --- | --- |
| `modules/photo_manager/manager.py` | `upload_engine_photos` | `photo_filename = f"ID{engine_id}_{next_idx + saved}{ext}"` | Сохранение с инкрементом |
| `modules/engine_parser/parser.py` | `extract_images_from_excel` | `photo_filename = f"ID{engine_id}_{idx+1}.png"` | Извлечение из Excel при импорте |
| `modules/photo_manager/incident_manager.py` | `upload_ticket_photos` | `photo_filename = f"ID{ticket_id}_{next_idx + saved}{ext}"` | Сохранение заявки Инцидента |
| `modules/photo_manager/equipment_manager.py` | (нет функции загрузки через эту схему напрямую, см. `routes/equipment_routes.py::upload_equipment_photos_route` → `equipment_manager.upload_equipment_photos`) | — | — |

### Точки парсинга схемы (где имя файла интерпретируется)

| Файл | Функция | Строка | Что делает |
| --- | --- | --- | --- |
| `modules/photo_manager/manager.py` | `engine_photo_disk_paths` | `pattern = f"ID{engine_id}_*.{ext.lstrip('.')}"` | Поиск существующих фото двигателя |
| `modules/photo_manager/manager.py` | `next_photo_index` | `pattern = re.compile(rf'^ID{engine_id}_(\d+)\.')` | Извлечение номера для инкремента |
| `modules/photo_manager/manager.py` | `replace_engine_photo` | `if not filename.startswith(f'ID{engine_id}_'):` | Проверка префикса перед заменой |
| `modules/photo_manager/incident_manager.py` | `ticket_photo_disk_paths` | `pattern = f"ID{ticket_id}_*.{ext.lstrip('.')}"` | Поиск |
| `modules/photo_manager/incident_manager.py` | `delete_ticket_photo` | `if not filename.startswith(f'ID{ticket_id}_'):` | Проверка префикса |
| `modules/photo_manager/equipment_manager.py` | `equipment_photo_disk_paths` | `pattern = f"ID{equipment_id}_*.{ext.lstrip('.')}"` | Поиск |
| `modules/photo_manager/equipment_manager.py` | `replace_equipment_photo`, `delete_equipment_photo` | `if not filename.startswith(f'ID{equipment_id}_'):` | Проверка префикса |

### Файлы, не входящие в эту схему

- `templates/` — `index.html`, `print.html`, `print_equipment.html`, `print_incident.html` — имена захардкожены, по `ID` не парсятся.
- `static/js/*.js`, `static/css/*.css`, `static/ico/*.svg` — статические файлы.
- `app.py`, `engine_data.db` (имя `engine_data.db` фиксировано в `config/settings.py:25`).
- `index.html`, `mockup.html`, `measurement.py`, `diag_*.py`, `test_mode_repo.py` — корневые (`promote_and_cleanup.py` в проекте нет).

### Дублирование логики схемы

Все три photo_manager реализуют **одну и ту же** логику (`glob` + regex) для своей сущности (двигатель/заявка/оборудование). Это повторение упоминается в `modules/photo_manager/incident_manager.py:1-19` и `equipment_manager.py:1-22` как осознанный выбор: "та же дисковая схема, что и modules/photo_manager/manager.py".

> **Находка:** три отдельные реализации `*_disk_paths`/`next_photo_index` фактически дублируют код. Единый общий хелпер (например, `glob_id_photos(folder, owner_id)`) мог бы устранить повторение, но не реализован — см. раздел 16.

### Различие между папками (избежание коллизий имён файлов)

Так как `ID{owner_id}_{n}.{ext}` может совпадать между сущностями (например, `ID7_1.png` существует и для `engine_id=7`, и для `ticket_id=7`, и для `equipment_id=7`), файлы хранятся в **РАЗНЫХ** папках:

- Двигатели → `photos/`
- Заявки Инцидентов → `PhotoI/`
- Оборудование → `PhotoE/`

Это явно зафиксировано в комментариях `config/settings.py:28-34`:

```
# Фото-вложения заявок "Инцидентов" — отдельная папка от PHOTOS_FOLDER
# (тот принадлежит двигателям, ID{engine_id}_{n}.ext) во избежание
# коллизий имён файлов между двумя разными сущностями с ID-неймингом.
INCIDENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoI')
# Фото номенклатуры оборудования (ТЗ "Инциденты + Оборудование", раздел 3.3) —
# та же логика обособления, что и у PhotoI.
EQUIPMENT_PHOTOS_FOLDER = str(BASE_DIR / 'PhotoE')
```

Путь к файлу в URL также различается:
- `/api/photos/ID{engine_id}_{n}.{ext}` — двигатели (`routes/photos.py::get_photo`)
- `/api/incident-photos/ID{ticket_id}_{n}.{ext}` — заявки (`routes/incident_photo_routes.py`)
- `/api/equipment-photos/ID{equipment_id}_{n}.{ext}` — оборудование (`routes/equipment_photo_routes.py`)

## 8. Жизненный цикл ID записей

### engines

В схеме БД: `id INTEGER PRIMARY KEY AUTOINCREMENT` (`modules/db.py:73`). Формально SQLite AUTOINCREMENT гарантирует только монотонный рост (не переиспользование удалённых id). Однако **фактическое поведение переиспользования** реализовано вручную в `repositories/engine_repo.py::create()` — процитировано ниже.

> **Требует уточнения:** На момент снимка я **не смог полностью прочитать `engine_repo.create()` в одном блоке** — файл читался по частям. По коду `repositories/engine_repo.py::create` (docstring + `_next_free_id(conn)`) для двигателей используется **явный поиск минимального свободного id** (а не чистый AUTOINCREMENT/lastrowid), чтобы при удалении id переиспользовались. Поведение, как описано в TASK:
>
> - **id при создании:** явный поиск минимального свободного id (см. `engine_repo.create`).
> - **id при удалении:** физически удаляется (`repositories/engine_repo.py::delete` — DELETE modes + DELETE works + DELETE engine). Последовательность sqlite_sequence НЕ уменьшается сама; но `engine_repo.create` ищет `MIN(id) WHERE id NOT IN (used_ids)` — поэтому удалённый id будет переиспользован при следующем create.
> - **Массовый импорт:** рассчитан на на пустую БД (см. комментарий `routes/import_routes.py:85` — "ПРОВЕРКА: массовый импорт рассчитан только на пустую БД"). Конкретная проверка — после первого `parse_file_fast` есть `INSERT INTO engines`, и в самом начале `import_folder` явно проверяется наличие файлов и используется логика "first_id = last_insert_rowid() − count" (см. комментарий в `import_routes.py:86`). **Требует уточнения:** на момент снимка я не смог прочитать эту часть полностью; **предположительно проверка "на пустую БД" НЕ выполняется в коде**, что означает: импорт в непустую БД может привести к конфликту id (если auto-increment секвенсер уже занят).

### equipment

| Событие | Поведение |
| --- | --- |
| Создание | `repositories/equipment_repo.py::create_equipment` — INSERT, AUTOINCREMENT/lastrowid |
| Удаление | `delete_equipment` — DELETE; cascade срабатывает для `equipment_type_attribute`; `specs_json` остаётся просто удалённой строкой |
| Массовый импорт | НЕТ (нет импорта оборудования) |

### incident_ticket

- `id INTEGER PRIMARY KEY AUTOINCREMENT` (`db.py:394`).
- Создание: через AUTOINCREMENT/lastrowid.
- Удаление: только superadmin, через `services/incident_service.delete_ticket`.
- Без переиспользования.

### location_node, crew, equipment_type, attribute_definition, equipment_type_attribute

Все используют обычный `INTEGER PRIMARY KEY AUTOINCREMENT` через `lastrowid`. Никаких особых правил переиспользования нет — удалённые id остаются "дырами" в нумерации (если не сбрасывать `sqlite_sequence`).

### tokens, files_user (id в `users` и `FILE_USER_ID_OFFSET`)

- DB-пользователи: AUTOINCREMENT, начинаются с 1.
- Файловые пользователи: id всегда ≥ `FILE_USER_ID_OFFSET = 1000000000` (`modules/auth/file_users.py:12`). Это гарантирует, что id файловых пользователей не пересекаются с id DB-пользователей и проходят через Flask `<int:user_id>` (конвертер Flask матчит только `\d+`, не отрицательные числа).
- Если в файле оказывается отрицательный id (старый формат), то `_migrate_negative_file_user_ids` (`modules/auth/file_users.py:20-44`) при каждой загрузке `users.json` молча переприсваивает им id ≥ `FILE_USER_ID_OFFSET`.

## 9. Обслуживание БД

### Очистка БД (`POST /api/clear`)

> **Обновление 2026-09-16 — реализация полностью изменилась.** Прежняя версия раздела описывала ручные `DELETE FROM ...` + `VACUUM`. Сейчас `routes/import_routes.py::clear_database` (строка 221) **удаляет файл БД целиком** и пересоздаёт схему через `db_module.init_db()` — тогда новые таблицы подхватываются автоматически, без правки списка `DELETE FROM`. Шаги:

1. Читаются и сохраняются в память строки `users` и `tokens` (чтобы админ мог снова войти).
2. Удаляются файлы `engine_data.db`, `engine_data.db-wal`, `engine_data.db-shm` (retry до 5 раз на Windows `PermissionError`; при неудаче — `{success: false, error}` 500 без изменений).
3. Вызывается `db_module.init_db()` — создаются все таблицы заново + досеиваются справочники (`equipment_type`, `attribute_definition`, `equipment_type_attribute`).
4. Сохранённые `users` и `tokens` возвращаются обратно (`INSERT`).
5. Фото-папки очищаются по списку `PHOTO_FOLDERS` из `config.settings` (`photos/`, `PhotoI/`, `PhotoE/`).

Возвращает `{success: true, message: ...}` или `{error: str}` с кодом 500.

### Что НЕ очищается при `/api/clear`

- `users` (пользователи) и `tokens` (сессии) — сохраняются и возвращаются обратно (единственное исключение, by design).
- Журнал изменений и wishlist — это отдельные JSON-файлы `data/changelog.json`, `data/wishlist.json`; очистка БД их не касается (таблиц `changelog_entries`/`wishlist_items` в схеме вообще нет).

**Всё остальное теряется безвозвратно** (пересоздаётся пустым): `engines` (+modes/works), `audit_log`, вся подсистема инцидентов (`incident_ticket*` и связанные), номенклатура оборудования (`equipment*`), `crew`, `location_node`. Прежняя версия документа ошибочно утверждала, что номенклатура, оборудование и инциденты «не удаляются».


### Защита через prompt на фронте (`static/js/importer.js::confirmClearDatabase`)

```js
const confirmation = prompt(
    `Это удалит ${engineCount} двигателей и ${photoCount} фото безвозвратно.\nВведите СТИРАТЬ для подтверждения:`
);
if (confirmation === 'СТИРАТЬ') {
    clearAll();
}
```

Пользователь ОБЯЗАН ввести слово «СТИРАТЬ» (кириллица, верхний регистр) — защита от случайной потери данных (см. раздел 17).

### Параметры журналирования SQLite

В `modules/db.py::get_db_connection`:

```python
conn.execute('PRAGMA journal_mode=WAL')           # Write-Ahead Logging
conn.execute('PRAGMA synchronous=NORMAL')        # fsync только при checkpoint
conn.execute('PRAGMA foreign_keys=ON')            # enforce FK-constraints
```

Журналирование переключается только при создании соединения (т.е. через `get_db_connection()` или `db_connection()`). Прямой вызов `sqlite3.connect(DB_PATH)` в `diag_photos.py:6` НЕ включает `journal_mode=WAL` и `foreign_keys=ON` (см. раздел 16). Раньше здесь упоминался `promote_and_cleanup.py:26` — файла в проекте нет.

### Очистка staging-папки бэкапов

`routes/backup_routes.py::confirm_restore_uploaded_backup` (строки 152-155):

```python
try:
    os.remove(staging_path)
except OSError:
    pass
```

Файл из `BACKUP_STAGING_FOLDER` удаляется после успешного restore. В остальных случаях staging может накапливаться.

## 10. Frontend — файлы и назначение

Файлы подключаются через `<script src="/static/js/...">` в `templates/index.html` в порядке (см. файл).

| Файл | Назначение |
| --- | --- |
| *(нет такого файла)* | **`static/js/api.js` и `static/js/app.js` в проекте отсутствуют** (сверено 2026-09-16). Прежняя версия документа описывала раннюю архитектуру с глобалами `window.Api` (API-клиент) и `window.App` (точка входа). Сейчас: API-обёртка — `apiFetch()` в `auth.js`, инициализация страницы — инлайн-скрипт в конце `index.html` + `authInit()` из `auth.js`, переключение табов — `switchTab()` в `catalog.js`. |
| `static/js/auth.js` | **Авторизация клиента**: константы `AUTH_TOKEN_KEY='motors_auth_token'`, `AUTH_USER_KEY='motors_auth_user'`. `getAuthToken/setAuthToken/clearAuth/getAuthUser`. `authPhotoUrl(path)` — добавляет `?token=` к URL для тега `<img>`. `apiFetch()` — обёртка над fetch с автоматической подстановкой Bearer, на 401 — `clearAuth() + location.reload()`. `parseJsonResponse`. `hideAppLoadingOverlay()`. UI-функции вкладки Админ |
| `static/js/common.js` | **Общие утилиты**: `escapeHtml`, `escapeAttr`, `debounce`, `highlightMatch`, `applyTheme`. Поля и утилиты карточки: `DETAIL_CHAR_FIELDS`, `PRINT_CHAR_FIELDS`, `_formatRuDate`, `formatRuDateTime`, `toggleModalMaximize`, `showToast`, `attachEntitySuggest`, `initPanelResizer` |
| *(нет такого файла)* | **`static/js/state.js` в проекте отсутствует** (сверено 2026-09-16). Глобального store `window.State` нет — состояние каталога живёт в плоских переменных `engines.js` и `locationTree.js` (см. раздел 11). |
| `static/js/catalog.js` | **Каталог**: `updateStats`, `loadSettings`, переключение вкладок, `loadEngines`, `applyDynamicPageSize`, `renderTable`, `navigateEngine`, `editEngine`, `deleteEngine`, сортировка, поиск с debounce, экспорт через `POST /api/engines/export` |
| `static/js/engines.js` | **Двигатели**: глобалы `currentPage`, `allEngines`, `currentSort`, `currentEngineId`, `currentPhotos`, `currentEngineData`, `detailEditMode`, `detailPhotoFiles`, `pendingPhotoFiles`, `selectedEngineIds`, `photoCacheBust`. `attachSuggestDropdown`, клавиатурная навигация (ArrowLeft/Right) |
| `static/js/engineCard.js` | **Детальная карточка двигателя**: `showDetail/closeDetail/renderDetailContent`, `navigateEngine`, `editEngine`, `openPhotoAddModal/closePhotoAddModal/renderDetailPhotoPreview/submitDetailPhotoAdd`, обрезка фото (`openCropModal`/`_openCropStage` и т.п.) |
| `static/js/exportManager.js` | **Форма добавления двигателя**: `renderPhotosPreview/removePendingPhoto/uploadPendingPhotos/resetForm/saveEngine`, `addModeRow/addWorkRow/collectRows` |
| `static/js/importer.js` | **Импорт + очистка**: `importFiles` (POST /api/import-folder), `clearAll` (POST /api/clear), `confirmClearDatabase` (с prompt 'СТИРАТЬ') |
| `static/js/equipment.js` | **Вкладка Оборудование**: глобалы `equipmentTypesCache`, `allEquipment`, `equipmentCurrentSort`, `equipmentCurrentPage`, `equipmentPendingPhotoFiles` и т.д. `loadEquipmentTab/switchEquipmentSubtab`, CRUD типов/атрибутов/оборудования, экспорт |
| `static/js/equipmentLocationTree.js` | **Дерево Оборудования**: `equipmentActiveLocationId`, `equipmentLocationCounts`, `equipmentCollapsedLocationIds`. `loadEquipmentLocationTree/renderEquipmentLocationTree/toggleEquipmentLocationNode/selectEquipmentLocation` |
| `static/js/equipmentPrint.js` | **Печать оборудования**: `getEquipmentIdFromUrl/renderEquipmentCharacteristics/renderEquipmentPhotos/renderEquipmentPage/waitForEquipmentImages/loadAndRenderEquipment` |
| `static/js/incidentCrew.js` | **Справочник людей**: `attachCrewTagInput` (тег-инпут), `editCrewMember/deleteCrewMember` |
| `static/js/incidentLocations.js` | **Дерево мест Инцидентов + пикер**: `LOCATION_NODE_TYPE_LABELS`. `attachLocationPicker/openCreateLocationWizard/loadLocationDictionary/addChildLocationNode/createRootLocationNode/renameLocationNode/deleteLocationNode` |
| `static/js/incidentLocationTree.js` | **Дерево Инцидентов**: `incidentActiveLocationId`, `incidentLocationCounts`, `incidentCollapsedLocationIds`. `loadIncidentLocationTree/renderIncidentLocationTree/toggleIncidentLocationNode/selectIncidentLocation` |
| `static/js/incidentPrint.js` | **Печать заявки Инцидента**: `getIncidentTicketIdFromUrl`, `INCIDENT_PRINT_PRIORITY_LABEL/STATUS_LABEL`, рендеринг |
| `static/js/incidents.js` | **Вкладка Инциденты (журнал)**: `INCIDENT_PRIORITY_LABEL/STATUS_LABEL`. Глобалы `incidentsList`, `currentIncidentId`, `incidentLocationPicker`, `incidentInitiatorsTag/ExecutorsTag`, `incidentEquipmentSelected`, `incidentPendingLinks`, `incidentPendingPhotoFiles`, `incidentEditPhotos`, `incidentEditLinks`, `incidentSelectedExportIds`. CRUD, листание, экспорт |
| `static/js/locationTree.js` | **Дерево Цех→Место на Каталоге**: `activeWorkshop`, `activeLocation`, `pendingNewEngineId`. `createAndOpenEngine/loadLocationTree/renderLocationTree/toggleTreeWorkshop/selectTreeLocation/resetLocationFilter` |
| `static/js/print.js` | **Печать двигателя**: `getEngineIdFromUrl/renderCharacteristics/renderModesTable/renderWorksTable/renderPhotos/renderPage/waitForImages/loadAndRender` |
| `static/js/search.js` | **Расширенный поиск**: `SEARCH_FIELDS` (массив `{value,label,type,operatorType?}`), `OPERATORS_TEXT/NUMBER`. `executeSearch/_renderSearchResultsTable`. Поиск перезаписывает `allEngines` (сохраняется в `originalAllEngines`) |
| `static/js/backup.js` | **Вкладка «Настройки → Бэкапы»**: `_formatBackupSize/loadBackupsList/renderBackupsList/createBackup/downloadBackup/deleteBackupFile/restoreServerBackup` |
| `static/js/info.js` | **Вкладка «Инфо»**: `switchInfoSubtab/loadInfoTab/loadSystemInfo`, changelog — `loadChangelog/renderChangelog`, wishlist — `loadWishlist/renderWishlist/addWishlistItem/toggleWishlistItem/deleteWishlistItem` (данные — JSON-эндпоинты `/api/changelog`, `/api/wishlist`) |
| `static/js/audit.js` | **Таб «Аудит»**: `loadAuditTab/loadAuditEntityTypes/loadAuditEntries/renderAuditTable/applyAuditFilters/resetAuditFilters/auditPrevPage/auditNextPage`, `_auditSectionLabel/_auditFilterParams` (`GET /api/audit/log`, `/api/audit/entity-types`) |

> **Файла `static/js/backupManager.js` в проекте нет** (сверено 2026-09-16) — его функции разделены между `backup.js` (бэкапы) и `info.js` (changelog/wishlist).

> **Три дерева мест:** `locationTree.js` (старое — текстовые `workshop/location` у engines, на вкладке Каталог), `equipmentLocationTree.js` (новое — таблица `location_node` на вкладке Оборудование), `incidentLocationTree.js` (то же дерево на вкладке Инциденты). Все три используют общий ресурс `location_node` (последние два), но потребляют по-разному — фильтрация списка заявок/оборудования vs. навигация по дереву.

## 11. Frontend — глобальные переменные

Все глобальные переменные фронтенда (`static/js/*.js`), кроме стандартных `window`, `document`, `localStorage`. Поиск проведён вручную по содержимому JS-файлов + по ключевым словам из задания.

### Глобалы каталога/двигателей (catalog.js, engines.js, engineCard.js)

| Имя | Объявлен в | Что | Кто пишет/читает |
| --- | --- | --- | --- |
| `allEngines` | `engines.js:4` | весь список двигателей | пишут: `loadEngines()`, `search.js::executeSearch` (перезаписывает результатами поиска с сохранением в `originalAllEngines`); читают: `navigateEngine`, `renderTable`, `engineCard.renderDetailContent` |
| `currentPage` | `engines.js:2` | текущая страница | пишут: `catalog.js::switchTab` (нет), поиск/sort/пагинация; читают: `loadEngines`, `renderTable` |
| `pageSize` | `engines.js:3` | размер страницы (старт 20) | `applyDynamicPageSize` пересчитывает под высоту |
| `currentSort` | `engines.js:5` | `{field, order}` | пишут: `catalog.js::sortSelect.onchange`; читают: `loadEngines`, `search.js::searchSort` |
| `currentSearchField` | `engines.js:6` | `'all'` или имя поля | `searchFieldSelect.onchange`; `loadEngines` |
| `currentEngineId` | `engines.js:9` | текущий id в карточке | `showDetail`, `navigateEngine`, `submitDetailPhotoAdd` |
| `currentPhotos` | `engines.js:10` | список фото двигателя | `showDetail`, `submitDetailPhotoAdd` |
| `currentPhotoIndex` | `engines.js:11` | индекс в `currentPhotos` | `navigatePhotoModal` |
| `currentEngineData` | `engines.js:12` | данные открытой карточки | `renderDetailContent`, `saveDetailEdit` |
| `detailEditMode`, `detailMode` | `engines.js:13-14` | флаги режима | `renderDetailContent` |
| `detailPhotoFiles` | `engines.js:15` | File[] ещё не загруженные | `openPhotoAddModal`, `submitDetailPhotoAdd` |
| `pendingPhotoFiles` | `engines.js:29` | File[] для нового двигателя | `exportManager.js::f_photos.change`, `saveEngine` |
| `selectedEngineIds` | `engines.js:30` | `Set` id выбранных для экспорта | `catalog.js::toggleEngineSelection`, `exportSelected` |
| `photoCacheBust` | `engines.js:22` | `Date.now()` для cache-busting | `submitDetailPhotoAdd` (обновляется только при реальных изменениях на диске) |

### Глобалы дерева на Каталоге (locationTree.js)

| Имя | Что |
| --- | --- |
| `activeWorkshop` | выбранный узел-цех (или null) |
| `activeLocation` | выбранное место (или null) |
| `pendingNewEngineId` | id двиг. созданного через "+", но не сохранённого |

### Глобалы оборудования (equipment.js, equipmentLocationTree.js)

| Имя | Что |
| --- | --- |
| `equipmentTypesCache`, `attributeDefinitionsCache`, `currentConstructorTypeId`, `equipmentFormLocationPicker`, `allEquipment`, `equipmentCurrentSort`, `equipmentCurrentPage`, `equipmentPageSize`, `equipmentShowInListAttrs`, `equipmentPendingPhotoFiles`, `equipmentExistingPhotos`, `equipmentSelectedExportIds` | состояние вкладки Оборудование |
| `equipmentActiveLocationId`, `equipmentLocationCounts`, `equipmentLocationNodesFlat`, `equipmentCollapsedLocationIds` | состояние дерева |

### Глобалы инцидентов

| Имя | Что |
| --- | --- |
| `INCIDENT_PRIORITY_LABEL`, `INCIDENT_STATUS_LABEL`, `INCIDENT_PRINT_PRIORITY_LABEL`, `INCIDENT_PRINT_STATUS_LABEL` | словари локализации |
| `incidentsList`, `currentIncidentId`, `currentIncidentData` | состояние журнала |
| `incidentLocationPicker`, `incidentInitiatorsTag`, `incidentExecutorsTag`, `incidentSelectedPriority`, `incidentSelectedStatus`, `incidentEquipmentSelected`, `incidentPendingLinks`, `incidentPendingPhotoFiles`, `incidentEditPhotos`, `incidentEditLinks`, `incidentSelectedExportIds` | состояние формы/карточки |
| `LOCATION_NODE_TYPE_LABELS`, `_locationDictNodes`, `_crewDictItems` | состояние справочников |
| `incidentActiveLocationId`, `incidentLocationCounts`, `incidentLocationNodesFlat`, `incidentCollapsedLocationIds` | состояние дерева Инцидентов |

### Глобалы поиска (search.js)

| Имя | Что |
| --- | --- |
| `SEARCH_FIELDS`, `OPERATORS_TEXT`, `OPERATORS_NUMBER`, `DEFAULT_RESULT_FIELDS` | конфигурация UI поиска |
| `searchSort`, `originalAllEngines` | состояние поиска |

### Прочее

| Имя | Что |
| --- | --- |
| `cropState` (engineCard.js) | `{list, index, image, sel, ...}` для обрезки |
| `wishlistItems` (info.js) | кэш пожеланий |

### Глобалы общего state

| Имя | Что |
| --- | --- |
| *(нет)* | `window.State` / `window.Api` / `window.App` в проекте **отсутствуют** — файлов `state.js`, `api.js`, `app.js` нет (сверено 2026-09-16) |
| `authPhotoUrl`, `getAuthUser`, `getAuthToken`, `setAuthToken`, `clearAuth`, `apiFetch` | функции auth.js |
| `escapeHtml`, `escapeAttr`, `debounce`, `highlightMatch`, `applyTheme`, `INITIAL_THEME`, `DETAIL_CHAR_FIELDS`, `PRINT_CHAR_FIELDS`, `_formatRuDate`, `formatRuDateTime`, `toggleModalMaximize`, `showToast`, `attachEntitySuggest`, `attachFieldAutocomplete`, `initPanelResizer`, `toggleDetailMaximize` | функции common.js |

### Глобалы localStorage

| Ключ | Что |
| --- | --- |
| `motors_auth_token` | opaque Bearer token |
| `motors_auth_user` | JSON user dict |
| `motors_theme` | `'dark'` для CSS dark-mode |

### Заметки

- `window.closeTimeout` (engineCard.js) — глобальный таймер cleanup анимации slide-out.
- `URL.createObjectURL`/`URL.revokeObjectURL` (стандарт) — для превью фото.

## 12. Frontend — ключевые функции

Только функции, вызываемые извне (onclick в HTML или из другого JS). Приватные хелперы не включены.

| Функция | Файл | Что делает | Откуда вызывается |
| --- | --- | --- | --- |
| `attachEntitySuggest` | `common.js` | Универсальный dropdown: position:fixed, поиск через `searchFn`, создание нового через `onCreateNew`. Защита от двойного биндинга через `dataset.autocompleteBound` | `engines.js::attachFieldAutocomplete`, `incidentLocations.js::attachLocationPicker`, `incidentCrew.js::attachCrewTagInput` |
| `attachFieldAutocomplete` | `engines.js` | `attachSuggestDropdown(inputEl, fieldName)` | `attachSuggestDropdown` в той же `engines.js`; `exportManager.js::addModeRow` |
| `attachSuggestDropdown` | `engines.js` | Кастомный dropdown для автоподсказок | `attachFieldAutocomplete`, прямые вызовы |
| `debounce` | `common.js` | Стандартный debounce | повсеместно |
| `escapeHtml`, `escapeAttr`, `highlightMatch`, `applyTheme`, `showToast`, `formatRuDateTime`, `toggleModalMaximize` | `common.js` | Экранирование/UI | из HTML и из других JS |
| `toggleDetailMaximize` | `engineCard.js` | fullscreen toggle карточки двигателя | `onclick="toggleDetailMaximize()"` в index.html |
| `initPanelResizer` | `common.js` | drag-resizer для боковых панелей | `catalog.js`, `equipment.js`, `incidentLocationTree.js`, `incidentLocations.js` |
| *(нет)* | `app.js` / `api.js` в проекте отсутствуют — загрузку данных выполняют `auth.js::authInit`, `catalog.js::loadEngines`, `backup.js::loadBackupsList`, `info.js::loadChangelog/loadWishlist` | — | — |
| `authInit/showLoginScreen/clearAuth/getAuthUser/getAuthToken/setAuthToken/authPhotoUrl/apiFetch/parseJsonResponse/hideAppLoadingOverlay` | `auth.js` | авторизация | init приложения |
| `loadAdminUsers/adminCreateUser/adminChangePassword/adminDeleteUser/adminRevokeUser/promptChangePassword` | `auth.js` | UI админки | `onclick="..."` в index.html |
| `updateStats/loadSettings/switchTab/loadEngines/applyDynamicPageSize/toggleEngineSelection/exportSelected/navigateEngine/editEngine/deleteEngine/sortSelect.onchange` | `catalog.js` | UI каталога | `onclick`/`onchange` в index.html |
| `loadLocationTree/toggleTreeWorkshop/selectTreeLocation/createAndOpenEngine/resetLocationFilter` | `locationTree.js` | Дерево Цех→Место | `onclick` в HTML |
| `loadEquipmentTab/loadEquipmentTypes/loadAttributeDefinitions/loadEquipmentLocationTree/loadEquipmentList/loadStockSummary/selectEquipmentLocation/resetEquipmentLocationFilter/createEquipmentType/...` | `equipment.js`, `equipmentLocationTree.js` | UI вкладки Оборудование | `onclick`/`onchange` в HTML |
| `loadIncidentsTab/loadIncidentsList/openIncidentModal/closeIncidentModal/renderIncidentDetailToolbar/navigateIncident/createIncidentAtLocation/submitIncident/printIncident/deleteCurrentIncident/...` | `incidents.js` | UI вкладки Инциденты | `onclick` в HTML |
| `executeSearch/resetSearch/_renderSearchResultsTable` | `search.js` | Расширенный поиск | `onclick="executeSearch()"` в HTML |
| `loadBackupsList/createBackup/restoreServerBackup/downloadBackup/deleteBackupFile` | `backup.js` | UI бэкапов | `onclick` в HTML настроек |
| `loadChangelog/loadWishlist/addWishlistItem/toggleWishlistItem/deleteWishlistItem/switchInfoSubtab/loadSystemInfo` | `info.js` | UI вкладки Инфо | `onclick` в HTML |
| `loadAuditTab/loadAuditEntries/applyAuditFilters/resetAuditFilters/auditPrevPage/auditNextPage` | `audit.js` | Таб «Аудит» | `onclick` в HTML |
| `showDetail/closeDetail/renderDetailContent/navigateEngine/editEngine/openPhotoAddModal/closePhotoAddModal/renderDetailPhotoPreview/submitDetailPhotoAdd/removeDetailPendingPhoto/openCropModal/closeCropModal` | `engineCard.js` | Карточка двигателя | `onclick` в HTML |
| `renderPhotosPreview/removePendingPhoto/uploadPendingPhotos/resetForm/saveEngine/addModeRow/addWorkRow/collectRows` | `exportManager.js` | Форма добавления | `onclick`/`oninput`/`submit` в HTML |
| `importFiles/clearAll/confirmClearDatabase` | `importer.js` | Импорт + очистка | `onclick` в HTML импорта |
| `getEngineIdFromUrl/renderCharacteristics/renderModesTable/renderWorksTable/renderPhotos/renderPage/waitForImages/loadAndRender` | `print.js` | Печать двигателя | `print.html::DOMContentLoaded` |
| `getEquipmentIdFromUrl/renderEquipmentCharacteristics/renderEquipmentPhotos/renderEquipmentPage/waitForEquipmentImages/loadAndRenderEquipment` | `equipmentPrint.js` | Печать оборудования | `print_equipment.html::DOMContentLoaded` |
| `getIncidentTicketIdFromUrl/renderIncidentField/renderIncidentLinks/renderIncidentPhotos/renderIncidentPage/waitForIncidentImages/loadAndRenderIncident` | `incidentPrint.js` | Печать заявки | `print_incident.html::DOMContentLoaded` |

### Обработчик глобальных клавиш

`engines.js:163-254` — `document.addEventListener('keydown', ...)`: обрабатывает стрелки ◀/▶ и Escape для активных модалок (`photoModal`, `detailModal`, `equipmentModal`, `incidentTicketModal`). Не перехватывает стрелки, если фокус внутри `input/textarea/contenteditable`.

## 13. UI-компоненты → файлы

Для каждого визуального блока: HTML-расположение в `templates/`, JS-файл управления, CSS-секция.

### Верхняя панель (topbar), вкладки, экран логина

- HTML: `templates/index.html` — `.topbar`, `.topbar-brand`, `.topbar-nav` (кнопки вкладок `data-tab`), `.topbar-stats` (`#totalEngines`, `#totalPhotos`), `.theme-toggle-btn` (`#themeToggleBtn`), `.topbar-user` (`#userName`, `#logoutBtn`). `<div id="loginScreen" class="hidden">...</div>` с `<form id="loginForm">`.
- JS: `static/js/auth.js::loadCurrentUser/handleLogin/authInit`, `static/js/common.js::applyTheme/INITIAL_THEME`, `static/js/catalog.js::switchTab`.
- CSS: `static/css/style.css` — `.topbar*`, `.tab-btn`, `.tab-content`, `.login-screen`.

### Каталог двигателей: таблица, сортировка, поиск, дерево, тулбар

- HTML: `templates/index.html` — `.catalog-layout`, `.catalog-left` (дерево мест `#locationTreeBody`), `.catalog-divider`, `.catalog-right` (таблица `#enginesTableBody`, пагинация `#pagination`, тулбар `#sortSelect`, `#searchInput`, `#searchFieldSelect`).
- JS: `static/js/locationTree.js` (дерево), `static/js/catalog.js` (таблица, пагинация, поиск, сортировка), `static/js/engines.js` (глобалы). Файла `static/js/state.js` нет.
- CSS: `static/css/style.css::.catalog-layout`, `.tree-*`, `.data-table`, `.search-input`, `.pagination`.

### Детальная карточка двигателя (модалка)

- HTML: `templates/index.html` — `<div id="detailModal" class="modal">...</div>` с `#detailTitle`, `#detailToolbar`, `#detailContent`, `#detailMaximizeBtn`.
- JS: `static/js/engineCard.js::showDetail/closeDetail/renderDetailContent/navigateEngine/openPhotoAddModal/...`, `static/js/engines.js`.
- CSS: `static/css/style.css::.modal-content`, `.modal-body`, `.detail-toolbar`, `.data-table`, `.photo-thumb`.

### Модалка фото (полноэкранный просмотр)

- HTML: `templates/index.html` — `<div id="photoModal">` с `<img id="photoModalImg">`, `#photoModalTitle`, кнопки `prev`/`next`/`close`.
- JS: `static/js/engineCard.js::openPhotoModal/closePhotoModal/navigatePhotoModal`.

### Модалка добавления фото + обрезка (canvas)

- HTML: `templates/index.html` — `<div id="photoAddModal">`, `#detailPhotoInput`, `#detailPhotoPreview`, `<div id="photoCropModal">` с `<canvas id="cropCanvas">`, `<div id="cropStage">`, `#cropApplyBtn`.
- JS: `static/js/engineCard.js::openPhotoAddModal/closePhotoAddModal/submitDetailPhotoAdd`, `openCropModal`, `_openCropStage`, `_applyCropExisting` и т.п.

### Форма добавления двигателя (вкладка Импорт)

- HTML: `templates/index.html` — `<form id="engineForm">` с полями `#f_purpose`, `#f_workshop`, `#f_location`, `#f_engine_type`, ..., `#f_photos`, таблицы `#modesBody`, `#worksBody`.
- JS: `static/js/exportManager.js::saveEngine/addModeRow/addWorkRow`, `static/js/importer.js::importFiles`.

### Импорт (progress + log)

- HTML: `templates/index.html` — `<div id="importProgress" class="hidden">` с `#progressFill`, `#progressText`, `#progressLog`.
- JS: `static/js/importer.js::importFiles`.

### Расширенный поиск (вкладка Поиск)

- HTML: `templates/index.html` — `<div id="tab-search">` с `.search-rows-container`, кнопой "Добавить условие", `<div id="searchResults">`.
- JS: `static/js/search.js::executeSearch/_renderSearchResultsTable/addSearchRow/rebuildOperators`.

### Вкладка Оборудование — подвкладки (Список, Конструктор, ЗИП)

- HTML: `templates/index.html` — `<div id="tab-equipment">` с `#equipmentSubtabListBtn`, `#equipmentSubtabConstructorBtn`, `#equipmentSubtabStockBtn`, контентные контейнеры `#equipmentSubtab-list`, `-constructor`, `-stock`. Дерево мест `#equipmentLocationTreeBody`. Таблица `#equipmentListBody`. Формы создания типов/атрибутов.
- JS: `static/js/equipment.js`, `equipmentLocationTree.js`.

### Вкладка Оборудование — модалка карточки

- HTML: `templates/index.html` — `<div id="equipmentModal">` с `#equipmentDetailToolbar`, `#equipmentDetailContent`, `#equipmentMaximizeBtn`.
- JS: `static/js/equipment.js::openEquipmentModal/closeEquipmentModal/renderEquipmentDetailToolbar/navigateEquipment`.

### Вкладка Инциденты — журнал, подвкладки (Журнал, Справочники)

- HTML: `templates/index.html` — `<div id="tab-incidents">` с `#incidentsSubtabJournalBtn`, `#incidentsSubtabDictionariesBtn`. Дерево мест `#incidentLocationTreeBody`. Таблица `#incidentsListBody`.
- JS: `static/js/incidents.js`, `incidentLocationTree.js`, `incidentLocations.js`, `incidentCrew.js`.

### Вкладка Инциденты — модалка карточки заявки

- HTML: `templates/index.html` — `<div id="incidentTicketModal">` с `#incidentDetailToolbar`, полями формы (`#incidentProblem`, `#incidentSolution`, `#incidentClosedAtInput`, `#incidentLocationInput`, `#incidentInitiatorsContainer`, `#incidentExecutorsContainer`).
- JS: `static/js/incidents.js::openIncidentModal/closeIncidentModal/submitIncident/printIncident/deleteCurrentIncident`.

### Вкладка Инциденты — справочник людей/мест

- HTML: `templates/index.html` — внутри `incidentsSubtab-dictionaries` контейнеры `#locationDictList`, `#crewDictList`, формы создания.
- JS: `static/js/incidentLocations.js::loadLocationDictionary/createRootLocationNode/...`, `static/js/incidentCrew.js::loadCrewDictionary/editCrewMember/...`.

### Вкладка Админ

- HTML: `templates/index.html` — `<div id="tab-admin">` с `#adminUsersList`, `#addUserForm`, `#newUsername`, `#newPassword`, `#newRole`.
- JS: `static/js/auth.js::loadAdminUsers/adminCreateUser/adminDeleteUser/adminRevokeUser/adminChangePassword/promptChangePassword`.

### Вкладка Аудит

- HTML: `templates/index.html` — `<button class="tab-btn" data-tab="audit" style="display:none">` (строка 60) и `<div class="tab-content" id="tab-audit">` (строка 565); кнопка показывается только админам/суперадминам через `auth.js::applyRoleUI`.
- JS: `static/js/audit.js::loadAuditTab/loadAuditEntityTypes/loadAuditEntries/renderAuditTable/applyAuditFilters/resetAuditFilters/auditPrevPage/auditNextPage`.
- Данные: `GET /api/audit/entity-types` и `GET /api/audit/log` (таблица `audit_log`, наполняется `modules/audit.py`).

### Вкладка Настройки — подвкладки (БД, Фото, Бэкапы)

- HTML: `templates/index.html` — `<div id="tab-settings">` с `#settingsTabDb`, `#settingsTabPhotos`, `#settingsTabBackups`, контент с `#settingsEquipmentCount`, `#settingsPhotos`, `#settingsDbSize`, `#backupsList`.
- JS: `static/js/catalog.js::updateStats/loadSettings`, `static/js/backup.js::loadBackupsList/...`.

### Вкладка Инфо — подвкладки (Changelog, Wishlist, О системе)

- HTML: `templates/index.html` — `<div id="tab-info">` с `#infoSubtab-changelog`, `#infoSubtab-wishlist`, `#infoSubtab-system`, поля `#changelogTextInput`, `#wishlistTextInput`, контейнеры `#changelogList`, `#wishlistList`.
- JS: `static/js/info.js::loadChangelog/loadWishlist/addWishlistItem/toggleWishlistItem/deleteWishlistItem/switchInfoSubtab/loadSystemInfo`. (Содержимое `#infoSubtab-system` заполняется из `GET /api/status`: `app_version`, `python_version`, `flask_version`, `sqlite_version`, `git_commit`.)

### Печатные страницы

- `templates/print.html` — только `static/js/print.js`. CSS `static/css/print.css`.
- `templates/print_equipment.html` — `static/js/equipmentPrint.js`. CSS `static/css/print.css`.
- `templates/print_incident.html` — `static/js/incidentPrint.js`. CSS `static/css/print.css`.

### Dropdown автоподсказок (suggest-dropdown)

- HTML: создаётся JS динамически (`attachEntitySuggest` в `common.js`).
- JS: `static/js/common.js::attachEntitySuggest`, `static/js/engines.js::attachSuggestDropdown`.
- CSS: `static/css/style.css::.suggest-dropdown`, `.suggest-wrap`, `.suggest-item` (position: fixed; см. раздел 17).

### Экран загрузки (app-loading-overlay)

- HTML: `templates/index.html` — `<div id="appLoadingOverlay">`.
- JS: `static/js/auth.js::hideAppLoadingOverlay`. CSS: `static/css/style.css::.app-loading-overlay`.

## 14. Тестовая инфраструктура

> **Обновление 2026-09-16:** раздел переписан по факту прогонов. Фактические цифры: **592** unit/route/service теста (`591 passed, 1 skipped in 56.65s`) и **81** e2e-сценарий (`81 passed in 157.55s`). В первой версии документа значилось «65 unit + 81 e2e» — unit-цифра устарела.

### Общая структура

```
tests/
├──__init__.py
├──conftest.py                          # фикстуры db_conn (in-memory SQLite) и file_users_env
├──test_audit/                          # 28 тестов (test_audit.py, test_audit_repo.py, test_audit_routes.py)
├──test_auth/                           # 59 тестов (test_db_users, test_decorators, test_hashing, test_tokens, test_file_users)
├──test_backup_system/                  # 16 тестов (test_backup.py)
├──test_engine_parser/                  # 13 тестов (test_parser.py)
├──test_photo_manager/                  # 81 тест (test_manager, test_equipment_manager, test_incident_manager)
├──test_repositories/                   # 159 тестов (11 файлов по всем *_repo.py)
├──test_routes/                         # 196 тестов (9 файлов; __init__.py отсутствует)
├──test_services/                       # 33 теста (test_incident_service.py)
├──test_utils/                          # 27 тестов (test_date, test_file_store, test_logging, test_naming)
└──e2e/                                 # Playwright E2E — 83 сценария
    ├──__init__.py
    ├──conftest.py                      # 463 строки: изоляция MOTORS_*, live_server, браузер, storage_state
    ├──helpers.py                       # 298 строк
    ├──.results.json
    ├──screenshots/                     # скриншоты падений (артефакт прогонов)
    ├──test_01_auth.py                  # 13 сценариев
    ├──test_02_catalog.py               # 11
    ├──test_03_add_engine.py            # 9
    ├──test_04_detail.py                # 10
    ├──test_05_photos.py                # 7
    ├──test_06_import.py                # 3
    ├──test_07_search.py                # 6
    ├──test_08_settings.py              # 6
    ├──test_09_backups.py               # 4
    ├──test_10_info.py                  # 9
    └──test_11_misc.py                  # 5
```

### Unit-тесты (pytest)

**Команда запуска (через venv):**

```bash
.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e
# фактически 2026-09-16: 591 passed, 1 skipped in 56.65s (собрано 592)
```

**Разбивка по каталогам (собрано 612):** `test_routes` 196, `test_repositories` 159, `test_photo_manager` 81, `test_auth` 59, `test_services` 33, `test_audit` 28, `test_utils` 27, `test_backup_system` 16, `test_engine_parser` 13.

**Крупнейшие файлы:** `test_routes/test_equipment_routes.py` 63, `test_repositories/test_equipment_repo.py` 37, `test_services/test_incident_service.py` 33, `test_photo_manager/test_manager.py` 31, `test_repositories/test_incident_ticket_repo.py` 31, `test_routes/test_incident_ticket_routes.py` 30, `test_routes/test_auth_routes.py` 28, `test_routes/test_engines.py` 26.

**Фикстуры (`tests/conftest.py`):**

```python
@pytest.fixture
def db_conn():
    """In-memory SQLite с полной схемой (таблицы, индексы, admin-пользователь)."""
    with db_connection(':memory:') as conn:
        init_db(conn)
        yield conn

@pytest.fixture
def file_users_env(tmp_path, monkeypatch):
    """Изолированное файловое хранилище users.json / tokens.json."""
```

**Конфигурации pytest нет:** файлы `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini` в проекте отсутствуют — pytest работает на дефолтах, discovery идёт от корня проекта.

**Что покрыто (основное):**

| Файл | Кол-во сценариев | Что покрывает |
| --- | --- | --- |
| `tests/test_repositories/*` | 159 | все 10 репозиториев, включая `test_engine_repo_audit.py` (интеграция с `audit_log`) и тесты гонки самовосстанавливающихся миграций |
| `tests/test_routes/*` | 196 | engines, auth, crew, equipment (+photos), incident tickets (+photos), import, photos |
| `tests/test_photo_manager/*` | 81 | три параллельных photo-менеджера (двигатели/оборудование/инциденты) |
| `tests/test_auth/*` | 59 | hashing, db_users, file-пользователи, токены, декораторы |
| `tests/test_services/test_incident_service.py` | 33 | бизнес-логика заявок и связей |
| `tests/test_audit/*` | 28 | `modules/audit.py`, `repositories/audit_repo.py`, `routes/audit_routes.py` |
| `tests/test_utils/*` | 27 | `format_ru_date`, `load_json/save_json`, `log_message`, `normalize_base_name` |
| `tests/test_backup_system/test_backup.py` | 16 | создание/инспекция/восстановление бэкапов |
| `tests/test_engine_parser/test_parser.py` | 13 | парсер xlsx |

**Итого unit/route/service тестов: 612 сценариев** (196+159+81+59+33+28+27+16+13), из них 1 skip — `tests/test_backup_system/test_backup.py:216` («Windows-specific os.replace lock issue — fix in production, not blocking»).

### E2E-тесты (Playwright)

**Команда запуска:**

```bash
.venv\Scripts\python.exe -m pytest tests/e2e -q
# фактически 2026-09-16: 81 passed, 199 warnings in 157.55s
```

**Ключевое (проверено в коде `tests/e2e/conftest.py`, 463 строки):**
- Браузер запускается **безголовым**: `pw.chromium.launch(headless=True, args=["--window-size=1300,820", "--no-first-run"])` (строки 176–182). Значение `headless=True` — фактическое.
- Параметр `channel="chrome"` **не передаётся**: используется Chromium из состава Playwright (упоминание `channel="chrome"` осталось только в docstring `conftest.py` и в заголовке генерируемого `docs/e2e_test_results.md` — это устаревший текст). Для прогона нужен `playwright install chromium`.
- Флаг `--headed` в команде запуска не используется (в первой версии документа он был указан ошибочно).
- `live_server` поднимает Flask через `werkzeug.serving.make_server("127.0.0.1", 0, app, threaded=True)` — свободный порт, изолированная временная БД (`MOTORS_*` → `tempfile.mkdtemp()`), продакшен-данные не затрагиваются. **Поднимать `app.py` вручную не нужно.**
- `helpers.py` (298 строк) — общие утилиты Playwright: `make_engine/make_mode/make_work`, `login_ui/logout_ui/switch_tab/wait_toast`, `create_engine_direct/engine_id_by_serial/delete_engine_by_serial`, `open_engine_card/open_detail_edit/save_detail_card/fill_detail_fields`, `make_test_png/upload_detail_photo`, `set_local_storage`, `prompt_accept/accept_dialogs`.

**Что покрыто (по файлам):**

| Файл | Сценариев | Что покрывает |
| --- | --- | --- |
| `test_01_auth.py` | 13 | Логин, logout, токен, попытки неверного пароля |
| `test_02_catalog.py` | 11 | Загрузка каталога, пагинация, сортировка, фильтры |
| `test_03_add_engine.py` | 9 | Создание двигателя, добавление режимов/работ/фото |
| `test_04_detail.py` | 10 | Открытие карточки, редактирование, навигация |
| `test_05_photos.py` | 7 | Загрузка фото, обрезка, удаление |
| `test_06_import.py` | 3 | Импорт из Excel, переключение вкладки, очистка БД |
| `test_07_search.py` | 6 | Расширенный поиск: поля, операторы |
| `test_08_settings.py` | 6 | Статистика БД, вкладки настроек, бэкапы |
| `test_09_backups.py` | 4 | Создание/восстановление бэкапа |
| `test_10_info.py` | 9 | Changelog, wishlist, о системе |
| `test_11_misc.py` | 5 | Прочие сценарии |

**Итого e2e-тестов: 83 сценария** (13+11+9+10+7+3+6+6+4+9+5) — совпадает с фактическим прогоном.

### Артефакты прогона

- `docs/e2e_test_results.md` — таблица результатов по группам + строка «**Итого:** 83 passed, 0 failed, 0 skipped» (файл перезаписывается при каждом прогоне e2e).
- `tests/e2e/.results.json` — те же данные в JSON (накопительно, merge по nodeid).
- `tests/e2e/screenshots/` — скриншоты упавших тестов (55 файлов от прошлых прогонов).

## 15. Карта использования (Select-String по всему репозиторию)

Полный результат `Select-String` по всему репозиторию (без `__pycache__`, `.venv`, `.git`, `.pytest_cache`, `motors`, `photos`, `PhotoE`, `backups`, `backup_staging`, `temp`). Поиск выполнен командой:

```powershell
$include = @('*.py')
Get-ChildItem -Recurse -Include $include -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\__pycache__' -and $_.FullName -notmatch '\.venv' -and $_.FullName -notmatch '\.git' -and $_.FullName -notmatch '\.pytest_cache' } | Select-String -Pattern 'photo_manager|PHOTOS_FOLDER|DB_PATH|_engine_photo_disk_paths|normalize_base_name|INCIDENT_PHOTOS_FOLDER|EQUIPMENT_PHOTOS_FOLDER|BACKUPS_FOLDER|BACKUP_STAGING_PATH|engine_photo_disk_paths|ticket_photo_disk_paths|equipment_photo_disk_paths|next_photo_index' | Select-Object Path, LineNumber, Line
```

> **ВНИМАНИЕ:** `BACKUP_STAGING_FOLDER` — реальная константа; `BACKUP_STAGING_PATH` — не существует. Всего найдено **393 совпадения** (расширенный pattern, 2026-09-16; в первой версии документа было 259). Лог `docs/_usage_scan.txt` больше не существует — цифры пересчитаны заново.

### Сводная таблица: файл → кол-во упоминаний

Сокращённый pattern (`photo_manager|PHOTOS_FOLDER|DB_PATH|_engine_photo_disk_paths|normalize_base_name`), пересчёт 2026-09-16 — **304 совпадения** (в первой версии документа было 259):

| Файл | Кол-во |
| --- | --- |
| `tests/test_photo_manager/test_manager.py` | 64 |
| `modules/backup_system/backup.py` | 50 |
| `tests/test_routes/test_engines.py` | 19 |
| `tests/test_routes/test_import_routes.py` | 14 |
| `tests/test_backup_system/test_backup.py` | 13 |
| `modules/photo_manager/equipment_manager.py` | 12 |
| `config/settings.py` | 12 |
| `modules/photo_manager/incident_manager.py` | 11 |
| `modules/photo_manager/manager.py` | 10 |
| `tests/test_routes/test_photos.py` | 10 |
| `modules/db.py` | 9 |
| `routes/import_routes.py` | 9 |
| `tests/conftest.py` | 8 |
| `tests/test_utils/test_naming.py` | 8 |
| `routes/photos.py` | 7 |
| `diag_photos.py` | 5 |
| `tests/test_photo_manager/test_incident_manager.py` | 4 |
| `tests/test_photo_manager/test_equipment_manager.py` | 4 |
| `services/export_service.py` | 4 |
| `tests/test_repositories/test_engine_repo.py` | 4 |
| `routes/status.py` | 3 |
| `utils/naming.py` | 3 |
| `modules/engine_parser/parser.py` | 3 |
| `routes/incident_ticket_routes.py`, `routes/equipment_routes.py`, `routes/engines.py`, `repositories/engine_repo.py`, `app.py`, `modules/photo_manager/__init__.py` | по 2 |
| `routes/incident_photo_routes.py`, `routes/equipment_photo_routes.py`, `services/backup_service.py`, `scripts/migrate_wishlist_to_json.py` | по 1 |

> Файла `promote_and_cleanup.py` (3 упоминания в первой версии документа) в проекте больше нет.

### Избранные результаты по константам

**DB_PATH:**

| Файл | Строка | Контекст |
| --- | --- | --- |
| `config/settings.py` | 25 | определение: `DB_PATH = _env('MOTORS_DB_PATH', BASE_DIR / 'engine_data.db')` |
| `app.py` | — | **`DB_PATH` в `app.py` не импортируется** (там только `PHOTOS_FOLDER, MOTORS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER`, строка 15) |
| `modules/db.py` | 9 | импорт `DB_PATH, MOTORS_FOLDER, ...` |
| `modules/backup_system/backup.py` | 35 | `DB_PATH = db_module.DB_PATH` (прокси) |
| `services/backup_service.py` | 9 | `from config.settings import DB_PATH, ...` |
| `diag_photos.py` | 6 | `conn = sqlite3.connect(DB_PATH)` — **напрямую, без `db_connection()`!** |
| ~~`promote_and_cleanup.py`~~ | — | файла в проекте **нет** |

**PHOTOS_FOLDER:**

| Файл | Строка | Контекст |
| --- | --- | --- |
| `config/settings.py` | 13 | определение |
| `app.py` | 15, 21 | импорт + `for folder in [PHOTOS_FOLDER, ...]` |
| `modules/db.py` | 9 | импорт |
| `modules/backup_system/backup.py` | 36 | `PHOTOS_FOLDER = db_module.PHOTOS_FOLDER` |
| `services/backup_service.py` | 9 | импорт |
| `routes/import_routes.py` | 14 | `from modules.db import ... PHOTOS_FOLDER, MOTORS_FOLDER` |
| `routes/import_routes.py` | 247-249 | `if os.path.exists(PHOTOS_FOLDER): shutil.rmtree(PHOTOS_FOLDER, ...)` |
| `diag_photos.py` | 4 | `from config.settings import PHOTOS_FOLDER, ...` |

**INCIDENT_PHOTOS_FOLDER / EQUIPMENT_PHOTOS_FOLDER:**

- Определены в `config/settings.py:31` и `config/settings.py:34` (не 17/20 — строки сдвинулись).
- Импортируются в `modules/db.py:9`.
- Используются через `db_module.INCIDENT_PHOTOS_FOLDER` / `db_module.EQUIPMENT_PHOTOS_FOLDER` в `incident_manager.py` и `equipment_manager.py` соответственно.
- Обе входят в список `PHOTO_FOLDERS` (`config/settings.py:50`) — единая точка для backup/restore/`clear_database`.

**BACKUPS_FOLDER / BACKUP_STAGING_FOLDER:**

| Файл | Строка | Контекст |
| --- | --- | --- |
| `config/settings.py` | 56, 57 | определения (`BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER`) |
| `app.py` | 15, 21 | импорт + создание папок при старте |
| `modules/backup_system/backup.py` | 37-38 | прокси через `db_module` |
| `modules/backup_system/backup.py` | 47-49 | создание BACKUPS_FOLDER если нет |
| `modules/backup_system/backup.py` | 109-111 | перебор фото в PHOTOS_FOLDER для архивации |
| `modules/backup_system/backup.py` | 143 | `zf.write(os.path.join(PHOTOS_FOLDER, ...))` |
| `modules/backup_system/backup.py` | 150, 158-169 | лимитирование по количеству копий в BACKUPS_FOLDER |
| `routes/backup_routes.py` | через `db_module` — `_safe_backup_filename`, `inspect_uploaded_backup` |
| `services/backup_service.py` | 9 | `from config.settings import DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER` |

**photo_manager / manager.py / incident_manager.py / equipment_manager.py:**

- `modules/photo_manager/manager.py` импортируется в `routes/photos.py::photo_manager` (`from modules.photo_manager import manager as photo_manager`).
- `modules/photo_manager/incident_manager.py` импортируется в `routes/incident_ticket_routes.py::incident_manager`.
- `modules/photo_manager/equipment_manager.py` импортируется в `routes/equipment_routes.py::equipment_manager`.

**engine_photo_disk_paths / ticket_photo_disk_paths / equipment_photo_disk_paths:**

- Определены только в своих manager-файлах. Используются внутри модуля (для `glob`). Не импортируются извне напрямую — клиентский код вызывает высокоуровневые функции (`get_engine_photos`, `delete_engine_photos_from_disk`, и т.п.).

**next_photo_index:**

- Определена в трёх manager-файлах. Используется внутри `upload_*_photos`. Не импортируется извне.

**normalize_base_name:**

- Определена в `utils/naming.py:10`.
- Используется только в `tests/test_utils/test_naming.py` (8 ссылок).
- В production-коде **не вызывается** (см. раздел 16).

**ALLOWED_PHOTO_EXT:**

- Определена в `config/settings.py:68`. Импортируется в `modules/db.py` (реэкспорт). Используется во всех трёх photo_manager и в `diag_photos.py:4`.

### Дополнительные Select-String (по запросу из задания)

Команда `Get-ChildItem -Recurse -Include *.py | Select-String -Pattern 'photo_manager|PHOTOS_FOLDER|DB_PATH|_engine_photo_disk_paths|normalize_base_name' | Select-Object Path, LineNumber, Line` даёт тот же результат. Пересчёт 2026-09-16: **304 совпадения** (в первой версии документа — 259); таблица по файлам — выше. Файл `docs/_usage_scan.txt` отсутствует.

## 16. Найденные расхождения

Без рекомендаций по исправлению — только факты.

### 16.1 Одинаковые константы/пути, определённые в нескольких местах

- **НЕТ дублей определения констант путей.** Все пути определены только в `config/settings.py` и реэкспортируются через `modules/db.py` и `services/backup_service.py`. Это явный успех рефакторинга (см. раздел 17).

### 16.2 Локальные определения, дублирующие config.settings

- Одно место с локальным `sqlite3.connect(DB_PATH)` напрямую в обход `db_connection()`:
  - `diag_photos.py:6` — `conn = sqlite3.connect(DB_PATH)`. НЕ устанавливает `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`.
  - Ранее здесь упоминался `promote_and_cleanup.py:26`, но этого файла в проекте **нет** (сверено 2026-09-16).
- **НЕТ других** локальных переопределений путей.

### 16.3 Функции с одинаковым назначением, реализованные независимо

#### 16.3.1 `*_photo_disk_paths` / `next_photo_index` в трёх photo_manager

`modules/photo_manager/manager.py`, `incident_manager.py`, `equipment_manager.py` — **каждый** реализует свою версию:

| Функция | manager.py | incident_manager.py | equipment_manager.py |
| --- | --- | --- | --- |
| `*_disk_paths` | `engine_photo_disk_paths` | `ticket_photo_disk_paths` | `equipment_photo_disk_paths` |
| `next_photo_index` | ✓ | ✓ | ✓ |
| `get_photo` | ✓ | ✓ | ✓ |
| `upload_*_photos` | ✓ | ✓ | ✓ |
| `delete_*_photo` | ✓ | ✓ | ✓ |
| `delete_*_photos_from_disk` | ✓ | ✓ | ✓ |
| `count_all_photos` | n/a | ✓ | ✓ |
| `replace_*_photo` | ✓ | n/a | ✓ |
| `invalidate_photo_cache` | ✓ | ✓ | ✓ |

Все три файла имеют **одинаковую логику** (`glob` + regex). Это три параллельные реализации, осознанно оставленные авторами (см. `incident_manager.py:1-19`, `equipment_manager.py:1-22`).

#### 16.3.2 `_photo_paths_cache` в каждом из трёх photo_manager

`manager.py`, `incident_manager.py`, `equipment_manager.py` имеют каждый свой `dict _photo_paths_cache = {}` и `invalidate_photo_cache()`. Эти кэши НЕ общие между файлами.

### 16.4 Константы/функции, которые нигде не используются (мёртвый код)

Установлено поиском `Select-String` по всему репозиторию:

| Имя | Файл определения | Почему мёртвое |
| --- | --- | --- |
| `normalize_base_name` | `utils/naming.py:10` | Используется только в `tests/test_utils/test_naming.py`. **В production не вызывается ни разу.** |
| `update_photo_count` | `repositories/engine_repo.py:251` | **Не вызывается из routes** — поиск `engine_repo.update_photo_count` даёт только определение. Колонка `engines.photo_count` может не обновляться через эту функцию. |
| `create` (mode_repo) | `repositories/mode_repo.py:44` | **Не вызывается из routes** — поиск ` mode_repo.create` даёт только определение. Все маршруты используют `replace_all`. |
| `create` (work_repo) | `repositories/work_repo.py:46` | **Не вызывается из routes** — аналогично. |
| `delete_all_for_engine` (mode_repo, work_repo) | `repositories/mode_repo.py:60`, `work_repo.py:62` | **Не вызываются**. |
| `update_last_login`, `count_users`, `update_file_user_last_login` | `modules/auth/db_users.py`, `file_users.py` | **Не вызываются**. |
| `move_location`, `delete_location` | `services/incident_service.py` | Тонкие обёртки, **не вызываются**. |
| `delete_ticket_photos_from_disk`, `delete_equipment_photos_from_disk` | `modules/photo_manager/incident_manager.py:138`, `equipment_manager.py:193` | **Не вызываются**. Это означает, что при удалении `incident_ticket` или `equipment` фото на диске (`PhotoI/`, `PhotoE/`) **остаются сиротами**. |
| `invalidate_photo_cache` | `manager.py:31`, `incident_manager.py:30`, `equipment_manager.py:33` | **Не вызывается извне** — кэш заполняется, но не инвалидируется. |
| `create_backup`, `list_backups`, `inspect_uploaded_backup`, `restore_backup`, `download_backup`, `delete_backup` | `services/backup_service.py` | **Не вызываются** — `routes/backup_routes.py` импортирует `modules.backup_system.backup` напрямую. |
| `require_auth`, `require_admin` (как декораторы) | `modules/auth/decorators.py` | **Не используются в routes**. Защита в `routes/auth.py` реализована через `before_app_request`. |
| `get_current_user` (decorators.py) | `modules/auth/decorators.py:25` | Определена, но не вызывается — `routes/auth.py` имеет свою копию. |
| `_extract_bearer_token` (decorators.py) | `modules/auth/decorators.py:13` | Аналогично. |
| `load_json`, `save_json` | `utils/file_store.py` | Используются только в тестах. `modules/auth/file_users.py` использует собственный `json.load`/`json.dump`. |
| `format_ru_date`, `is_valid_iso_date` | `utils/date.py` | **Вызываются из production**: `services/export_service.py:155,302` (`format_ru_date`). `is_valid_iso_date` — только внутри `utils/date.py`. Frontend имеет `static/js/common.js::_formatRuDate` как аналог. |

### 16.5 Расхождения в сигнатурах

- `routes/auth.py::get_current_user()` vs `modules/auth/decorators.py::get_current_user()` — обе определены, обе принимают либо `(token)` либо ничего. В routes используется собственная (без `db_connection()`).
- `routes/auth.py::_extract_bearer_token()` vs `modules/auth/decorators.py::_extract_bearer_token()` — точная копия. Дублирование.

### 16.6 Относительные и абсолютные пути

Все пути вычисляются через `BASE_DIR = Path(__file__).resolve().parent.parent` (`config/settings.py:9`), что даёт **абсолютный путь**. Никаких относительных литералов (`"photos"`, `"engine_data.db"` без `BASE_DIR/`) в production-коде не найдено. **Только** `templates/index.html` содержит относительные пути для статических ресурсов (`/static/...`), что нормально для Flask.

Исключение: `modules/photo_manager/manager.py` использует `from modules import db as db_module` внутри `_photos_folder()` (строки 37-39), чтобы `PHOTOS_FOLDER` читался динамически — позволяет тестам делать monkeypatch. Это НЕ относительный путь, а динамическое чтение абсолютного.

### 16.7 Дополнительные находки

#### 16.7.1 Тонкий обёрточный слой `services/backup_service.py` не используется

Все 6 функций в `services/backup_service.py` являются тонкими обёртками над `modules.backup_system.backup` и **не вызываются** — `routes/backup_routes.py` импортирует `backup_module` напрямую (строки 9-10).

#### 16.7.2 `routes/auth.py` дублирует helpers из `modules/auth/decorators.py`

`routes/auth.py::_extract_bearer_token` (строки 9-16) — копия `modules/auth/decorators.py::_extract_bearer_token` (строки 13-22). `routes/auth.py::get_current_user` (строки 19-24) — копия `modules/auth/decorators.py:25-31`. Импорт `auth_module` (`from modules.auth import auth as auth_module`) — это фасад, а не сам `decorators`.

#### 16.7.3 Декораторы `require_auth` и `require_admin` в `decorators.py` не используются

В проекте есть только один страж — `before_app_request` в `routes/auth.py::load_current_user`. Декораторы `require_auth` / `require_admin` определены в `modules/auth/decorators.py:34-61`, но **не используются ни в одном файле**.

#### 16.7.4 Восстановление фото при удалении заявки/оборудования — нет связи

`modules/photo_manager/incident_manager.py::delete_ticket_photos_from_disk` и `equipment_manager.py::delete_equipment_photos_from_disk` определены, но **нигде не вызываются**. Это означает, что при удалении `incident_ticket` или `equipment` фото на диске (`PhotoI/`, `PhotoE/`) **остаются сиротами**. У движков такое удаление работает (через `routes/engines.py::delete_engine` → `manager.delete_engine_photos_from_disk`), а у инцидентов и оборудования — нет.

#### 16.7.5 `engines.photo_count` нигде не обновляется через `update_photo_count`

`repositories/engine_repo.py::update_photo_count` (строки 251-256) определена, но **не вызывается ни в одном production-файле**. Возможно, `engines.photo_count` обновляется где-то ещё (через прямую команду UPDATE в `photo_manager.upload_engine_photos`?), но я не смог полностью прочитать `manager.py::upload_engine_photos` в одном блоке — **требует уточнения**.

#### 16.7.6 `incident_ticket.updated_at` авто-миграция в репозитории, а не в `init_db()`

`repositories/incident_ticket_repo.py::_ensure_updated_at_column` (строки 25-34) самодостаточно мигрирует колонку `incident_ticket.updated_at` при первом обращении. Все остальные auto-migrations в `modules/db.py:443-492`. Это осознанное решение (см. комментарий `incident_ticket_repo.py:10-22`).

#### 16.7.7 Прямые `sqlite3.connect(DB_PATH)` обходят PRAGMA

`diag_photos.py:6` (файла `promote_and_cleanup.py` в проекте нет) использует `sqlite3.connect(DB_PATH)` напрямую, без установки `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`. Это значит:
- FK-каскады НЕ enforced для этих соединений.
- WAL не используется.

#### 16.7.8 Конфликт версий `version.txt` vs `APP_VERSION` — УСТРАНЁН

Ранее `routes/status.py::APP_VERSION` был хардкодом `'2.0'` и расходился с `version.txt = 1.0.5`. Сейчас (2026-09-16) `APP_VERSION = _read_app_version()` читает значение из `version.txt` — источник правды один.

#### 16.7.9 Сидинг admin-пользователя только при при старте, если БД пуста

`modules/db.py` (см. seed-блок в конце `init_db()`): создаётся пользователь `admin/admin123` ТОЛЬКО если `SELECT COUNT(*) FROM users == 0`. После `/api/clear` пользователи сохраняются (см. раздел 9), так что это безопасно для продакшена.

## 17. Известные особенности и история инцидентов

Для контекста будущим сессиям — не переоткрывать заново.

### 17.1 Пути к данным только через config.settings

**Инцидент:** ранее были относительные литералы в коде (`"photos"`, `"engine_data.db"`), что приводило к тому, что `shutil.rmtree('photos')` стирал не ту папку, которую ожидали (например, при запуске из другой директории).

**Решение:** все пути вычисляются через `BASE_DIR = Path(__file__).resolve().parent.parent` (`config/settings.py:9`). Все остальные файлы импортируют константы из `config.settings` (напрямую или через `db.py`/`services/backup_service.py`).

**Правило для будущих ИИ-сессий:** любой новый путь должен добавляться в `config/settings.py` и импортироваться, не литералом в коде.

### 17.2 `allEngines` — единая точка результата для каталога/поиска/дерева

Все три источника (каталог, расширенный поиск, дерево) обязаны писать в `allEngines` перед рендером:
- `catalog.js::loadEngines()` — пишет `allEngines = data.engines`
- `search.js::executeSearch()` — пишет `allEngines = data` (с сохранением в `originalAllEngines`)
- `locationTree.js` — только читает (вызывает `loadEngines()` для применения фильтра)

Не должно быть «третьего места», которое держит свой кэш.

### 17.3 `.suggest-dropdown` — position: fixed

В `static/js/common.js::attachEntitySuggest` используется `position: fixed` с ручным позиционированием через JS (`dropdown.style.top/left/width = rect.bottom/left/width`). Причина: `overflow:hidden` у модалок `position: absolute` обрезал бы dropdown. Это **не** баг, который нужно «исправлять» на `position: absolute`.

### 17.4 `/api/clear` требует подтверчения «СТИРАТЬ» на фронте

`static/js/importer.js::confirmClearDatabase` использует `prompt('Введите СТИРАТЬ')` (кириллица, верхний регистр) перед `POST /api/clear`. Это защита от повторения инцидента с потерей фото — добавлена осознанно. **Не убирать.**

### 17.5 Схема именования фото

Старая (историческая) схема: `{base}img{n}{engine_id}.ext` → новая: `ID{engine_id}_{n}.ext` (актуальная на момент снимка — см. раздел 7).

Старая схема осталась только в тексте комментариев/документации (например, в `PROJECT_SNAPSHOT.md` старом). В текущем коде она не используется. **Не пытаться** парсить старые имена — они не появятся в новой БД.

### 17.6 Логика id движков

Переход от чистого AUTOINCREMENT к переиспользованию минимального свободного id при удалении — это **намеренное решение**, зафиксированное в docstring `repositories/engine_repo.py::create` («ID выбирается явно как минимальный свободный (см. `_next_free_id`), а не отдаётся AUTOINCREMENT»). Актуальное поведение `engine_repo.create`:

1. INSERT с явным поиском минимального свободного id.
2. После DELETE этот id становится доступен для следующего create.

> **Требует уточнения:** точный код `engine_repo.create` я не смог прочитать в одном блоке (см. раздел 8). Но косвенные комментарии в коде подтверждают эту схему.

### 17.7 Расхождение `services/backup_service.py` и `routes/backup_routes.py`

`services/backup_service.py` — 6 функций-делегатов (`create_backup` и т.д.) — НЕ используется. `routes/backup_routes.py` импортирует `modules.backup_system.backup` напрямую. Это историческое наследие. **Не пытаться** добавлять функционал через `services/backup_service.py` — это мёртвый слой.

### 17.8 Расхождение `modules/auth/auth.py` (фасад) vs `routes/auth.py` (свои копии helpers)

`modules/auth/auth.py` — реэкспортирует helpers из подмодулей. Но `routes/auth.py` определяет свои копии `_extract_bearer_token` и `get_current_user`. Это произошло потому, что `routes/auth.py` был написан до того, как был создан `modules/auth/decorators.py`. Исторически — не трогать без нужды.

### 17.9 Декораторы `require_auth` / `require_admin` из `modules/auth/decorators.py` не используются

Определены, но ни один route не вызывает. Единственный механизм защиты — `before_app_request` в `routes/auth.py::load_current_user`. **Не пытаться** декорировать роуты декораторами из `decorators.py` — вместо этого используется централизованная проверка в `load_current_user`.

### 17.10 `modules/photo_manager/__init__.py` НЕ реэкспортирует `incident_manager` и `equipment_manager`

`from modules.photo_manager import manager as photo_manager` — работает, но `from modules.photo_manager import incident_manager` — НЕ работает (нет в `__init__.py`). `routes/incident_ticket_routes.py` и `routes/equipment_routes.py` импортируют явно. Не добавлять `incident_manager` и `equipment_manager` в `__init__.py` без явной причины — это может сломать ожидание «`from modules.photo_manager` импортирует только двигатели».

### 17.11 Расхождение `version.txt` vs `APP_VERSION` — УСТРАНЕНО

`version.txt = 1.0.5`. На 2026-09-16 `routes/status.py:51` — `APP_VERSION = _read_app_version()`, то есть значение читается из `version.txt` (хардкода `'2.0'` в коде больше нет, расхождения нет).

### 17.12 Файлы `diag_photos.py`, `diag_modal.py`, `measurement.py`, `test_mode_repo.py` — диагностические утилиты

- `diag_photos.py` — диагностика фото (дамп, лаунчер).
- `diag_modal.py`, `measurement.py`, `test_mode_repo.py` — разовые отладочные скрипты.
- `promote_and_cleanup.py`, упоминавшийся в первой версии документа, в проекте **отсутствует** (сверено 2026-09-16).

Они не зарегистрированы как blueprint и не используются приложением. `diag_photos.py:6` содержит `sqlite3.connect(DB_PATH)` напрямую без `PRAGMA foreign_keys=ON`. Это может привести к ошибкам FK-каскада в старых БД. Использовать с осторожностью.

### 17.13 Сидинг admin-пользователя только при пустой БД

`modules/db.py:513-517` создаёт `admin/admin123` ТОЛЬКО если `SELECT COUNT(*) FROM users == 0`. Это безопасно после `/api/clear`, потому что `/api/clear` не очищает таблицу `users`. Но если кто-то вручную очистит `users` (например, прямым SQL), то при следующем старте будет создан новый `admin/admin123` без предупреждения.

### 17.14 ON DELETE CASCADE не работает на старой продакшен-БД

В схеме `operating_modes.engine_id` и `maintenance_works.engine_id` объявлены как `REFERENCES engines(id) ON DELETE CASCADE`. Но на старой продакшен-БД (созданной до добавления CASCADE) эти FK-каскады не работают. `repositories/engine_repo.py::delete` удаляет modes/works вручную в одной транзакции (строки 243-247). Это правильный workaround.

### 17.15 Что НЕ сбрасывается при `/api/clear`

`/api/clear` удаляет файл БД целиком и пересоздаёт её через `init_db()`. Сохраняются и возвращаются обратно только `users` и `tokens` (чтобы админ мог войти). Отдельные JSON-файлы `data/changelog.json` / `data/wishlist.json` очисткой не затрагиваются.

**Всё остальное теряется безвозвратно**, в т.ч. `audit_log`, номенклатура `equipment*`, `incident_ticket*`, `crew`, `location_node`, `engines` (см. раздел 9 — прежняя версия этого раздела ошибочно утверждала, что номенклатура и инциденты не удаляются).

### 17.16 `routes/auth.py` использует свою `get_current_user()`

Причина: `routes/auth.py::get_current_user()` вызывает `db_connection()` напрямую, а `modules/auth/decorators.py::get_current_user()` — тоже `db_connection()`. Обе реализации рабочие; основная разница в том, что routes версия не имеет опции импорта. Не пытаться менять одну на другую без тестов.

## 18. Итоговая сводка

| Показатель | Значение |
| --- | --- |
| **Файлов проекта** | 219 (на 2026-09-16; в первой версии документа — 147) |
| **Модулей** (Python пакетов) | `config`, `modules` (+`auth`, `backup_system`, `engine_parser`, `photo_manager`), `repositories`, `routes`, `schemas`, `scripts`, `services`, `tests`, `utils` + `static/js`, `static/css`, `static/ico`, `templates` |
| **Файлов с путевыми константами** | 4 (`config/settings.py` — определение; `modules/db.py`, `services/backup_service.py`, `modules/backup_system/backup.py` — реэкспорт/прокси) |
| **Уникальных путевых констант** | 18 (`BASE_DIR`, `DB_PATH`, `MOTORS_FOLDER`, `PHOTOS_FOLDER`, `INCIDENT_PHOTOS_FOLDER`, `EQUIPMENT_PHOTOS_FOLDER`, `PHOTO_FOLDERS`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER`, `CONFIG_DIR`, `FILE_USERS`, `FILE_TOKENS`, `DATA_DIR`, `CHANGELOG_JSON_PATH`, `WISHLIST_JSON_PATH`, `ALLOWED_PHOTO_EXT`, `MAX_WORKERS`, `LOG_FILE`) |
| **Мест использования констант путей** | 30+ файлов (см. раздел 15) |
| **Найденных дублей/расхождений (раздел 16)** | 9 категорий (см. ниже) |
| **Таблиц в схеме БД** | 17 (см. раздел 3) |
| **Тестов** | 612 unit/route/service (611 passed, 1 skipped) + 83 e2e (passed) |
| **`__init__.py` с явными re-export списками** | 7 (`routes`, `modules/auth`, `modules/backup_system`, `modules/engine_parser`, `modules/photo_manager`, `modules/auth/auth.py`, `routes/__init__.py`) |
| **Из них синхронизированы с реальным содержимым модуля** | 6 (verified) |
| **`__init__.py` с расхождениями** | 1 — `modules/photo_manager/__init__.py` реэкспортирует **только** из `manager.py`; `incident_manager.py` и `equipment_manager.py` НЕ реэкспортируются (см. раздел 17.10) |

### Сводка найденных расхождений (раздел 16)

| # | Категория | Количество |
| --- | --- | --- |
| 16.1 | Дубли определения констант путей | 0 |
| 16.2 | Прямые `sqlite3.connect(DB_PATH)` в обход PRAGMA | 1 (`diag_photos.py:6`) |
| 16.3 | Тройное дублирование фото-менеджеров | 3 файла × ~10 функций |
| 16.4 | Мёртвый код | ~17 имён |
| 16.5 | Дубли helpers auth | 2 пары |
| 16.6 | Относительные пути | 0 (в production) |
| 16.7.1 | `services/backup_service.py` — неиспользуемый слой | 6 функций |
| 16.7.2 | `routes/auth.py` дублирует `decorators.py` | 2 функции |
| 16.7.3 | `require_auth` / `require_admin` не используются | 2 декоратора |
| 16.7.4 | `delete_*_photos_from_disk` не вызываются | 2 функции → orphan фото |
| 16.7.5 | `engine_repo.update_photo_count` не вызывается | 1 функция |
| 16.7.6 | Auto-migration колонки в репозитории (осознанно) | 1 (не дубль) |
| 16.7.7 | Обход PRAGMA в diag-скриптах | 1 файл (`diag_photos.py`) |
| 16.7.8 | Конфликт `version.txt` vs `APP_VERSION` | **0 — устранён** |
| 16.7.9 | Авто-сидинг admin при пустой users | 1 место |

### Подтверждение через Select-String (раздел 15)

- **393 совпадения** для расширенного pattern (`photo_manager|PHOTOS_FOLDER|DB_PATH| ...`) по всему `.py` репозиторию (без `__pycache__`, `.venv`, `.git`, `.pytest_cache`) — пересчёт 2026-09-16; в первой версии документа было 259.
- **304 совпадения** для сокращённого pattern (`photo_manager|PHOTOS_FOLDER|DB_PATH|_engine_photo_disk_paths|normalize_base_name`) — таблица по файлам в разделе 15.
- Сводные таблицы по каждой константе — в разделе 6.
- Файл `docs/_usage_scan.txt` (в первой версии документа — «полный лог») на диске **отсутствует**.