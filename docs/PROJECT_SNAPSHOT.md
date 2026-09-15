# PROJECT_SNAPSHOT — motors_project

> **Снимок архитектуры и состояния кода** на основе реального содержимого репозитория `c:\motors_project`.
> Документ описывает **как устроен** проект (что есть), **как запускается** (как поднять) и **как развивается** (как добавлять новое).
> Дата снимка: 2026-01-09.
> **Обновление 2026-09-15:** удалены описания вырезанных модулей «База знаний»/«Заявки» (`knowledge_*`, `ticket_*` — commit 758aa34).

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
- учёт инцидентов (тикеты) и обслуживание оборудования (crew, equipment, incidents) с фото-связями;
- журнал изменений (`changelog_entries`) и wishlist;
- аутентификация по логину/паролю, токены, роли (`admin` / `user`).

**Стек.**

| Слой        | Технология                                                   |
|-------------|--------------------------------------------------------------|
| Backend     | Python 3, Flask (Blueprints), SQLite (стандартный модуль)    |
| HTTP-клиент | встроенные запросы из JS через `fetch` (`static/js/api.js`) |
| Frontend    | Vanilla JS (ES-модули), HTML, CSS (без фреймворков)          |
| Excel       | `openpyxl`                                                   |
| Архивация   | стандартный `zipfile` + `sqlite3` Online Backup API          |
| Тесты       | `pytest` (юнит/repo), `playwright` (e2e, Chrome headfull)   |

**Ключевые принципы архитектуры (как они видны в коде):**
- **Repository pattern** — SQL изолирован в `repositories/`, сервисы и роуты работают с функциями-репозиториями.
- **Сервисный слой** (`services/`) оркеструет репозитории и инкапсулирует файловые/zip-операции.
- **Тонкие роуты** (`routes/`) — принимают запрос, вызывают сервис/репозиторий, сериализуют ответ.
- **Frontend без сборки** — браузер сам подгружает ES-модули по `<script type="module">`.
- **Атомарность бэкапов** — staging-папка + rollback point, чтобы можно было безопасно восстановиться.
- **Декомпозиция по фичам** — каждая фича в своих подпапках (`modules/`, `routes/`, `repositories/`, `schemas/`).

---

## 2. Структура каталогов

Реальная структура (сокращённо):

