"""Repository для номенклатуры оборудования (equipment_type, attribute_definition,
equipment_type_attribute, equipment).

Содержит ТОЛЬКО SQL-запросы. Стиль — как engine_repo.py/knowledge_repo.py.
Все функции принимают sqlite3.Connection первым аргументом.
"""
import json
from datetime import datetime

from repositories import location_repo


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
        SELECT ad.*, eta.is_required, eta.weight_override, eta.show_in_list
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


def get_show_in_list_attributes(conn, type_id: int):
    """Атрибуты типа (С УЧЁТОМ наследования), отмеченные show_in_list —
    ТЗ раздел 3.2: становятся динамическими колонками таблицы
    номенклатуры, когда фильтр "Тип" сужен до конкретного типа."""
    return [
        {'key': a['key'], 'label': a['label'], 'unit': a.get('unit')}
        for a in get_effective_attributes(conn, type_id)
        if a.get('show_in_list')
    ]


def set_type_attributes(conn, type_id: int, assignments: list) -> None:
    """Полная замена набора атрибутов типа — DELETE+INSERT, тот же
    паттерн, что replace_all в mode_repo/work_repo и
    _replace_article_causes в knowledge_repo.
    assignments: [{'attribute_definition_id': int, 'is_required': bool,
                    'weight_override': int|None, 'show_in_list': bool}, ...]
    """
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment_type_attribute WHERE equipment_type_id = ?', (type_id,))
    if assignments:
        cur.executemany('''
            INSERT INTO equipment_type_attribute
                (equipment_type_id, attribute_definition_id, is_required, weight_override, show_in_list)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            (type_id, a['attribute_definition_id'], int(bool(a.get('is_required'))), a.get('weight_override'),
             int(bool(a.get('show_in_list'))))
            for a in assignments
        ])
    conn.commit()


# ---------------------------------------------------------------------
# equipment — сами записи номенклатуры
# ---------------------------------------------------------------------

def get_equipment_by_id(conn, equipment_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT e.*, et.name AS equipment_type_name, et.code AS equipment_type_code,
               ln.name AS location_name
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        LEFT JOIN location_node ln ON ln.id = e.location_node_id
        WHERE e.id = ?
    ''', (equipment_id,))
    row = _row_to_dict(cur.fetchone())
    if row is None:
        return None
    row['specs'] = json.loads(row['specs_json']) if row.get('specs_json') else {}
    return row


EQUIPMENT_SORT_COLUMNS = {
    'name': 'e.name',
    'equipment_type_name': 'et.name',
    'article': 'e.article',
    'criticality': 'e.criticality',
}


