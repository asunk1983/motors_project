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
        return rows[offset:offset + limit], total

    cur.execute(f'SELECT COUNT(*) AS c FROM audit_log {where_clause}', params)
    total = cur.fetchone()['c']

    cur.execute(
        f'SELECT * FROM audit_log {where_clause} ORDER BY changed_at DESC, id DESC LIMIT ? OFFSET ?',
        params + [limit, offset]
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    return rows, total


def list_entity_types(conn) -> list[str]:
    """Список различных entity_type, уже встречавшихся в журнале — для
    выпадающего фильтра на фронте. Не хардкодим список типов сущностей на
    клиенте: он сам пополнится, когда в журнале появится первая запись
    нового типа (например, после добавления логирования в новый repo)."""
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT entity_type FROM audit_log ORDER BY entity_type')
    return [r['entity_type'] for r in cur.fetchall()]
