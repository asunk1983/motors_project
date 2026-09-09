"""Диагностика: применён ли и работает ли Этап 1 журнала изменений (audit_log).

Проверяет, без участия джуна:
1. Применены ли файлы (modules/audit.py существует, repo-функции engine/
   equipment/incident_ticket принимают параметр actor).
2. Создалась ли таблица audit_log и индекс в БД (значит сервер был
   перезапущен после применения правок в modules/db.py).
3. Живой функциональный тест на РЕАЛЬНОМ двигателе (первом из списка):
   временно меняет поле note на тестовое значение, проверяет, что в
   audit_log появилась корректная запись (поле/старое значение/новое
   значение/автор), затем проверяет, что повторное сохранение БЕЗ
   изменений НЕ создаёт лишней записи. В конце — восстанавливает
   исходное значение note, что бы ни случилось (try/finally).

Для equipment/equipment_repo и incident_ticket_repo функциональный тест
не запускается (их update принимает полный набор полей, а не частичный
dict, как у engine — трогать боевую запись оборудования/заявки без
точного знания её текущих полей рискованнее); проверяется только то,
что функции ПРИНИМАЮТ actor (сигнатура), это подтверждает, что правки
из handoff применены к файлу.

Запуск: python -X utf8 scripts/diag_audit_log.py
Только из корня проекта (где лежит engine_data.db и config/).
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


def print_summary(all_ok: bool) -> None:
    print("\n=== ИТОГ ===")
    if all_ok:
        print("Все проверки пройдены — Этап 1 применён и работает корректно.")
    else:
        print("Есть проваленные проверки — см. FAIL выше.")


def main() -> int:
    print("=== Диагностика: Этап 1 журнала изменений (audit_log) ===\n")
    all_ok = True

    # --- 1. Файлы применены (сигнатуры функций) --------------------------
    print("--- 1. Проверка применённых файлов ---")
    try:
        from modules.audit import log_field_changes  # noqa: F401
        all_ok &= check("modules/audit.py существует и импортируется", True)
    except ImportError as e:
        all_ok &= check("modules/audit.py существует и импортируется", False, str(e))

    from repositories import engine_repo, equipment_repo, incident_ticket_repo

    for mod, func_name in [
        (engine_repo, 'update'),
        (equipment_repo, 'update_equipment'),
        (incident_ticket_repo, 'update'),
    ]:
        func = getattr(mod, func_name, None)
        has_actor = func is not None and 'actor' in inspect.signature(func).parameters
        all_ok &= check(f"{mod.__name__}.{func_name}() принимает actor", has_actor)

    try:
        from services import incident_service
        has_actor = 'actor' in inspect.signature(incident_service.update_ticket).parameters
        all_ok &= check("services/incident_service.py::update_ticket() принимает actor", has_actor)
    except ImportError as e:
        all_ok &= check("services/incident_service.py импортируется", False, str(e))

    # --- 2. Таблица audit_log существует в БД -----------------------------
    print("\n--- 2. Проверка схемы БД ---")
    from modules.db import db_connection

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        table_exists = cur.fetchone() is not None
        all_ok &= check("Таблица audit_log существует", table_exists)

        idx_exists = False
        if table_exists:
            cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_audit_log_entity'")
            idx_exists = cur.fetchone() is not None
            all_ok &= check("Индекс idx_audit_log_entity существует", idx_exists)

    if not table_exists:
        print("\nТаблица audit_log отсутствует — функциональный тест (шаг 3) пропущен.")
        print("Возможные причины: сервер не перезапускался после применения правок")
        print("в modules/db.py, либо правки не были применены вообще.")
        print_summary(all_ok)
        return 0 if all_ok else 1

    # --- 3. Функциональный тест на реальном двигателе ---------------------
    print("\n--- 3. Функциональный тест (временная правка существующего двигателя) ---")
    from repositories.engine_repo import get_all, update as engine_update

    with db_connection() as conn:
        engines = get_all(conn, limit=1, offset=0)

    if not engines:
        check("Есть хотя бы один двигатель для теста", False, "таблица engines пуста — тест пропущен")
        print_summary(all_ok)
        return 0 if all_ok else 1

    test_engine_id = engines[0]['id']
    original_note = engines[0].get('note')
    test_marker = '__AUDIT_DIAG_TEST__'
    fake_actor = {'id': 999999, 'username': 'diag_script', 'display_name': 'Диагностика (скрипт)'}

    print(f"(используется двигатель id={test_engine_id}, поле note временно изменится и будет восстановлено)")

    try:
        # Правка -> должна создать запись в audit_log
        with db_connection() as conn:
            engine_update(conn, test_engine_id, {'note': test_marker}, actor=fake_actor)

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT field_name, old_value, new_value, changed_by_display_name "
                "FROM audit_log WHERE entity_type='engine' AND entity_id=? "
                "ORDER BY id DESC LIMIT 5",
                (test_engine_id,)
            )
            rows = cur.fetchall()

        note_row = next((r for r in rows if r['field_name'] == 'note'), None)
        all_ok &= check(
            "Правка создала запись в audit_log",
            note_row is not None,
            "" if note_row else f"найдено {len(rows)} свежих строк, ни одной по полю 'note'"
        )
        if note_row:
            all_ok &= check(
                "new_value записан корректно",
                note_row['new_value'] == test_marker,
                f"ожидалось {test_marker!r}, получено {note_row['new_value']!r}"
            )
            all_ok &= check(
                "changed_by_display_name записан корректно",
                note_row['changed_by_display_name'] == fake_actor['display_name'],
                f"получено {note_row['changed_by_display_name']!r}"
            )

        # Повторное сохранение ТЕХ ЖЕ данных -> НЕ должно создать новую запись
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM audit_log")
            count_before = cur.fetchone()['c']

            engine_update(conn, test_engine_id, {'note': test_marker}, actor=fake_actor)

            cur.execute("SELECT COUNT(*) AS c FROM audit_log")
            count_after = cur.fetchone()['c']

        all_ok &= check(
            "Сохранение БЕЗ изменений не создаёт новую запись",
            count_before == count_after,
            f"было {count_before}, стало {count_after}"
        )

    finally:
        # Восстанавливаем исходное значение вне зависимости от результата теста.
        with db_connection() as conn:
            engine_update(conn, test_engine_id, {'note': original_note}, actor=fake_actor)
        print(f"(поле note двигателя id={test_engine_id} восстановлено в исходное значение)")

    print_summary(all_ok)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
