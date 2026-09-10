"""Диагностика: почему в журнале (audit_log) нет записей по оборудованию
и инцидентам, хотя код (по отчёту) применён.

Проверяет:
1. Реально ли в текущих файлах на диске есть вызов log_field_changes
   внутри equipment_repo.update_equipment() и incident_ticket_repo.update()
   (текстовый поиск по исходнику функции — не полагаемся на "применено,
   потому что так написали").
2. Что реально есть в audit_log прямо сейчас (группировка по entity_type).
3. Живой тест: если в БД есть хотя бы одна запись equipment/incident_ticket,
   пробует их отредактировать (безопасное текстовое поле) и проверить,
   появляется ли запись в audit_log. Восстанавливает исходное значение.

Запуск: python -X utf8 scripts/diag_audit_missing_entities.py
"""
import inspect
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main() -> int:
    print("=== Диагностика: почему нет equipment/incident_ticket в audit_log ===\n")

    from repositories import equipment_repo, incident_ticket_repo

    print("--- 1. Реально ли в исходнике на диске есть вызов log_field_changes ---")
    eq_src = inspect.getsource(equipment_repo.update_equipment)
    check("equipment_repo.update_equipment() содержит вызов log_field_changes",
          'log_field_changes' in eq_src)

    it_src = inspect.getsource(incident_ticket_repo.update)
    check("incident_ticket_repo.update() содержит вызов log_field_changes",
          'log_field_changes' in it_src)

    print("\n--- 2. Что реально есть в audit_log сейчас ---")
    from modules.db import db_connection
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT entity_type, COUNT(*) AS c FROM audit_log GROUP BY entity_type ORDER BY entity_type')
        rows = cur.fetchall()
    if not rows:
        print("(audit_log пуст)")
    for r in rows:
        print(f"  {r['entity_type']}: {r['c']} записей")

    print("\n--- 3. Живой тест: оборудование ---")
    from modules.db import db_connection
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, equipment_type_id, name, article, manufacturer, workshop, '
                     'location, location_node_id, criticality, installed_at, specs_json, note '
                     'FROM equipment LIMIT 1')
        eq_row = cur.fetchone()

    if not eq_row:
        print("Таблица equipment пуста — живой тест пропущен.")
    else:
        eq = {k: eq_row[k] for k in eq_row.keys()}
        eq_id = eq['id']
        original_note = eq.get('note')
        fake_actor = {'id': 999999, 'username': 'diag_script', 'display_name': 'Диагностика (пропавшие сущности)'}

        def do_update(conn, note_value):
            data = dict(eq)
            data['note'] = note_value
            # equipment_repo.update_equipment ожидает 'specs' (dict) для
            # пересборки specs_json — используем что есть как есть, не
            # трогаем структуру.
            data['specs'] = {}
            equipment_repo.update_equipment(conn, eq_id, data, actor=fake_actor)

        try:
            with db_connection() as conn:
                do_update(conn, '__AUDIT_DIAG_MISSING_TEST__')

            with db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT field_name, new_value FROM audit_log "
                    "WHERE entity_type='equipment' AND entity_id=? ORDER BY id DESC LIMIT 5",
                    (eq_id,)
                )
                rows = cur.fetchall()
            note_row = next((r for r in rows if r['field_name'] == 'note'), None)
            check("Правка оборудования создала запись в audit_log", note_row is not None,
                  "" if note_row else f"найдено {len(rows)} строк за это редактирование, ни одной по 'note'")
        except Exception as e:
            check("Правка оборудования выполнилась без ошибок", False, repr(e))
        finally:
            with db_connection() as conn:
                do_update(conn, original_note)
            print(f"(оборудование id={eq_id}: note восстановлено)")

    print("\n--- 4. Живой тест: заявка инцидента ---")
    from repositories import incident_ticket_repo as itr
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM incident_ticket LIMIT 1')
        it_row = cur.fetchone()

    if not it_row:
        print("Таблица incident_ticket пуста — живой тест пропущен.")
    else:
        ticket_id = it_row['id']
        with db_connection() as conn:
            ticket = itr.get_by_id(conn, ticket_id)
        original_solution = ticket.get('solution')
        fake_actor = {'id': 999999, 'username': 'diag_script', 'display_name': 'Диагностика (пропавшие сущности)'}

        try:
            with db_connection() as conn:
                itr.update(conn, ticket_id, actor=fake_actor, solution='__AUDIT_DIAG_MISSING_TEST__')

            with db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT field_name, new_value FROM audit_log "
                    "WHERE entity_type='incident_ticket' AND entity_id=? ORDER BY id DESC LIMIT 5",
                    (ticket_id,)
                )
                rows = cur.fetchall()
            sol_row = next((r for r in rows if r['field_name'] == 'solution'), None)
            check("Правка заявки инцидента создала запись в audit_log", sol_row is not None,
                  "" if sol_row else f"найдено {len(rows)} строк за это редактирование, ни одной по 'solution'")
        except Exception as e:
            check("Правка заявки инцидента выполнилась без ошибок", False, repr(e))
        finally:
            with db_connection() as conn:
                itr.update(conn, ticket_id, actor=fake_actor, solution=original_solution)
            print(f"(заявка id={ticket_id}: solution восстановлено)")

    print("\n=== Готово — смотри FAIL/пустые разделы выше для диагноза ===")
    return 0


if __name__ == '__main__':
    sys.exit(main())
