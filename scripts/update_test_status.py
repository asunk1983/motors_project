"""CLI-утилита: перезаписать docs/TEST_STATUS.md — единый источник правды
по последнему прогону тестов.

Цифры руками не вводятся: итоги (passed/failed/skipped) и список отклонений
текущего прогона берутся из junit-xml, который pytest пишет при прогоне
(`--junitxml`, см. run_tests.bat -> `_pytest_artifacts/unit.xml` и `e2e.xml`).

«Известные допустимые отклонения» — словарь KNOWN_DEVIATIONS ниже. Он
ревьюится как код: новый fail/skip попадает в отчёт как неожиданное
отклонение, пока запись не добавлена в словарь осознанно.

Коммит-хэш, ветка и автор берутся из git автоматически (автор — из
`git config user.name`, переопределяется `--updated-by`).

Использование:
    python -X utf8 scripts/update_test_status.py
    python -X utf8 scripts/update_test_status.py --note "правка роутов движков"
    python -X utf8 scripts/update_test_status.py --unit-xml путь --e2e-xml путь

Запуск из корня проекта (где лежат `_pytest_artifacts/` и `docs/`).

Коды возврата:
    0 — файл статуса обновлён;
    1 — ошибка записи файла;
    2 — артефактов нет / не распарсились / невалидные аргументы
        (файл статуса НЕ тронут).
"""
import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# Безопасный вывод кириллицы в Windows-консоли (по умолчанию cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Скрипт лежит в scripts/, но ему нужен config.settings для BASE_DIR.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import BASE_DIR

ARTIFACTS_DIR = Path(BASE_DIR) / "_pytest_artifacts"
DEFAULT_UNIT_XML = ARTIFACTS_DIR / "unit.xml"
DEFAULT_E2E_XML = ARTIFACTS_DIR / "e2e.xml"
DEFAULT_STATUS_FILE = Path(BASE_DIR) / "docs" / "TEST_STATUS.md"

# Если e2e-артефакт старше unit-артефакта больше чем на столько секунд — предупреждаем:
# типичный признак, что e2e не перезапускали, и его цифры — из прошлого прогона.
STALE_ARTIFACT_SECONDS = 600

# Известные допустимые отклонения от зелёного статуса. Ревьюится как код:
# всё, что не совпало с записями здесь, печатается в отчёте как неожиданное.
#   match  — подстрока в "classname::name" (nodeid) или в тексте отклонения;
#   kind   — "failed" | "error" | "skipped";
#   reason — почему отклонение допустимо (попадает в отчёт как есть).
KNOWN_DEVIATIONS = [
    {
        "match": "test_restore_preserves_users",
        "kind": "skipped",
        "reason": (
            "Windows-specific os.replace lock issue — fix in production, "
            "not blocking (tests/test_backup_system/test_backup.py:216)"
        ),
    },
]


class ArtifactError(Exception):
    """junit-артефакт отсутствует или не читается — файл статуса не трогаем."""