```
c:\motors_project\
+- app.py                              # Flask-приложение, точка входа
+- config\settings.py                  # Пути и константы (DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, ...)
+- data\                               # runtime: engine_data.db, changelog.json, wishlist.json
+- backups\                            # готовые zip-бэкапы
+- backup_staging\                     # временная зона для restore (см. §8)
+- photos\                             # фото двигателей: photos/<engine_id>/<base_name>.<ext>
+- photos_equipment\                   # фото оборудования (по equipment_id)
+- photos_incidents\                   # фото инцидентов
+- uploads\                            # staging для загружаемых файлов (xlsx, zip)
+- exports\                            # результаты ручного экспорта JSON
+- modules\
|  +- db.py                            # get_db_connection, db_connection (context manager), init_db
|  +- auth.py                          # хеши паролей, токены, CRUD пользователей
|  +- engine_parser\
|  |  +- parser.py                     # parse_xlsx, normalize_base_name
|  +- photo_manager\
|  |  +- manager.py                    # add_photo, remove_photo (engine)
|  |  +- equipment_manager.py          # фото оборудования
|  |  +- incident_manager.py           # фото инцидентов
|  +- backup_system\
|     +- __init__.py                   # create_backup, list_backups, restore_backup, ...
|     +- backup.py                     # zip+SQLite Online Backup + manifest + checksums
+- repositories\                       # тонкий слой SQL (см. §4)
|  +- engine_repo.py, mode_repo.py, work_repo.py
|  +- location_repo.py, changelog_repo.py, wishlist_repo.py
|  +- crew_repo.py, equipment_repo.py, incident_equipment_repo.py
|  +- incident_link_repo.py, incident_ticket_repo.py
+- routes\                             # Flask Blueprints (см. §6)
|  +- auth.py, engines.py, search.py
|  +- equipment_routes.py, equipment_photo_routes.py
|  +- incident_ticket_routes.py, incident_photo_routes.py
|  +- backup_routes.py, import_routes.py, export_routes.py
|  +- location_routes.py
|  +- pages.py, status.py, photos.py
|  +- changelog.py, crew_routes.py
+- schemas\                            # Pydantic-подобные валидаторы (легковесные, на dataclass)
|  +- engine_schema.py, equipment_schema.py
|  +- incident_ticket_schema.py
|  +- incident_equipment_repo.py
+- services\
|  +- import_service.py                # xlsx-импорт + привязка фото
|  +- export_service.py                # JSON-экспорт каталога
|  +- incident_service.py              # бизнес-логика инцидентов
|  +- backup_service.py                # фасад над modules.backup_system
+- utils\
|  +- naming.py                        # normalize_base_name (единый источник правды)
|  +- file_store.py                    # load_json / save_json
+- static\
|  +- js\
|  |  +- app.js                        # bootstrap страницы, видимость табов по роли
|  |  +- state.js                      # глобальное состояние каталога (см. §12)
|  |  +- api.js                        # тонкая обёртка над fetch с auth-headers
|  |  +- common.js                     # общие хелперы (escape, toast, форматтеры)
|  |  +- catalog.js                    # список двигателей + фильтры
|  |  +- engines.js                    # CRUD двигателей + режимы + работы
|  |  +- engineCard.js                 # детальная карточка + фото-галерея
|  |  +- equipment.js, incidents.js
|  |  +- search.js                     # поиск по всем полям
|  +- css\                             # стили (tabs, modal, toast, ...)
|  +- img\                             # статические изображения UI
+- templates\
|  +- index.html                       # единая SPA-HTML страница (табы #tab-*)
+- tests\
|  +- conftest.py                      # фикстуры db_conn, app, client
|  +- test_repositories\               # юнит-тесты репозиториев
|  +- e2e\
|  |  +- conftest.py                   # Playwright, browser=Chrome headfull, фикстуры api/page
|  |  +- helpers.py                    # make_engine, login_ui, switch_tab, wait_toast
|  |  +- test_01_auth.py ... test_11_misc.py
+- docs\                               # эта и другие документации
+- requirements.txt
+- README.md
```

---

## 3. Запуск и окружение

**Зависимости** (`requirements.txt`): Flask, openpyxl, pytest, pytest-playwright (и их транзитивные).

**Переменные окружения:**
- `E2E_BASE_URL` — URL приложения для e2e (по умолчанию `http://localhost:5000`).
- `FLASK_ENV`, `FLASK_DEBUG` — стандартные для Flask.

**Пути в `config/settings.py`:**
- `DB_PATH` — путь к `data/engine_data.db` (создаётся автоматически).
- `PHOTOS_FOLDER` — `photos/` (для двигателей).
- `PHOTOS_EQUIPMENT_FOLDER` — `photos_equipment/`.
- `PHOTOS_INCIDENTS_FOLDER` — `photos_incidents/`.
- `BACKUPS_FOLDER` — `backups/`.
- `BACKUP_STAGING_FOLDER` — `backup_staging/` (временная зона при restore).
- `UPLOADS_FOLDER` — `uploads/`.
- `EXPORTS_FOLDER` — `exports/`.
- `CHANGELOG_FILE` — `data/changelog.json`.
- `WISHLIST_FILE` — `data/wishlist.json`.

**Команды:**

