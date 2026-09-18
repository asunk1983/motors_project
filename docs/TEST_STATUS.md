# TEST_STATUS — последний прогон тестов

> Единственный источник правды по цифрам последнего прогона тестов.
> Файл перезаписывается целиком скриптом `scripts/update_test_status.py` —
> руками не редактировать, правки исчезнут при следующем прогоне.
> Обновляется автоматически последней секцией `run_tests.bat`.

- **Коммит:** `53e3e44` (ветка main) — `53e3e44f488b5db75992ce210ef0fb27d6d6dd61`
- **Дата обновления:** 2026-09-18T10:12:48+03:00
- **Обновил:** asunk1983
- **Отслеживаемые файлы с правками вне коммита:** 4 (.clinerules, .gitignore, run_tests.bat, …)
- **Итог:** ✅ ЗЕЛЁНЫЙ
- **Цифры:** 612 unit/route: 611 passed, 0 failed, 1 skipped; 83 e2e: 83 passed, 0 failed, 0 skipped

## Команда для воспроизведения

```bash
run_tests.bat
# полный прогон (unit/route + e2e), лог в docs/test_results_<TS>.md,
# junit-артефакты в _pytest_artifacts/, затем перезапись этого файла.

# по частям — обязательно с --junitxml, иначе скрипт прочитает старые артефакты:
.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/e2e --junitxml=_pytest_artifacts/unit.xml
.venv\Scripts\python.exe -m pytest tests/e2e -q --junitxml=_pytest_artifacts/e2e.xml
python -X utf8 scripts/update_test_status.py
```

## Unit/route (`tests`, без e2e)

- passed: **611**
- failed: **0** (failures: 0, errors: 0)
- skipped: **1**
- собрано тестов: 612
- длительность: 54.59 с
- артефакт: `_pytest_artifacts/unit.xml`, прогон 2026-09-18 10:09:13 +03:00

## E2E (`tests/e2e`)

- passed: **83**
- failed: **0** (failures: 0, errors: 0)
- skipped: **0**
- собрано тестов: 83
- длительность: 158.44 с
- артефакт: `_pytest_artifacts/e2e.xml`, прогон 2026-09-18 10:10:09 +03:00

## Отклонения текущего прогона

### Известные (допустимые)

- skipped `tests.test_backup_system.test_backup.TestAtomicRestore::test_restore_preserves_users`
  - допуск: Windows-specific os.replace lock issue — fix in production, not blocking (tests/test_backup_system/test_backup.py:216)

### Неожиданные

- нет — прогон полностью зелёный

## Словарь допустимых отклонений

Живёт в `scripts/update_test_status.py::KNOWN_DEVIATIONS` и ревьюится как код:
всё, что не совпало с записями ниже, выше попадает в «Неожиданные».

- `test_restore_preserves_users` (skipped) — Windows-specific os.replace lock issue — fix in production, not blocking (tests/test_backup_system/test_backup.py:216)

---

Цифры взяты из junit-артефактов прогона, не из текстового вывода pytest.
Логи прогонов (`docs/test_results_*.md`) в git не коммитятся — они
исторические и не являются источником правды.