def _run_git(*args):
    """stdout git-команды ("" — если git недоступен или команда упала)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _git_info():
    """Коммит/ветка/автор + список отслеживаемых файлов с правками вне коммита."""
    # Только отслеживаемые файлы: сам TEST_STATUS.md при первом прогоне ещё
    # untracked, и это не «грязное дерево».
    porcelain = _run_git("status", "--porcelain", "--untracked-files=no")
    dirty = [line for line in porcelain.splitlines() if line.strip()]
    return {
        "head": _run_git("rev-parse", "HEAD"),
        "short": _run_git("rev-parse", "--short", "HEAD"),
        "branch": _run_git("rev-parse", "--abbrev-ref", "HEAD"),
        "author": _run_git("config", "user.name"),
        "dirty": dirty,
    }


def _int_attr(node, name):
    """Числовой атрибут testsuite (отсутствует -> 0)."""
    raw = node.get(name)
    if raw is None:
        return 0
    try:
        return int(raw)
    except ValueError:
        raise ArtifactError(f"атрибут {name}={raw!r} — не число")


def _case_deviations(case):
    """Отклонения одного <testcase>: failed / error / skipped + текст."""
    classname = case.get("classname") or ""
    name = case.get("name") or ""
    label = f"{classname}::{name}" if classname else name
    found = []
    for element, kind in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
        child = case.find(element)
        if child is None:
            continue
        text = (child.get("message") or "").strip()
        if not text:
            body = (child.text or "").strip()
            text = body.splitlines()[0] if body else ""
        found.append({"kind": kind, "label": label, "text": " ".join(text.split())})
    return found


def parse_junit(path):
    """Читает junit-xml: итоги прогона + отклонения (по nodeid).

    Итоги берутся из атрибутов <testsuite> (tests/failures/errors/skipped),
    passed считается как остаток — это ровно то, что печатает сам pytest,
    но без разбора человеческого вывода.
    """
    xml_path = Path(path)
    if not xml_path.exists():
        raise ArtifactError(
            f"нет файла {xml_path} (нужен прогон pytest с --junitxml={xml_path})"
        )
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as e:
        raise ArtifactError(f"{xml_path} не является junit-xml: {e}")
    except OSError as e:
        raise ArtifactError(f"не удалось прочитать {xml_path}: {e}")

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        raise ArtifactError(f"в {xml_path} нет ни одного <testsuite>")

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    seconds = 0.0
    timestamps = []
    deviations = []
    for suite in suites:
        for key in totals:
            totals[key] += _int_attr(suite, key)
        try:
            seconds += float(suite.get("time") or 0.0)
        except ValueError:
            pass
        timestamp = suite.get("timestamp")
        if timestamp:
            timestamps.append(timestamp)
        for case in suite.iter("testcase"):
            deviations.extend(_case_deviations(case))

    return {
        "path": xml_path,
        "totals": totals,
        "passed": totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"],
        "seconds": seconds,
        "timestamp": min(timestamps) if timestamps else "",
        "deviations": deviations,
        "mtime": xml_path.stat().st_mtime,
    }


def classify_deviations(deviations):
    """Делит отклонения на известные (по KNOWN_DEVIATIONS) и неожиданные."""
    known, unexpected = [], []
    for dev in deviations:
        haystack = f"{dev['label']} {dev['text']}"
        entry = next(
            (e for e in KNOWN_DEVIATIONS
             if e["kind"] == dev["kind"] and e["match"] in haystack),
            None,
        )
        if entry is None:
            unexpected.append(dev)
        else:
            known.append((dev, entry))
    return known, unexpected


def _fmt_timestamp(raw):
    """2026-09-18T08:59:57.152262+03:00 -> 2026-09-18 08:59:57 +03:00."""
    if not raw:
        return "неизвестно"
    text = re.sub(r"\.\d+", "", raw).replace("T", " ")
    return re.sub(r"([+-]\d{2}):(\d{2})$", r" \1:\2", text)


def _rel(path):
    """Путь относительно корня проекта (для читаемости в отчёте)."""
    try:
        return str(Path(path).relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _dev_line(dev, reason=None):
    """Строка markdown для одного отклонения."""
    text = dev["text"]
    # Для известного допуска текст причины часто совпадает с текстом из XML —
    # не дублируем его дважды.
    if text and reason and text in reason:
        text = ""
    line = f"- {dev['kind']} `{dev['label']}`" + (f" — {text}" if text else "")
    if reason:
        line += f"\n  - допуск: {reason}"
    return line


def _section(title, data, artifact_hint):
    """Блок «карточки» по одному прогону."""
    t = data["totals"]
    return [
        f"## {title}",
        "",
        f"- passed: **{data['passed']}**",
        f"- failed: **{t['failures'] + t['errors']}**"
        f" (failures: {t['failures']}, errors: {t['errors']})",
        f"- skipped: **{t['skipped']}**",
        f"- собрано тестов: {t['tests']}",
        f"- длительность: {data['seconds']:.2f} с",
        f"- артефакт: `{artifact_hint}`, прогон {_fmt_timestamp(data['timestamp'])}",
        "",
    ]

def render_card(git_info, unit, e2e, now, updated_by, note, warnings):
    """Собирает содержимое docs/TEST_STATUS.md (карточка, а не таблица).

    Возвращает (текст, вердикт, известные, неожиданные отклонения) — вердикт
    и отклонения нужны вызывающему для вывода в консоль.
    """
    u_known, u_unexpected = classify_deviations(unit["deviations"])
    e_known, e_unexpected = classify_deviations(e2e["deviations"])
    known = u_known + e_known
    unexpected = u_unexpected + e_unexpected

    # Сырые failed/error нужны только для строки «Цифры» и секций прогонов.
    # На вердикт они не влияют: известное допустимое отклонение
    # (KNOWN_DEVIATIONS) с kind failed/error не должно красить прогон в красный.
    unit_red = unit["totals"]["failures"] + unit["totals"]["errors"]
    e2e_red = e2e["totals"]["failures"] + e2e["totals"]["errors"]
    unexpected_red = sum(1 for dev in unexpected if dev["kind"] in ("failed", "error"))
    if unexpected_red:
        verdict = "❌ НЕ ЗЕЛЁНЫЙ"
    elif unexpected:
        verdict = "⚠️ УСЛОВНО ЗЕЛЁНЫЙ (есть неожиданные отклонения)"
    else:
        verdict = "✅ ЗЕЛЁНЫЙ"

    if git_info["dirty"]:
        shown = ", ".join(line.split(maxsplit=1)[-1].strip()
                          for line in git_info["dirty"][:3])
        more = ", …" if len(git_info["dirty"]) > 3 else ""
        dirty_line = f"{len(git_info['dirty'])} ({shown}{more})"
    else:
        dirty_line = "нет"

    unit_total = (f"{unit['totals']['tests']} unit/route: {unit['passed']} passed, "
                  f"{unit_red} failed, {unit['totals']['skipped']} skipped")
    e2e_total = (f"{e2e['totals']['tests']} e2e: {e2e['passed']} passed, "
                 f"{e2e_red} failed, {e2e['totals']['skipped']} skipped")

    lines = [
        "# TEST_STATUS — последний прогон тестов",
        "",
        "> Единственный источник правды по цифрам последнего прогона тестов.",
        "> Файл перезаписывается целиком скриптом `scripts/update_test_status.py` —",
        "> руками не редактировать, правки исчезнут при следующем прогоне.",
        "> Обновляется автоматически последней секцией `run_tests.bat`.",
        "",
        f"- **Коммит:** `{git_info['short'] or '?'}` "
        f"(ветка {git_info['branch'] or '?'}) — `{git_info['head'] or '?'}`",
        f"- **Дата обновления:** {now}",
        f"- **Обновил:** {updated_by}",
        f"- **Отслеживаемые файлы с правками вне коммита:** {dirty_line}",
        f"- **Итог:** {verdict}",
        f"- **Цифры:** {unit_total}; {e2e_total}",
        "",
        "## Команда для воспроизведения",
        "",
        "```bash",
        "run_tests.bat",
        "# полный прогон (unit/route + e2e), лог в docs/test_results_<TS>.md,",
        "# junit-артефакты в _pytest_artifacts/, затем перезапись этого файла.",
        "",
        "# по частям — обязательно с --junitxml, иначе скрипт прочитает старые артефакты:",
        ".venv\\Scripts\\python.exe -m pytest tests -q --ignore=tests/e2e "
        "--junitxml=_pytest_artifacts/unit.xml",
        ".venv\\Scripts\\python.exe -m pytest tests/e2e -q "
        "--junitxml=_pytest_artifacts/e2e.xml",
        "python -X utf8 scripts/update_test_status.py",
        "```",
        "",
    ]
    lines += _section("Unit/route (`tests`, без e2e)", unit, _rel(unit["path"]))
    lines += _section("E2E (`tests/e2e`)", e2e, _rel(e2e["path"]))

    lines += ["## Отклонения текущего прогона", "", "### Известные (допустимые)", ""]
    lines += [_dev_line(dev, entry["reason"]) for dev, entry in known] or ["- нет", ""]
    lines += ["", "### Неожиданные", ""]
    lines += [_dev_line(dev) for dev in unexpected] or [
        "- нет — прогон полностью зелёный",
    ]
    lines += [""]

    if warnings:
        lines += ["## Предупреждения", ""]
        lines += [f"- {warning}" for warning in warnings]
        lines += [""]

    lines += [
        "## Словарь допустимых отклонений",
        "",
        "Живёт в `scripts/update_test_status.py::KNOWN_DEVIATIONS` и ревьюится как код:",
        "всё, что не совпало с записями ниже, выше попадает в «Неожиданные».",
        "",
    ]
    lines += [
        f"- `{entry['match']}` ({entry['kind']}) — {entry['reason']}"
        for entry in KNOWN_DEVIATIONS
    ] or ["- словарь пуст"]
    lines += [""]

    if note:
        lines += ["## Примечание", "", note, ""]

    lines += [
        "---",
        "",
        "Цифры взяты из junit-артефактов прогона, не из текстового вывода pytest.",
        "Логи прогонов (`docs/test_results_*.md`) в git не коммитятся — они",
        "исторические и не являются источником правды.",
        "",
    ]
    return "\n".join(lines), verdict, known, unexpected

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Перезаписать docs/TEST_STATUS.md по junit-артефактам последнего прогона."
    )
    parser.add_argument(
        "--unit-xml",
        default=str(DEFAULT_UNIT_XML),
        help="junit-xml unit/route-прогона (по умолчанию _pytest_artifacts/unit.xml).",
    )
    parser.add_argument(
        "--e2e-xml",
        default=str(DEFAULT_E2E_XML),
        help="junit-xml e2e-прогона (по умолчанию _pytest_artifacts/e2e.xml).",
    )
    parser.add_argument(
        "--status-file",
        default=str(DEFAULT_STATUS_FILE),
        help="Куда писать статус (по умолчанию docs/TEST_STATUS.md).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Дата обновления YYYY-MM-DD. Если не указана - текущие дата и время.",
    )
    parser.add_argument(
        "--updated-by",
        default=None,
        help="Кто обновил. По умолчанию - git config user.name.",
    )
    parser.add_argument(
        "--note",
        default=None,
        help="Необязательное примечание (попадает в отчёт отдельным разделом).",
    )
    args = parser.parse_args()

    if args.date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        print("Ошибка: --date должен быть в формате YYYY-MM-DD", file=sys.stderr)
        return 2

    # Оба артефакта читаются ДО записи: отсутствующий/битый XML не должен
    # затирать валидный статус частичными данными.
    try:
        unit = parse_junit(args.unit_xml)
        e2e = parse_junit(args.e2e_xml)
    except ArtifactError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        print("Файл статуса не тронут.", file=sys.stderr)
        return 2

    warnings = []
    lag = unit["mtime"] - e2e["mtime"]
    if lag > STALE_ARTIFACT_SECONDS:
        warnings.append(
            f"e2e-артефакт старше unit-артефакта на {lag / 60:.0f} мин — похоже, e2e "
            "в этом прогоне не перезапускали, его цифры из предыдущего прогона."
        )
    for name, data in (("unit/route", unit), ("e2e", e2e)):
        if data["totals"]["tests"] == 0:
            warnings.append(f"в артефакте {name} 0 тестов — проверьте команду прогона.")

    git_info = _git_info()
    updated_by = (args.updated_by or git_info["author"] or "").strip() or "неизвестно"
    now = args.date or datetime.now().astimezone().isoformat(timespec="seconds")

    card, verdict, known, unexpected = render_card(
        git_info, unit, e2e, now, updated_by, args.note, warnings
    )

    status_path = Path(args.status_file)
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with open(status_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(card)
    except OSError as e:
        print(f"Ошибка при записи {status_path}: {e}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] {warning}")
    for dev in unexpected:
        text = f" — {dev['text']}" if dev["text"] else ""
        print(f"[НЕОЖИДАННОЕ ОТКЛОНЕНИЕ] {dev['kind']}: {dev['label']}{text}")
    print(f"Обновлён {_rel(status_path)}")
    print(f"  unit/route: {unit['passed']} passed, "
          f"{unit['totals']['failures'] + unit['totals']['errors']} failed, "
          f"{unit['totals']['skipped']} skipped (из {unit['totals']['tests']})")
    print(f"  e2e: {e2e['passed']} passed, "
          f"{e2e['totals']['failures'] + e2e['totals']['errors']} failed, "
          f"{e2e['totals']['skipped']} skipped (из {e2e['totals']['tests']})")
    print(f"  известных отклонений: {len(known)}, неожиданных: {len(unexpected)}")
    print(f"  коммит: {git_info['short'] or '?'} ({git_info['branch'] or '?'}), "
          f"обновил: {updated_by}")
    print(f"  итог: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())