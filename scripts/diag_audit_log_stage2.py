"""Диагностика: применён ли и работает ли Этап 2 журнала изменений (audit_log).

Покрывает 9 функций: crew_repo.update, location_repo.update/move,
ticket_repo.update_ticket_status/update_ticket/update_failure,
knowledge_repo.update_article, engine_repo.update_status/update_photo_count.

Для каждой — проверка сигнатуры (принимает ли actor). Живой функциональный
тест (временная правка реальной записи + проверка audit_log + откат в
try/finally) — только для полей, где это безопасно: обычный текст без
побочных эффектов для остального приложения. НЕ трогает вживую:
- location_repo.move — меняет структуру дерева мест, риск для UI/дерева
  даже на краткий момент;
- ticket_repo.update_ticket_status / engine_repo.update_status — статусы
  имеют деловой смысл (бейджи, фильтры, возможные side-effects вроде
  простановки timestamp'ов), временное переключение рискованнее, чем
  правка текстового поля.
Для них проверяется только сигнатура функции.

Запуск: python -X utf8 scripts/diag_audit_log_stage2.py
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
        print("Все проверки пройдены — Этап 2 применён и работает корректно.")
    else:
        print("Есть проваленные проверки — см. FAIL выше.")


FAKE_ACTOR = {'id': 999999, 'username': 'diag_script', 'display_name': 'Диагностика (скрипт, этап 2)'}
TEST_MARKER = '__AUDIT_DIAG_STAGE2_TEST__'


def get_last_audit_row(conn, entity_type, entity_id, field_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT field_name, old_value, new_value, changed_by_display_name "
        "FROM audit_log WHERE entity_type=? AND entity_id=? AND field_name=? "
        "ORDER BY id DESC LIMIT 1",
        (entity_type, entity_id, field_name)
    )
    return cur.fetchone()


def audit_count(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM audit_log")
    return cur.fetchone()['c']


def run_text_field_test(all_ok, label, entity_type, entity_id, field_name,
                          original_value, do_update, restore_update, expected_new_value=None):
    """Общий шаблон: временно меняет одно поле, проверяет audit_log,
    проверяет отсутствие лишней записи при повторном сохранении тех же
    данных, восстанавливает исходное значение в finally вне зависимости
    от результата.

    expected_new_value — что должно оказаться в new_value после do_update
    (по умолчанию TEST_MARKER — подходит для текстовых полей; для
    нетекстовых, например photo_count, передаётся явно)."""
    if expected_new_value is None:
        expected_new_value = TEST_MARKER
    print(f"\n--- {label} ---")
    try:
        from modules.db import db_connection

        with db_connection() as conn:
            do_update(conn)

        with db_connection() as conn:
            row = get_last_audit_row(conn, entity_type, entity_id, field_name)

        ok = check(f"{label}: правка создала запись в audit_log", row is not None)
        all_ok &= ok
        if row:
            all_ok &= check(
                f"{label}: new_value записан корректно",
                str(row['new_value']) == str(expected_new_value),
                f"ожидалось {expected_new_value!r}, получено {row['new_value']!r}"
            )
            all_ok &= check(
                f"{label}: changed_by_display_name записан корректно",
                row['changed_by_display_name'] == FAKE_ACTOR['display_name'],
                f"получено {row['changed_by_display_name']!r}"
            )

        with db_connection() as conn:
            count_before = audit_count(conn)
            do_update(conn)  # повторно те же данные — не должно создать новую строку
            count_after = audit_count(conn)
        all_ok &= check(
            f"{label}: повторное сохранение без изменений не создаёт новую запись",
            count_before == count_after,
            f"было {count_before}, стало {count_after}"
        )
    except Exception as e:
        all_ok = check(f"{label}: тест выполнился без ошибок", False, repr(e))
    finally:
        try:
            with db_connection() as conn:
                restore_update(conn)
            print(f"({label}: исходное значение восстановлено)")
        except Exception as e:
            print(f"({label}: ВНИМАНИЕ — не удалось восстановить исходное значение: {e!r})")

    return all_ok


def main() -> int:
    print("=== Диагностика: Этап 2 журнала изменений (audit_log) ===\n")
    all_ok = True

    # --- 1. Сигнатуры функций ---------------------------------------------
    print("--- 1. Проверка сигнатур (принимают ли actor) ---")
    from repositories import crew_repo, location_repo, ticket_repo, knowledge_repo, engine_repo

    signature_targets = [
        (crew_repo, 'update'),
        (location_repo, 'update'),
        (location_repo, 'move'),
        (ticket_repo, 'update_ticket_status'),
        (ticket_repo, 'update_ticket'),
        (ticket_repo, 'update_failure'),
        (knowledge_repo, 'update_article'),
        (engine_repo, 'update_status'),
        (engine_repo, 'update_photo_count'),
    ]
    for mod, func_name in signature_targets:
        func = getattr(mod, func_name, None)
        has_actor = func is not None and 'actor' in inspect.signature(func).parameters
        all_ok &= check(f"{mod.__name__}.{func_name}() принимает actor", has_actor)

    from modules.db import db_connection

    # --- 2. crew_repo.update — поле position -------------------------------
    with db_connection() as conn:
        crew_list = crew_repo.list_all(conn)
    if crew_list:
        crew_id = crew_list[0]['id']
        original_position = crew_list[0].get('position')
        all_ok = run_text_field_test(
            all_ok, "crew_repo.update", 'crew', crew_id, 'position', original_position,
            do_update=lambda conn: crew_repo.update(conn, crew_id, position=TEST_MARKER, actor=FAKE_ACTOR),
            restore_update=lambda conn: crew_repo.update(conn, crew_id, position=original_position, actor=FAKE_ACTOR),
        )
    else:
        check("crew_repo.update: есть хотя бы одна запись crew для теста", False, "таблица crew пуста — тест пропущен")

    # --- 3. location_repo.update — поле name -------------------------------
    with db_connection() as conn:
        locations = location_repo.list_all(conn)
    if locations:
        node_id = locations[0]['id']
        original_name = locations[0]['name']
        all_ok = run_text_field_test(
            all_ok, "location_repo.update", 'location_node', node_id, 'name', original_name,
            do_update=lambda conn: location_repo.update(conn, node_id, name=TEST_MARKER, actor=FAKE_ACTOR),
            restore_update=lambda conn: location_repo.update(conn, node_id, name=original_name, actor=FAKE_ACTOR),
        )
    else:
        check("location_repo.update: есть хотя бы один узел для теста", False, "таблица location_node пуста — тест пропущен")
    print("(location_repo.move НЕ тестируется вживую — меняет структуру дерева мест, только сигнатура проверена выше)")

    # --- 4. ticket_repo.update_ticket — поле description --------------------
    with db_connection() as conn:
        tickets = ticket_repo.list_tickets(conn)
    if tickets:
        t = tickets[0]
        ticket_id = t['id']
        original_desc = t.get('description')

        def do_ticket_update(conn, desc=TEST_MARKER):
            ticket_repo.update_ticket(conn, ticket_id, {
                'equipment_id': t.get('equipment_id'),
                'priority': t.get('priority', 'normal'),
                'title': t['title'],
                'description': desc,
            }, actor=FAKE_ACTOR)

        all_ok = run_text_field_test(
            all_ok, "ticket_repo.update_ticket", 'ticket', ticket_id, 'description', original_desc,
            do_update=lambda conn: do_ticket_update(conn, TEST_MARKER),
            restore_update=lambda conn: do_ticket_update(conn, original_desc),
        )
    else:
        check("ticket_repo.update_ticket: есть хотя бы одна заявка для теста", False, "таблица ticket пуста — тест пропущен")
    print("(ticket_repo.update_ticket_status НЕ тестируется вживую — статус имеет деловой смысл и side-эффекты, только сигнатура проверена выше)")

    # --- 5. ticket_repo.update_failure — поле description -------------------
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM failure LIMIT 1')
        row = cur.fetchone()
    if row:
        failure_id = row['id']
        with db_connection() as conn:
            failure = ticket_repo.get_failure_by_id(conn, failure_id)
        original_desc = failure.get('description')

        def do_failure_update(conn, desc=TEST_MARKER):
            ticket_repo.update_failure(conn, failure_id, {
                'failure_mode_id': failure.get('failure_mode_id'),
                'failure_cause_id': failure.get('failure_cause_id'),
                'knowledge_article_id': failure.get('knowledge_article_id'),
                'symptom': failure.get('symptom'),
                'description': desc,
                'confirmed': failure.get('confirmed'),
                'occurred_at': failure.get('occurred_at'),
                'restored_at': failure.get('restored_at'),
            }, actor=FAKE_ACTOR)

        all_ok = run_text_field_test(
            all_ok, "ticket_repo.update_failure", 'failure', failure_id, 'description', original_desc,
            do_update=lambda conn: do_failure_update(conn, TEST_MARKER),
            restore_update=lambda conn: do_failure_update(conn, original_desc),
        )
    else:
        check("ticket_repo.update_failure: есть хотя бы один отказ для теста", False, "таблица failure пуста — тест пропущен")

    # --- 6. knowledge_repo.update_article — поле reference_note -------------
    with db_connection() as conn:
        articles = knowledge_repo.list_articles(conn)
    if articles:
        article_id = articles[0]['id']
        with db_connection() as conn:
            article = knowledge_repo.get_article_by_id(conn, article_id)
        original_note = article.get('reference_note')

        def do_article_update(conn, note=TEST_MARKER):
            knowledge_repo.update_article(conn, article_id, {
                'title': article.get('title'),
                'symptom': article.get('symptom'),
                'failure_mode_id': article.get('failure_mode_id'),
                'diagnostic_steps': article.get('diagnostic_steps'),
                'recommended_action': article.get('recommended_action'),
                'reference_note': note,
            }, actor=FAKE_ACTOR)

        all_ok = run_text_field_test(
            all_ok, "knowledge_repo.update_article", 'knowledge_article', article_id, 'reference_note', original_note,
            do_update=lambda conn: do_article_update(conn, TEST_MARKER),
            restore_update=lambda conn: do_article_update(conn, original_note),
        )
    else:
        check("knowledge_repo.update_article: есть хотя бы одна статья для теста", False, "таблица knowledge_article пуста — тест пропущен")

    # --- 7. engine_repo.update_photo_count -----------------------------------
    with db_connection() as conn:
        engines = engine_repo.get_all(conn, limit=1, offset=0)
    if engines:
        engine_id = engines[0]['id']
        original_count = engines[0].get('photo_count') or 0
        test_count = original_count + 1

        all_ok = run_text_field_test(
            all_ok, "engine_repo.update_photo_count", 'engine', engine_id, 'photo_count', original_count,
            do_update=lambda conn: engine_repo.update_photo_count(conn, engine_id, test_count, actor=FAKE_ACTOR),
            restore_update=lambda conn: engine_repo.update_photo_count(conn, engine_id, original_count, actor=FAKE_ACTOR),
            expected_new_value=test_count,
        )
    else:
        check("engine_repo.update_photo_count: есть хотя бы один двигатель для теста", False, "таблица engines пуста — тест пропущен")
    print("(engine_repo.update_status НЕ тестируется вживую — статус имеет деловой смысл, только сигнатура проверена выше)")

    print_summary(all_ok)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
