"""Playwright e2e infrastructure для motors_project.

- Браузер: Google Chrome через channel="chrome", ВИДИМЫЙ (headless=False).
- Один браузер на сессию; для каждого теста — отдельный контекст (изоляция
  localStorage/cookies) и отдельная страница, чтобы несколько окон не
  всплывали одновременно (контекст закрывается в конце теста).
- Тестовые сущности (двигатели, пользователи и т.п.) создаются и удаляются
  каждым тестом; реальные данные / бэкапы / фото не трогаются.
- Собираются: ошибки консоли (error/warning), JS-исключения, сетевые ответы >= 400,
  скриншот при падении. Результаты складываются в docs/e2e_test_results.md.
"""
import json
import os

import pytest
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:5000")

# Тестовый админ (создаётся в БД, удаляется в конце pytest-сессии).
TEST_ADMIN = "e2e_test_admin"
TEST_ADMIN_PW = "E2E_admin_123"
TEST_USER = "e2e_test_user"
TEST_USER_PW = "E2E_user_123"

# Префикс маркеров для двигателей/пользовелей созданных тестами.
MARKER = "E2E_TESTS"

# Где храним артефакты.
E2E_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(E2E_DIR, "screenshots")
RESULTS_JSON = os.path.join(E2E_DIR, ".results.json")
RESULTS_MD = os.path.join(PROJECT_ROOT, "docs", "e2e_test_results.md")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Тестовые пользователи в БД (один раз создаём, в конце сессии удаляем).
# ---------------------------------------------------------------------------
def _ensure_test_users():
    from modules.auth import auth as auth_module
    from modules.db import init_db, db_connection
    init_db()
    with db_connection() as conn:
        for uname, pw, role in [(TEST_ADMIN, TEST_ADMIN_PW, "admin"),
                                (TEST_USER, TEST_USER_PW, "user")]:
            if auth_module.get_user_by_username(conn, uname) is None:
                auth_module.create_user(conn, uname, pw, role=role)


def _delete_test_user(uname):
    from modules.auth import auth as auth_module
    from modules.db import db_connection
    try:
        with db_connection() as conn:
            u = auth_module.get_user_by_username(conn, uname)
            if u is not None and u.get("id") != 1:
                auth_module.delete_user(conn, u["id"])
    except Exception as e:
        print(f"[e2e-teardown] delete_user({uname}) error: {e}")


# ---------------------------------------------------------------------------
# Playwright + браузер
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(pw):
    # Видимый браузер, как просил пользователь.
    b = pw.chromium.launch(headless=False,
                           args=["--window-size=1300,820", "--no-first-run"])
    yield b
    b.close()


# ---------------------------------------------------------------------------
# Сессионный токен admin через реальную UI-логин форму (один раз).
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def storage_state(browser, pw, _session_users_and_results):
    # _session_users_and_results гарантирует, что e2e_test_admin существует
    # до первой UI-логина, и удаляет его после последнего теста.
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE_URL + "/", wait_until="domcontentloaded")
    page.wait_for_selector("#login-overlay", state="visible", timeout=10000)
    page.fill("#login-username", TEST_ADMIN)
    page.fill("#login-password", TEST_ADMIN_PW)
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("#login-overlay", state="hidden", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=10000)
    state = page.context.storage_state()
    ctx.close()
    return state


# ---------------------------------------------------------------------------
# Захват ошибок консоли / сети / pageerror для каждой страницы.
# ---------------------------------------------------------------------------
class Capture:
    def __init__(self, page, node_id):
        self.page = page
        self.node_id = node_id
        self.console = []   # (level, msg)
        self.network = []   # (url, status, method)
        self.pageerrors = []
        self.screenshot = None

        def on_console(msg):
            if msg.type in ("error", "warning"):
                self.console.append((msg.type, msg.text))

        def on_response(resp):
            if resp.status >= 400:
                self.network.append((resp.url, resp.status, resp.request.method))

        def on_pageerror(exc):
            self.pageerrors.append(str(exc))

        page.on("console", on_console)
        page.on("response", on_response)
        page.on("pageerror", on_pageerror)

    def summary(self):
        rows = []
        if self.console:
            rows.append("Console errors/warnings: " + "; ".join(
                f"[{t}] {m[:160]}" for t, m in self.console))
        if self.network:
            rows.append("Network >=400: " + "; ".join(
                f"{m} {u} -> {s}" for u, s, m in self.network))
        if self.pageerrors:
            rows.append("Page errors: " + "; ".join(p[:160] for p in self.pageerrors))
        return "\n".join(rows) if rows else ""


# ---------------------------------------------------------------------------
# Фикстуры страниц
# ---------------------------------------------------------------------------
def _app_ready(page):
    """Ждём, пока SPA загрузит данные и каталог станет видимым."""
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    try:
        page.wait_for_selector("#tab-catalog", state="visible", timeout=10000)
    except Exception:
        pass


@pytest.fixture
def page(browser, storage_state, request):
    """Авторизованная (admin) страница."""
    ctx = browser.new_context(storage_state=storage_state)
    p = ctx.new_page()
    p.goto(BASE_URL + "/", wait_until="domcontentloaded")
    _app_ready(p)
    cap = Capture(p, request.node.nodeid)
    request.node._e2e_cap = cap
    yield p
    ctx.close()


@pytest.fixture
def fresh_page(browser, request):
    """НЕавторизованная страница (для сценариев аутентификации)."""
    ctx = browser.new_context()
    p = ctx.new_page()
    p.goto(BASE_URL + "/", wait_until="domcontentloaded")
    try:
        p.wait_for_selector("#login-overlay", state="visible", timeout=10000)
    except Exception:
        pass
    cap = Capture(p, request.node.nodeid)
    request.node._e2e_cap = cap
    yield p
    ctx.close()


