"""Repository для заявок (ticket), отказов (failure) и работ (equipment_work).

Содержит ТОЛЬКО SQL-запросы. Стиль — как engine_repo.py/equipment_repo.py.
Все функции принимают sqlite3.Connection первым аргументом.

ticket != failure: заявка — сырое обращение, не каждая станет отказом.
equipment_work существует только через failure (осознанное решение — см.
обсуждение с пользователем): если заявка не подтвердилась, работ по ней
не бывает, только закрытие тикета с rejection_reason.
"""
from datetime import datetime


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------------
# ticket
# ---------------------------------------------------------------------

def list_tickets(conn, status: str = '', equipment_id=None):
    cur = conn.cursor()
    conditions = []
    params = []
    if status:
        conditions.append('t.status = ?')
        params.append(status)
    if equipment_id:
        conditions.append('t.equipment_id = ?')
        params.append(equipment_id)
    where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    cur.execute(f'''
        SELECT t.*, e.name AS equipment_name, u.username AS created_by_username,
               (SELECT f.id FROM failure f WHERE f.ticket_id = t.id LIMIT 1) AS failure_id
        FROM ticket t
        LEFT JOIN equipment e ON e.id = t.equipment_id
        LEFT JOIN users u ON u.id = t.created_by_user_id
        {where_clause}
        ORDER BY t.created_at DESC
    ''', params)
    return [_row_to_dict(row) for row in cur.fetchall()]


def get_ticket_by_id(conn, ticket_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT t.*, e.name AS equipment_name, u.username AS created_by_username
        FROM ticket t
        LEFT JOIN equipment e ON e.id = t.equipment_id
        LEFT JOIN users u ON u.id = t.created_by_user_id
        WHERE t.id = ?
    ''', (ticket_id,))
    ticket = _row_to_dict(cur.fetchone())
    if ticket is None:
        return None
    cur.execute('SELECT id FROM failure WHERE ticket_id = ?', (ticket_id,))
    ticket['failure_ids'] = [r['id'] for r in cur.fetchall()]
    return ticket


def create_ticket(conn, data: dict) -> int:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO ticket
            (equipment_id, created_by_user_id, priority, status, title, description, created_at)
        VALUES (?, ?, ?, 'new', ?, ?, ?)
    ''', (
        data.get('equipment_id'), data.get('created_by_user_id'),
        data.get('priority', 'normal'), data['title'], data.get('description'), now,
    ))
    conn.commit()
    return cur.lastrowid


def update_ticket_status(conn, ticket_id: int, status: str, rejection_reason=None) -> bool:
    """Единая точка смены статуса — сама проставляет соответствующий
    timestamp (resolved_at/closed_at/rejected_at), как resolved_at/closed_at
    у ticket в самом первом обсуждении этой сущности."""
    now = datetime.now().isoformat()
    field_map = {
        'resolved': 'resolved_at',
        'closed': 'closed_at',
        'rejected': 'rejected_at',
    }
    cur = conn.cursor()
    if status in field_map:
        ts_field = field_map[status]
        if status == 'rejected':
            cur.execute(
                f'UPDATE ticket SET status = ?, {ts_field} = ?, rejection_reason = ? WHERE id = ?',
                (status, now, rejection_reason, ticket_id)
            )
        else:
            cur.execute(f'UPDATE ticket SET status = ?, {ts_field} = ? WHERE id = ?', (status, now, ticket_id))
    else:
        cur.execute('UPDATE ticket SET status = ? WHERE id = ?', (status, ticket_id))
    conn.commit()
    return cur.rowcount > 0


def update_ticket(conn, ticket_id: int, data: dict) -> bool:
    cur = conn.cursor()
    cur.execute('''
        UPDATE ticket SET equipment_id = ?, priority = ?, title = ?, description = ?
        WHERE id = ?
    ''', (data.get('equipment_id'), data.get('priority', 'normal'), data['title'], data.get('description'), ticket_id))
    conn.commit()
    return cur.rowcount > 0


