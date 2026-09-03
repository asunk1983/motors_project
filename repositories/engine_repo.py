"""Repository для двигателей (таблица engines).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
Все функции принимают sqlite3.Connection как первый аргумент.
"""
from datetime import datetime

from modules.db import ENGINE_COLUMNS_ORDERED


def _row_to_dict(row):
    """Преобразует sqlite3.Row в dict."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def get_by_id(conn, engine_id: int):
    """Получить двигатель по ID (без modes/works)."""
    cur = conn.cursor()
    cur.execute('SELECT * FROM engines WHERE id = ?', (engine_id,))
    return _row_to_dict(cur.fetchone())


def get_with_details(conn, engine_id: int):
    """Получить двигатель + modes + works (для карточки/печати)."""
    engine = get_by_id(conn, engine_id)
    if engine is None:
        return None
    engine['modes'] = get_modes_for_engine(conn, engine_id)
    engine['works'] = get_works_for_engine(conn, engine_id)
    engine['photo_count'] = engine.get('photo_count') or 0
    return engine


def get_modes_for_engine(conn, engine_id: int):
    """Получить режимы работы двигателя."""
    from repositories.mode_repo import get_all
    return get_all(conn, engine_id)


def get_works_for_engine(conn, engine_id: int):
    """Получить произведённые работы двигателя."""
    from repositories.work_repo import get_all
    return get_all(conn, engine_id)


def get_all(conn, limit: int = 30, offset: int = 0, sort: str = 'location_asc',
            search_field: str = 'all', search_query: str = '',
            workshop: str = None, location: str = None, status: str = None):
    """Получить список двигателей с пагинацией, сортировкой и поиском.

    workshop/location — точный (не LIKE) фильтр для дерева навигации,
    комбинируется с обычным текстовым поиском (search_field/search_query).
    Пустая строка '' означает "без цеха"/"без места установки" (NULL или '').

    status — точный фильтр по эксплуатационному состоянию
    ('work'/'reserve'/'repair'). Фильтр работает по вычисляемому полю
    last_work_status (= статус последней записи maintenance_works по
    (date, id), см. CTE ниже), а не по устаревшему engines.status.
    None — фильтр не активен (все статусы).

    Поле `status` в возвращаемых dict'ах = COALESCE(last_work_status,
    'reserve'). Если у движка нет ни одной записи в maintenance_works —
    используется дефолт 'reserve'. engines.status остаётся в SELECT как
    engines_status для обратной совместимости, но в JSON для фронта
    отдаётся именно пересчитанный status (см. SELECT-list).
    """
    sort_map = {
        'location_asc': 'location ASC',
        'location_desc': 'location DESC',
        'id_desc': 'id DESC',
        'id_asc': 'id ASC',
        'engine_type_asc': 'engine_type ASC',
        'engine_type_desc': 'engine_type DESC',
        'manufacturer_asc': 'manufacturer ASC',
        'manufacturer_desc': 'manufacturer DESC',
        'created_at_asc': 'created_at ASC',
        'created_at_desc': 'created_at DESC',
        'updated_at_asc': 'updated_at ASC',
        'updated_at_desc': 'updated_at DESC',
        'photo_count_asc': 'photo_count ASC',
        'photo_count_desc': 'photo_count DESC',
    }
    order_by = sort_map.get(sort, 'location ASC')

    conditions = []
    params = []
    if search_query:
        if search_field == 'all':
            conditions.append('(' + ' OR '.join(
                f"{col} LIKE ?" for col in
                ('location', 'engine_type', 'serial_number', 'manufacturer', 'purpose', 'workshop')
            ) + ')')
            params += [f'%{search_query}%'] * 6
        elif search_field in ENGINE_COLUMNS_ORDERED:
            conditions.append(f'{search_field} LIKE ?')
            params.append(f'%{search_query}%')

    if workshop is not None:
        if workshop == '':
            conditions.append("(workshop IS NULL OR workshop = '')")
        else:
            conditions.append('workshop = ?')
            params.append(workshop)

    if location is not None:
        if location == '':
            conditions.append("(location IS NULL OR location = '')")
        else:
            conditions.append('location = ?')
            params.append(location)

    # Фильтр по статусу — по вычисляемому last_work_status, а не по
    # устаревшему engines.status. SQLite НЕ разрешает алиас CTE в WHERE,
    # поэтому дублируем выражение подзапроса прямо здесь. Корректность
    # гарантирована тем, что выражение полностью совпадает с CTE ниже
    # (тот же ORDER BY date DESC, id DESC, LIMIT 1, тот же COALESCE с
    # дефолтом 'reserve').
    if status:
        conditions.append(
            "COALESCE((SELECT status FROM maintenance_works w "
            "WHERE w.engine_id = e.id "
            "ORDER BY w.date DESC, w.id DESC LIMIT 1), 'reserve') = ?"
        )
        params.append(status)

    where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    # CTE: для каждого engine_id берём ровно одну запись maintenance_works
    # — ту, что максимальна по паре (date, id). ROW_NUMBER() + PARTITION BY
    # делает это явно. NULL date сортируется ниже валидной ISO-даты в DESC,
    # поэтому запись с реальной датой всегда выигрывает; tie-breaker по
    # id DESC для записей с одинаковой датой.
    #
    # Колонка CTE названа `last_work_status` (а не просто `status`) —
    # чтобы избежать неоднозначности с колонкой `status` таблицы
    # maintenance_works и с алиасом `status` в основном SELECT-list:
    # в SQLite при наличии нескольких источников с одинаковым именем
    # колонки в разных scope (CTE + основная таблица + алиас результата)
    # разрешение имени в ORDER BY/WHERE может стать неоднозначным и
    # приводить к `no such column: status` в некоторых версиях SQLite.
    # Явное переименование делает каждое обращение квалифицированным.
    #
    # В основном SELECT engines.status алиасится на COALESCE(...,'reserve')
    # и отдаётся под ключом 'status' — фронт (catalog.js) ничего не знает
    # о переименовании и продолжает читать e.status.
    sql = f'''
        WITH last_work AS (
            SELECT engine_id, status AS last_work_status,
                   ROW_NUMBER() OVER (
                       PARTITION BY engine_id
                       ORDER BY date DESC, id DESC
                   ) AS rn
            FROM maintenance_works
        )
        SELECT e.id, e.filename, e.purpose, e.workshop, e.location,
               e.engine_type, e.manufacturer, e.serial_number,
               e.bearing_front, e.bearing_rear, e.shaft_diameter,
               e.protection_class, e.mounting_type, e.temp_sensor,
               e.encoder, e.cooling, e.note, e.photo_count,
               e.created_at, e.updated_at,
               COALESCE(lw.last_work_status, 'reserve') AS status,
               e.status AS engines_status
        FROM engines e
        LEFT JOIN last_work lw ON lw.engine_id = e.id AND lw.rn = 1
        {where_clause}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
    '''

    cur = conn.cursor()
    cur.execute(sql, params + [limit, offset])
    return [_row_to_dict(row) for row in cur.fetchall()]


def count_all(conn, search_field: str = 'all', search_query: str = ''):
    """Посчитать общее количество двигателей (для пагинации)."""
    where_clause = ''
    params = []
    if search_query:
        if search_field == 'all':
            where_clause = 'WHERE ' + ' OR '.join(
                f"{col} LIKE ?" for col in
                ('location', 'engine_type', 'serial_number', 'manufacturer', 'purpose', 'workshop')
            )
            params = [f'%{search_query}%'] * 6
        elif search_field in ENGINE_COLUMNS_ORDERED:
            where_clause = f'WHERE {search_field} LIKE ?'
            params = [f'%{search_query}%']

    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) FROM engines {where_clause}', params)
    return cur.fetchone()[0]


def _next_free_id(conn) -> int:
    """Находит минимальный свободный id: если id=1 отсутствует — вернёт 1,
    иначе первую "дыру" в последовательности после существующих id, а если
    дыр нет — max(id)+1. Гарантирует инвариант "max(id) никогда не
    превышает количество записей" при штучном удалении/создании.

    Оборачивается вызывающей стороной в BEGIN IMMEDIATE, чтобы вычисление
    свободного id и последующий INSERT были атомарны (иначе при двух
    одновременных запросах на создание оба могут вычислить один и тот же
    свободный id и вставка второго упадёт на PK constraint)."""
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM engines WHERE id = 1')
    if cur.fetchone() is None:
        return 1
    cur.execute('''
        SELECT MIN(id + 1) FROM engines e
        WHERE NOT EXISTS (SELECT 1 FROM engines e2 WHERE e2.id = e.id + 1)
    ''')
    return cur.fetchone()[0]


def create(conn, data: dict) -> int:
    """Создать двигатель. Возвращает ID.

    ID выбирается явно как минимальный свободный (см. _next_free_id), а не
    отдаётся AUTOINCREMENT — так id никогда не "убегает" вперёд количества
    записей при штучном создании/удалении в процессе обычной работы.
    Массовый импорт (import_routes.py) идёт отдельным путём через
    executemany и сюда не заходит — там своя логика, рассчитанная на то,
    что импорт всегда выполняется на пустую БД (гарантия зафиксирована в
    /api/clear и /api/import-folder).

    created_at/updated_at — ВСЕГДА серверное время создания, а не то, что
    (если вообще) пришло в data. created_at/updated_at нет в
    ENGINE_COLUMNS_ORDERED, поэтому sanitize_engine_data (schemas/
    engine_schema.py) уже отфильтровал их из клиентского payload раньше —
    это дублирующая, но не лишняя защита на случай прямого вызова
    create() в обход роута."""
    now = datetime.now().isoformat()
    data_columns = [k for k in ENGINE_COLUMNS_ORDERED if k != 'id' and k in data]
    all_columns = data_columns + ['created_at', 'updated_at']
    col_names = ', '.join(['id'] + all_columns)
    placeholders = ', '.join(['?'] * (len(all_columns) + 1))
    values = [data[k] for k in data_columns] + [now, now]

    cur = conn.cursor()
    cur.execute('BEGIN IMMEDIATE')
    try:
        engine_id = _next_free_id(conn)
        cur.execute(
            f'INSERT INTO engines ({col_names}) VALUES ({placeholders})',
            [engine_id] + values
        )
        conn.commit()
        return engine_id
    except Exception:
        conn.rollback()
        raise


def update(conn, engine_id: int, data: dict) -> bool:
    """Обновить двигатель. Возвращает True если строка была изменена.

    updated_at проставляется на КАЖДОЕ сохранение карточки — характеристики,
    режимы и работы теперь сохраняются одним PUT-запросом (см.
    routes/engines.py::update_engine), поэтому "сохранение карточки" и
    "изменение updated_at" — синонимы. created_at не трогается: он
    неизменяем после create() (и, как и там, отфильтрован из клиентского
    payload заранее, т.к. отсутствует в ENGINE_COLUMNS_ORDERED)."""
    now = datetime.now().isoformat()
    set_parts = []
    values = []
    for col in ENGINE_COLUMNS_ORDERED:
        if col == 'id':
            continue
        if col in data:
            set_parts.append(f'{col} = ?')
            values.append(data[col])

    set_parts.append('updated_at = ?')
    values.append(now)

    values.append(engine_id)
    cur = conn.cursor()
    cur.execute(
        f'UPDATE engines SET {", ".join(set_parts)} WHERE id = ?',
        values
    )
    conn.commit()
    return cur.rowcount > 0


def delete(conn, engine_id: int) -> bool:
    """Удалить двигатель (каскадно удаляет modes и works).

    Схема БД имеет ON DELETE CASCADE, но на продакшен-БД (созданной
    до добавления CASCADE) он не работает. Поэтому удаляем дочерние
    записи явно — в одной транзакции, до удаления самого двигателя.

    ВАЖНО: фото на диске (ID{engine_id}_*.ext) этой функцией НЕ удаляются —
    репозиторий содержит только SQL. Чистка файлов — на уровне роута
    (routes/engines.py::delete_engine), через
    modules.photo_manager.manager.delete_engine_photos_from_disk().
    """
    cur = conn.cursor()
    cur.execute('DELETE FROM operating_modes WHERE engine_id = ?', (engine_id,))
    cur.execute('DELETE FROM maintenance_works WHERE engine_id = ?', (engine_id,))
    cur.execute('DELETE FROM engines WHERE id = ?', (engine_id,))
    conn.commit()
    return cur.rowcount > 0


def update_photo_count(conn, engine_id: int, count: int) -> None:
    """Обновить счётчик фото для двигателя."""
    cur = conn.cursor()
    cur.execute('UPDATE engines SET photo_count = ? WHERE id = ?', (count, engine_id))
    conn.commit()


VALID_STATUSES = ('work', 'reserve', 'repair')


def update_status(conn, engine_id: int, status: str) -> bool:
    """Обновить эксплуатационный статус двигателя.

    Отдельная лёгкая операция (не через update()/ENGINE_COLUMNS_ORDERED) —
    статус меняется кликом по переключателю в карточке, без входа в режим
    редактирования и без валидации остальных полей характеристик.
    updated_at НЕ трогаем: смена статуса — не редактирование карточки.
    """
    cur = conn.cursor()
    cur.execute('UPDATE engines SET status = ? WHERE id = ?', (status, engine_id))
    conn.commit()
    return cur.rowcount > 0


def get_by_filename(conn, filename: str):
    """Найти двигатель по имени файла (для импорта)."""
    cur = conn.cursor()
    cur.execute('SELECT * FROM engines WHERE filename = ?', (filename,))
    return _row_to_dict(cur.fetchone())


def get_locations_tree(conn):
    """Сгруппировать двигатели по workshop → location с подсчётом.

    Возвращает {workshop: {location: count}}. Пустые/NULL значения
    группируются под ключом '' — фронтенд подписывает их как
    "Без цеха"/"Без места установки".
    """
    cur = conn.cursor()
    cur.execute('''
        SELECT COALESCE(workshop, '') AS workshop,
               COALESCE(location, '') AS location,
               COUNT(*) AS cnt
        FROM engines
        GROUP BY workshop, location
    ''')
    tree = {}
    for row in cur.fetchall():
        tree.setdefault(row['workshop'], {})[row['location']] = row['cnt']
    return tree
