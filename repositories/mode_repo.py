"""Repository для режимов работы (таблица operating_modes).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
"""
from modules.db import MODE_COLUMNS


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def get_all(conn, engine_id: int):
    """Получить все режимы работы для двигателя."""
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM operating_modes WHERE engine_id = ? ORDER BY id',
        (engine_id,)
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def replace_all(conn, engine_id: int, modes: list[dict]) -> None:
    """Заменить все режимы двигателя (удалить старые, вставить новые)."""
    cur = conn.cursor()
    cur.execute('DELETE FROM operating_modes WHERE engine_id = ?', (engine_id,))
    if modes:
        columns = [k for k in MODE_COLUMNS if k in modes[0]]
        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join(columns)
        values = []
        for m in modes:
            row = [m.get(k) for k in columns]
            row.append(engine_id)
            values.append(row)
        cur.executemany(
            f'INSERT INTO operating_modes ({col_names}, engine_id) VALUES ({placeholders}, ?)',
            values
        )
    conn.commit()


def create(conn, engine_id: int, mode: dict) -> int:
    """Создать один режим работы."""
    columns = [k for k in MODE_COLUMNS if k in mode]
    placeholders = ', '.join(['?'] * len(columns))
    col_names = ', '.join(columns)
    values = [mode[k] for k in columns]

    cur = conn.cursor()
    cur.execute(
        f'INSERT INTO operating_modes ({col_names}, engine_id) VALUES ({placeholders}, ?)',
        values + [engine_id]
    )
    conn.commit()
    return cur.lastrowid


def delete_all_for_engine(conn, engine_id: int) -> None:
    """Удалить все режимы для двигателя."""
    cur = conn.cursor()
    cur.execute('DELETE FROM operating_modes WHERE engine_id = ?', (engine_id,))
    conn.commit()
