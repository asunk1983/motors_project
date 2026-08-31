# repositories/incident_ticket_repo.py — заявки модуля "Инциденты".
# Только SQL, без бизнес-логики (валидация — в services/incident_service.py).

import sqlite3

from repositories import incident_equipment_repo, location_repo


# ---------------------------------------------------------------------
# Самовосстанавливающаяся миграция: колонка updated_at
# ---------------------------------------------------------------------
# incident_ticket изначально заводился только с created_at/closed_at —
# "Изменено" в шапке карточки (см. фронт: incidents.js::
# renderIncidentDetailToolbar) нечего показывать без отдельной колонки.
# Вместо правки modules/db.py (общая точка миграций, файл здесь не
# запрашивался) — самодостаточная проверка прямо в репозитории: если
# колонки ещё нет, добавляем её и один раз бэкафилливаем существующие
# строки значением created_at. ALTER TABLE ... ADD COLUMN в SQLite —
# дешёвая операция, PRAGMA table_info тоже, но кэшируем результат
# флагом на модуль, чтобы не гонять её на каждый запрос в рамках
# одного процесса.
_updated_at_ensured = False


def _ensure_updated_at_column(conn: sqlite3.Connection) -> None:
    global _updated_at_ensured
    if _updated_at_ensured:
        return
    cols = [row[1] for row in conn.execute('PRAGMA table_info(incident_ticket)').fetchall()]
    if 'updated_at' not in cols:
        conn.execute('ALTER TABLE incident_ticket ADD COLUMN updated_at TEXT')
        conn.execute('UPDATE incident_ticket SET updated_at = created_at WHERE updated_at IS NULL')
        conn.commit()
    _updated_at_ensured = True


def list_all(conn: sqlite3.Connection, status: str | None = None, priority: str | None = None,
             location_node_id: int | None = None) -> list[dict]:
    """Список заявок с фильтрами (ТЗ раздел 6: GET /api/incident-tickets —
    список с фильтрами). Каждая строка сразу дополнена breadcrumb места
    и списками ФИО инициаторов/исполнителей — тот же паттерн, что уже
    даёт /api/tickets в существующем ticket_routes (equipment_name и т.п.),
    чтобы фронту не нужно было делать N+1 запросов на список."""
    where, params = [], []
    if status:
        where.append('t.status = ?')
        params.append(status)
    if priority:
        where.append('t.priority = ?')
        params.append(priority)
    if location_node_id is not None:
        where.append('t.location_node_id = ?')
        params.append(location_node_id)
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    _ensure_updated_at_column(conn)
    cur = conn.execute(
        f'''
        SELECT t.id, t.location_node_id, t.problem, t.solution, t.priority, t.status,
               t.created_at, t.updated_at, t.closed_at, t.created_by_user_id,
               ln.name AS location_name,
               u.username AS created_by_username
        FROM incident_ticket t
        LEFT JOIN location_node ln ON ln.id = t.location_node_id
        LEFT JOIN users u ON u.id = t.created_by_user_id
        {where_sql}
        ORDER BY t.created_at DESC
        ''',
        params
    )
    rows = [dict(row) for row in cur.fetchall()]
    for row in rows:
        # ln.name из JOIN даёт только имя последнего узла ("Секция А"),
        # а не весь путь — фронт (incidents.js: список заявок и
        # incidentTicketModal) ожидает в location_name полный путь, как
        # уже строит location_repo.search() для автопоиска. Тот же
        # приём, что и с initiators/executors ниже: один построчный
        # дозапрос поверх основного SELECT, без раздувания самого JOIN.
        if row['location_node_id'] is not None:
            row['location_name'] = location_repo.get_breadcrumb_text(conn, row['location_node_id'])
        row['initiators'] = get_initiators(conn, row['id'])
        row['executors'] = get_executors(conn, row['id'])
    return rows


