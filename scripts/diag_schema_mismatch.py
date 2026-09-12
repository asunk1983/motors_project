"""Диагностика: сравнить схему боевой БД (после восстановления локально)
с тем, что ожидает текущий код проекта — в первую очередь по таблицам,
затронутым журналом изменений (audit_log) и колонкой "Изменил".

Не чинит ничего — только показывает, чего не хватает или что расходится.

Запуск: python -X utf8 scripts/diag_schema_mismatch.py
Только из корня проекта (где лежит engine_data.db).
"""
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


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "OK  " if condition else "MISS"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))


def cols(conn, table):
    try:
        return [row[1] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()]
    except Exception as e:
        return None


def main():
    print("=== Диагностика: схема боевой БД vs ожидания кода ===\n")
    from modules.db import db_connection

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = {r[0] for r in cur.fetchall()}

        print(f"Всего таблиц в БД: {len(all_tables)}\n")

        print("--- audit_log ---")
        check("Таблица audit_log существует", 'audit_log' in all_tables)
        if 'audit_log' in all_tables:
            expected = {'id', 'entity_type', 'entity_id', 'field_name', 'old_value',
                        'new_value', 'changed_by_user_id', 'changed_by_display_name', 'changed_at'}
            actual = set(cols(conn, 'audit_log'))
            missing = expected - actual
            check("Все ожидаемые колонки на месте", not missing, f"не хватает: {missing}" if missing else "")

        print("\n--- engines (last_edited_by/at) ---")
        engines_cols = cols(conn, 'engines')
        if engines_cols is None:
            check("Таблица engines существует", False)
        else:
            check("engines.last_edited_by есть", 'last_edited_by' in engines_cols)
            check("engines.last_edited_at есть", 'last_edited_at' in engines_cols)

        print("\n--- equipment (last_edited_by/at) ---")
        equipment_cols = cols(conn, 'equipment')
        if equipment_cols is None:
            check("Таблица equipment существует", False)
        else:
            check("equipment.last_edited_by есть", 'last_edited_by' in equipment_cols)
            check("equipment.last_edited_at есть", 'last_edited_at' in equipment_cols)

        print("\n--- incident_ticket (полная схема) ---")
        it_cols = cols(conn, 'incident_ticket')
        if it_cols is None:
            check("Таблица incident_ticket существует", False)
        else:
            expected_it = {'id', 'location_node_id', 'problem', 'solution', 'priority', 'status',
                           'closed_at', 'created_by_user_id', 'created_at', 'updated_at',
                           'rejection_reason', 'last_edited_by', 'last_edited_at'}
            actual_it = set(it_cols)
            missing_it = expected_it - actual_it
            extra_it = actual_it - expected_it
            check("Все ожидаемые колонки на месте", not missing_it, f"не хватает: {missing_it}" if missing_it else "")
            if extra_it:
                print(f"     (доп. колонки в БД, которых нет в ожидаемом списке — не проблема: {extra_it})")

        print("\n--- Вспомогательные таблицы инцидентов ---")
        for t in ['incident_ticket_initiator', 'incident_ticket_executor',
                  'incident_ticket_link', 'incident_ticket_equipment', 'location_node']:
            check(f"Таблица {t} существует", t in all_tables)

        print("\n--- Живой прогон incident_ticket_repo.list_all() ---")
        try:
            from repositories import incident_ticket_repo
            result = incident_ticket_repo.list_all(conn)
            print(f"[OK  ] list_all() выполнился успешно, записей: {len(result)}")
        except Exception as e:
            print(f"[FAIL] list_all() упал с ошибкой:")
            import traceback
            traceback.print_exc()

        print("\n--- Живой прогон incident_ticket_repo.get_location_counts() ---")
        try:
            from repositories import incident_ticket_repo
            result = incident_ticket_repo.get_location_counts(conn)
            print(f"[OK  ] get_location_counts() выполнился успешно, узлов: {len(result)}")
        except Exception as e:
            print(f"[FAIL] get_location_counts() упал с ошибкой:")
            import traceback
            traceback.print_exc()

    print("\n=== Готово ===")


if __name__ == '__main__':
    main()