def delete_ticket(conn, ticket_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment_work WHERE failure_id IN (SELECT id FROM failure WHERE ticket_id = ?)', (ticket_id,))
    cur.execute('DELETE FROM failure WHERE ticket_id = ?', (ticket_id,))
    cur.execute('DELETE FROM ticket WHERE id = ?', (ticket_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# failure
# ---------------------------------------------------------------------

def get_failure_by_id(conn, failure_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT f.*, e.name AS equipment_name,
               fm.name AS failure_mode_name, fc.name AS failure_cause_name,
               ka.title AS knowledge_article_title
        FROM failure f
        JOIN equipment e ON e.id = f.equipment_id
        LEFT JOIN failure_mode fm ON fm.id = f.failure_mode_id
        LEFT JOIN failure_cause fc ON fc.id = f.failure_cause_id
        LEFT JOIN knowledge_article ka ON ka.id = f.knowledge_article_id
        WHERE f.id = ?
    ''', (failure_id,))
    failure = _row_to_dict(cur.fetchone())
    if failure is None:
        return None
    failure['work'] = get_work_for_failure(conn, failure_id)
    return failure


def create_failure(conn, data: dict) -> int:
    """Создать отказ по заявке. Не проверяет и не меняет статус заявки —
    это ответственность роута (симметрично тому, как engine_repo.py не
    лезет в чужие таблицы сам, только выполняет то, о чём его просят)."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO failure
            (ticket_id, equipment_id, failure_mode_id, failure_cause_id, knowledge_article_id,
             symptom, description, confirmed, occurred_at, restored_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['ticket_id'], data['equipment_id'], data.get('failure_mode_id'),
        data.get('failure_cause_id'), data.get('knowledge_article_id'),
        data.get('symptom'), data.get('description'), int(bool(data.get('confirmed', True))),
        data.get('occurred_at'), data.get('restored_at'), now,
    ))
    conn.commit()
    return cur.lastrowid


def update_failure(conn, failure_id: int, data: dict) -> bool:
    cur = conn.cursor()
    cur.execute('''
        UPDATE failure SET
            failure_mode_id = ?, failure_cause_id = ?, knowledge_article_id = ?,
            symptom = ?, description = ?, confirmed = ?, occurred_at = ?, restored_at = ?
        WHERE id = ?
    ''', (
        data.get('failure_mode_id'), data.get('failure_cause_id'), data.get('knowledge_article_id'),
        data.get('symptom'), data.get('description'), int(bool(data.get('confirmed', True))),
        data.get('occurred_at'), data.get('restored_at'), failure_id,
    ))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# equipment_work
# ---------------------------------------------------------------------

def get_work_for_failure(conn, failure_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT ew.*, mat.name AS action_type_name, mat.is_software, u.username AS executor_username
        FROM equipment_work ew
        LEFT JOIN maintenance_action_type mat ON mat.id = ew.action_type_id
        LEFT JOIN users u ON u.id = ew.executor_user_id
        WHERE ew.failure_id = ?
        ORDER BY ew.created_at
    ''', (failure_id,))
    return [_row_to_dict(row) for row in cur.fetchall()]


def create_work(conn, data: dict) -> int:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO equipment_work
            (failure_id, action_type_id, executor_user_id, description, result, successful,
             version_from, version_to, parameter_changed, old_value, new_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['failure_id'], data.get('action_type_id'), data.get('executor_user_id'),
        data.get('description'), data.get('result'),
        None if data.get('successful') is None else int(bool(data.get('successful'))),
        data.get('version_from'), data.get('version_to'), data.get('parameter_changed'),
        data.get('old_value'), data.get('new_value'), now,
    ))
    conn.commit()
    return cur.lastrowid


def delete_work(conn, work_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment_work WHERE id = ?', (work_id,))
    conn.commit()
    return cur.rowcount > 0


def list_maintenance_action_types(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM maintenance_action_type ORDER BY name')
    return [_row_to_dict(row) for row in cur.fetchall()]
