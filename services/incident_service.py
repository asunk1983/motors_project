# services/incident_service.py — бизнес-логика модуля "Инциденты".
# ТЗ раздел 2.3: валидация (место существует, ≥1 инициатор, problem не
# пусто), auto-fill created_at/closed_at, guard на удаление Места/Crew.
# Репозитории (location_repo/crew_repo) уже возвращают (ok, error) с
# собственными guard-проверками (дети/ссылки, защита от цикла в move) —
# этот слой их не дублирует, а добавляет то, чего в чистом SQL-репозитории
# по конвенции проекта быть не должно: правила про даты и обязательность
# инициатора для конкретно заявки инцидента.

import sqlite3
from datetime import datetime

from repositories import (
    location_repo, crew_repo, equipment_repo, incident_ticket_repo, incident_equipment_repo,
)

VALID_PRIORITIES = {'low', 'medium', 'high'}
VALID_STATUSES = {'in_progress', 'resolved', 'rejected'}


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _resolve_closed_at(old_status: str, new_status: str, old_closed_at: str | None,
                        explicit_closed_at: str | None) -> str | None:
    """ТЗ раздел 2.5: переход в 'resolved'/'rejected' без явной даты
    закрытия -> дата закрытия = сейчас; возврат в 'in_progress' ->
    сбрасывает дату закрытия; явно переданная дата в payload побеждает
    авто-логику в обоих направлениях (даты редактируемы вручную)."""
    if explicit_closed_at is not None:
        return explicit_closed_at
    if new_status == old_status:
        return old_closed_at
    if new_status in ('resolved', 'rejected'):
        return old_closed_at or _now()
    if new_status == 'in_progress':
        return None
    return old_closed_at


def create_ticket(conn: sqlite3.Connection, *, location_node_id: int, problem: str,
                   created_by_user_id: int, solution: str | None = None,
                   priority: str = 'medium', status: str = 'in_progress',
                   initiator_ids: list[int] | None = None,
                   executor_ids: list[int] | None = None,
                   closed_at: str | None = None) -> tuple[int | None, str | None]:
    problem = (problem or '').strip()
    if not problem:
        return None, 'Поле "Проблема" обязательно'
    initiator_ids = initiator_ids or []
    if len(initiator_ids) < 1:
        return None, 'Нужен хотя бы один инициатор'
    if priority not in VALID_PRIORITIES:
        return None, f'Недопустимый приоритет: {priority}'
    if status not in VALID_STATUSES:
        return None, f'Недопустимый статус: {status}'
    if location_repo.get_by_id(conn, location_node_id) is None:
        return None, 'Указанное место не найдено'
    for crew_id in initiator_ids + (executor_ids or []):
        if crew_repo.get_by_id(conn, crew_id) is None:
            return None, f'Человек с id={crew_id} не найден'

    if closed_at is None and status in ('resolved', 'rejected'):
        closed_at = _now()

    ticket_id = incident_ticket_repo.create(
        conn, location_node_id=location_node_id, problem=problem, created_by_user_id=created_by_user_id,
        solution=solution, priority=priority, status=status, closed_at=closed_at
    )
    incident_ticket_repo.set_initiators(conn, ticket_id, initiator_ids)
    if executor_ids:
        incident_ticket_repo.set_executors(conn, ticket_id, executor_ids)
    return ticket_id, None


