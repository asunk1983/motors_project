# services/equipment_location_migration.py — одноразовая миграция
# equipment.workshop/location (TEXT) -> equipment.location_node_id
# (ТЗ "Инциденты + Оборудование", раздел 3.1).
#
# НЕ вызывается автоматически из init_db() — миграция данных требует
# явного запуска (например, разовой командой из консоли/скрипта
# накатки), а не молчаливого срабатывания при каждом старте приложения.
# После однократного успешного прогона повторные вызовы безвредны:
# WHERE location_node_id IS NULL в UPDATE ниже не трогает уже
# смигрированные записи.

import sqlite3

from repositories import location_repo


def find_or_create_node(conn: sqlite3.Connection, name: str, parent_id: int | None, node_type: str) -> int:
    """Найти узел с точным совпадением (parent_id, name), иначе создать.
    Точное текстовое совпадение уместно ИМЕННО здесь (в одноразовой
    миграции существующих данных, не в runtime UI) — это разовая
    консолидация уже известного набора значений workshop/location, где
    случайных дублей/опечаток заведомо не возникает за один проход.

    Обязательно find-OR-create, а не голый create(): миграция может
    запускаться повторно (новое оборудование с уже смигрированным ранее
    сочетанием цех+место) — слепой create() на второй раз упал бы на
    UNIQUE(parent_id, name)."""
    if parent_id is None:
        row = conn.execute(
            'SELECT id FROM location_node WHERE parent_id IS NULL AND name = ?', (name,)
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT id FROM location_node WHERE parent_id = ? AND name = ?', (parent_id, name)
        ).fetchone()
    if row:
        return row['id']
    return location_repo.create(conn, name, node_type=node_type, parent_id=parent_id)


def find_or_create_root_node(conn: sqlite3.Connection, name: str, node_type: str = 'workshop') -> int:
    return find_or_create_node(conn, name, parent_id=None, node_type=node_type)


def migrate_equipment_locations(conn: sqlite3.Connection) -> dict:
    """Переносит уникальные пары (workshop, location) из equipment в
    дерево location_node и проставляет equipment.location_node_id.
    Возвращает статистику {workshops_created, locations_created,
    equipment_updated} — для лога/консольного вывода при запуске.
    """
    stats = {'workshops_created': 0, 'locations_created': 0, 'equipment_updated': 0}
    workshop_node_cache: dict[str, int] = {}

    rows = conn.execute(
        "SELECT DISTINCT workshop, location FROM equipment "
        "WHERE workshop IS NOT NULL AND workshop != '' AND location_node_id IS NULL"
    ).fetchall()

    for row in rows:
        workshop = row['workshop']
        location = row['location']

        if workshop in workshop_node_cache:
            workshop_id = workshop_node_cache[workshop]
        else:
            before = conn.execute(
                'SELECT COUNT(*) c FROM location_node WHERE parent_id IS NULL AND name = ?', (workshop,)
            ).fetchone()['c']
            workshop_id = find_or_create_root_node(conn, workshop, node_type='workshop')
            if before == 0:
                stats['workshops_created'] += 1
            workshop_node_cache[workshop] = workshop_id

        location_id = workshop_id
        if location:
            before_loc = conn.execute(
                'SELECT COUNT(*) c FROM location_node WHERE parent_id = ? AND name = ?', (workshop_id, location)
            ).fetchone()['c']
            location_id = find_or_create_node(conn, location, parent_id=workshop_id, node_type='other')
            if before_loc == 0:
                stats['locations_created'] += 1

        if location:
            cur = conn.execute(
                'UPDATE equipment SET location_node_id = ? '
                'WHERE workshop = ? AND location = ? AND location_node_id IS NULL',
                (location_id, workshop, location)
            )
        else:
            cur = conn.execute(
                'UPDATE equipment SET location_node_id = ? '
                'WHERE workshop = ? AND (location IS NULL OR location = \'\') AND location_node_id IS NULL',
                (location_id, workshop)
            )
        stats['equipment_updated'] += cur.rowcount

    conn.commit()
    return stats


if __name__ == '__main__':
    # Точка ручного запуска: python -m services.equipment_location_migration
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    from modules.db import db_connection

    with db_connection() as conn:
        result = migrate_equipment_locations(conn)
    logger.info(
        'Миграция мест оборудования завершена: цехов создано %d, мест создано %d, записей оборудования обновлено %d',
        result['workshops_created'], result['locations_created'], result['equipment_updated']
    )
