"""Repository для номенклатуры оборудования (equipment_type, attribute_definition,
equipment_type_attribute, equipment).

Содержит ТОЛЬКО SQL-запросы. Стиль — как engine_repo.py/knowledge_repo.py.
Все функции принимают sqlite3.Connection первым аргументом.
"""
import json
from datetime import datetime


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------------
# equipment_type — иерархия классов (по образцу IBM Maximo Classifications)
# ---------------------------------------------------------------------

def list_equipment_types(conn):
    """Плоский список типов с именем родителя — дерево строит фронтенд
    (тот же паттерн, что get_locations_tree в engine_repo.py, только
    группировка на клиенте, а не на сервере)."""
    cur = conn.cursor()
    cur.execute('''
        SELECT et.*, parent.name AS parent_name
        FROM equipment_type et
        LEFT JOIN equipment_type parent ON parent.id = et.parent_type_id
        ORDER BY et.name
    ''')
    return [_row_to_dict(row) for row in cur.fetchall()]


def get_equipment_type(conn, type_id: int):
    cur = conn.cursor()
    cur.execute('SELECT * FROM equipment_type WHERE id = ?', (type_id,))
    return _row_to_dict(cur.fetchone())


def create_equipment_type(conn, code: str, name: str, parent_type_id=None, description=None) -> int:
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO equipment_type (code, name, parent_type_id, description) VALUES (?, ?, ?, ?)',
        (code, name, parent_type_id, description)
    )
    conn.commit()
    return cur.lastrowid


def equipment_type_in_use(conn, type_id: int) -> bool:
    """True, если у типа есть записи оборудования ИЛИ дочерние типы —
    в обоих случаях удаление сломало бы данные."""
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM equipment WHERE equipment_type_id = ? LIMIT 1', (type_id,))
    if cur.fetchone():
        return True
    cur.execute('SELECT 1 FROM equipment_type WHERE parent_type_id = ? LIMIT 1', (type_id,))
    return cur.fetchone() is not None


