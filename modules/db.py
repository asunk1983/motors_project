import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

from config.settings import DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, INCIDENT_PHOTOS_FOLDER, EQUIPMENT_PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, ALLOWED_PHOTO_EXT

ENGINE_COLUMNS_ORDERED = [
    'id', 'filename', 'purpose', 'workshop', 'location', 'engine_type',
    'manufacturer', 'serial_number', 'bearing_front', 'bearing_rear',
    'shaft_diameter', 'protection_class', 'mounting_type', 'temp_sensor',
    'encoder', 'cooling', 'note', 'photo_count'
]
ENGINE_COLUMNS = frozenset(ENGINE_COLUMNS_ORDERED)

MODE_COLUMNS = frozenset([
    'frequency', 'power', 'voltage', 'connection_type', 'current', 'rpm'
])


def get_db_connection(db_path=None):
    """Создаёт соединение с SQLite.

    db_path=None — использует DB_PATH из config.settings (production).
    db_path=':memory:' — для тестов (in-memory SQLite).
    """
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


@contextmanager
def db_connection(db_path=None):
    """Контекст-менеджер для соединения с БД.

    db_path=None — production (DB_PATH).
    db_path=':memory:' — in-memory для тестов.
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def _ensure_column(cursor, table, column, definition):
    """Добавляет колонку в таблицу, если она ещё не существует (auto-migration)."""
    cursor.execute(f'PRAGMA table_info({table})')
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def init_db(conn=None):
    """Инициализирует схему БД.

    conn=None — создаёт собственное соединение (production).
    conn=<sqlite3.Connection> — использует переданное соединение (тесты).
    """
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                purpose TEXT,
                workshop TEXT,
                location TEXT,
                engine_type TEXT,
                manufacturer TEXT,
                serial_number TEXT,
                bearing_front TEXT,
                bearing_rear TEXT,
                shaft_diameter TEXT,
                protection_class TEXT,
                mounting_type TEXT,
                temp_sensor TEXT,
                encoder TEXT,
                cooling TEXT,
                note TEXT,
                photo_count INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'work',
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operating_modes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_id INTEGER,
                frequency TEXT,
                power TEXT,
                voltage TEXT,
                connection_type TEXT,
                current TEXT,
                rpm TEXT,
                FOREIGN KEY (engine_id) REFERENCES engines (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_id INTEGER,
                work_number TEXT,
                date TEXT,
                work_description TEXT,
                isolation TEXT,
                inspection TEXT,
                signature TEXT,
                status TEXT NOT NULL DEFAULT 'work',
                FOREIGN KEY (engine_id) REFERENCES engines (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changelog_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wishlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login TEXT,
                last_edit TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # --- База знаний по отказам (справочники + статьи) --------------
        # Полностью автономна от engines/maintenance_works — намеренно.
        # Сейчас это отдельный, не привязанный к двигателям инструмент.
        # На перспективу: привязка добавится тем же способом, что и
        # остальные auto-migration поля в этом файле — например,
        # _ensure_column(cursor, 'maintenance_works', 'failure_mode_id',
        # 'INTEGER REFERENCES failure_mode(id)') — без переделки этих
        # таблиц. failure_mode/failure_cause/knowledge_article спроектированы
        # так, чтобы не потребовать миграции данных, когда это понадобится.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_mode (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_cause (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_article (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                symptom TEXT NOT NULL,
                failure_mode_id INTEGER REFERENCES failure_mode(id),
                diagnostic_steps TEXT,
                recommended_action TEXT,
                reference_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_article_cause (
                knowledge_article_id INTEGER NOT NULL REFERENCES knowledge_article(id) ON DELETE CASCADE,
                failure_cause_id INTEGER NOT NULL REFERENCES failure_cause(id),
                PRIMARY KEY (knowledge_article_id, failure_cause_id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modes_engine ON operating_modes(engine_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_works_engine ON maintenance_works(engine_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changelog_date ON changelog_entries(entry_date)')
        for col in ('location', 'engine_type', 'manufacturer', 'serial_number', 'workshop', 'purpose'):
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_engines_{col} ON engines({col})')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_hash ON tokens(token_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ka_mode ON knowledge_article(failure_mode_id)')

        # --- Номенклатура оборудования (equipment) -----------------------
        # Полностью отдельно от engines — своя номенклатура, свои типы.
        # Разнородные характеристики решены по образцу NetBox Custom Fields
        # (JSON-хранение значений + централизованный переиспользуемый пул
        # определений атрибутов) и IBM Maximo Classifications (иерархия
        # типов с наследованием атрибутов от родительского типа).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_type (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                parent_type_id INTEGER REFERENCES equipment_type(id),
                description TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attribute_definition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                group_name TEXT,
                value_type TEXT NOT NULL DEFAULT 'text'
                    CHECK (value_type IN ('text','number','select','boolean','textarea')),
                unit TEXT,
                options_json TEXT,
                default_value TEXT,
                weight INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_type_attribute (
                equipment_type_id INTEGER NOT NULL REFERENCES equipment_type(id) ON DELETE CASCADE,
                attribute_definition_id INTEGER NOT NULL REFERENCES attribute_definition(id) ON DELETE CASCADE,
                is_required INTEGER NOT NULL DEFAULT 0,
                weight_override INTEGER,
                PRIMARY KEY (equipment_type_id, attribute_definition_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type_id INTEGER NOT NULL REFERENCES equipment_type(id),
                name TEXT NOT NULL,
                article TEXT,
                manufacturer TEXT,
                serial_number TEXT,
                workshop TEXT,
                location TEXT,
                firmware_version TEXT,
                criticality INTEGER CHECK (criticality BETWEEN 1 AND 5),
                installed_at TEXT,
                specs_json TEXT,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_type_parent ON equipment_type(parent_type_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_eta_type ON equipment_type_attribute(equipment_type_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(equipment_type_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_workshop ON equipment(workshop)')

        # equipment_placement — экземпляры оборудования по местам со схемными
        # обозначениями (ТЗ "Место"). НЕ путать с equipment.location_node_id
        # (единственное "основное" место записи, используется деревом слева
        # и /api/equipment?location_node_id= для навигации/фильтра — эта
        # логика не меняется). equipment_placement — дополнительная, более
        # детальная раскладка: одна карточка оборудования (например, "Пускатель
        # КМ", модель/артикул) физически стоит в НЕСКОЛЬКИХ местах, а в
        # пределах одного места может быть несколько экземпляров с разными
        # схемными обозначениями (пример из ТЗ: шкаф +E021, КМ1/КМ2/КМ3 —
        # 3 строки в этой таблице с одним и тем же location_node_id).
        #
        # Схемные обозначения НЕ становятся узлами location_node — их будет
        # на порядки больше, чем реальных мест, это раздуло бы общее дерево
        # (используется тремя вкладками — 17.2/16.7 в снимке проекта).
        # designation хранится как обычный атрибут связи.
        #
        # ON DELETE CASCADE у equipment_id — при удалении оборудования его
        # места удаляются вместе с ним (аналог того, как удаляются фото —
        # equipment_manager.delete_equipment_photos_from_disk). Без CASCADE
        # у location_node_id (как и у equipment.location_node_id) — узел
        # дерева нельзя удалить, если на него ссылается placement (см.
        # location_repo.is_referenced, дополняется ниже).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_placement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
                location_node_id INTEGER NOT NULL REFERENCES location_node(id),
                designation TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_placement_equipment ON equipment_placement(equipment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_placement_location ON equipment_placement(location_node_id)')
        # Схемное обозначение уникально В ПРЕДЕЛАХ одного места (ТЗ) — но
        # НЕ глобально (КМ1 может стоять и в +E021, и в +E022). Частичный
        # уникальный индекс: WHERE designation IS NOT NULL — в SQLite NULL
        # никогда не равен NULL, поэтому без этого условия несколько строк
        # с designation=NULL в одном месте всё равно не конфликтовали бы
        # между собой, условие здесь для ясности замысла, а не по необходимости.
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_equipment_placement_unique_designation
            ON equipment_placement(location_node_id, designation)
            WHERE designation IS NOT NULL
        ''')

        # --- Заявки -> Отказы -> Работы -------------------------------
        # ticket ≠ failure: заявка — сырое обращение, не каждая станет
        # подтверждённым отказом. equipment_work существует только через
        # failure (см. обсуждение) — если заявка не подтвердилась, работ
        # по ней не бывает, только закрытие с rejection_reason.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER REFERENCES equipment(id),
                created_by_user_id INTEGER REFERENCES users(id),
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'new',
                title TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                closed_at TEXT,
                rejected_at TEXT,
                rejection_reason TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES ticket(id),
                equipment_id INTEGER NOT NULL REFERENCES equipment(id),
                failure_mode_id INTEGER REFERENCES failure_mode(id),
                failure_cause_id INTEGER REFERENCES failure_cause(id),
                knowledge_article_id INTEGER REFERENCES knowledge_article(id),
                symptom TEXT,
                description TEXT,
                confirmed INTEGER NOT NULL DEFAULT 0,
                occurred_at TEXT,
                restored_at TEXT,
                downtime_minutes INTEGER GENERATED ALWAYS AS (
                    CASE WHEN restored_at IS NOT NULL AND occurred_at IS NOT NULL
                         THEN CAST((julianday(restored_at) - julianday(occurred_at)) * 1440 AS INTEGER)
                         ELSE NULL END
                ) STORED,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_action_type (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                is_software INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_work (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                failure_id INTEGER NOT NULL REFERENCES failure(id) ON DELETE CASCADE,
                action_type_id INTEGER REFERENCES maintenance_action_type(id),
                executor_user_id INTEGER REFERENCES users(id),
                description TEXT,
                result TEXT,
                successful INTEGER,
                version_from TEXT,
                version_to TEXT,
                parameter_changed TEXT,
                old_value TEXT,
                new_value TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticket_equipment ON ticket(equipment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticket_status ON ticket(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticket_created ON ticket(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_failure_ticket ON failure(ticket_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_failure_equipment ON failure(equipment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_work_failure ON equipment_work(failure_id)')

        # --- Дерево мест (location_node) -------------------------------
        # Общий ресурс уровня всего проекта (ТЗ "Инциденты + Оборудование",
        # раздел 1) — НЕ принадлежит ни одному конкретному модулю,
        # применяется первым из всех новых шагов. 'warehouse' включён в
        # CHECK сразу, с первой версии таблицы (понадобится для будущего
        # раздела "Учёт ЗИП"), чтобы не пересобирать таблицу под CHECK
        # второй раз — SQLite не умеет менять CHECK через обычный ALTER TABLE.
        # UNIQUE(parent_id, name) не защищает корневые узлы от дублей
        # (NULL != NULL для UNIQUE в SQLite) — риск известен и принят.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_node (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER REFERENCES location_node(id),
                name TEXT NOT NULL,
                node_type TEXT CHECK (node_type IN
                    ('workshop','installation','unit','zone','warehouse','other')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(parent_id, name)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_parent ON location_node(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_name ON location_node(name)')

        # --- Модуль "Инциденты" -----------------------------------------
        # Личный журнал диагностики отказов (замена Excel) — отдельно от
        # ticket/failure выше (тот сценарий — формализованный протокол
        # ремонта типизированной единицы оборудования с измерениями;
        # этот — свободная запись "что/где/кто/как решили"). Модули НЕ
        # смешиваются ни в БД, ни в UI (см. ТЗ "Инциденты", раздел 0).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crew (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                position TEXT,
                workshop TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_crew_name ON crew(full_name)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incident_ticket (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_node_id INTEGER NOT NULL REFERENCES location_node(id),
                problem TEXT NOT NULL,
                solution TEXT,
                priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
                status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','resolved','rejected')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                closed_at TEXT,
                created_by_user_id INTEGER NOT NULL REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incident_status ON incident_ticket(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incident_location ON incident_ticket(location_node_id)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incident_ticket_initiator (
                ticket_id INTEGER NOT NULL REFERENCES incident_ticket(id) ON DELETE CASCADE,
                crew_id INTEGER NOT NULL REFERENCES crew(id),
                PRIMARY KEY (ticket_id, crew_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incident_ticket_executor (
                ticket_id INTEGER NOT NULL REFERENCES incident_ticket(id) ON DELETE CASCADE,
                crew_id INTEGER NOT NULL REFERENCES crew(id),
                PRIMARY KEY (ticket_id, crew_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incident_ticket_equipment (
                ticket_id INTEGER NOT NULL REFERENCES incident_ticket(id) ON DELETE CASCADE,
                equipment_id INTEGER NOT NULL REFERENCES equipment(id),
                PRIMARY KEY (ticket_id, equipment_id)
            )
        ''')

        # Только ссылки — фото идут файловым паттерном PhotoI/, не через БД.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incident_ticket_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES incident_ticket(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                caption TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_ticket ON incident_ticket_link(ticket_id)')

        # Auto-migration: добавляем новые колонки, если БД была создана ранее
        _ensure_column(cursor, 'users', 'last_login', 'TEXT')
        _ensure_column(cursor, 'users', 'last_edit', 'TEXT')
        _ensure_column(cursor, 'engines', 'created_at', 'TEXT')
        _ensure_column(cursor, 'engines', 'updated_at', 'TEXT')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_updated_at ON engines(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_created_at ON engines(created_at)')

        # status — эксплуатационное состояние двигателя: work/reserve/repair
        # (в работе/в резерве/в ремонте). ADD COLUMN с DEFAULT в SQLite
        # заполняет им и уже существующие строки, отдельный backfill не нужен.
        _ensure_column(cursor, 'engines', 'status', "TEXT NOT NULL DEFAULT 'work'")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_status ON engines(status)')

        # maintenance_works.status — тот же словарь состояний, что и у
        # engines.status (work/reserve/repair): в каком состоянии
        # оказался двигатель по итогам этой работы (например, "ремонт"
        # для записи о выводе в ремонт, "в работе" — для ввода обратно).
        _ensure_column(cursor, 'maintenance_works', 'status', "TEXT NOT NULL DEFAULT 'work'")

        # knowledge_article <-> equipment_type: статья привязывается к КЛАССУ
        # оборудования (не к конкретному экземпляру) — статья про перегрев
        # ЧРП актуальна для всех ЧРП этого типа, а не для одной серийной
        # единицы. NULL допустим — общая статья без привязки к типу.
        # resolution_type — прямой ответ на "чинится софтом или руками",
        # см. обсуждение при проектировании equipment: причина, по которой
        # вообще понадобилась универсальная номенклатура вместо engines.
        _ensure_column(cursor, 'knowledge_article', 'equipment_type_id', 'INTEGER REFERENCES equipment_type(id)')
        _ensure_column(cursor, 'knowledge_article', 'resolution_type', "TEXT NOT NULL DEFAULT 'HARDWARE'")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ka_equipment_type ON knowledge_article(equipment_type_id)')

        # equipment -> location_node (ТЗ "Инциденты + Оборудование", раздел
        # 3.1). workshop/location (TEXT) остаются на переходный период —
        # старые записи мигрируются одноразовым скриптом
        # (services/equipment_location_migration.py::migrate_equipment_locations),
        # НЕ здесь в init_db() — миграция данных требует явного запуска
        # (не должна молча срабатывать при каждом старте приложения).
        _ensure_column(cursor, 'equipment', 'location_node_id', 'INTEGER REFERENCES location_node(id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipment_location_node ON equipment(location_node_id)')

        # equipment_type_attribute.show_in_list — ТЗ раздел 3.2: 2-3
        # "главных" атрибута на тип становятся динамическими колонками
        # таблицы номенклатуры (когда выбран конкретный тип, не "Все типы").
        _ensure_column(cursor, 'equipment_type_attribute', 'show_in_list', 'INTEGER NOT NULL DEFAULT 0')

        # equipment_type.min_stock_qty — ТЗ раздел 3.7 (учёт ЗИП): норма
        # пополнения запаса, свойство ТИПА (политика), не физической
        # единицы и не места. NULL = норма не задана (не путать с 0 =
        # "норма ноль, докупать не нужно") — поэтому INTEGER без
        # NOT NULL/DEFAULT.
        _ensure_column(cursor, 'equipment_type', 'min_stock_qty', 'INTEGER')

        # Backfill для записей, созданных до появления этих колонок —
        # реальная историческая дата создания неизвестна, поэтому проставляем
        # момент миграции. Это разовая операция (WHERE ... IS NULL — на
        # уже заполненные строки повторно не влияет), но означает, что все
        # "старые" двигатели после первого запуска этой версии будут иметь
        # одинаковые created_at/updated_at — сортировка "по дате изменения"
        # станет содержательной только для записей, отредактированных ПОСЛЕ
        # этого момента.
        cursor.execute('SELECT COUNT(*) FROM engines WHERE created_at IS NULL OR updated_at IS NULL')
        if cursor.fetchone()[0] > 0:
            backfill_ts = datetime.now().isoformat()
            cursor.execute(
                'UPDATE engines SET created_at = COALESCE(created_at, ?), '
                'updated_at = COALESCE(updated_at, ?) '
                'WHERE created_at IS NULL OR updated_at IS NULL',
                (backfill_ts, backfill_ts)
            )
            logger.warning('Проставлены created_at/updated_at для двигателей без даты (backfill: %s)', backfill_ts)

        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            from modules.auth import auth as auth_module
            auth_module.create_user(conn, 'admin', 'admin123', role='admin')
            logger.warning('Создан пользователь admin (роль: admin). Смените пароль!')

        cursor.execute('SELECT COUNT(*) FROM changelog_entries')
        if cursor.fetchone()[0] == 0:
            seed_date = datetime.now().strftime('%Y-%m-%d')
            seed_ts = datetime.now().isoformat()
            changelog_seed = [
                'Автодополнение полей (карточка, форма добавления, расширенный поиск) переведено с нативного <input list>/datalist на свой выпадающий список — подсказки открываются сразу по клику, без треугольника-индикатора браузера.',
                'Добавлена обрезка фото при добавлении (ещё не загруженные файлы) — модалка с canvas и перетаскиваемой рамкой выделения, свободные пропорции.',
                'Обрезка распространена на уже загруженные фото прямо в карточке (кнопка "✂️" рядом с фото в режиме редактирования) — обрезанный вариант заменяет оригинал на диске.',
                'Режимы работы двигателя теперь редактируются прямо в карточке (все строки сразу редактируемые в режиме редактирования), без отдельной модалки.',
                'Добавлена вкладка "Инфо": лог изменений (эта запись как раз оттуда) и список пожеланий с чекбоксами "внедрено".',
            ]
            cursor.executemany(
                'INSERT INTO changelog_entries (entry_date, text, created_at) VALUES (?, ?, ?)',
                [(seed_date, text, seed_ts) for text in changelog_seed]
            )

        cursor.execute('SELECT COUNT(*) FROM failure_mode')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO failure_mode (code, name) VALUES (?, ?)',
                [
                    ('WINDING_BREAK', 'Обрыв обмотки'),
                    ('WINDING_SHORT', 'Межвитковое замыкание'),
                    ('GROUND_FAULT', 'Пробой на корпус'),
                    ('BEARING_WEAR', 'Износ подшипника'),
                    ('ROTOR_IMBALANCE', 'Дисбаланс ротора'),
                    ('OVERHEATING', 'Перегрев'),
                    ('INSULATION_DAMAGE', 'Повреждение изоляции'),
                    ('NO_START', 'Не запускается'),
                    ('VIBRATION', 'Повышенная вибрация'),
                    ('NOISE', 'Посторонний шум'),
                ]
            )
            logger.info('Загружен справочник failure_mode (10 записей)')

        cursor.execute('SELECT COUNT(*) FROM failure_cause')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO failure_cause (code, name) VALUES (?, ?)',
                [
                    ('OVERLOAD', 'Перегрузка'),
                    ('INSULATION_AGING', 'Старение изоляции'),
                    ('MOISTURE', 'Влага / конденсат'),
                    ('POOR_LUBRICATION', 'Некачественная смазка'),
                    ('BEARING_DEFECT', 'Заводской дефект подшипника'),
                    ('VOLTAGE_IMBALANCE', 'Дисбаланс питающего напряжения'),
                    ('POOR_INSTALLATION', 'Некачественный монтаж'),
                    ('CONTAMINATION', 'Загрязнение'),
                    ('MECHANICAL_DAMAGE', 'Механическое повреждение'),
                    ('WEAR', 'Естественный износ'),
                ]
            )
            logger.info('Загружен справочник failure_cause (10 записей)')

        cursor.execute('SELECT COUNT(*) FROM maintenance_action_type')
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO maintenance_action_type (code, name, is_software) VALUES (?, ?, ?)',
                [
                    ('DIAGNOSTICS', 'Диагностика', 0),
                    ('REPAIR', 'Ремонт', 0),
                    ('REPLACEMENT', 'Замена', 0),
                    ('CALIBRATION', 'Калибровка', 0),
                    ('FIRMWARE_UPDATE', 'Обновление прошивки', 1),
                    ('CONFIG_CHANGE', 'Изменение конфигурации', 1),
                ]
            )
            logger.info('Загружен справочник maintenance_action_type (6 записей)')

        conn.commit()
    finally:
        if own_conn:
            conn.close()
    logger.info('База данных готова')
