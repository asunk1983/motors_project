import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

from config.settings import DB_PATH, MOTORS_FOLDER, PHOTOS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER, ALLOWED_PHOTO_EXT

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

        # Auto-migration: добавляем новые колонки, если БД была создана ранее
        _ensure_column(cursor, 'users', 'last_login', 'TEXT')
        _ensure_column(cursor, 'users', 'last_edit', 'TEXT')
        _ensure_column(cursor, 'engines', 'created_at', 'TEXT')
        _ensure_column(cursor, 'engines', 'updated_at', 'TEXT')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_updated_at ON engines(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_created_at ON engines(created_at)')

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