def delete_equipment_type(conn, type_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment_type_attribute WHERE equipment_type_id = ?', (type_id,))
    cur.execute('DELETE FROM equipment_type WHERE id = ?', (type_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# attribute_definition — переиспользуемый пул (по образцу NetBox Custom
# Fields / MAXATTRIBUTE у Maximo)
# ---------------------------------------------------------------------

def list_attribute_definitions(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM attribute_definition ORDER BY group_name IS NULL, group_name, weight, label')
    result = []
    for row in cur.fetchall():
        d = _row_to_dict(row)
        d['options'] = json.loads(d['options_json']) if d.get('options_json') else []
        result.append(d)
    return result


def create_attribute_definition(conn, data: dict) -> int:
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO attribute_definition
            (key, label, group_name, value_type, unit, options_json, default_value, weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['key'], data['label'], data.get('group_name'), data.get('value_type', 'text'),
        data.get('unit'), json.dumps(data['options'], ensure_ascii=False) if data.get('options') else None,
        data.get('default_value'), data.get('weight', 0),
    ))
    conn.commit()
    return cur.lastrowid


def attribute_definition_in_use(conn, attribute_definition_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM equipment_type_attribute WHERE attribute_definition_id = ? LIMIT 1',
                (attribute_definition_id,))
    return cur.fetchone() is not None


def delete_attribute_definition(conn, attribute_definition_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM attribute_definition WHERE id = ?', (attribute_definition_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# equipment_type_attribute — назначение атрибута типу + наследование
# ---------------------------------------------------------------------

def get_assigned_attributes(conn, type_id: int):
    """Атрибуты, назначенные ИМЕННО этому типу (без наследования) —
    для экрана-конструктора, где видно, что настроено конкретно тут."""
    cur = conn.cursor()
    cur.execute('''
        SELECT ad.*, eta.is_required, eta.weight_override
        FROM equipment_type_attribute eta
        JOIN attribute_definition ad ON ad.id = eta.attribute_definition_id
        WHERE eta.equipment_type_id = ?
    ''', (type_id,))
    result = []
    for row in cur.fetchall():
        d = _row_to_dict(row)
        d['options'] = json.loads(d['options_json']) if d.get('options_json') else []
        result.append(d)
    return result


def get_effective_attributes(conn, type_id: int):
    """Атрибуты типа С УЧЁТОМ наследования от родительских типов
    (Maximo-паттерн: Насос -> Центробежный насос наследует атрибуты
    Насоса). Идём от корня к листу, чтобы настройка is_required/weight
    на дочернем уровне могла переопределить родительскую — ближе к
    листу побеждает.
    """
    # Строим цепочку от корня к текущему типу
    chain = []
    current_id = type_id
    visited = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        t = get_equipment_type(conn, current_id)
        if t is None:
            break
        chain.append(current_id)
        current_id = t.get('parent_type_id')
    chain.reverse()  # теперь от корня к листу

    merged = {}  # attribute_definition_id -> dict
    for tid in chain:
        for attr in get_assigned_attributes(conn, tid):
            merged[attr['id']] = attr  # более глубокий уровень переопределяет

    result = list(merged.values())
    result.sort(key=lambda a: (a['group_name'] or '', a['weight_override'] if a['weight_override'] is not None else a['weight']))
    return result


def set_type_attributes(conn, type_id: int, assignments: list) -> None:
    """Полная замена набора атрибутов типа — DELETE+INSERT, тот же
    паттерн, что replace_all в mode_repo/work_repo и
    _replace_article_causes в knowledge_repo.
    assignments: [{'attribute_definition_id': int, 'is_required': bool,
                    'weight_override': int|None}, ...]
    """
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment_type_attribute WHERE equipment_type_id = ?', (type_id,))
    if assignments:
        cur.executemany('''
            INSERT INTO equipment_type_attribute
                (equipment_type_id, attribute_definition_id, is_required, weight_override)
            VALUES (?, ?, ?, ?)
        ''', [
            (type_id, a['attribute_definition_id'], int(bool(a.get('is_required'))), a.get('weight_override'))
            for a in assignments
        ])
    conn.commit()


# ---------------------------------------------------------------------
# equipment — сами записи номенклатуры
# ---------------------------------------------------------------------

def get_equipment_by_id(conn, equipment_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT e.*, et.name AS equipment_type_name, et.code AS equipment_type_code
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        WHERE e.id = ?
    ''', (equipment_id,))
    row = _row_to_dict(cur.fetchone())
    if row is None:
        return None
    row['specs'] = json.loads(row['specs_json']) if row.get('specs_json') else {}
    return row


def list_equipment(conn, equipment_type_id=None, search: str = ''):
    cur = conn.cursor()
    conditions = []
    params = []
    if equipment_type_id:
        conditions.append('e.equipment_type_id = ?')
        params.append(equipment_type_id)
    if search:
        conditions.append('(e.name LIKE ? OR e.article LIKE ? OR e.serial_number LIKE ?)')
        params += [f'%{search}%'] * 3
    where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    cur.execute(f'''
        SELECT e.*, et.name AS equipment_type_name
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        {where_clause}
        ORDER BY e.updated_at DESC
    ''', params)
    result = []
    for row in cur.fetchall():
        d = _row_to_dict(row)
        d['specs'] = json.loads(d['specs_json']) if d.get('specs_json') else {}
        result.append(d)
    return result


def create_equipment(conn, data: dict) -> int:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO equipment
            (equipment_type_id, name, article, manufacturer, serial_number,
             workshop, location, firmware_version, criticality, installed_at,
             specs_json, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['equipment_type_id'], data['name'], data.get('article'), data.get('manufacturer'),
        data.get('serial_number'), data.get('workshop'), data.get('location'),
        data.get('firmware_version'), data.get('criticality'), data.get('installed_at'),
        json.dumps(data.get('specs', {}), ensure_ascii=False), data.get('note'), now, now,
    ))
    conn.commit()
    return cur.lastrowid


def update_equipment(conn, equipment_id: int, data: dict) -> bool:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        UPDATE equipment SET
            equipment_type_id = ?, name = ?, article = ?, manufacturer = ?, serial_number = ?,
            workshop = ?, location = ?, firmware_version = ?, criticality = ?, installed_at = ?,
            specs_json = ?, note = ?, updated_at = ?
        WHERE id = ?
    ''', (
        data['equipment_type_id'], data['name'], data.get('article'), data.get('manufacturer'),
        data.get('serial_number'), data.get('workshop'), data.get('location'),
        data.get('firmware_version'), data.get('criticality'), data.get('installed_at'),
        json.dumps(data.get('specs', {}), ensure_ascii=False), data.get('note'), now, equipment_id,
    ))
    conn.commit()
    return cur.rowcount > 0


def delete_equipment(conn, equipment_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment WHERE id = ?', (equipment_id,))
    conn.commit()
    return cur.rowcount > 0
