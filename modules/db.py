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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modes_engine ON operating_modes(engine_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_works_engine ON maintenance_works(engine_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changelog_date ON changelog_entries(entry_date)')
        for col in ('location', 'engine_type', 'manufacturer', 'serial_number', 'workshop', 'purpose'):
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_engines_{col} ON engines({col})')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_hash ON tokens(token_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id)')

        # Auto-migration: добавляем новые колонки, если БД была создана ранее
        _ensure_column(cursor, 'users', 'last_login', 'TEXT')
        _ensure_column(cursor, 'users', 'last_edit', 'TEXT')
        _ensure_column(cursor, 'engines', 'created_at', 'TEXT')
        _ensure_column(cursor, 'engines', 'updated_at', 'TEXT')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_updated_at ON engines(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_engines_created_at ON engines(created_at)')

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
        conn.commit()
    finally:
        if own_conn:
            conn.close()
    logger.info('База данных готова')
