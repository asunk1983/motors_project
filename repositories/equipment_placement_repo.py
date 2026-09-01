"""Repository для equipment_placement — места установки оборудования со
схемными обозначениями.

Не путать с equipment.location_node_id ("основное" место записи — им
по-прежнему занимается equipment_repo.py, дерево слева и фильтр списка
не трогаются). Здесь — дополнительная детализация: одна карточка
оборудования может стоять в нескольких местах, а в пределах одного
места — несколько экземпляров с разными схемными обозначениями
(шкаф +E021: КМ1, КМ2, КМ3 — три строки с одним location_node_id).

Стиль — как в location_repo.py/engine_repo.py. Только SQL, без
бизнес-логики/Flask; бизнес-валидация (bulk-разбор строки обозначений,
проверка занятости) — в routes-слое, по конвенции этого проекта
(см. equipment_repo.py::list_equipment, комментарий про attr_filters).
"""
import sqlite3

from repositories import location_repo


def list_by_equipment(conn: sqlite3.Connection, equipment_id: int) -> list[dict]:
    """Все места оборудования, сгруппировать по месту — задача фронтенда
    (несколько строк с одним location_node_id — это одно место с
    несколькими обозначениями). Отдаём breadcrumb сразу, тем же способом,
    что и list_tickets_route (incident_ticket_repo) — чтобы не делать
    отдельный запрос на каждое место при рендере таблицы."""
    cur = conn.execute('''
        SELECT id, equipment_id, location_node_id, designation, note, created_at
        FROM equipment_placement
        WHERE equipment_id = ?
        ORDER BY location_node_id, designation
    ''', (equipment_id,))
    rows = [dict(row) for row in cur.fetchall()]
    for row in rows:
        row['location_path'] = location_repo.get_breadcrumb_text(conn, row['location_node_id'])
    return rows


def designation_exists_in_location(conn: sqlite3.Connection, location_node_id: int, designation: str | None) -> bool:
    """Занято ли обозначение в этом месте — NULL-обозначения никогда не
    конфликтуют (см. частичный уникальный индекс в db.py), поэтому для
    пустого designation сразу False без похода в БД."""
    if not designation:
        return False
    cur = conn.execute(
        'SELECT 1 FROM equipment_placement WHERE location_node_id = ? AND designation = ? LIMIT 1',
        (location_node_id, designation)
    )
    return cur.fetchone() is not None


def create(conn: sqlite3.Connection, equipment_id: int, location_node_id: int,
           designation: str | None = None, note: str | None = None) -> int:
    cur = conn.execute('''
        INSERT INTO equipment_placement (equipment_id, location_node_id, designation, note, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (equipment_id, location_node_id, designation, note))
    conn.commit()
    return cur.lastrowid


def get_by_id(conn: sqlite3.Connection, placement_id: int) -> dict | None:
    cur = conn.execute(
        'SELECT id, equipment_id, location_node_id, designation, note, created_at '
        'FROM equipment_placement WHERE id = ?',
        (placement_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def delete(conn: sqlite3.Connection, placement_id: int) -> bool:
    cur = conn.execute('DELETE FROM equipment_placement WHERE id = ?', (placement_id,))
    conn.commit()
    return cur.rowcount > 0
