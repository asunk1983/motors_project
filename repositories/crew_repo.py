# repositories/crew_repo.py — справочник людей (модуль "Инциденты").
# ТЗ раздел 2.1.2: identity = id, без UNIQUE по имени — смена должности
# или разное написание ФИО не должны "ломать" идентичность человека.
# Только SQL, без бизнес-логики — по конвенции репозиториев проекта.

import sqlite3


def list_all(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute('SELECT id, full_name, position, workshop, created_at FROM crew')
    rows = [dict(row) for row in cur.fetchall()]
    rows.sort(key=lambda r: r['full_name'].lower())
    return rows


def get_by_id(conn: sqlite3.Connection, crew_id: int) -> dict | None:
    cur = conn.execute(
        'SELECT id, full_name, position, workshop, created_at FROM crew WHERE id = ?',
        (crew_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Регистронезависимый поиск по ФИО в Python — см. подробное
    обоснование в location_repo.search(): встроенная в SQLite
    регистронезависимость LIKE/COLLATE NOCASE не работает для кириллицы."""
    query_lower = query.lower()
    cur = conn.execute('SELECT id, full_name, position, workshop FROM crew')
    rows = [dict(row) for row in cur.fetchall() if query_lower in row['full_name'].lower()]
    rows.sort(key=lambda r: r['full_name'].lower())
    return rows[:limit]


def create(conn: sqlite3.Connection, full_name: str, position: str | None = None, workshop: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO crew (full_name, position, workshop, created_at) VALUES (?, ?, ?, datetime('now'))",
        (full_name, position, workshop)
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, crew_id: int, full_name: str | None = None,
           position: str | None = None, workshop: str | None = None) -> bool:
    fields, params = [], []
    if full_name is not None:
        fields.append('full_name = ?')
        params.append(full_name)
    if position is not None:
        fields.append('position = ?')
        params.append(position)
    if workshop is not None:
        fields.append('workshop = ?')
        params.append(workshop)
    if not fields:
        return False
    params.append(crew_id)
    cur = conn.execute(f'UPDATE crew SET {", ".join(fields)} WHERE id = ?', params)
    conn.commit()
    return cur.rowcount > 0


def is_referenced(conn: sqlite3.Connection, crew_id: int) -> bool:
    """Guard для удаления: человек указан хоть в одной заявке
    (инициатор или исполнитель) — ТЗ раздел 2.5."""
    cur = conn.execute('SELECT 1 FROM incident_ticket_initiator WHERE crew_id = ? LIMIT 1', (crew_id,))
    if cur.fetchone() is not None:
        return True
    cur = conn.execute('SELECT 1 FROM incident_ticket_executor WHERE crew_id = ? LIMIT 1', (crew_id,))
    return cur.fetchone() is not None


def delete(conn: sqlite3.Connection, crew_id: int) -> tuple[bool, str | None]:
    if is_referenced(conn, crew_id):
        return False, 'Человек указан хотя бы в одной заявке — удаление невозможно'
    cur = conn.execute('DELETE FROM crew WHERE id = ?', (crew_id,))
    conn.commit()
    return cur.rowcount > 0, None