def list_equipment(conn, equipment_type_id=None, search: str = '', location_node_id=None,
                    unassigned: bool = False, sort: str = None, order: str = 'desc',
                    attr_filters: dict = None):
    """location_node_id — фильтр "этот узел дерева мест и всё, что ниже"
    (ТЗ раздел 3.1): разворачиваем в список id через
    location_repo.get_subtree_ids() и фильтруем, а не точным совпадением —
    клик по цеху должен находить оборудование во ВСЕХ вложенных узлах
    (установках/секциях/зонах), не только привязанное буквально к самому
    цеху.

    С доработкой "Места" (equipment_placement, ТЗ) запись оборудования
    может физически стоять в НЕСКОЛЬКИХ местах — единственного
    equipment.location_node_id для фильтрации уже недостаточно. Условие
    ниже: запись попадает под фильтр, если ЛИБО у неё есть хотя бы один
    placement в найденном поддереве, ЛИБО (если у записи вообще НЕТ ни
    одного placement) её старое legacy location_node_id попадает в
    поддерево — обратная совместимость с записями, заведёнными до
    появления "Мест", и складскими позициями без детализации.

    unassigned=True — отдельная ветка (несовместимая с location_node_id,
    вызывающий выбирает одно из двух): показывает записи БЕЗ единого
    места вообще — ни одного placement, ни legacy location_node_id.
    Соответствует псевдо-узлу "Без места" в equipmentLocationTree.js.

    sort/order — ТЗ раздел 3.2: whitelist колонок (EQUIPMENT_SORT_COLUMNS)
    во избежание SQL-инъекции через имя колонки (нельзя параметризовать
    идентификатор колонки через placeholder, только через явную сверку
    со списком разрешённых). Намеренно НЕТ сортировки по месту
    (workshop/location_node.name) — см. комментарий в ТЗ: workshop
    переходное поле, не гарантированно заполнено у новых записей, а
    навигация по месту уже полностью закрыта деревом слева (3.1).

    attr_filters — ТЗ раздел 3.4: {attribute_key: value}, ключи должны
    быть УЖЕ провалидированы ВЫЗЫВАЮЩИМ (routes-слой, сверка против
    get_effective_attributes(type_id)) до передачи сюда — этот
    репозиторий сам ничего не валидирует (по конвенции проекта —
    репозитории только SQL). json_extract() второй аргумент (путь)
    строится через конкатенацию `'$.' || ?` — это ОБЫЧНОЕ выражение
    SQLite, значение пути передаётся как параметризованный bind (не
    склеено вручную в SQL-строку), инъекция через сам ключ невозможна
    даже без валидации на уровне routes; валидация нужна для другого —
    не пускать в фильтр атрибуты, которые вообще не принадлежат этому
    типу (семантическая, а не security-защита)."""
    cur = conn.cursor()
    conditions = []
    params = []
    if equipment_type_id:
        conditions.append('e.equipment_type_id = ?')
        params.append(equipment_type_id)
    if search:
        conditions.append('(e.name LIKE ? OR e.article LIKE ?)')
        params += [f'%{search}%'] * 2
    if unassigned:
        conditions.append('''(
            NOT EXISTS (SELECT 1 FROM equipment_placement ep0 WHERE ep0.equipment_id = e.id)
            AND e.location_node_id IS NULL
        )''')
    elif location_node_id:
        subtree_ids = location_repo.get_subtree_ids(conn, location_node_id)
        if not subtree_ids:
            return []
        placeholders = ','.join('?' * len(subtree_ids))
        conditions.append(f'''(
            EXISTS (SELECT 1 FROM equipment_placement ep WHERE ep.equipment_id = e.id AND ep.location_node_id IN ({placeholders}))
            OR (
                NOT EXISTS (SELECT 1 FROM equipment_placement ep2 WHERE ep2.equipment_id = e.id)
                AND e.location_node_id IN ({placeholders})
            )
        )''')
        params += subtree_ids + subtree_ids
    for key, value in (attr_filters or {}).items():
        conditions.append("json_extract(e.specs_json, '$.' || ?) = ?")
        params += [key, value]
    where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    if sort in EQUIPMENT_SORT_COLUMNS:
        order_sql = 'ASC' if str(order).lower() == 'asc' else 'DESC'
        order_clause = f'ORDER BY {EQUIPMENT_SORT_COLUMNS[sort]} {order_sql}'
    else:
        order_clause = 'ORDER BY e.updated_at DESC'

    # placement_count/placement_location_name — для колонки "Место" в
    # таблице списка (ТЗ 3.2): показывает первое место установки + сколько
    # их всего (карточка сама даёт полный список через "Места установки").
    # Легаси location_name оставлен для записей без единого placement —
    # см. локальный фолбэк в equipment.js::renderEquipmentTable.
    cur.execute(f'''
        SELECT e.*, et.name AS equipment_type_name, ln.name AS location_name,
            (SELECT COUNT(*) FROM equipment_placement ep3 WHERE ep3.equipment_id = e.id) AS placement_count,
            (SELECT ln3.name FROM equipment_placement ep4
                JOIN location_node ln3 ON ln3.id = ep4.location_node_id
                WHERE ep4.equipment_id = e.id ORDER BY ep4.id LIMIT 1) AS placement_location_name
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        LEFT JOIN location_node ln ON ln.id = e.location_node_id
        {where_clause}
        {order_clause}
    ''', params)
    result = []
    for row in cur.fetchall():
        d = _row_to_dict(row)
        d['specs'] = json.loads(d['specs_json']) if d.get('specs_json') else {}
        result.append(d)
    return result


