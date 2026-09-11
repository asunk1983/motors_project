"""Repository для режимов работы (таблица operating_modes).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
"""
from modules.db import MODE_COLUMNS
from modules.audit import log_field_changes


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _summarize_modes(modes: list[dict]) -> str:
    """Компактная человекочитаемая сводка списка режимов — для журнала
    изменений (modules/audit.py::log_field_changes). Режимы заменяются
    целиком (replace_all — DELETE всех + INSERT новых, без стабильных id
    между сохранениями карточки), поэтому точечный дифф "было поле X,
    стало Y" по одному режиму не применим — логируем весь список одной
    строкой поля 'modes' у родителя (entity_type='engine')."""
    if not modes:
        return ''
    parts = []
    for m in modes:
        bits = []
        if m.get('power'):
            bits.append(f"{m['power']}кВт")
        if m.get('frequency'):
            bits.append(f"{m['frequency']}Гц")
        if m.get('rpm'):
            bits.append(f"{m['rpm']}об/мин")
        parts.append('/'.join(bits) if bits else '(пусто)')
    return '; '.join(parts)


def get_all(conn, engine_id: int):
    """Получить все режимы работы для двигателя."""
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM operating_modes WHERE engine_id = ? ORDER BY id',
        (engine_id,)
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def replace_all(conn, engine_id: int, modes: list[dict], actor: dict | None = None) -> None:
    """Заменить все режимы двигателя (удалить старые, вставить новые).

    actor — dict текущего пользователя (request.current_user), для
    журнала изменений (см. _summarize_modes выше — логируется одной
    строкой на весь список, как поле 'modes' сущности 'engine')."""
    old_summary = _summarize_modes(get_all(conn, engine_id))
    new_summary = _summarize_modes(modes)
    log_field_changes(conn, 'engine', engine_id, actor,
                       {'modes': old_summary}, {'modes': new_summary})

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