def update_ticket(conn: sqlite3.Connection, ticket_id: int, *, location_node_id: int | None = None,
                   problem: str | None = None, solution: str | None = None,
                   priority: str | None = None, status: str | None = None,
                   initiator_ids: list[int] | None = None, executor_ids: list[int] | None = None,
                   closed_at: str | None = None,
                   closed_at_explicitly_set: bool = False) -> tuple[bool, str | None]:
    """closed_at_explicitly_set — отличает "поле не передавали" (None,
    авто-логика по смене статуса) от "поле передали и хотят NULL"
    (пользователь вручную очистил дату закрытия в форме)."""
    current = incident_ticket_repo.get_by_id(conn, ticket_id)
    if current is None:
        return False, 'Заявка не найдена'

    if problem is not None:
        problem = problem.strip()
        if not problem:
            return False, 'Поле "Проблема" не может быть пустым'
    if priority is not None and priority not in VALID_PRIORITIES:
        return False, f'Недопустимый приоритет: {priority}'
    if status is not None and status not in VALID_STATUSES:
        return False, f'Недопустимый статус: {status}'
    if location_node_id is not None and location_repo.get_by_id(conn, location_node_id) is None:
        return False, 'Указанное место не найдено'
    if initiator_ids is not None and len(initiator_ids) < 1:
        return False, 'Нужен хотя бы один инициатор'
    for crew_id in (initiator_ids or []) + (executor_ids or []):
        if crew_repo.get_by_id(conn, crew_id) is None:
            return False, f'Человек с id={crew_id} не найден'

    new_status = status if status is not None else current['status']
    if closed_at_explicitly_set:
        resolved_closed_at = closed_at
    else:
        resolved_closed_at = _resolve_closed_at(current['status'], new_status, current['closed_at'], None)

    incident_ticket_repo.update(
        conn, ticket_id,
        location_node_id=location_node_id, problem=problem, solution=solution,
        priority=priority, status=status, closed_at=resolved_closed_at
    )
    if initiator_ids is not None:
        incident_ticket_repo.set_initiators(conn, ticket_id, initiator_ids)
    if executor_ids is not None:
        incident_ticket_repo.set_executors(conn, ticket_id, executor_ids)
    return True, None


def delete_ticket(conn: sqlite3.Connection, ticket_id: int) -> tuple[bool, str | None]:
    """Физическое удаление — вызывающий routes ОБЯЗАН сам проверить
    role == 'superadmin' до вызова этой функции (ТЗ раздел 2.1.4); здесь
    только существование записи, не права."""
    if incident_ticket_repo.get_by_id(conn, ticket_id) is None:
        return False, 'Заявка не найдена'
    incident_ticket_repo.delete(conn, ticket_id)
    return True, None


def add_equipment_link(conn: sqlite3.Connection, ticket_id: int, equipment_id: int) -> tuple[bool, str | None]:
    if incident_ticket_repo.get_by_id(conn, ticket_id) is None:
        return False, 'Заявка не найдена'
    if equipment_repo.get_equipment_by_id(conn, equipment_id) is None:
        # Превращаем гонку "оборудование удалили, пока форма была открыта" из
        # голой sqlite3.IntegrityError (FK на incident_ticket_equipment.
        # equipment_id → equipment.id) в понятное сообщение пользователю.
        # Тот же паттерн, что в create_ticket для location/crew: get_by_id
        # в репозитории, проверка is None → возврат (False, текст).
        return False, f'Оборудование с id={equipment_id} не найдено — возможно, было удалено. Обновите форму и попробуйте снова.'
    incident_equipment_repo.add_relation(conn, ticket_id, equipment_id)
    return True, None


def remove_equipment_link(conn: sqlite3.Connection, ticket_id: int, equipment_id: int) -> tuple[bool, str | None]:
    ok = incident_equipment_repo.remove_relation(conn, ticket_id, equipment_id)
    if not ok:
        return False, 'Связь не найдена'
    return True, None


def move_location(conn: sqlite3.Connection, node_id: int, new_parent_id: int | None) -> tuple[bool, str | None]:
    """Тонкая обёртка над location_repo.move() — сам repo уже делает
    проверку цикла через рекурсивный CTE (см. location_repo._is_descendant,
    покрыто тестами на шаге 1). Метод существует в этом слое, а не только
    в repo, чтобы вызывающий код (routes) всегда шёл через service-слой
    по конвенции проекта, а не напрямую в repositories."""
    return location_repo.move(conn, node_id, new_parent_id)


def delete_location(conn: sqlite3.Connection, node_id: int) -> tuple[bool, str | None]:
    """Аналогично move_location — guard (дети/ссылки) уже реализован в
    location_repo.delete(), здесь только проксирование по конвенции слоёв."""
    return location_repo.delete(conn, node_id)


def delete_crew(conn: sqlite3.Connection, crew_id: int) -> tuple[bool, str | None]:
    return crew_repo.delete(conn, crew_id)