```bash
# Установка
pip install -r requirements.txt

# Запуск приложения
python app.py
# -> http://localhost:5000

# Юнит-тесты репозиториев
pytest tests/test_repositories -q

# Все pytest-тесты
pytest -q

# E2E (Playwright, требует установленные браузеры: `playwright install chrome`)
pytest tests/e2e -q
# Результаты пишутся в docs/e2e_test_results.md
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
- `replace_all(conn, engine_id, items)` — атомарная замена всех режимов/работ двигателя.
- `add`, `update`, `delete`, `get_for_engine` — точечные операции.

**`location_repo.py`:**
- `get_all_locations()`, `add_location(name)`, `remove_location(name)` — справочник мест установки.

**`incident_*`, `crew_repo`, `equipment_repo`:**
- Аналогичный набор CRUD-операций для соответствующих сущностей.

### 4.5. Схемы (`schemas/`)

Лёгкая валидация входных данных (например, `engine_schema.py`) — отдельный шаг между роутом и репозиторием. Это dataclass-стиль проверок (поля, типы, обязательность), без Pydantic. Нужна, чтобы:
1. Не доверять фронту.
2. Не разносить валидацию по роутам.

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

### 5.2. Сервисы

**`services/import_service.py`** — импорт Excel (`*.xlsx`) с автоприкреплением фото:
- Принимает путь к xlsx и список файлов фото (или путь к папке с фото).
- Парсит строки через `modules/engine_parser/parser.py`.
- Для каждой строки создаёт запись в `engines`, режимы, работы.
- Фото прикрепляются по нормализованному имени файла (см. §10).

**`services/export_service.py`** — экспорт каталога в JSON:
- Возвращает полный снимок: `engines` + `modes` + `works` + (опц.) `locations`.
- Удобен для миграций и обмена между инсталляциями.

**`services/incident_service.py`** — бизнес-логика инцидентов:
- Создание/обновление/связывание инцидентов с оборудованием, привязка фото.
- Скорее всего тут сосредоточены правила вроде «инцидент нельзя закрыть без оборудования» и т.п.

**`services/backup_service.py`** — фасад над `modules/backup_system/backup.py`:
- `create_backup()`, `list_backups()`, `inspect_uploaded_backup(zip_path)`,
  `restore_backup(zip_path)`, `download_backup(filename)`, `delete_backup(filename)`.
- Сам ничего не делает, кроме делегирования; нужен, чтобы отделить «знание о путях» от «знания о zip+SQLite Online Backup API».

---

## 6. HTTP-роуты (Flask Blueprints)

Все роуты — Blueprint'ы, регистрируются в `app.py`. Ниже — что каждый делает.

| Blueprint (`routes/`) | Префикс (предп.) | Назначение |
|---|---|---|
| `pages.py` | `/` | Единственная HTML-страница (`index.html`), SPA на табах. |
| `auth.py` | `/api/auth` | `/login`, `/logout`, `/me`. |
| `engines.py` | `/api/engines` | CRUD двигателей, режимы, работы. |
| `search.py` | `/api/search` | Полнотекстовый/поиск по полям. |
| `equipment_routes.py` | `/api/equipment` | CRUD оборудования. |
| `equipment_photo_routes.py` | `/api/equipment/<id>/photos` | Фото оборудования. |
| `incident_ticket_routes.py` | `/api/incidents` | Тикеты инцидентов. |
| `incident_photo_routes.py` | `/api/incidents/<id>/photos` | Фото инцидентов. |
| `backup_routes.py` | `/api/backups` | Создание/список/скачивание/удаление/загрузка/инспекция/восстановление. |
| `import_routes.py` | `/api/import` | Импорт xlsx. |
| `export_routes.py` | `/api/export` | Экспорт каталога. |
| `location_routes.py` | `/api/locations` | Справочник мест. |
| `changelog.py` | `/api/changelog` | Журнал изменений. |
| `crew_routes.py` | `/api/crew` | Бригады. |
| `photos.py` | `/api/engines/<id>/photos` | Фото двигателей (CRUD). |
| `status.py` | `/api/status` | Пинг/версия. |

**Шаблон обработчика** (тонкий роут):
```python
@bp.route("/<id>", methods=["GET"])
@require_auth  # или @require_admin
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