def get_equipment_location_counts(conn) -> dict:
    """{location_node_id: count} — только СОБСТВЕННЫЕ счётчики узлов
    (сколько оборудования привязано ИМЕННО к этому узлу), без
    суммирования по поддереву — суммирование вверх по дереву делает
    фронтенд (equipmentLocationTree.js::_equipmentSubtreeCount), т.к.
    дерево уже загружено там целиком и пересчитывать на каждый клик
    дешевле в памяти браузера, чем гонять рекурсивный SQL на каждый
    рендер дерева.

    Отдельно добавляем ключ 'unassigned' — количество оборудования БЕЗ
    места (location_node_id IS NULL). Раньше такое оборудование вообще не
    попадало в выборку (WHERE location_node_id IS NOT NULL), из-за чего
    итог "Все объекты" в боковом дереве (сумма по всем узлам-корням) был
    занижен ровно на количество непривязанного оборудования и не совпадал
    с реальным числом записей в номенклатуре.
    Ключи возвращаемого словаря — ВСЕ строки (str(location_node_id) и
    'unassigned'), а не int. Иначе Flask's jsonify (sort_keys=True по
    умолчанию) при сортировке ключей перед сериализацией падает:
    TypeError: '<' not supported between instances of 'str' and 'int' —
    Python не умеет сравнивать int и str для сортировки смешанного
    словаря. На фронтенде ничего не меняется: JSON-ключи и так всегда
    строки на проводе, а JS обращается к ним через object[nodeId], что
    само приводит nodeId к строке при доступе.
    """
    cur = conn.cursor()
    cur.execute(
        'SELECT location_node_id, COUNT(*) as cnt FROM equipment '
        'GROUP BY location_node_id'
    )
    result = {}
    unassigned = 0
    for row in cur.fetchall():
        if row['location_node_id'] is None:
            unassigned = row['cnt']
        else:
            result[str(row['location_node_id'])] = row['cnt']
    result['unassigned'] = unassigned
    return result


def create_equipment(conn, data: dict) -> int:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO equipment
            (equipment_type_id, name, article, manufacturer,
             workshop, location, location_node_id, criticality, installed_at,
             specs_json, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['equipment_type_id'], data['name'], data.get('article'), data.get('manufacturer'),
        data.get('workshop'), data.get('location'), data.get('location_node_id'),
        data.get('criticality'), data.get('installed_at'),
        json.dumps(data.get('specs', {}), ensure_ascii=False), data.get('note'), now, now,
    ))
    conn.commit()
    return cur.lastrowid


