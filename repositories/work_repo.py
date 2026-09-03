"""Repository для произведённых работ (таблица maintenance_works).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
"""
WORK_COLUMNS = frozenset([
    'work_number', 'date', 'work_description', 'isolation', 'inspection', 'signature', 'status'
])


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def get_all(conn, engine_id: int):
    """Получить все произведённые работы для двигателя.

    Сортировка: ORDER BY date, id — сначала по дате (хронологический
    порядок), затем по id как tie-breaker (для записей с одинаковой датой,
    в т.ч. NULL/пустой). Это контракт для карточки двигателя: последний
    элемент массива = «последняя запись по хронологии». Совпадает с
    логикой вычисления статуса в engine_repo.get_all (тот же критерий).
    """
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM maintenance_works WHERE engine_id = ? '
        'ORDER BY date, id',
        (engine_id,)
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def replace_all(conn, engine_id: int, works: list[dict]) -> None:
    """Заменить все работы двигателя (удалить старые, вставить новые)."""
    cur = conn.cursor()
    cur.execute('DELETE FROM maintenance_works WHERE engine_id = ?', (engine_id,))
    if works:
        columns = [k for k in WORK_COLUMNS if k in works[0]]
        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join(columns)
        values = []
        for w in works:
            row = [w.get(k) for k in columns]
            row.append(engine_id)
            values.append(row)
        cur.executemany(
            f'INSERT INTO maintenance_works ({col_names}, engine_id) VALUES ({placeholders}, ?)',
            values
        )
    conn.commit()


def create(conn, engine_id: int, work: dict) -> int:
    """Создать одну запись о работе."""
    columns = [k for k in WORK_COLUMNS if k in work]
    placeholders = ', '.join(['?'] * len(columns))
    col_names = ', '.join(columns)
    values = [work[k] for k in columns]

    cur = conn.cursor()
    cur.execute(
        f'INSERT INTO maintenance_works ({col_names}, engine_id) VALUES ({placeholders}, ?)',
        values + [engine_id]
    )
    conn.commit()
    return cur.lastrowid


def delete_all_for_engine(conn, engine_id: int) -> None:
    """Удалить все работы для двигателя."""
    cur = conn.cursor()
    cur.execute('DELETE FROM maintenance_works WHERE engine_id = ?', (engine_id,))
    conn.commit()
