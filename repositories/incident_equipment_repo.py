# repositories/incident_equipment_repo.py — связь заявки Инцидента с
# затронутым оборудованием. ТЗ раздел 2.1.6: простая связь без типов
# "affected/related/suspected" — просто список "что трогали".

import sqlite3


def get_relations(conn: sqlite3.Connection, ticket_id: int) -> list[dict]:
    cur = conn.execute(
        'SELECT e.id, e.name FROM incident_ticket_equipment te '
        'JOIN equipment e ON e.id = te.equipment_id '
        'WHERE te.ticket_id = ? ORDER BY e.name COLLATE NOCASE',
        (ticket_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def add_relation(conn: sqlite3.Connection, ticket_id: int, equipment_id: int) -> None:
    conn.execute(
        'INSERT OR IGNORE INTO incident_ticket_equipment (ticket_id, equipment_id) VALUES (?, ?)',
        (ticket_id, equipment_id)
    )
    conn.commit()


def remove_relation(conn: sqlite3.Connection, ticket_id: int, equipment_id: int) -> bool:
    cur = conn.execute(
        'DELETE FROM incident_ticket_equipment WHERE ticket_id = ? AND equipment_id = ?',
        (ticket_id, equipment_id)
    )
    conn.commit()
    return cur.rowcount > 0