def update_equipment(conn, equipment_id: int, data: dict) -> bool:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        UPDATE equipment SET
            equipment_type_id = ?, name = ?, article = ?, manufacturer = ?,
            workshop = ?, location = ?, location_node_id = ?, criticality = ?, installed_at = ?,
            specs_json = ?, note = ?, updated_at = ?
        WHERE id = ?
    ''', (
        data['equipment_type_id'], data['name'], data.get('article'), data.get('manufacturer'),
        data.get('workshop'), data.get('location'), data.get('location_node_id'),
        data.get('criticality'), data.get('installed_at'),
        json.dumps(data.get('specs', {}), ensure_ascii=False), data.get('note'), now, equipment_id,
    ))
    conn.commit()
    return cur.rowcount > 0


def equipment_referenced_by_incidents(conn, equipment_id: int) -> bool:
    """Guard для удаления: оборудование привязано хотя бы к одной заявке
    Инцидента (incident_ticket_equipment). Найдено при финальной
    совместной приёмке модулей: incident_ticket_equipment.equipment_id
    объявлен REFERENCES equipment(id) БЕЗ ON DELETE CASCADE/SET NULL, а
    PRAGMA foreign_keys=ON включён — без этой проверки прямое удаление
    оборудования, на которое ссылается живая заявка, падало сырым
    `sqlite3.IntegrityError: FOREIGN KEY constraint failed` (500), а не
    понятным сообщением пользователю."""
    cur = conn.execute(
        'SELECT 1 FROM incident_ticket_equipment WHERE equipment_id = ? LIMIT 1', (equipment_id,)
    )
    return cur.fetchone() is not None


def delete_equipment(conn, equipment_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM equipment WHERE id = ?', (equipment_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# Учёт ЗИП (ТЗ раздел 3.7) — ЗИП это тоже equipment, просто с особым
# местом (node_type='warehouse'). Отдельной таблицы склада нет.
# ---------------------------------------------------------------------

def get_stock_summary(conn):
    """Сводка по типам оборудования: сколько всего/в эксплуатации/в
    ЗИП/не размещено + дефицит против нормы.

    Начинаем с equipment_type (не с equipment) — иначе типы с заданной
    min_stock_qty, но без единиц в базе, выпали бы из сводки. Ровно один
    склад — соглашение, не enforced constraint (см. ТЗ): если случайно
    помечено НЕСКОЛЬКО узлов node_type='warehouse', суммируем поддеревья
    всех, не падаем и не выбираем "первый попавшийся".

    Единица подсчёта — не строка equipment, а физический экземпляр.
    С появлением equipment_placement (ТЗ "Место") одна строка equipment
    может представлять несколько физических единиц: шкаф +E021 с
    обозначениями КМ1/КМ2/КМ3 — это 3 экземпляра одного типа, а не один.
    Поэтому для записи оборудования, у которой ЕСТЬ строки в
    equipment_placement, количество единиц = число этих строк (каждая
    строка placement — один физический экземпляр, вне зависимости от
    того, задано у неё designation или нет). Для записи БЕЗ единого
    placement (ещё не размещена ни в одном месте вообще) — считаем как
    1 единицу по старому equipment.location_node_id (обратная
    совместимость с записями, заведёнными до появления "Мест", и просто
    удобство для склад-item без детализации по месту)."""
    warehouse_rows = conn.execute(
        "SELECT id FROM location_node WHERE node_type = 'warehouse'"
    ).fetchall()
    warehouse_subtree_ids = set()
    for row in warehouse_rows:
        warehouse_subtree_ids.update(location_repo.get_subtree_ids(conn, row['id']))

    types = conn.execute(
        'SELECT id, code, name, min_stock_qty FROM equipment_type ORDER BY name'
    ).fetchall()

    result = []
    for t in types:
        # Один запрос на тип: строка оборудования + все её placements
        # (LEFT JOIN — для записей без единого placement ep.id будет NULL,
        # это и есть сигнал "считать по старому location_node_id").
        rows = conn.execute('''
            SELECT e.id AS equipment_id, e.location_node_id AS equip_loc,
                   ep.id AS placement_id, ep.location_node_id AS placement_loc
            FROM equipment e
            LEFT JOIN equipment_placement ep ON ep.equipment_id = e.id
            WHERE e.equipment_type_id = ?
        ''', (t['id'],)).fetchall()

        by_equipment = {}
        for r in rows:
            by_equipment.setdefault(r['equipment_id'], []).append(r)

        # Разворачиваем каждую запись оборудования в список локаций ЕЁ
        # физических единиц: несколько placements -> несколько единиц,
        # ни одного placement -> одна единица по legacy-полю.
        unit_locations = []
        for eq_id, group in by_equipment.items():
            placement_rows = [g for g in group if g['placement_id'] is not None]
            if placement_rows:
                unit_locations.extend(g['placement_loc'] for g in placement_rows)
            else:
                unit_locations.append(group[0]['equip_loc'])

        total = len(unit_locations)
        unlocated = sum(1 for loc in unit_locations if loc is None)
        in_stock = sum(1 for loc in unit_locations if loc is not None and loc in warehouse_subtree_ids)

        # in_use — остаток, а не отдельный COUNT: unlocated (место не
        # указано) НЕ должно молча попадать в "в эксплуатации" — иначе
        # искажается картина "всё занято" для старых немигрированных
        # записей (см. ТЗ, пояснение к этому разделу).
        in_use = total - in_stock - unlocated

        deficit = None
        if t['min_stock_qty'] is not None:
            deficit = max(0, t['min_stock_qty'] - in_stock)

        result.append({
            'equipment_type_id': t['id'],
            'code': t['code'],
            'name': t['name'],
            'total': total,
            'in_use': in_use,
            'in_stock': in_stock,
            'unlocated': unlocated,
            'min_stock_qty': t['min_stock_qty'],
            'deficit': deficit,
        })
    return result


def update_equipment_type_min_stock_qty(conn, type_id: int, min_stock_qty) -> bool:
    """min_stock_qty может быть None (норма не задана — отличается от 0
    = "норма ноль, докупать не нужно")."""
    cur = conn.cursor()
    cur.execute('UPDATE equipment_type SET min_stock_qty = ? WHERE id = ?', (min_stock_qty, type_id))
    conn.commit()
    return cur.rowcount > 0


def count_all(conn) -> int:
    """Общее количество записей оборудования — ТЗ раздел 4 (дашборд-
    счётчики). Тот же принцип, что count_all в incident_ticket_repo."""
    return conn.execute('SELECT COUNT(*) AS c FROM equipment').fetchone()['c']
