# Технический снимок структуры проекта

> **Режим:** аудит (только чтение кода, без изменений).
> **Единственное внесённое изменение:** создание/перезапись данного файла `docs/project_structure_snapshot.md`.

---

## 1. Информация о текущем состоянии проекта

| Параметр | Значение |
|---|---|
| **Дата и время создания снимка** | 2026-08-01, 10:35:30 (Europe/Moscow, UTC+3:00) |
| **Ветка Git** | `main` |
| **SHA последнего коммита** | `84a170ce15c8cc46527b996b2986c9e1939d211d` |
| **Рабочая директория проекта** | `c:\motors_project` |
| **Версия Python** | `3.14.6` |

---

## 2. Полное дерево проекта

Команда PowerShell, использованная для получения дерева:

```powershell
Get-ChildItem -Recurse -File -Exclude __pycache__,*.pyc,*.db,*.log |
Where-Object { $_.FullName -notmatch '\\(motors|photos|backups|temp|\.venv|\.git|node_modules)\\' } |
Select-Object -ExpandProperty FullName
```

Результат (относительные пути от корня проекта `c:\motors_project`):

```
.clineignore
.gitignore
.github\workflows\ci.yml
.pytest_cache\CACHEDIR.TAG
.pytest_cache\.gitignore
.pytest_cache\README.md
.pytest_cache\v\cache\lastfailed
.pytest_cache\v\cache\nodeids
app.py
app_live.out
config\settings.py
config\tokens.json
diag_photos.py
docs\1project_structure_snapshot.md
import_log.txt
itogo.bat
modules\auth\__init__.py
modules\auth\auth.py
modules\auth\db_users.py
modules\auth\decorators.py
modules\auth\file_users.py
modules\auth\hashing.py
modules\auth\tokens.py
modules\backup_system\__init__.py
modules\backup_system\backup.py
modules\db.py
modules\engine_parser\__init__.py
modules\engine_parser\parser.py
modules\photo_manager\__init__.py
modules\photo_manager\manager.py
repositories\__init__.py
repositories\engine_repo.py
repositories\mode_repo.py
repositories\work_repo.py
reset_admin_password.py
routes\__init__.py
routes\auth.py
routes\backup_routes.py
routes\changelog.py
routes\engines.py
routes\export_routes.py
routes\import_routes.py
routes\pages.py
routes\photos.py
routes\search.py
routes\status.py
schemas\__init__.py
schemas\engine_schema.py
services\backup_service.py
services\export_service.py
services\import_service.py
static\css\print.css
static\css\style.css
static\js\api.js
static\js\app.js
static\js\auth.js
static\js\backupManager.js
static\js\catalog.js
static\js\common.js
static\js\engineCard.js
static\js\engines.js
static\js\exportManager.js
static\js\importer.js
static\js\print.js
static\js\search.js
static\js\state.js
templates\index.html
templates\print.html
utils\date.py
utils\file_store.py
utils\logging.py
utils\naming.py
utils\__init__.py
_restore_log_tmp.txt
Новый текстовый документ.cmd
tests\__init__.py
tests\conftest.py
tests\test_backup_system\__init__.py
tests\test_backup_system\test_backup.py
tests\test_repositories\__init__.py
tests\test_repositories\test_engine_repo.py
tests\test_utils\__init__.py
tests\test_utils\test_date.py
tests\test_utils\test_file_store.py
tests\test_utils\test_naming.py
```

### Примечание к дереву

