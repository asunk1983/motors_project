"""Repository для произведённых работ (таблица maintenance_works).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в services/.
"""
from modules.audit import log_field_changes

WORK_COLUMNS = frozenset([
    'work_number', 'date', 'work_description', 'isolation', 'inspection', 'signature', 'status'
])


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


_WORK_FIELDS_ORDER = ('date', 'work_number', 'work_description', 'isolation', 'inspection', 'signature', 'status')

_WORK_FIELD_LABELS = {
    'date': 'дата',
    'work_number': '№',
    'work_description': 'описание',
    'isolation': 'изоляция',
    'inspection': 'осмотр',
    'signature': 'подпись',
    'status': 'статус',
}


def _fmt_work_field(field: str, value) -> str:
    """Человекочитаемое значение одного поля работы (без метки)."""
    if value is None or value == '':
        return '(пусто)'
    if field == 'work_number':
        return f"№{value}"
    return str(value)


def _fmt_work_row_full(work: dict) -> str:
    """Полное описание одной работы (для добавленной/удалённой строки)."""
    bits = [f"{_WORK_FIELD_LABELS[f]}: {_fmt_work_field(f, work.get(f))}"
            for f in _WORK_FIELDS_ORDER if work.get(f)]
    return ', '.join(bits) if bits else '(пусто)'


def _diff_works(old_rows: list[dict], new_rows: list[dict]):
    """Возвращает (old_str, new_str) — в журнал попадают ТОЛЬКО изменённые
    поля, а не весь список целиком.

    Работы заменяются через replace_all (DELETE всех + INSERT новых),
    стабильных id у строк нет, поэтому строки сопоставляются ПО ИНДЕКСУ.
    Для изменённой строки в 'было'/'стало' попадают только те поля,
    значение которых реально изменилось (например 'статус: work' ->
    'статус: done'), а добавленные/удалённые строки показываются целиком.
    Если списки идентичны — возвращает ('', ''), и log_field_changes не
    пишет запись."""
    old_parts, new_parts = [], []
    n = max(len(old_rows), len(new_rows))
    for i in range(n):
        old_row = old_rows[i] if i < len(old_rows) else None
        new_row = new_rows[i] if i < len(new_rows) else None
        if old_row == new_row:
            continue
        label = f"работа {i + 1}"
        if old_row is None:
            new_parts.append(f"{label} добавлена: {_fmt_work_row_full(new_row)}")
        elif new_row is None:
            old_parts.append(f"{label} удалена: {_fmt_work_row_full(old_row)}")
        else:
            o_bits, n_bits = [], []
            for f in _WORK_FIELDS_ORDER:
                ov, nv = old_row.get(f), new_row.get(f)
                if str(ov or '') != str(nv or ''):
                    o_bits.append(f"{_WORK_FIELD_LABELS[f]}: {_fmt_work_field(f, ov)}")
                    n_bits.append(f"{_WORK_FIELD_LABELS[f]}: {_fmt_work_field(f, nv)}")
            if o_bits:
                old_parts.append(f"{label}: " + ', '.join(o_bits))
                new_parts.append(f"{label}: " + ', '.join(n_bits))
    return '; '.join(old_parts), '; '.join(new_parts)


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


def replace_all(conn, engine_id: int, works: list[dict], actor: dict | None = None) -> None:
    """Заменить все работы двигателя (удалить старые, вставить новые).

    actor — dict текущего пользователя (request.current_user), для
    журнала изменений (см. _diff_works выше — логируется одной строкой
    на весь список, как поле 'works' сущности 'engine', но в 'было'/'стало'
    попадают только реально изменённые поля)."""
    old_rows = get_all(conn, engine_id)
    old_summary, new_summary = _diff_works(old_rows, works)
    log_field_changes(conn, 'engine', engine_id, actor,
                       {'works': old_summary}, {'works': new_summary})

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
