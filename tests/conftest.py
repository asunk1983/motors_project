"""Тестовые фикстуры.

Предоставляет in-memory SQLite со схемой БД — без необходимости
поднимать production engine_data.db.

Здесь же — вывод русского описания теста рядом с его результатом в
`pytest -v` (см. tests/descriptions.py). Описание берётся из
`@pytest.mark.scn(...)` (как в e2e), иначе из docstring теста/класса,
иначе собирается из имени теста. В обычном/`-q` режиме вывод не меняется.
"""
import sys

import pytest

from tests import descriptions

# Конфиг pytest: нужен в консольных хуках, куда config не передаётся.
_CONFIG = None


@pytest.fixture
def db_conn():
    """In-memory SQLite с полной схемой (таблицы, индексы, admin-пользователь).

    Используется в тестах repository и service слоёв.
    """
    from modules.db import init_db, db_connection

    with db_connection(':memory:') as conn:
        init_db(conn)
        yield conn


@pytest.fixture
def file_users_env(tmp_path, monkeypatch):
    """Изолированное файловое хранилище users.json / tokens.json.

    Патчит глобальные пути модуля file_users на временную директорию,
    чтобы тесты auth не читали и не перезаписывали реальные
    config/users.json и config/tokens.json.
    """
    from modules.auth import file_users as fu
    users_path = str(tmp_path / 'users.json')
    tokens_path = str(tmp_path / 'tokens.json')
    monkeypatch.setattr(fu, 'CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(fu, 'FILE_USERS', users_path)
    monkeypatch.setattr(fu, 'FILE_TOKENS', tokens_path)
    return {'users': users_path, 'tokens': tokens_path}


# ---------------------------------------------------------------------------
# Русское описание теста рядом с результатом (только в режиме -v)
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Регистрируем маркер описания — тот же механизм, что в e2e."""
    global _CONFIG
    _CONFIG = config
    config.addinivalue_line(
        "markers",
        "scn(text): короткое описание того, что проверяет тест "
        "(tests/descriptions.py; для e2e — название сценария)",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Считаем описание и приклеиваем его к отчёту: в лог-хуке нет item."""
    outcome = yield
    report = outcome.get_result()
    if report.when in ("call", "setup"):
        report.ru_description = descriptions.describe(item)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_logreport(report):
    """Печатаем описание отдельной строкой под результатом теста.

    Сам вывод pytest не меняем: статус, nodeid и short test summary
    остаются стандартными, поэтому разбор "passed/failed/skipped"
    в CI/скриптах не затрагивается. Описание выводится только при `-v`
    (в `-q` и по умолчанию прогресс-вывод не трогается).
    """
    yield
    if _CONFIG is None or _CONFIG.option.verbose < 1:
        return
    text = getattr(report, "ru_description", "")
    if not text:
        return
    # один тест = одна строка описания: call, либо сорванный/пропущенный setup
    if report.when == "call" or (report.when == "setup"
                                 and (report.failed or report.skipped)):
        reporter = _CONFIG.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            write_description(reporter, text)


def write_description(reporter, text):
    """Печатает строку описания в UTF-8, минуя кодировку текстового потока.

    Почему в обход текстовой прослойки. `TerminalWriter` кодировкой не
    управляет — он пишет в переданный поток «как есть» (`self._file.write`).
    Кодировка этого потока зависит от того, куда идёт вывод:

      * консоль (tty): всегда `utf-8` (WindowsConsoleIO/WriteConsoleW) —
        кириллица в консоли работает и без правок;
      * файл или пайп: кодовая страница ANSI (на этой машине `cp1252`,
        `GetACP()` = 1252), в которой кириллицы нет. Тогда поток либо
        заменяет символы на `?` (`errors="replace"`), либо печатает
        `\\uXXXX`-экранирование (`errors="backslashreplace"`) — это и был
        симптом «вместо кириллицы знаки вопроса» при перенаправлении
        вывода (в т.ч. в `run_tests.bat` через `Tee-Object`).

    Поэтому строка пишется байтами UTF-8 прямо в бинарный поток
    (как e2e-conftest пишет свой отчёт с явным `encoding="utf-8"`).
    Порядок строк сохраняется: сначала сбрасываем текстовую прослойку,
    затем пишем байты и сбрасываем бинарный поток. Если бинарный поток
    недоступен — откатываемся на обычную текстовую запись.
    """
    payload = ("\n    " + text).encode("utf-8")
    stream = _binary_stream(reporter)
    if stream is None:
        reporter.write("\n    " + text)
        return
    try:
        _flush_text(reporter)
        stream.write(payload)
        stream.flush()
    except (OSError, ValueError):
        reporter.write("\n    " + text)


def _flush_text(reporter):
    """Сбрасываем текстовую прослойку, чтобы наши байты не обогнали её."""
    for stream in (getattr(getattr(reporter, "_tw", None), "_file", None),
                   sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, OSError, ValueError):
            pass


def _binary_stream(reporter):
    """Ищем бинарный поток (`buffer`) за текстовым потоком репортёра.

    Текстовый поток может быть обёрткой colorama (TerminalWriter оборачивает
    tty-поток в `AnsiToWin32(...).stream`), поэтому разворачиваем обёртки.
    """
    start = getattr(getattr(reporter, "_tw", None), "_file", None)
    seen = set()
    candidates = [start, getattr(start, "stream", None), getattr(start, "wrapped", None)]
    for candidate in candidates:
        if candidate is None or id(candidate) in seen:
            continue
        seen.add(id(candidate))
        buf = getattr(candidate, "buffer", None)
        if buf is not None and hasattr(buf, "write"):
            return buf
    # запасной вариант: стандартный stdout процесса
    for candidate in (sys.stdout, sys.stderr):
        buf = getattr(candidate, "buffer", None)
        if buf is not None and hasattr(buf, "write"):
            return buf
    return None