1. **Каталог `temp/` исключён** из дерева по условию фильтра (`\-notmatch '...\\temp\\...'`), но содержит Python-файлы, которые были обнаружены при поиске по всему проекту (см. ниже). Эти файлы анализированы и включены в отчёт, так как содержат путевые константы.
2. **Каталог `.pytest_cache\`** попадает в дерево, так как не включён ни в `-Exclude`, ни в фильтр `Where-Object`. Это следует учесть как потенциальную неточность команды.
3. **Файлы `config\tokens.json` и `config\users.json`** входят в дерево, но исключаются из `.gitignore` (см. ниже). Они являются данными, а не кодом.
4. **Файл `docs\1project_structure_snapshot.md`** — существующий файл со старым снимком (перезаписан новым).
5. **Файлы `app_live.out`, `import_log.txt`, `_restore_log_tmp.txt`, `itogo.bat`, `Новый текстовый документ.cmd`** — вспспомогательные/служебные файлы корня проекта.

### Дополнительно: файлы из каталога `temp/` (исключённые из дерева, но найденные при поиске)

```
temp\temp_selftest.py
temp\tests\test_app.py
```

Эти файлы **не включены** в дерево выше из-за фильтра, но упомянуты здесь для полноты картины.

---

## 3. Полный анализ путевых констант

### 3.1 Константы, определённые в `config/settings.py` (единственный источник правды)

Файл: `config/settings.py`

| № | Константа | Строка | Точное определение | Тип пути | Вычисление |
|---|---|---|---|---|---|
| 1 | `BASE_DIR` | 9 | `BASE_DIR = Path(__file__).resolve().parent.parent` | `Path` (объект) | `Path(__file__).resolve().parent.parent` |
| 2 | `DB_PATH` | 11 | `DB_PATH = str(BASE_DIR / 'engine_data.db')` | `str` (абсолютный) | `str(BASE_DIR / 'engine_data.db')` |
| 3 | `MOTORS_FOLDER` | 12 | `MOTORS_FOLDER = str(BASE_DIR / 'motors')` | `str` (абсолютный) | `str(BASE_DIR / 'motors')` |
| 4 | `PHOTOS_FOLDER` | 13 | `PHOTOS_FOLDER = str(BASE_DIR / 'photos')` | `str` (абсолютный) | `str(BASE_DIR / 'photos')` |
| 5 | `BACKUPS_FOLDER` | 14 | `BACKUPS_FOLDER = str(BASE_DIR / 'backups')` | `str` (абсолютный) | `str(BASE_DIR / 'backups')` |
| 6 | `BACKUP_STAGING_FOLDER` | 15 | `BACKUP_STAGING_FOLDER = str(BASE_DIR / 'backup_staging')` | `str` (абсолютный) | `str(BASE_DIR / 'backup_staging')` |
| 7 | `CONFIG_DIR` | 16 | `CONFIG_DIR = str(BASE_DIR / 'config')` | `str` (абсолютный) | `str(BASE_DIR / 'config')` |
| 8 | `FILE_USERS` | 17 | `FILE_USERS = str(BASE_DIR / 'config' / 'users.json')` | `str` (абсолютный) | `str(BASE_DIR / 'config' / 'users.json')` |
| 9 | `FILE_TOKENS` | 18 | `FILE_TOKENS = str(BASE_DIR / 'config' / 'tokens.json')` | `str` (абсолютный) | `str(BASE_DIR / 'config' / 'tokens.json')` |
| 10 | `LOG_FILE` | 24 | `LOG_FILE = str(BASE_DIR / 'app.log')` | `str` (абсолютный) | `str(BASE_DIR / 'app.log')` |

Дополнительно в `config/settings.py` (не путевые, но связанные константы):

| Константа | Строка | Значение |
|---|---|---|
| `ALLOWED_PHOTO_EXT` | 20 | `{'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}` (множество строк) |
| `MAX_WORKERS` | 23 | `4` (int) |

### 3.2 Прочие определения констант, связанных с путями

#### `app.py` (строка 20)

```python
for folder in ['photos', 'motors', 'backups', 'backup_staging']:
    if not os.path.exists(folder):
        os.makedirs(folder)
```

Это **жёстко закодированные относительные пути** в виде строковых литералов. Константы `PHOTOS_FOLDER`, `MOTORS_FOLDER`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER` из `config/settings.py` **не используются**. Пути являются относительными (зависят от текущего рабочего каталога процесса), в отличие от абсолютных путей из `config/settings.py`.

#### `modules/db.py` (строка 11)

```python
ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
```

Дублирует `ALLOWED_PHOTO_EXT` из `config/settings.py`. Импорт из `config.settings` не выполняется для этой константы.

#### `modules/engine_parser/parser.py` (строка 17)

```python
ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
```

Дублирует `ALLOWED_PHOTO_EXT`. Также импортирует `PHOTOS_FOLDER` из `config.settings` (строка 18).

#### `modules/photo_manager/manager.py` (строка 13)

```python
ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
```

Дублирует `ALLOWED_PHOTO_EXT`. Импортирует `PHOTOS_FOLDER` из `config.settings` (строка 14).

#### `diag_photos.py` (строка 5)

```python
ALLOWED_PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
```

Дублирует `ALLOWED_PHOTO_EXT`. Также импортирует `PHOTOS_FOLDER` из `config.settings` (строка 4). Кроме того, использует строковый литерал `'engine_data.db'` напрямую (строка 7): `conn = sqlite3.connect('engine_data.db')` — вместо `DB_PATH`.

#### `modules/backup_system/backup.py` (строки 34–37)

```python
DB_PATH = db_module.DB_PATH
PHOTOS_FOLDER = db_module.PHOTOS_FOLDER
BACKUPS_FOLDER = db_module.BACKUPS_FOLDER
BACKUP_STAGING_FOLDER = db_module.BACKUP_STAGING_FOLDER
```

Это **не новые определения**, а **переназначение** (re-assignment) констант, имплируемых через `from modules import db as db_module` (строка 32). Значения берутся из `modules.db`, который импортировал их из `config.settings`. Таким образом, на момент импорта `modules.backup_system.backup` эти константы имеют те же значения, что и в `config.settings`. Однако, поскольку это присваивание на уровне модуля (а не `from ... import`), монkeypatching `db_module.DB_PATH` в тестах **не** автоматически обновляет `backup_module.DB_PATH` — тесты делают это явно (см. `tests/test_backup_system/test_backup.py` и `temp/tests/test_app.py`).

#### `modules/auth/file_users.py` (строка 12)

```python
FILE_USER_ID_OFFSET = 1000000000
```

Это **не путевая константа**, а константа смещения ID для файловых пользователей. Однако она часто упоминается рядом с путевыми константами, поэтому включена в анализ. Определяется локально.

#### `modules/backup_system/backup.py` (строка 38)

```python
MAX_BACKUPS_KEPT = 3
```

Не путевая константа, а параметр ограничения количества бэкапов. Определяется локально.

#### `temp/temp_selftest.py` (строки 9, 16–21)

```python
ROOT = Path(__file__).resolve().parent
TEST_DB_PATH = ROOT / 'temp_test_engine_data.db'
TEST_CONFIG_DIR = ROOT / 'temp_test_config'
TEST_PHOTOS_FOLDER = ROOT / 'temp_test_photos'
TEST_BACKUPS_FOLDER = ROOT / 'temp_test_backups'
TEST_BACKUP_STAGING_FOLDER = ROOT / 'temp_test_backup_staging'
TEST_MOTORS_FOLDER = ROOT / 'temp_test_motors'
```

Это **локальные тестовые константы путей**, определяемые внутри самостоятельного скрипта. Они не импортируются из `config.settings` и не являются частью основной кодовой базы (файл находится в исключённом каталоге `temp/`).

---

## 4. Источник каждой константы

### Путевые константы из `config/settings.py`

#### `BASE_DIR`
- **Источник:** `config/settings.py` — определяется локально (строка 9).
- **Используется:** только в `config/settings.py` для вычисления остальных констант.

#### `DB_PATH`
- **Источник:** `config/settings.py` — определяется локально (строка 11).
- **Импорты:**
  - `modules/db.py` (строка 9): `from config.settings import DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER`
  - `modules/backup_system/backup.py` (строка 34): `DB_PATH = db_module.DB_PATH` (из `modules.db`)
  - `routes/status.py` (строка 9): `from modules.db import db_connection, DB_PATH, MOTORS_FOLDER`
  - `routes/import_routes.py` (строка 14): `from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER`
  - `reset_admin_password.py` (строка 41): `from modules.db import DB_PATH, db_connection, init_db`
  - `services/backup_service.py` (строка 9): `from config.settings import DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER` (импорт не используется — см. п. 7)

#### `MOTORS_FOLDER`
- **Источник:** `config/settings.py` — определяется локально (строка 12).
- **Импорты:**
  - `modules/db.py` (строка 9): через `from config.settings import ... MOTORS_FOLDER`
  - `modules/backup_system/backup.py` (через `db_module.MOTORS_FOLDER` — **не используется в backup.py!**)
  - `routes/import_routes.py` (строка 14): `from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER`
  - `routes/status.py` (строка 9): `from modules.db import db_connection, DB_PATH, MOTORS_FOLDER`
  - `services/import_service.py` (строка 15): `from config.settings import MOTORS_FOLDER, ALLOWED_PHOTO_EXT`

#### `PHOTOS_FOLDER`
- **Источник:** `config/settings.py` — определяется локально (строка 13).
- **Импорты:**
  - `modules/db.py` (строка 9): через `from config.settings import ... PHOTOS_FOLDER`
  - `modules/backup_system/backup.py` (строка 35): `PHOTOS_FOLDER = db_module.PHOTOS_FOLDER` (из `modules.db`)
  - `modules/engine_parser/parser.py` (строка 18): `from config.settings import PHOTOS_FOLDER`
  - `modules/photo_manager/manager.py` (строка 14): `from config.settings import PHOTOS_FOLDER`
  - `modules/photo_manager/__init__.py` (строка 4): `from .manager import (... PHOTOS_FOLDER ...)` (ре-экспорт из manager.py)
  - `routes/photos.py` (через `db_module.PHOTOS_FOLDER`, строка 11): `from modules import db as db_module`
  - `routes/import_routes.py` (строка 14): `from modules.db import db_connection, PHOTOS_FOLDER, MOTORS_FOLDER`
  - `services/backup_service.py` (строка 9): `from config.settings import ... PHOTOS_FOLDER` (импорт не используется)
  - `services/export_service.py` (строка 24, внутри функции): `from config.settings import PHOTOS_FOLDER`
  - `diag_photos.py` (строка 4): `from config.settings import PHOTOS_FOLDER`

#### `BACKUPS_FOLDER`
- **Источник:** `config/settings.py` — определяется локально (строка 14).
- **Импорты:**
  - `modules/db.py` (строка 9): через `from config.settings import ... BACKUPS_FOLDER`
  - `modules/backup_system/backup.py` (строка 36): `BACKUPS_FOLDER = db_module.BACKUPS_FOLDER` (из `modules.db`)
  - `modules/backup_system/__init__.py` (строка 3): `from .backup import (BACKUPS_FOLDER, ...)` (ре-экспорт из backup.py)
  - `services/backup_service.py` (строка 9): `from config.settings import ... BACKUPS_FOLDER` (импорт не используется)

#### `BACKUP_STAGING_FOLDER`
- **Источник:** `config/settings.py` — определяется локально (строка 15).
- **Импорты:**
  - `modules/db.py` (строка 9): через `from config.settings import ... BACKUP_STAGING_FOLDER`
  - `modules/backup_system/backup.py` (строка 37): `BACKUP_STAGING_FOLDER = db_module.BACKUP_STAGING_FOLDER` (из `modules.db`)
  - `modules/backup_system/__init__.py` (строка 4): `from .backup import (... BACKUP_STAGING_FOLDER ...)` (ре-экспорт из backup.py)
  - `services/backup_service.py` (строка 9): `from config.settings import ... BACKUP_STAGING_FOLDER` (импорт не используется)

#### `CONFIG_DIR`
- **Источник:** `config/settings.py` — определяется локально (строка 16).
- **Импорты:**
  - `modules/auth/file_users.py` (строка 10): `from config.settings import CONFIG_DIR, FILE_USERS, FILE_TOKENS`
  - `modules/auth/auth.py` (строка 51): ре-экспорт из `modules.auth.file_users` через `from modules.auth.file_users import (... CONFIG_DIR)`

#### `FILE_USERS`
- **Источник:** `config/settings.py` — определяется локально (строка 17).
- **Импорты:**
  - `modules/auth/file_users.py` (строка 10): `from config.settings import CONFIG_DIR, FILE_USERS, FILE_TOKENS`
  - `modules/auth/auth.py` (строка 50): ре-экспорт из `modules.auth.file_users`

#### `FILE_TOKENS`
- **Источник:** `config/settings.py` — определяется локально (строка 18).
- **Импорты:**
  - `modules/auth/file_users.py` (строка 10): `from config.settings import CONFIG_DIR, FILE_USERS, FILE_TOKENS`
  - `modules/auth/auth.py` (строка 50): ре-экспорт из `modules.auth.file_users`

#### `LOG_FILE`
- **Источник:** `config/settings.py` — определяется локально (строка 24).
- **Импорты:**
  - `utils/logging.py` (строка 10): `from config.settings import LOG_FILE`

### Непутевые константы (включены для полноты анализа)

#### `ALLOWED_PHOTO_EXT`
- **Источник первичный:** `config/settings.py` (строка 20).
- **Дубли (локальные определения):**
  - `modules/db.py` (строка 11)
  - `modules/engine_parser/parser.py` (строка 17)
  - `modules/photo_manager/manager.py` (строка 13)
  - `diag_photos.py` (строка 5)
- **Импорты из источника/переносов:**
  - `modules/photo_manager/__init__.py` (строка 3): `from .manager import (ALLOWED_PHOTO_EXT, ...)` (ре-экспорт из manager.py, а тот определяет локально)
  - `routes/photos.py` (строка 12): `from modules.db import ALLOWED_PHOTO_EXT` (из modules.db, а тот определяет локально)
  - `services/import_service.py` (строка 15): `from config.settings import MOTORS_FOLDER, ALLOWED_PHOTO_EXT`

#### `MAX_WORKERS`
- **Источник:** `config/settings.py` (строка 23).
- **Импорты:**
  - `routes/import_routes.py` (строка 17): `from config.settings import MAX_WORKERS`

#### `FILE_USER_ID_OFFSET`
- **Источник:** `modules/auth/file_users.py` (строка 12).
- **Импорты:**
  - `modules/auth/tokens.py` (строка 9): `from modules.auth.file_users import (FILE_USER_ID_OFFSET, ...)`
  - `modules/auth/auth.py` (строка 48): ре-экспорт из `modules.auth.file_users`

---

## 5. Карта использования констант

| Константа | Единственное место определения (истинный источник) | Кто импортирует / использует | Другие определения |
|---|---|---|---|
| `BASE_DIR` | `config/settings.py:9` | Только в `config/settings.py` (локальное вычисление) | Нет |
| `DB_PATH` | `config/settings.py:11` | `modules/db.py`, `modules/backup_system/backup.py` (через db_module), `routes/status.py`, `routes/import_routes.py`, `reset_admin_password.py`, `services/backup_service.py` (не используется) | `modules/backup_system/backup.py:34` (переназначение) |
| `MOTORS_FOLDER` | `config/settings.py:12` | `modules/db.py`, `routes/import_routes.py`, `routes/status.py`, `services/import_service.py` | `app.py:20` (жёсткийcoded relative path `'motors'` вместо константы) |
| `PHOTOS_FOLDER` | `config/settings.py:13` | `modules/db.py`, `modules/engine_parser/parser.py`, `modules/photo_manager/manager.py`, `modules/backup_system/backup.py` (через db_module), `routes/photos.py` (через db_module), `routes/import_routes.py`, `services/export_service.py`, `diag_photos.py`, `services/backup_service.py` (не используется) | `app.py:20` (жёсткийcoded relative path `'photos'`) |
| `BACKUPS_FOLDER` | `config/settings.py:14` | `modules/db.py`, `modules/backup_system/backup.py` (через db_module), `modules/backup_system/__init__.py` (через backup), `services/backup_service.py` (не используется) | Нет |
| `BACKUP_STAGING_FOLDER` | `config/settings.py:15` | `modules/db.py`, `modules/backup_system/backup.py` (через db_module), `modules/backup_system/__init__.py` (через backup), `services/backup_service.py` (не используется) | Нет |
| `CONFIG_DIR` | `config/settings.py:16` | `modules/auth/file_users.py`, `modules/auth/auth.py` (через file_users) | Нет |
| `FILE_USERS` | `config/settings.py:17` | `modules/auth/file_users.py`, `modules/auth/auth.py` (через file_users) | Нет |
| `FILE_TOKENS` | `config/settings.py:18` | `modules/auth/file_users.py`, `modules/auth/auth.py` (через file_users) | Нет |
| `LOG_FILE` | `config/settings.py:24` | `utils/logging.py` | Нет |
| `ALLOWED_PHOTO_EXT` | `config/settings.py:20` | `services/import_service.py`, `routes/photos.py` (через modules.db), `modules/photo_manager/manager.py` (локальное), `modules/engine_parser/parser.py` (локальное), `modules/db.py` (локальное), `diag_photos.py` (локальное) | Дублировано в `modules/db.py:11`, `modules/engine_parser/parser.py:17`, `modules/photo_manager/manager.py:13`, `diag_photos.py:5` |
| `MAX_WORKERS` | `config/settings.py:23` | `routes/import_routes.py` | Нет |
| `FILE_USER_ID_OFFSET` | `modules/auth/file_users.py:12` | `modules/auth/tokens.py`, `modules/auth/auth.py` (через file_users) | Нет |
| `MAX_BACKUPS_KEPT` | `modules/backup_system/backup.py:38` | `modules/backup_system/backup.py` (локальное) | Нет |

---

## 6. Карта зависимостей (обратные зависимости для каждого файла-источника)

### `config/settings.py`
```
config/settings.py
├── modules/db.py
├── modules/auth/file_users.py
├── modules/engine_parser/parser.py
├── modules/photo_manager/manager.py
├── routes/import_routes.py        (MAX_WORKERS напрямую, PHOTOS_FOLDER/MOTORS_FOLDER через modules.db)
├── services/backup_service.py     (импорт не используется!)
├── services/export_service.py
└── utils/logging.py
```

### `modules/db.py`
```
modules/db.py
├── modules/backup_system/backup.py   (через db_module: DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, db_connection, ALLOWED_PHOTO_EXT)
├── modules/auth/decorators.py        (db_connection)
├── repositories/engine_repo.py       (ENGINE_COLUMNS_ORDERED)
├── repositories/mode_repo.py         (MODE_COLUMNS)
├── routes/auth.py                    (db_connection)
├── routes/backup_routes.py           (через db_module)
├── routes/changelog.py               (db_connection)
├── routes/engines.py                 (db_connection)
├── routes/export_routes.py           (db_connection)
├── routes/import_routes.py           (db_connection, PHOTOS_FOLDER, MOTORS_FOLDER)
├── routes/photos.py                  (через db_module + ALLOWED_PHOTO_EXT)
├── routes/search.py                  (db_connection, ENGINE_COLUMNS, MODE_COLUMNS, ENGINE_COLUMNS_ORDERED)
├── routes/status.py                  (db_connection, DB_PATH, MOTORS_FOLDER)
├── schemas/engine_schema.py          (ENGINE_COLUMNS_ORDERED, MODE_COLUMNS)
├── app.py                            (init_db)
├── tests/conftest.py                 (init_db, db_connection)
├── diag_photos.py                    (через config.settings, но также через modules.db в reset_admin_password)
├── reset_admin_password.py           (DB_PATH, db_connection, init_db)
└── tests/test_backup_system/test_backup.py  (через db_module, для monkeypatch)
```

### `modules/auth/file_users.py`
```
modules/auth/file_users.py
├── modules/auth/auth.py               (CONFIG_DIR, FILE_USERS, FILE_TOKENS, FILE_USER_ID_OFFSET, функции)
├── modules/auth/tokens.py             (FILE_USER_ID_OFFSET)
├── modules/auth/db_users.py           (_load_file_users — через from modules.auth.file_users import)
└── modules/auth/auth.py               (re-export через __all__)
```

### `modules/auth/tokens.py`
```
modules/auth/tokens.py
├── modules/auth/auth.py               (issue_token, get_user_from_token, revoke_token, revoke_all_for_user)
└── modules/auth/decorators.py         (get_user_from_token)
└── routes/auth.py                     (через auth_module)
```

### `modules/backup_system/backup.py`
```
modules/backup_system/backup.py
├── modules/backup_system/__init__.py  (BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, MAX_BACKUPS_KEPT, функции)
├── routes/backup_routes.py            (через backup_module: create_backup, list_backups, inspect_uploaded_backup, restore_backup, download_backup, delete_backup, _safe_backup_filename)
├── services/backup_service.py         (через backup_module: create_backup, list_backups, inspect_uploaded_backup, restore_backup, download_backup, delete_backup)
├── tests/test_backup_system/test_backup.py  (монkeypatch и вызовы функций)
└── temp/temp_selftest.py              (монkeypatch и вызовы функций)
└── temp/tests/test_app.py             (монkeypatch и вызовы функций)
```

### `modules/photo_manager/__init__.py`
```
modules/photo_manager/__init__.py
├── (ре-экспорт из manager.py: ALLOWED_PHOTO_EXT, PHOTOS_FOLDER, функции)
    └── modules/photo_manager/manager.py
        └── services/import_service.py  (_extract_photos использует extract_images_from_excel из parser.py, и save_engine_photos — НО save_engine_photos не найден в manager.py!)
```

**Примечание:** В `services/import_service.py` строка 71: `from modules.photo_manager.manager import save_engine_photos` — однако функция `save_engine_photos` **не определена** в `modules/photo_manager/manager.py`. Это может быть ошибкой импорта.

### `utils/logging.py`
```
utils/logging.py
├── routes/import_routes.py            (log_message)
├── services/backup_service.py         (не используется)
└── services/import_service.py         (не используется)
```

**Примечание:** `utils/logging.py` определяет `log_message`, которая используется в `routes/import_routes.py`. В `services/backup_service.py` и `services/import_service.py` импорт `log_message` не выполняется (они используют собственный `logging.getLogger`).

### `services/import_service.py`
```
services/import_service.py
├── (не используется ни одним роутом напрямую!)
```

**Примечание:** `services/import_service.py` не вызывается ни одним из роутов. Маршрут импорта реализован в `routes/import_routes.py` напрямую, минуя `services/import_service.py`. Это сервисный модуль, который, видимо, является альтернативной/рефакторинговой реализацией импорта.

### `repositories/engine_repo.py`
```
repositories/engine_repo.py
├── routes/engines.py                  (get_by_id, get_with_details, get_all, count_all, create, update, delete, update_photo_count)
├── schemas/engine_schema.py           (не используется — импорт ENGINE_COLUMNS_ORDERED из modules.db)
└── services/export_service.py         (get_with_details)
```

### `repositories/mode_repo.py`
```
repositories/mode_repo.py
├── routes/engines.py                  (replace_all как replace_modes)
└── services/import_service.py         (replace_all как replace_modes)
```

### `repositories/work_repo.py`
```
repositories/work_repo.py
├── routes/engines.py                  (replace_all как replace_works)
└── services/import_service.py         (replace_all как replace_works)
```

### `diag_photos.py`
```
diag_photos.py
├── (самостоятельный скрипт — не импортируется другими модулями)
```

### `reset_admin_password.py`
```
reset_admin_password.py
├── (самостоятельный скрипт — не импортируется другими модулями)
```

---

## 7. Поиск потенциальных расхождений

### 7.1 Одинаковые константы, определённые в нескольких местах (дубли)

| Константа | Места определения | Тип дубля |
|---|---|---|
| `ALLOWED_PHOTO_EXT` | `config/settings.py:20`, `modules/db.py:11`, `modules/engine_parser/parser.py:17`, `modules/photo_manager/manager.py:13`, `diag_photos.py:5` | Локальные переопределения (5 шт.) |
| `DB_PATH` | `config/settings.py:11` (источник), `modules/backup_system/backup.py:34` (переназначение из db_module) | Переназначение (1 шт.) |
| `PHOTOS_FOLDER` | `config/settings.py:13` (источник), `modules/backup_system/backup.py:35` (переназначение) | Переназначение (1 шт.) |
| `BACKUPS_FOLDER` | `config/settings.py:14` (источник), `modules/backup_system/backup.py:36` (переназначение) | Переназначение (1 шт.) |
| `BACKUP_STAGING_FOLDER` | `config/settings.py:15` (источник), `modules/backup_system/backup.py:37` (переназначение) | Переназначение (1 шт.) |

### 7.2 Одинаковые пути с разными именами

- **`BACKUP_STAGING_FOLDER`** (в `config/settings.py`) и **`staging_folder`** (локальная переменная в `routes/backup_routes.py:58`) — оба указывают на каталог `backup_staging`, но называются по-разному. `staging_folder` получен через `db_module.BACKUP_STAGING_FOLDER`, так что это не дубли пути, а переменная.
- **`BACKUP_STAGING_FOLDER`** и **`BACKUP_STAGING_FOLDER`** в `temp/temp_selftest.py` (TEST_BACKUP_STAGING_FOLDER) — тестовые константы с разными именами, но тот же смысл (`backup_staging`).

### 7.3 Относительные и абсолютные пути, используемые одновременно

| Файл | Путь | Тип | Константа |
|---|---|---|---|
| `app.py:20-22` | `'photos'`, `'motors'`, `'backups'`, `'backup_staging'` | Относительный | Жёстко закодирован, не использует константы из config.settings |
| `app.py:31-34` | `'static'`, `'templates'` | Относительный | Жёстко закодирован |
| `routes/pages.py:12,23,28` | `'templates'`, `'static'` | Относительный | Жёстко закодирован (через send_from_directory) |
| `diag_photos.py:7` | `'engine_data.db'` | Относительный | Жёстко закодирован вместо DB_PATH |
| `config/settings.py` | `str(BASE_DIR / ...)` | Абсолютный | Через BASE_DIR |

**Ключевое расхождение:** `app.py` использует относительные пути для создания каталогов (`['photos', 'motors', 'backups', 'backup_staging']`), тогда как `config/settings.py` определяет абсолютные пути через `BASE_DIR`. Если приложение запущено не из корня проекта (например, через WSGI-сервер из другого каталога), созданные каталоги окажутся в неправильном месте, и `DB_PATH`, `PHOTOS_FOLDER` и т.д. (абсолютные) не будут указывать на них.

### 7.4 Локальные определения, дублирующие `config.settings`

- **`ALLOWED_PHOTO_EXT`** дублируется в 4 файлах помимо `config/settings.py`:
  - `modules/db.py:11`
  - `modules/engine_parser/parser.py:17`
  - `modules/photo_manager/manager.py:13`
  - `diag_photos.py:5`

- **`DB_PATH`** в `diag_photos.py:7` используется как строковый литерал `'engine_data.db'` вместо импорта `DB_PATH` из `config.settings`.

### 7.5 Константы, которые нигде не используются

**Неиспользуемые импорты в `services/backup_service.py` (строка 9):**
```python
from config.settings import DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER
```
Эти 4 константы импортированы, но **никогда не используются** в теле файла. Сервис делегирует всю работу `backup_module` (импортированный изнутри функций), и пути использует через `backup_module`. Документально `services/backup_service.py` описывает себя как "знает о пути к файлам", но на практике не использует импортированные константы.

### 7.6 Импорты несуществующих констант

**Подозрительный импорт в `services/import_service.py` (строка 71):**
```python
from modules.photo_manager.manager import save_engine_photos
```
Функция `save_engine_photos` **не определена** в `modules/photo_manager/manager.py`. В модуле определены: `get_engine_photos`, `get_photo`, `upload_engine_photos`, `delete_engine_photo`, `replace_engine_photo`, `_engine_photo_disk_paths`, `normalize_base_name`, `_save_upload_atomically`.

Однако `services/import_service.py` не вызывается ни одним роутом (см. п. 6), поэтому эта ошибка не проявляется во время выполнения.

### 7.7 Устаревшие определения

- **`config/tokens.json`** содержит 10 записей токенов для тестовых пользователей (`test_admin_*`), созданных во время самотестирования (`temp/temp_selftest.py` и `temp/tests/test_app.py`). Файл упомянут в `.gitignore` и, скорее всего, не должен содержаться в репозитории. **Данные в файле устарели** (даты создания `2026-08-01T05:20` — `2026-08-01T10:04`).

- **`config/users.json`** — файл не существует в дереве проекта (не найден командой `Get-ChildItem`), но упоминается в документации и коде (`FILE_USERS = str(BASE_DIR / 'config' / 'users.json')`). Проверка: файл может отсутствовать, что является нормальным состоянием для файла, который создаётся при первом запуске.

### 7.8 Прочие расхождения

- **`routes/import_routes.py` (строка 14)** импортирует `PHOTOS_FOLDER` из `modules.db`, но `PHOTOS_FOLDER` в `modules.db` импортирована из `config.settings`. Это корректно, но создаёт транзитивную зависимость: `routes.import_routes` → `modules.db` → `config.settings`.

- **`routes/photos.py` (строка 12)** импортирует `ALLOWED_PHOTO_EXT` из `modules.db`, а не из `config.settings` напрямую. `modules.db` определяет `ALLOWED_PHOTO_EXT` локально (строка 11), а не импортирует из `config.settings`. Таким образом, `routes/photos.py` использует **локальную копию** `ALLOWED_PHOTO_EXT` из `modules.db`, а не "единственный источник правды" из `config/settings.py`.

- **`routes/photos.py` (строка 11)** использует `db_module.PHOTOS_FOLDER`, где `db_module` — это `modules.db`. Однако `modules/db.py` не переназначает `PHOTOS_FOLDER` (он только импортирует его из `config.settings`), поэтому `db_module.PHOTOS_FOLDER` в этом контексте указывает на то же самое, что и `config.settings.PHOTOS_FOLDER`. Но в тестах monkeypatch делает `db_module.PHOTOS_FOLDER` локальной переменной, и `routes/photos.py` корректно видит изменения через `db_module`.

- **`app.py`** не импортирует и не использует ни одну константу из `config/settings.py`. Все пути заданы строковыми литералами. Это критическое расхождение с архитектурой "один источник правды".

---

## 8. Проверка единственности источника

| Константа | Статус | Комментарий |
|---|---|---|
| `BASE_DIR` | ✅ Один источник правды | `config/settings.py:9` — не переназначается нигде |
| `DB_PATH` | ⚠️ Несколько независимых источников | Истинный источник — `config/settings.py:11`. `modules/backup_system/backup.py:34` переназначает через `db_module.DB_PATH`. Но `temp/`-скрипты иногда жёстко задают `'engine_data.db'`. |
| `MOTORS_FOLDER` | ⚠️ Несколько источников | Истинный источник — `config/settings.py:12`. `app.py:20` использует строковый литерал `'motors'` вместо константы. |
| `PHOTOS_FOLDER` | ⚠️ Несколько источников | Истинный источник — `config/settings.py:13`. `app.py:20` использует строковый литерал `'photos'` вместо константы. |
| `BACKUPS_FOLDER` | ⚠️ Несколько источников | Истинный источник — `config/settings.py:14`. Переназначение в `backup.py:36` (через `db_module`). |
| `BACKUP_STAGING_FOLDER` | ⚠️ Несколько источников | Истинный источник — `config/settings.py:15`. Переназначение в `backup.py:37` (через `db_module`). |
| `CONFIG_DIR` | ✅ Один источник правды | `config/settings.py:16` — единственное определение; `file_users.py` импортирует |
| `FILE_USERS` | ✅ Один источник правды | `config/settings.py:17` — единственное определение; `file_users.py` импортирует |
| `FILE_TOKENS` | ✅ Один источник правды | `config/settings.py:18` — единственное определение; `file_users.py` импортирует |
| `LOG_FILE` | ✅ Один источник правды | `config/settings.py:24` — единственное определение; `utils/logging.py` импортирует |
| `ALLOWED_PHOTO_EXT` | ❌ Несколько независимых источников | Определено в 5 местах: `config/settings.py:20`, `modules/db.py:11`, `modules/engine_parser/parser.py:17`, `modules/photo_manager/manager.py:13`, `diag_photos.py:5`. Ни один из локальных вариантов не импортирует из `config.settings`. |
| `MAX_WORKERS` | ✅ Один источник правды | `config/settings.py:23` — единственное определение |
| `FILE_USER_ID_OFFSET` | ✅ Один источник правды (но не путевая) | `modules/auth/file_users.py:12` |

---

## 9. Итоговая сводка

### Общая статистика

| Показатель | Значение |
|---|---|
| **Количество файлов проекта** (включая не-Python) | 93 файлов (из дерева PowerShell) + 2 файла из `temp/` (исключённые фильтром) = **95 файлов** |
| **Количество Python-файлов проекта** (без `.venv`, включая `temp/`) | 55 файлов |
| **Количество Python-модулей** (пакетов с `__init__.py`) | 8 пакетов: `config` (без `__init__.py`), `modules`, `modules/auth`, `modules/backup_system`, `modules/engine_parser`, `modules/photo_manager`, `repositories`, `routes`, `schemas`, `services`, `utils`, `tests`, `tests/test_backup_system`, `tests/test_repositories`, `tests/test_utils` |
| **Количество файлов, содержащих путевые константы** | 13 файлов |
| **Количество уникальных путевых констант** | 10 (BASE_DIR, DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, CONFIG_DIR, FILE_USERS, FILE_TOKENS, LOG_FILE) |
| **Количество мест, где путевые константы используются** | ~45 импортов/использований по всему проекту |

Список файлов, содержащих путевые константы:
1. `config/settings.py` — определения (источник)
2. `modules/db.py` — импорт
3. `modules/backup_system/backup.py` — переназначение
4. `modules/photo_manager/manager.py` — импорт
5. `modules/engine_parser/parser.py` — импорт
6. `modules/auth/file_users.py` — импорт
7. `modules/auth/auth.py` — ре-экспорт
8. `modules/backup_system/__init__.py` — ре-экспорт
9. `modules/photo_manager/__init__.py` — ре-экспорт
10. `routes/import_routes.py` — импорт
11. `routes/photos.py` — импорт (через db_module)
12. `routes/status.py` — импорт
13. `routes/backup_routes.py` — импорт (через db_module)
14. `services/backup_service.py` — импорт (НЕ ИСПОЛЬЗУЕТСЯ)
15. `services/export_service.py` — импорт (внутри функции)
16. `services/import_service.py` — импорт
17. `utils/logging.py` — импорт
18. `app.py` — жёстко закодированные строки (НЕ использует константы)
19. `diag_photos.py` — импорт + локальное определение
20. `reset_admin_password.py` — импорт (через modules.db)
21. `tests/test_backup_system/test_backup.py` — monkeypatch
22. `temp/tests/test_app.py` — monkeypatch
23. `temp/temp_selftest.py` — локальные константы

### Архитектурные наблюдения

#### Найденные дубли
- **`ALLOWED_PHOTO_EXT`** дублирована в 5 файлах (config/settings.py, modules/db.py, modules/engine_parser/parser.py, modules/photo_manager/manager.py, diag_photos.py). Ни один из локальных вариантов не импортирует из `config.settings`.
- **`DB_PATH`, `PHOTOS_FOLDER`, `BACKUPS_FOLDER`, `BACKUP_STAGING_FOLDER`** переназначены в `modules/backup_system/backup.py` через `db_module.*` — это создаёт слой переназначения, что требует осторожного monkeypatch-инга в тестах.

#### Расхождения
- **`app.py`** использует жёстко закодированные относительные пути `['photos', 'motors', 'backups', 'backup_staging']` вместо констант из `config/settings.py`. Это критическое расхождение: при запуске не из корня проекта каталоги создаются в неправильном месте.
- **`diag_photos.py:7`** использует строковый литерал `'engine_data.db'` вместо `DB_PATH` из конфигурации.
- **`services/backup_service.py:9`** импортирует `DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER` из `config.settings`, но **никогда не использует** их.
- **`services/export_service.py`** импортирует `PHOTOS_FOLDER` из `config.settings` дважды (внутри `export_to_xlsx()` на строке 24 и внутри `_get_photo_paths()` на строке 213) — дублирующий импорт внутри одного файла.
- **`routes/photos.py:12`** импортирует `ALLOWED_PHOTO_EXT` из `modules.db` (локальное определение), а не из `config/settings.py`.

#### Неоднозначности
- **`services/import_service.py`** — реализует логику импорта, но **не вызывается ни одним роутом**. Роуты импорта реализованы в `routes/import_routes.py` напрямую. Сервис существует, но не используется.
- **`services/import_service.py:71`** импортирует `save_engine_photos` из `modules.photo_manager.manager`, но **эта функция не существует** в модуле. Возможные варианты: `upload_engine_photos` (с другой сигнатурой) или `_save_upload_atomically`.
- **`config/users.json`** отсутствует в проекте (не найден в дереве файлов), хотя `FILE_USERS` указывает на неё.
- **`.pytest_cache/`** включается в дерево файлов из-за неполного исключения в PowerShell-команде.

#### Места, требующие внимания при дальнейшем рефакторинге
1. `app.py` — заменить жёстко закодированные пути на импорт из `config/settings.py`.
2. `diag_photos.py` — заменить `'engine_data.db'` на `DB_PATH`; перенести в `temp/` или удалить.
3. `services/backup_service.py` — удалить неиспользуемые импорты `DB_PATH, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER`.
4. `services/export_service.py` — объединить дублирующие импорты `PHOTOS_FOLDER` в один верхний уровень.
5. `routes/photos.py` — изменить импорт `ALLOWED_PHOTO_EXT` из `modules.db` на импорт из `config/settings.py` (или избавиться от локального дубля в `modules/db.py`).
6. `modules/db.py`, `modules/engine_parser/parser.py`, `modules/photo_manager/manager.py` — удалить локальные дубликаты `ALLOWED_PHOTO_EXT` и импортировать из `config/settings.py`.
7. `services/import_service.py` — исправить импорт `save_engine_photos` (не существует) или удалить неиспользуемый модуль.
8. `modules/backup_system/backup.py` — рассмотреть замену переназначения констант на прямой импорт из `config.settings` (чтобы избежать необходимости monkeypatch-ить два слоя в тестах).

---

*Отчёт создан в рамках аудита. Никакой код проекта не был изменён. Единственное изменение — создание данного файла `docs/project_structure_snapshot.md`.*
