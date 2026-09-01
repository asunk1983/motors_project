# repositories/location_repo.py — дерево мест (location_node).
# Общий ресурс уровня всего проекта (ТЗ, раздел 1) — используется и
# модулем "Инциденты", и доработкой "Оборудование". Только SQL, без
# бизнес-логики/Flask — по конвенции репозиториев проекта.

import sqlite3


VALID_NODE_TYPES = {'workshop', 'installation', 'unit', 'zone', 'warehouse', 'other'}


def list_all(conn: sqlite3.Connection) -> list[dict]:
    """Плоский список всех узлов — клиент сам собирает дерево по parent_id
    (тот же паттерн, что у locationTree.js для engines, только источник
    теперь единая таблица, а не COALESCE по workshop/location в engines).
    Сортируем в Python (см. search() ниже про то, почему не SQL ORDER BY —
    та же причина, только тут нет фильтрации, поэтому строим срез иначе)."""
    cur = conn.execute('SELECT id, parent_id, name, node_type, created_at FROM location_node')
    rows = [dict(row) for row in cur.fetchall()]
    rows.sort(key=lambda r: (r['parent_id'] is not None, r['name'].lower()))
    return rows


def get_children(conn: sqlite3.Connection, parent_id: int | None) -> list[dict]:
    if parent_id is None:
        cur = conn.execute(
            'SELECT id, parent_id, name, node_type, created_at FROM location_node WHERE parent_id IS NULL'
        )
    else:
        cur = conn.execute(
            'SELECT id, parent_id, name, node_type, created_at FROM location_node WHERE parent_id = ?',
            (parent_id,)
        )
    rows = [dict(row) for row in cur.fetchall()]
    rows.sort(key=lambda r: r['name'].lower())
    return rows