**`modules/auth.py`** — основной модуль:
- Хеширование паролей (используется безопасный хеш с солью).
- Генерация/проверка токенов: `create_token`, `verify_token` (хранится `token_hash` в БД, не сам токен).
- CRUD пользователей: `create_user`, `delete_user`, `get_user_by_username`, `update_user`.
- `require_auth` / `require_admin` — декораторы, которые читают заголовок `Authorization: Bearer <token>`, находят пользователя и прокидывают в обработчик.

**Поток логина:**
1. Клиент шлёт `POST /api/auth/login` с `{username, password}`.
2. Сервер проверяет пароль, генерирует токен, сохраняет `token_hash` в `tokens`, возвращает `{token, user}`.
3. Клиент сохраняет токен (frontend — `api.js` централизованно подставляет `Authorization`).
4. `last_login` обновляется.

**Роли:**
- `admin` — может создавать/удалять пользователей, удалять любые сущности, управлять бэкапами.
- `user` — базовые CRUD по доменным сущностям; не имеет доступа к `/api/auth/users` и `/api/backups` (или имеет read-only — см. `routes/auth.py`).

**Защита:** все чувствительные роуты — под `@require_auth`; админские — под `@require_admin`.

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
2. Копируются фото из `photos/` (а также из `photos_equipment/`, `photos_incidents/`, если они включены).
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

- Эндпоинт: `POST /api/import` (multipart: `file=<xlsx>`, опц. `photos=<files>` или `photos_dir=<path>`).
- Сервис: `services/import_service.py`.
- Парсер: `modules/engine_parser/parser.py` (читает `openpyxl`).
- Алгоритм:
  1. Открыть xlsx, пройти по строкам.
  2. Для каждой строки собрать dict характеристик, валидировать (`schemas/engine_schema.py`).
  3. Создать `engines` (через `engine_repo.create`).
  4. Создать режимы (`mode_repo.replace_all`) и работы (`work_repo.replace_all`).
  5. Пройтись по фото: имя файла → `normalize_base_name` → искать engine, у которого в `filename` или в `serial_number`/`engine_type` совпадает база → прикрепить (см. §10).

### 9.2. Экспорт JSON

- Эндпоинт: `GET /api/export` (или `POST` с фильтрами).
- Сервис: `services/export_service.py`.
- Возвращает JSON-файл: `{ "version": ..., "engines": [...], "locations": [...] }`.
- Используется для миграций и обмена между инсталляциями.

### 9.3. Импорт JSON

Скорее всего обратный сценарий в `import_routes.py` — `POST /api/import/json` принимает такой JSON и идемпотентно вливает в БД (upsert по `serial_number` или `id`).

---

## 10. Парсер xlsx-каталога и нормализация имён фото

### 10.1. Парсер

`modules/engine_parser/parser.py`:
- `parse_xlsx(path) -> list[dict]` — читает `openpyxl.load_workbook(path, data_only=True)`, по каждой строке собирает dict с полями двигателя, плюс вложенные списки `modes` и `works` (если строки разнесены по разделам листа).
- Использует заголовки столбцов для маппинга на поля БД.

### 10.2. Нормализация имён фото

Когда оператор складывает xlsx и папку с фото, ожидается что имя файла фото (без расширения) совпадает с одним из идентификаторов двигателя — обычно `serial_number` или `engine_type` (модель).

Алгоритм в `import_service.py`:
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

`photo_manager/manager.py`:
- `add_photo(engine_id, file_storage)` — сохраняет с нормализованным именем.
- `remove_photo(engine_id, filename)` — удаляет файл и обновляет `engines.photo_count`.
- При удалении двигателя — каскадно чистится папка (через `os` + `shutil`, или через хук в `engine_repo.delete`).

---

## 11. Frontend: HTML + vanilla JS (модули)

### 11.1. Точка входа

`templates/index.html` — единственная HTML-страница. Подключает JS-модули из `static/js/` через `<script type="module">`:
```html
<script type="module" src="{{ url_for('static', filename='js/app.js') }}"></script>
```

### 11.2. Модули JS

