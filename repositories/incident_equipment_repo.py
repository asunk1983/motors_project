# repositories/incident_equipment_repo.py — связь заявки Инцидента с
# затронутым оборудованием. ТЗ раздел 2.1.6: простая связь без типов
# "affected/related/suspected" — просто список "что трогали".

import sqlite3

from modules.audit import log_field_changes


def _equipment_name(conn: sqlite3.Connection, equipment_id: int) -> str:
    cur = conn.execute('SELECT name FROM equipment WHERE id = ?', (equipment_id,))
    row = cur.fetchone()
    return row['name'] if row else str(equipment_id)


def get_relations(conn: sqlite3.Connection, ticket_id: int) -> list[dict]:
    cur = conn.execute(
        'SELECT e.id, e.name FROM incident_ticket_equipment te '
        'JOIN equipment e ON e.id = te.equipment_id '
        'WHERE te.ticket_id = ? ORDER BY e.name COLLATE NOCASE',
        (ticket_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def add_relation(conn: sqlite3.Connection, ticket_id: int, equipment_id: int, actor: dict | None = None) -> None:
    """actor — dict текущего пользователя (request.current_user), для
    журнала изменений. Логируется как изменение поля 'equipment_link' у
    родителя-заявки (entity_type='incident_ticket') — та же связь может
    добавляться/убираться много раз, стабильного id самой связи нет
    (составной ключ ticket_id+equipment_id), поэтому не отдельная
    сущность, а поле-диф по аналогии с modes/works у engine."""
    cur = conn.execute(
        'INSERT OR IGNORE INTO incident_ticket_equipment (ticket_id, equipment_id) VALUES (?, ?)',
        (ticket_id, equipment_id)
    )
    if cur.rowcount > 0:
        name = _equipment_name(conn, equipment_id)
        log_field_changes(conn, 'incident_ticket', ticket_id, actor,
                           {'equipment_link': None}, {'equipment_link': name})
    conn.commit()


def remove_relation(conn: sqlite3.Connection, ticket_id: int, equipment_id: int, actor: dict | None = None) -> bool:
    """actor — dict текущего пользователя (request.current_user), для
    журнала изменений (см. add_relation выше)."""
    name = _equipment_name(conn, equipment_id)
    cur = conn.execute(
        'DELETE FROM incident_ticket_equipment WHERE ticket_id = ? AND equipment_id = ?',
        (ticket_id, equipment_id)
    )
    if cur.rowcount > 0:
        log_field_changes(conn, 'incident_ticket', ticket_id, actor,
                           {'equipment_link': name}, {'equipment_link': None})
    conn.commit()
    return cur.rowcount > 0
