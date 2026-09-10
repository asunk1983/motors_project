"""repositories/audit_repo.py — чтение журнала изменений (audit_log).

Только SQL/Python-фильтрация, без бизнес-логики — по конвенции репозиториев
проекта. Запись в audit_log делает modules/audit.py::log_field_changes
(вызывается ИЗ каждой repository-функции обновления) — это отдельный
модуль намеренно: modules/audit.py — точка ЗАПИСИ (используется всеми
repo с UPDATE), audit_repo.py — точка ЧТЕНИЯ (используется только
вкладкой "Журнал").
"""

# Потолок строк, вычитываемых из SQL перед Python-фильтрацией по автору
# (см. list_entries) — защита от загрузки всего журнала в память при
# очень широком фильтре на большом объёме данных.
MAX_SCAN_ROWS = 5000


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def list_entries(conn, entity_type: str | None = None, entity_id: int | None = None,
                  actor_query: str = '', date_from: str | None = None, date_to: str | None = None,
                  limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """Возвращает (записи_для_страницы, всего_найдено_с_учётом_фильтров).

    entity_type/entity_id/date_from/date_to — фильтруются в SQL (значения
    латиница/ISO-даты, регистронезависимость не нужна).

    actor_query — фильтруется В PYTHON после SQL-выборки (регистронезависимый
    поиск по ФИО автора): встроенная в SQLite регистронезависимость
    LIKE/COLLATE NOCASE не работает для кириллицы (тот же принцип и то же
    обоснование, что в location_repo.search/crew_repo.search — 'Зона' LIKE
    '%зона%' в чистом SQLite вернёт 0 без ICU-расширения). При активном
    actor_query пагинация считается по итогам Python-фильтрации, а не по
    SQL COUNT — то есть total в этом случае не может превышать MAX_SCAN_ROWS
    (для масштаба этого проекта это не практическое ограничение)."""
    conditions = []
    params = []
    if entity_type:
        conditions.append('entity_type = ?')
        params.append(entity_type)
    if entity_id is not None:
        conditions.append('entity_id = ?')
        params.append(entity_id)
    if date_from:
        conditions.append('changed_at >= ?')
        params.append(date_from)
    if date_to:
        conditions.append('changed_at <= ?')
        params.append(date_to)
    where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    cur = conn.cursor()

    if actor_query:
        cur.execute(
            f'SELECT * FROM audit_log {where_clause} ORDER BY changed_at DESC, id DESC LIMIT ?',
            params + [MAX_SCAN_ROWS]
        )
        rows = [_row_to_dict(r) for r in cur.fetchall()]
        q = actor_query.lower()
        rows = [r for r in rows if q in (r.get('changed_by_display_name') or '').lower()]
        total = len(rows)
        page_rows = _attach_value_labels(conn, rows[offset:offset + limit])
        return page_rows, total

    cur.execute(f'SELECT COUNT(*) AS c FROM audit_log {where_clause}', params)
    total = cur.fetchone()['c']

    cur.execute(
        f'SELECT * FROM audit_log {where_clause} ORDER BY changed_at DESC, id DESC LIMIT ? OFFSET ?',
        params + [limit, offset]
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    rows = _attach_value_labels(conn, rows)
    return rows, total


def _resolve_location_label(conn, value):
    """location_node_id -> человекочитаемый путь места (breadcrumb),
    например 'Цех №1 → Линия 2 → Зона 3', вместо голого числового id."""
    if value in (None, ''):
        return None
    try:
        node_id = int(value)
    except (TypeError, ValueError):
        return None
    from repositories import location_repo
    if location_repo.get_by_id(conn, node_id) is None:
        return None  # место с таким id больше не существует (удалено) — оставляем голый id на фронте
    return location_repo.get_breadcrumb_text(conn, node_id)


# Резолверы значений полей, хранящих внешний ключ (id), в человекочитаемый
# label — расширяемо: добавить новый FK-field_name сюда, когда понадобится
# (например crew_id -> ФИО, equipment_type_id -> название типа). Каждый
# резолвер: (conn, raw_value) -> str | None. None means "не смогли
# определить" — фронт в этом случае покажет исходное значение как есть.
FIELD_VALUE_RESOLVERS = {
    'location_node_id': _resolve_location_label,
}


def _attach_value_labels(conn, rows: list[dict]) -> list[dict]:
    """Добавляет old_value_display/new_value_display для полей из
    FIELD_VALUE_RESOLVERS — не переопределяет old_value/new_value (сырые
    значения остаются в ответе), фронт сам решает, что показывать."""
    for row in rows:
        resolver = FIELD_VALUE_RESOLVERS.get(row.get('field_name'))
        if not resolver:
            continue
        row['old_value_display'] = resolver(conn, row.get('old_value'))
        row['new_value_display'] = resolver(conn, row.get('new_value'))
    return rows


def growth_stats(conn, days: int = 90) -> dict:
    """Кол-во новых записей audit_log по дням за последние `days` дней
    (для графика динамики разрастания журнала) + общее количество строк
    в audit_log на текущий момент. changed_at хранится в ISO-формате
    (datetime.now().isoformat()) — первые 10 символов всегда YYYY-MM-DD,
    группировка по этому префиксу корректна без парсинга даты."""
    cur = conn.cursor()
    cur.execute(
        "SELECT substr(changed_at, 1, 10) AS day, COUNT(*) AS c "
        "FROM audit_log WHERE changed_at >= date('now', ?) "
        "GROUP BY day ORDER BY day",
        (f'-{days} days',)
    )
    by_day = {r['day']: r['c'] for r in cur.fetchall()}
    cur.execute('SELECT COUNT(*) AS c FROM audit_log')
    total = cur.fetchone()['c']
    return {'by_day': by_day, 'total': total, 'days': days}


def list_entity_types(conn) -> list[str]:
    """Список различных entity_type, уже встречавшихся в журнале — для
    выпадающего фильтра на фронте. Не хардкодим список типов сущностей на
    клиенте: он сам пополнится, когда в журнале появится первая запись
    нового типа (например, после добавления логирования в новый repo)."""
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT entity_type FROM audit_log ORDER BY entity_type')
    return [r['entity_type'] for r in cur.fetchall()]