| Файл | Ответственность |
|---|---|
| `app.js` | Bootstrap: после `DOMContentLoaded` проверить токен, показать `#login-overlay` или основное приложение; настроить видимость табов по роли. |
| `state.js` | Глобальное состояние каталога: `allEngines`, `currentSort`, `currentPage`, `activeWorkshop`, `activeLocation`, `selectedEngineIds`, `currentTab`/`activeTab`. Экспортирует объект `state` и хелперы `setState/getState`. |
| `api.js` | `apiGet`, `apiPost`, `apiPut`, `apiDelete` с автоматической подстановкой `Authorization: Bearer <token>` (из `localStorage`/cookie) и JSON-сериализацией. |
| `common.js` | `escapeHtml`, `formatDate`, `toast(msg, type)`, `debounce`. |
| `catalog.js` | Рендер таблицы каталога, фильтры, пагинация, сортировка. |
| `engines.js` | CRUD форм добавления/редактирования двигателя, режимов и работ. |
| `engineCard.js` | Детальная карточка (модалка `#detailModal`), просмотр/редактирование, фото-галерея, переключение view/edit. |
| `equipment.js` | UI для оборудования. |
| `incidents.js` | UI для инцидентов. |
| `search.js` | Поиск по всем полям с автодополнением/дебаунсом. |

### 11.3. API-обёртка (`api.js`)

```js
const token = localStorage.getItem("auth_token");
fetch(url, {
  headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
  body: JSON.stringify(data),
  method: "POST"
})
```

Возвращает распарсенный JSON либо бросает осмысленную ошибку (включая 401 → редирект на логин).

### 11.4. Toast

`toast(message, type='info')` создаёт элемент `.toast` с автозакрытием через ~3.3с. Используется во всех формах для обратной связи.

### 11.5. CSS

`static/css/` — стили табов, модалок, форм, toast, кнопок. Без препроцессоров.

---

## 12. UI-табы и состояние каталога

В `index.html` (и `state.js`) выделяются следующие глобальные идентификаторы (по поиску `allEngines|currentSort|currentPage|activeWorkshop|activeLocation|selectedEngineIds|currentTab|activeTab`):

- **`allEngines`** — кеш всех двигателей, загруженных с сервера (используется для фильтрации/сортировки на клиенте).
- **`currentSort`** — текущий ключ сортировки (`{field, dir}`).
- **`currentPage`** — номер страницы в каталоге.
- **`activeWorkshop`** — фильтр по цеху.
- **`activeLocation`** — фильтр по месту установки.
- **`selectedEngineIds`** — набор выбранных id (для bulk-операций).
- **`currentTab` / `activeTab`** — какой таб сейчас активен (`catalog`, `add`, `detail`, `equipment`, `incidents`, `admin`, `settings`, `search`, ...).

**Переключение табов:** клик по `.tab-btn[data-tab="<name>"]` → `switch_tab(name)` из `app.js`. `activeTab` обновляется, `#tab-<name>` становится `display: block`, остальные `none`.

**Согласованность состояния:** при операциях с данными (создание/удаление/редактирование) `loadEngines()` перечитывает каталог с сервера и обновляет `allEngines`, после чего таблица перерисовывается через `renderCatalog()`.

---

## 13. Тестирование: pytest + Playwright e2e

### 13.1. Юнит-тесты (`tests/test_repositories/`)

Пример: `tests/test_repositories/test_engine_repo.py` (177 строк).
- Использует фикстуру `db_conn` (временная in-memory или файл SQLite, инициализированная через `init_db`).
- Классы `TestCreateAndGet`, `TestUpdate`, `TestDelete`, `TestGetAll`, `TestPhotoCount`, `TestGetByFilename`.
- Проверяются каскадные удаления (`delete` сносит `modes`/`works` через `ON DELETE CASCADE`).
- Проверяется пагинация (`limit`/`offset`) и поиск (`search_field` + `search_query`).

Фикстуры — в `tests/conftest.py` (общий для репозиториев и сервисов).