def search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Автопоиск для формы (Инциденты/Оборудование) — по имени узла, с
    breadcrumb-строкой (полный путь) для каждого результата, чтобы в
    выпадающем списке различались одноимённые узлы в разных ветках дерева
    (например, "зона 1" под разными экструдерами).

    ВАЖНО: фильтрация регистронезависимого совпадения делается в Python
    (str.lower()), а не через SQL `LIKE ... COLLATE NOCASE` — встроенная
    в SQLite регистронезависимость LIKE/COLLATE NOCASE работает только
    для ASCII (без расширения ICU), кириллица не матчится:
    'Зона' LIKE '%зона%' в чистом SQLite вернёт 0. Загрузка всех узлов в
    память безопасна при масштабе проекта (два пользователя, дерево мест
    одной небольшой фабрики — не десятки тысяч строк)."""
    query_lower = query.lower()
    cur = conn.execute('SELECT id, parent_id, name, node_type FROM location_node')
    rows = [dict(row) for row in cur.fetchall() if query_lower in row['name'].lower()]
    rows.sort(key=lambda r: r['name'].lower())
    rows = rows[:limit]
    for row in rows:
        row['path'] = get_breadcrumb_text(conn, row['id'])
    return rows


def get_breadcrumb(conn: sqlite3.Connection, node_id: int) -> list[dict]:
    """Путь от корня до узла (включительно), один рекурсивный запрос —
    см. ТЗ раздел 1."""
    cur = conn.execute(
        '''
        WITH RECURSIVE breadcrumb(id, parent_id, name, node_type, depth) AS (
            SELECT id, parent_id, name, node_type, 0 FROM location_node WHERE id = ?
            UNION ALL
            SELECT ln.id, ln.parent_id, ln.name, ln.node_type, b.depth + 1
            FROM location_node ln
            JOIN breadcrumb b ON ln.id = b.parent_id
        )
        SELECT id, parent_id, name, node_type FROM breadcrumb ORDER BY depth DESC
        ''',
        (node_id,)
    )
    return [dict(row) for row in cur.fetchall()]


def get_breadcrumb_text(conn: sqlite3.Connection, node_id: int, sep: str = ' → ') -> str:
    return sep.join(n['name'] for n in get_breadcrumb(conn, node_id))


def get_by_id(conn: sqlite3.Connection, node_id: int) -> dict | None:
    cur = conn.execute(
        'SELECT id, parent_id, name, node_type, created_at FROM location_node WHERE id = ?',
        (node_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def create(conn: sqlite3.Connection, name: str, node_type: str, parent_id: int | None = None) -> int:
    cur = conn.execute(
        'INSERT INTO location_node (parent_id, name, node_type, created_at) '
        "VALUES (?, ?, ?, datetime('now'))",
        (parent_id, name, node_type)
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, node_id: int, name: str | None = None, node_type: str | None = None) -> bool:
    fields, params = [], []
    if name is not None:
        fields.append('name = ?')
        params.append(name)
    if node_type is not None:
        fields.append('node_type = ?')
        params.append(node_type)
    if not fields:
        return False
    params.append(node_id)
    cur = conn.execute(f'UPDATE location_node SET {", ".join(fields)} WHERE id = ?', params)
    conn.commit()
    return cur.rowcount > 0


def get_subtree_ids(conn: sqlite3.Connection, node_id: int) -> list[int]:
    """Все id узла и ВСЕХ его потомков (включительно) — используется
    фильтром оборудования "этот узел и всё, что ниже" (ТЗ раздел 3.1):
    WHERE location_node_id IN (get_subtree_ids(node_id)). Та же
    рекурсивная CTE, что уже была приватной частью _is_descendant()
    (защита от цикла в move()) — здесь она публичный самостоятельный
    метод, т.к. смысл использования другой (не проверка предка/потомка,
    а получение полного списка)."""
    cur = conn.execute(
        '''
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM location_node WHERE id = ?
            UNION ALL
            SELECT ln.id FROM location_node ln JOIN subtree s ON ln.parent_id = s.id
        )
        SELECT id FROM subtree
        ''',
        (node_id,)
    )
    return [row['id'] for row in cur.fetchall()]


def _is_descendant(conn: sqlite3.Connection, node_id: int, candidate_ancestor_id: int) -> bool:
    """True, если candidate_ancestor_id находится ВНУТРИ поддерева node_id
    (включая сам node_id) — используется move() для защиты от цикла
    (нельзя перенести узел под собственного потомка). Реализована через
    get_subtree_ids() — та же рекурсивная CTE, один источник правды."""
    return candidate_ancestor_id in get_subtree_ids(conn, node_id)


def move(conn: sqlite3.Connection, node_id: int, new_parent_id: int | None) -> tuple[bool, str | None]:
    """Смена родителя с защитой от цикла. Возвращает (ok, error)."""
    if new_parent_id is not None:
        if new_parent_id == node_id:
            return False, 'Нельзя сделать узел родителем самого себя'
        if _is_descendant(conn, node_id, new_parent_id):
            return False, 'Нельзя перенести узел в собственное поддерево'
        if get_by_id(conn, new_parent_id) is None:
            return False, 'Новый родитель не найден'
    cur = conn.execute('UPDATE location_node SET parent_id = ? WHERE id = ?', (new_parent_id, node_id))
    conn.commit()
    return cur.rowcount > 0, None


def has_children(conn: sqlite3.Connection, node_id: int) -> bool:
    cur = conn.execute('SELECT 1 FROM location_node WHERE parent_id = ? LIMIT 1', (node_id,))
    return cur.fetchone() is not None


def is_referenced(conn: sqlite3.Connection, node_id: int) -> bool:
    """Guard для удаления: узел используется где-то ещё в проекте.

    incident_ticket.location_node_id — с шага "Инциденты".
    equipment.location_node_id — с шага 6 (миграция Оборудования на
    общее дерево мест). equipment_placement.location_node_id — с
    доработки "Место" (несколько экземпляров/схемных обозначений на
    одно оборудование). Все проверки нужны ОДНОВРЕМЕННО: FK-колонки
    объявлены без ON DELETE CASCADE/SET NULL (кроме equipment_id внутри
    equipment_placement — там CASCADE, но это про удаление ОБОРУДОВАНИЯ,
    не места), и SQLite не enforce-ит FK-constraints без явного PRAGMA
    foreign_keys=ON — без этой проверки удаление узла молча оставило бы
    оборудование, заявку или placement ссылающимися на несуществующее
    место."""
    cur = conn.execute('SELECT 1 FROM incident_ticket WHERE location_node_id = ? LIMIT 1', (node_id,))
    if cur.fetchone() is not None:
        return True
    cur = conn.execute('SELECT 1 FROM equipment WHERE location_node_id = ? LIMIT 1', (node_id,))
    if cur.fetchone() is not None:
        return True
    cur = conn.execute('SELECT 1 FROM equipment_placement WHERE location_node_id = ? LIMIT 1', (node_id,))
    if cur.fetchone() is not None:
        return True
    return False


def delete(conn: sqlite3.Connection, node_id: int) -> tuple[bool, str | None]:
    if has_children(conn, node_id):
        return False, 'У узла есть дочерние места — сначала удалите или перенесите их'
    if is_referenced(conn, node_id):
        return False, 'Узел используется в оборудовании или заявках — удаление невозможно'
    cur = conn.execute('DELETE FROM location_node WHERE id = ?', (node_id,))
    conn.commit()
    return cur.rowcount > 0, None