@pytest.fixture
def admin_api(pw):
    """Request-context с bearer-токеном admin для проверок/уборки."""
    ctx = pw.request.new_context(base_url=BASE_URL)
    resp = ctx.post("/api/auth/login",
                    data=json.dumps({"username": TEST_ADMIN, "password": TEST_ADMIN_PW}),
                    headers={"Content-Type": "application/json"})
    token = resp.json()["token"]
    ctx.dispose()
    ctx = pw.request.new_context(base_url=BASE_URL,
                                 extra_http_headers={"Authorization": "Bearer " + token})
    yield ctx
    ctx.dispose()


@pytest.fixture
def test_engine(admin_api):
    """Создать тестовый двигатель через API; удалить после теста."""
    from tests.e2e.helpers import make_engine
    payload = make_engine()
    resp = admin_api.post("/api/engine", data=json.dumps(payload),
                          headers={"Content-Type": "application/json"})
    data = resp.json()
    if resp.status != 200 or not data.get("success"):
        pytest.fail("create engine api failed: " + str(data))
    eid = data["id"]
    payload["id"] = eid
    yield payload
    try:
        admin_api.delete("/api/engine/" + str(eid))
    except Exception:
        pass


def accept_dialogs(page):
    """Автоподтверждать confirm/alert (для деструктивных действий, где нужно ОК)."""
    page.on("dialog", lambda d: d.accept())


def dismiss_dialogs(page):
    """Автоматически отклонять confirm/prompt (для тестов, где нужно Отмена)."""
    page.on("dialog", lambda d: d.dismiss())


# ---------------------------------------------------------------------------
# Маркер сценария + запись результатов
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line("markers", "scn(text): e2e сценарий")


# Модульный реестр результатов: nodeid -> запись
_RESULTS = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    cap = getattr(item, "_e2e_cap", None)
    node_id = item.nodeid
    if rep.when == "call" or (rep.failed and rep.when == "setup"):
        # скриншот при падении
        if rep.failed and cap is not None and cap.page is not None:
            try:
                path = os.path.join(SCREENSHOT_DIR,
                                    node_id.replace("::", "__").replace("/", "_") + ".png")
                cap.page.screenshot(path=path, full_page=True)
                cap.screenshot = path
            except Exception as e:
                print("[e2e-screenshot] error:", e)
        _RESULTS[node_id] = {
            "nodeid": node_id,
            "scenario": (item.get_closest_marker("scn").args[0]
                         if item.get_closest_marker("scn") else node_id),
            "group": (item.module.__name__.split(".")[-1]
                      if hasattr(item, "module") else ""),
            "status": "failed" if rep.failed else ("skipped" if rep.skipped else "passed"),
            "duration": round(call.duration, 2) if call and hasattr(call, "duration") else 0,
            "details": str(rep.longrepr)[:500] if rep.failed else "",
            "console": cap.summary() if cap is not None else "",
            "screenshot": cap.screenshot if cap is not None else None,
        }


def _write_results():
    # Слияние с уже накопленным JSON (чтобы сквозь разные прогоны сохранялся порядок групп)
    existing = {}
    if os.path.exists(RESULTS_JSON):
        try:
            with open(RESULTS_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    existing.update(_RESULTS)
    try:
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[e2e-results] write json error:", e)

    # Таблица в markdown
    GROUP_ORDER = ["test_01_auth", "test_02_catalog", "test_03_add_engine",
                   "test_04_detail", "test_05_photos", "test_06_import",
                   "test_07_search", "test_08_settings", "test_09_backups",
                   "test_10_info", "test_11_misc"]
    by_group = {}
    for v in existing.values():
        by_group.setdefault(v["group"], []).append(v)

    lines = ["# E2E test results", "",
             "Браузер: Google Chrome (channel=\"chrome\"), headless=False. "
             "Данные тестовые (создаются и удаляются каждым тестом).",
             "",
             "| Группа | Сценарий | Статус | Детали при провале |",
             "| --- | --- | --- | --- |"]
    for g in GROUP_ORDER:
        for v in by_group.get(g, []):
            status = v["status"].upper()
            det = v["details"]
            if not det and v.get("console"):
                det = v["console"]
            det = det.replace("|", "/").replace("\n", " ")[:280]
            sc = v["scenario"].replace("|", "/")
            lines.append(f"| {g} | {sc} | {status} | {det} |")
    for g in [g for g in by_group if g not in GROUP_ORDER]:
        for v in by_group[g]:
            status = v["status"].upper()
            det = (v["details"] or v.get("console") or "")[:280].replace("|", "/").replace("\n", " ")
            lines.append(f"| {g} | {v['scenario'].replace('|','/')} | {status} | {det} |")

    lines.append("")
    n_pass = sum(1 for v in existing.values() if v["status"] == "passed")
    n_fail = sum(1 for v in existing.values() if v["status"] == "failed")
    n_skip = sum(1 for v in existing.values() if v["status"] == "skipped")
    lines.append(f"**Итого:** {n_pass} passed, {n_fail} failed, {n_skip} skipped")
    lines.append("")
    try:
        with open(RESULTS_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print("[e2e-results] write md error:", e)


@pytest.fixture(scope="session", autouse=True)
def _session_users_and_results():
    _ensure_test_users()
    yield
    _write_results()
    _delete_test_user(TEST_ADMIN)
    _delete_test_user(TEST_USER)