def get_by_id(conn: sqlite3.Connection, ticket_id: int) -> dict | None:
    _ensure_updated_at_column(conn)
    cur = conn.execute(
        '''
        SELECT t.id, t.location_node_id, t.problem, t.solution, t.priority, t.status,
               t.created_at, t.updated_at, t.closed_at, t.created_by_user_id,
               ln.name AS location_name,
               u.username AS created_by_username
        FROM incident_ticket t
        LEFT JOIN location_node ln ON ln.id = t.location_node_id
        LEFT JOIN users u ON u.id = t.created_by_user_id
        WHERE t.id = ?
        ''',
        (ticket_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    data = dict(row)
    if data['location_node_id'] is not None:
        data['location_name'] = location_repo.get_breadcrumb_text(conn, data['location_node_id'])
    data['initiators'] = get_initiators(conn, ticket_id)
    data['executors'] = get_executors(conn, ticket_id)
    data['equipment'] = incident_equipment_repo.get_relations(conn, ticket_id)
    data['links'] = get_links(conn, ticket_id)
    return data


def create(conn: sqlite3.Connection, location_node_id: int, problem: str, created_by_user_id: int,
           solution: str | None = None, priority: str = 'medium', status: str = 'in_progress',
           closed_at: str | None = None) -> int:
    _ensure_updated_at_column(conn)
    cur = conn.execute(
        '''
        INSERT INTO incident_ticket
            (location_node_id, problem, solution, priority, status, closed_at, created_by_user_id,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''',
        (location_node_id, problem, solution, priority, status, closed_at, created_by_user_id)
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, ticket_id: int, **fields) -> bool:
    """fields — любые из: location_node_id, problem, solution, priority,
    status, closed_at. None-значения игнорируются (кроме closed_at,
    которому явный None нужно уметь ставить при возврате в "В работе" —
    для этого используется отдельный именованный параметр)."""
    _ensure_updated_at_column(conn)
    allowed = {'location_node_id', 'problem', 'solution', 'priority', 'status'}
    set_parts, params = [], []
    for key, value in fields.items():
        if key in allowed and value is not None:
            set_parts.append(f'{key} = ?')
            params.append(value)
    if 'closed_at' in fields:
        # closed_at может быть осмысленно выставлен в NULL (сброс при
        # возврате статуса в 'in_progress') — обрабатывается отдельно от
        # общего None-пропуска выше.
        set_parts.append('closed_at = ?')
        params.append(fields['closed_at'])
    if not set_parts:
        return False
    # "Изменено" в шапке карточки (incidents.js::renderIncidentDetailToolbar)
    # держим актуальным на любое реальное изменение — тот же принцип, что
    # updated_at у equipment (см. update_equipment в equipment_repo.py).
    set_parts.append("updated_at = datetime('now')")
    params.append(ticket_id)
    cur = conn.execute(f'UPDATE incident_ticket SET {", ".join(set_parts)} WHERE id = ?', params)
    conn.commit()
    return cur.rowcount > 0


def delete(conn: sqlite3.Connection, ticket_id: int) -> bool:
    """Физическое удаление — вызывающий (routes) обязан проверить
    role == 'superadmin' до вызова (ТЗ раздел 2.1.4). initiator/executor/
    equipment-link/link удаляются каскадом (ON DELETE CASCADE)."""
    cur = conn.execute('DELETE FROM incident_ticket WHERE id = ?', (ticket_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# Инициаторы / исполнители
# ---------------------------------------------------------------------

def get_initiators(conn: sqlite3.Connection, ticket_id: int) -> list[dict]:
    cur = conn.execute(
        'SELECT c.id, c.full_name FROM incident_ticket_initiator i '
        'JOIN crew c ON c.id = i.crew_id WHERE i.ticket_id = ? ORDER BY c.full_name COLLATE NOCASE',
        (ticket_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def get_executors(conn: sqlite3.Connection, ticket_id: int) -> list[dict]:
    cur = conn.execute(
        'SELECT c.id, c.full_name FROM incident_ticket_executor e '
        'JOIN crew c ON c.id = e.crew_id WHERE e.ticket_id = ? ORDER BY c.full_name COLLATE NOCASE',
        (ticket_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def set_initiators(conn: sqlite3.Connection, ticket_id: int, crew_ids: list[int]) -> None:
    """Полная замена набора — проще и надёжнее точечного diff при
    редактировании тег-инпута на фронте (тот же паттерн, что уже принят
    в проекте для modes/works двигателя — DELETE+INSERT)."""
    conn.execute('DELETE FROM incident_ticket_initiator WHERE ticket_id = ?', (ticket_id,))
    conn.executemany(
        'INSERT INTO incident_ticket_initiator (ticket_id, crew_id) VALUES (?, ?)',
        [(ticket_id, cid) for cid in dict.fromkeys(crew_ids)]  # dedup, сохраняя порядок
    )
    conn.commit()


def set_executors(conn: sqlite3.Connection, ticket_id: int, crew_ids: list[int]) -> None:
    conn.execute('DELETE FROM incident_ticket_executor WHERE ticket_id = ?', (ticket_id,))
    conn.executemany(
        'INSERT INTO incident_ticket_executor (ticket_id, crew_id) VALUES (?, ?)',
        [(ticket_id, cid) for cid in dict.fromkeys(crew_ids)]
    )
    conn.commit()


# ---------------------------------------------------------------------
# Ссылки-вложения (файлы-фото — отдельно, через photo_manager/PhotoI/)
# ---------------------------------------------------------------------

def get_links(conn: sqlite3.Connection, ticket_id: int) -> list[dict]:
    cur = conn.execute(
        'SELECT id, url, caption, created_at FROM incident_ticket_link '
        'WHERE ticket_id = ? ORDER BY created_at',
        (ticket_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def add_link(conn: sqlite3.Connection, ticket_id: int, url: str, caption: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO incident_ticket_link (ticket_id, url, caption, created_at) VALUES (?, ?, ?, datetime('now'))",
        (ticket_id, url, caption)
    )
    conn.commit()
    return cur.lastrowid


def delete_link(conn: sqlite3.Connection, link_id: int) -> bool:
    cur = conn.execute('DELETE FROM incident_ticket_link WHERE id = ?', (link_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# Дерево мест на вкладке "Инциденты" (по аналогии с
# equipment_repo.get_equipment_location_counts — см. HANDOFF, раздел 4:
# та же СВОЯ ошибка там уже была найдена и исправлена, здесь сразу
# делаем правильно)
# ---------------------------------------------------------------------

def get_location_counts(conn: sqlite3.Connection) -> dict:
    """Количество заявок на каждый location_node_id — СВОИ узлы, без
    суммирования по поддереву (это делает фронт, incidentLocationTree.js,
    как и equipmentLocationTree.js). Заявки без места
    (location_node_id IS NULL) считаются отдельно под ключом 'unassigned'.

    Все ключи словаря приводятся к str ЯВНО. Причина — уже найденный на
    equipment баг: Flask's jsonify по умолчанию сериализует со
    sort_keys=True, а Python не умеет сравнивать int и str при сортировке
    в одном dict → TypeError на КАЖДОМ запросе (500 на бэкенде), фронт при
    этом тихо принимал {"error": ...} за валидные счётчики и показывал
    везде 0 без единой видимой ошибки. Мешать int (id узла) и str
    ('unassigned') в одном dict без явного приведения — тот же паттерн,
    воспроизводить его здесь не нужно."""
    cur = conn.execute(
        'SELECT location_node_id, COUNT(*) AS cnt FROM incident_ticket GROUP BY location_node_id'
    )
    counts = {}
    unassigned = 0
    for row in cur.fetchall():
        if row['location_node_id'] is None:
            unassigned += row['cnt']
        else:
            counts[str(row['location_node_id'])] = row['cnt']
    counts['unassigned'] = unassigned
    return counts


# ---------------------------------------------------------------------
# Дашборд-счётчики (ТЗ раздел 4)
# ---------------------------------------------------------------------

def count_all(conn: sqlite3.Connection) -> int:
    return conn.execute('SELECT COUNT(*) FROM incident_ticket').fetchone()[0]


def count_by_status(conn: sqlite3.Connection, status: str) -> int:
    return conn.execute('SELECT COUNT(*) FROM incident_ticket WHERE status = ?', (status,)).fetchone()[0]