**Актуальное состояние (2026-09-15):** покрыты репозитории `crew`, `engine` (в т.ч. аудит-интеграция `test_engine_repo_audit.py`), `equipment`, `equipment_placement`, `incident_equipment`, `incident_ticket`, `location`, `mode`, `work` — **158 тестов, прогон полностью зелёный** (`python -X utf8 -m pytest tests/test_repositories/`). Плюс роуты: `tests/test_routes/test_crew_routes.py`, `test_engines.py` (зелёные).

### 13.2. E2E (`tests/e2e/`)

- `conftest.py` (337 строк) — инфраструктура Playwright:
  - Браузер: Google Chrome (`channel="chrome"`), **видимый** (`headless=False`).
  - Один браузер на сессию, для каждого теста — отдельный контекст (изоляция `localStorage`/cookies).
  - Тестовые пользователи: `e2e_test_admin` (`admin`), `e2e_test_user` (`user`) — создаются в начале сессии, удаляются в teardown.
  - Префикс `MARKER = "E2E_TESTS"` для тестовых сущностей.
  - Сбор диагностики: ошибки консоли, JS-исключения, сетевые ответы `>= 400`, скриншот при падении.
  - Сессионная фикстура `storage_state` — логинит admin через реальную UI-форму один раз и переиспользует storage.
  - Результаты агрегируются в `docs/e2e_test_results.md` (таблица + totals) и `tests/e2e/.results.json`.

- `helpers.py` (242 строки) — переиспользуемые функции:
  - `make_engine(**overrides)`, `make_mode()`, `make_work()` — генерация тестовых данных с уникальным `E2E-<uuid>`.
  - `login_ui(page, username, password)`, `logout_ui(page)`, `switch_tab(page, tab)`, `wait_toast(page, text)`.
  - `engine_id_by_serial(api, serial)`, `delete_engine_by_serial(api, serial)` — API-чистка.
  - `fill_engine_form(page, payload)`, `open_engine_card(page, id)`, `close_detail(page)`, `open_detail_edit(page)`.
  - `make_test_png(path, ...)` — создаёт валидный PNG без сторонних библиотек (через `zlib`).
  - `upload_detail_photo(page, image_path)`.

- Тестовые модули:
  - `test_01_auth.py` — логин/логаут, неверный пароль, сессия.
  - `test_02_catalog.py` — каталог, фильтры, сортировка, пагинация.
  - `test_03_add_engine.py` ... `test_11_misc.py` — остальные сценарии (CRUD двигателя, детальная карточка, фото, импорт, поиск, настройки, бэкапы, инциденты, оборудование, прочее).

### 13.3. Как запускать

```bash
# только репозитории/сервисы
pytest tests/test_repositories -q

# только e2e
pytest tests/e2e -q

# всё
pytest -q
```

**Перед e2e** нужно поднять приложение (`python app.py`) и убедиться, что `playwright install chrome` выполнен.

---

## 14. Известные ограничения и решения

Эти ограничения зафиксированы прямо в комментариях кода и важно о них помнить при расширении.

1. **`normalize_base_name` не обрезает имя до 100 символов** (`utils/naming.py`).
   *Причина:* обратная совместимость с фото в `photos/`. Не вводите обрезку — поломаете старые пути.

2. **Сохранение обратной совместимости JSON-файлов.**
   `auth.py` раньше имел дубли `load_file_users`/`save_file_users`/... — теперь всё в `utils/file_store.py`. При добавлении новых полей в `users.json` используйте `default=[]` и миграционные шаги.

3. **E2E запускается в видимом Chrome** (`headless=False`).
   Это требование пользователя — не пытайтесь переключить в headless без согласования.

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
2. В `app.js` (или в конкретном `*.js` модуле таба) — обработчик `switch_tab('sensor')`, lazy-init.
3. Если таб только для админа — проверить роль в `app.js` и скрыть кнопку/секцию.
4. E2E: добавить сценарий в новый `tests/e2e/test_NN_*.py`, использовать `switch_tab(page, "sensor")` и `wait_toast(...)`.

### 15.4. Новый эндпоинт бэкапа

