"""Repository для режимов работы (таблица operating_modes).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
"""
from modules.db import MODE_COLUMNS
from modules.audit import log_field_changes


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


_MODE_FIELDS_ORDER = ('power', 'frequency', 'voltage', 'current', 'rpm', 'connection_type')

_MODE_FIELD_LABELS = {
    'power': 'мощность',
    'frequency': 'частота',
    'voltage': 'напряжение',
    'current': 'ток',
    'rpm': 'обороты',
    'connection_type': 'тип соединения',
}


def _fmt_mode_field(field: str, value) -> str:
    """Человекочитаемое значение одного поля режима (без метки)."""
    if value is None or value == '':
        return '(пусто)'
    if field == 'power':
        return f'{value}кВт'
    if field == 'frequency':
        return f'{value}Гц'
    if field == 'voltage':
        return f'{value}В'
    if field == 'current':
        return f'{value}А'
    if field == 'rpm':
        return f'{value}об/мин'
    return str(value)  # connection_type — просто текст


def _fmt_mode_row_full(mode: dict) -> str:
    """Полное описание одного режима (для добавленной/удалённой строки)."""
    bits = [f"{_MODE_FIELD_LABELS[f]}: {_fmt_mode_field(f, mode.get(f))}"
            for f in _MODE_FIELDS_ORDER if mode.get(f)]
    return ', '.join(bits) if bits else '(пусто)'


def _diff_modes(old_rows: list[dict], new_rows: list[dict]):
    """Возвращает (old_str, new_str) — в журнал попадают ТОЛЬКО изменённые
    поля, а не весь список целиком.

    Режимы заменяются через replace_all (DELETE всех + INSERT новых),
    стабильных id у строк нет, поэтому строки сопоставляются ПО ИНДЕКСУ.
    Для изменённой строки в 'было'/'стало' попадают только те поля,
    значение которых реально изменилось (например 'напряжение: 380В' ->
    'напряжение: 220В'), а добавленные/удалённые строки показываются
    целиком. Если списки идентичны — возвращает ('', ''), и
    log_field_changes не пишет запись."""
    old_parts, new_parts = [], []
    n = max(len(old_rows), len(new_rows))
    for i in range(n):
        old_row = old_rows[i] if i < len(old_rows) else None
        new_row = new_rows[i] if i < len(new_rows) else None
        if old_row == new_row:
            continue
        label = f"режим {i + 1}"
        if old_row is None:
            new_parts.append(f"{label} добавлен: {_fmt_mode_row_full(new_row)}")
        elif new_row is None:
            old_parts.append(f"{label} удалён: {_fmt_mode_row_full(old_row)}")
        else:
            o_bits, n_bits = [], []
            for f in _MODE_FIELDS_ORDER:
                ov, nv = old_row.get(f), new_row.get(f)
                if str(ov or '') != str(nv or ''):
                    o_bits.append(f"{_MODE_FIELD_LABELS[f]}: {_fmt_mode_field(f, ov)}")
                    n_bits.append(f"{_MODE_FIELD_LABELS[f]}: {_fmt_mode_field(f, nv)}")
            if o_bits:
                old_parts.append(f"{label}: " + ', '.join(o_bits))
                new_parts.append(f"{label}: " + ', '.join(n_bits))
    return '; '.join(old_parts), '; '.join(new_parts)


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
    журнала изменений (см. _diff_modes выше — логируется одной строкой
    на весь список, как поле 'modes' сущности 'engine', но в 'было'/'стало'
    попадают только реально изменённые поля)."""
    old_rows = get_all(conn, engine_id)
    old_summary, new_summary = _diff_modes(old_rows, modes)
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
