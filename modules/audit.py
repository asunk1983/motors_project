"""Единая точка записи изменений в журнал (audit_log).

Вызывается ИЗ repository-функций обновления (engine_repo.update,
equipment_repo.update_equipment, incident_ticket_repo.update и т.д.) —
единой обёртки/декоратора над всеми UPDATE в проекте нет (каждая
repo-функция пишет свой SQL сама), поэтому вызов этого helper'а
добавляется в каждую точечно, но сама логика сравнения и записи диффа
общая и живёт только здесь.
"""
from datetime import datetime


def log_creation(conn, entity_type: str, entity_id: int, actor: dict | None, summary: str | None) -> None:
    """Пишет одну строку в audit_log о создании записи.

    summary — короткое человекочитаемое описание созданного (например,
    название/заголовок/ФИО), чтобы в журнале было видно, ЧТО создали, а не
    только entity_id. field_name зафиксирован как '__created__' —
    служебный маркер, отличимый от обычных имён полей (не может
    совпасть с реальной колонкой таблицы, так как содержит подчёркивания
    по краям и никогда не встретится как имя SQL-колонки в этом проекте)."""
    actor_id = actor.get('id') if actor else None
    actor_name = (actor.get('display_name') or actor.get('username')) if actor else None
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO audit_log '
        '(entity_type, entity_id, field_name, old_value, new_value, '
        ' changed_by_user_id, changed_by_display_name, changed_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (entity_type, entity_id, '__created__', None, summary, actor_id, actor_name, now)
    )


def log_deletion(conn, entity_type: str, entity_id: int, actor: dict | None, summary: str | None) -> None:
    """Пишет одну строку в audit_log об удалении записи.

    summary — короткое описание того, что удалили; вызывающая сторона
    обязана достать его из записи ДО DELETE (после удаления читать уже
    нечего) — см. места вызова в repositories/*.py::delete*()."""
    actor_id = actor.get('id') if actor else None
    actor_name = (actor.get('display_name') or actor.get('username')) if actor else None
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO audit_log '
        '(entity_type, entity_id, field_name, old_value, new_value, '
        ' changed_by_user_id, changed_by_display_name, changed_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (entity_type, entity_id, '__deleted__', summary, None, actor_id, actor_name, now)
    )


def log_field_changes(conn, entity_type: str, entity_id: int, actor: dict | None,
                       old_row: dict | None, new_fields: dict) -> None:
    """Пишет по одной строке audit_log на каждое РЕАЛЬНО изменившееся поле.

    old_row — dict текущей записи ДО изменения (например, результат
    get_by_id/прямого SELECT), должен содержать ключи из new_fields.
    new_fields — dict {имя_поля: новое_значение} — только те поля,
    которые вызывающая сторона реально собирается записать этим UPDATE
    (не весь возможный набор колонок таблицы).
    actor — dict вроде request.current_user (ожидаются ключи id,
    username, display_name) или None — правка без привязки к
    пользователю (служебный/системный вызов), тогда changed_by_*
    пишутся NULL.

    Сравнение — по строковому представлению (str(old) == str(new)),
    чтобы не давать ложных срабатываний из-за разницы типов между тем,
    что хранит SQLite (TEXT/INTEGER как есть), и тем, что прислал JSON
    (int/str/None) для одного и того же по смыслу значения.

    Не делает commit — вызывающая сторона коммитит изменение записи и
    журнал в одной транзакции (см. места вызова)."""
    if not old_row:
        return

    actor_id = actor.get('id') if actor else None
    actor_name = (actor.get('display_name') or actor.get('username')) if actor else None
    now = datetime.now().isoformat()

    cur = conn.cursor()
    for field, new_value in new_fields.items():
        if field not in old_row:
            continue
        old_value = old_row.get(field)
        old_str = '' if old_value is None else str(old_value)
        new_str = '' if new_value is None else str(new_value)
        if old_str == new_str:
            continue
        cur.execute(
            'INSERT INTO audit_log '
            '(entity_type, entity_id, field_name, old_value, new_value, '
            ' changed_by_user_id, changed_by_display_name, changed_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (entity_type, entity_id, field,
             old_value if old_value is None else str(old_value),
             new_value if new_value is None else str(new_value),
             actor_id, actor_name, now)
        )