1. В `modules/backup_system/backup.py` (или отдельный файл рядом) — функция.
2. Зарегистрировать в фасаде `services/backup_service.py`.
3. Добавить маршрут в `routes/backup_routes.py` под `@require_admin`.
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
| `static/js/state.js` | Глобальные `currentSort`/`activeWorkshop`/... — много плоских переменных. | По мере роста — выделить `catalogFilters`, `tablePagination` в подобъекты. |
| `services/import_service.py` | Стратегия сопоставления фото с двигателем — по точному совпадению нормализованного имени. | Добавить fuzzy-match по `serial_number` или `engine_type` с приоритетами. |
| `tests/e2e/` | На данный момент 11 тестовых модулей, но групп в `conftest.py` зарезервировано до 11. | При добавлении группы >11 — расширить `GROUP_ORDER` в `_write_results`. |
| `routes/photos.py` и `photo_manager/manager.py` | Фото двигателей хранятся по `<engine_id>/...`, но при переимпорте xlsx с тем же `serial_number` могут дублироваться. | Добавить дедупликацию по хешу содержимого. |
| `repositories/equipment_repo.py` | Оборудование сейчас не привязано к двигателям жёстко. | Связать `equipment.engine_id` (через `_ensure_column`). |
| `templates/index.html` | Единая SPA-страница, раздувается при росте функциональности. | Разнести по partials (через `<template>` и клонирование), либо перейти к per-tab страницам. |
| `modules/backup_system/backup.py` | Снимок фото делается полным копированием. | Добавить инкрементальные бэкапы (по `mtime`/`hash`). |
| `static/js/api.js` | `Authorization` берётся из `localStorage`. | При росте требований к безопасности — httpOnly cookie + CSRF. |
| `tests/test_repositories/` | Покрыты все репозитории (158 тестов, зелёные). | Расширять по мере добавления новых функций репозиториев/роутов. |

---

## Приложение А. Соответствие "файл → роль"

| Слой | Где живет |
|---|---|
| Точка входа | `app.py` |
| Конфигурация | `config/settings.py` |
| БД (схема + соединение) | `modules/db.py` |
| Аутентификация | `modules/auth.py`, `routes/auth.py` |
| Доменные модули | `modules/engine_parser/`, `modules/photo_manager/`, `modules/backup_system/` |
| SQL (Repository) | `repositories/*_repo.py` |
| Валидация | `schemas/*_schema.py` |
| Бизнес-логика | `services/*_service.py` |
| HTTP | `routes/*_routes.py` |
| Утилиты | `utils/naming.py`, `utils/file_store.py` |
| UI | `templates/index.html`, `static/js/*.js`, `static/css/*` |
| Тесты | `tests/test_repositories/`, `tests/e2e/` |
| Документация | `README.md`, `docs/*.md` |

## Приложение Б. Глобальное состояние фронта

Найдено в `static/js/state.js` (и/или в `app.js`):

- `allEngines` — массив всех двигателей (клиентский кеш).
- `currentSort` — `{field, dir}`.
- `currentPage` — номер страницы каталога.
- `activeWorkshop` — фильтр по цеху.
- `activeLocation` — фильтр по месту.
- `selectedEngineIds` — Set/Array id выбранных двигателей (для bulk-операций).
- `currentTab` / `activeTab` — имя активного таба.
- `auth_token` (localStorage) — токен авторизации.

## Приложение В. Команды на каждый день

```bash
# Поднять приложение
python app.py

# Прогнать юнит-тесты
pytest tests/test_repositories -v

# Прогнать e2e (нужен поднятый app.py)
pytest tests/e2e -v

# Посмотреть отчёт e2e
cat docs/e2e_test_results.md

# Создать бэкап вручную (через API)
curl -X POST -H "Authorization: Bearer <admin_token>" http://localhost:5000/api/backups

# Восстановить из бэкапа (через UI, кнопка "Восстановить" сначала показывает inspect)
```

---

*Конец снимка. Документ сгенерирован на основе прямого чтения исходников `c:\motors_project`. При расхождениях — опирайтесь на код, а не на этот документ; правки приветствуются.*
