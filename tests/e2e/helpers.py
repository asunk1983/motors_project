"""Вспомогательные функции для e2e-тестов (чистый код без side effects)."""
import json
import os
import re
import uuid

from playwright.sync_api import expect

MARKER = "E2E_TESTS"

TEST_ADMIN = "e2e_test_admin"
TEST_ADMIN_PW = "E2E_admin_123"
TEST_USER = "e2e_test_user"
TEST_USER_PW = "E2E_user_123"


def make_engine(**ov):
    sn = "E2E-" + uuid.uuid4().hex[:8]
    data = {
        "location": "Тестовое место " + MARKER,
        "engine_type": "Электродвигатель",
        "serial_number": sn,
        "manufacturer": "ТестПроизв",
        "purpose": "Тестовое назначение",
        "workshop": "1",
        "bearing_front": "220",
        "bearing_rear": "320",
        "shaft_diameter": "55",
        "protection_class": "IP54",
        "mounting_type": "Прямая",
        "temp_sensor": "Есть",
        "encoder": "Есть",
        "cooling": "Есть",
        "note": "E2E тестовая запись",
        "modes": [],
        "works": [],
    }
    data.update(ov)
    return data


def make_mode(**ov):
    m = {"frequency": "50", "power": "1.5", "voltage": "230",
         "connection_type": "Звезда", "current": "5.2", "rpm": "1425"}
    m.update(ov)
    return m


def make_work(**ov):
    from datetime import date
    w = {"work_number": "1", "date": date.today().isoformat(),
         "work_description": "Техническое обслуживание", "isolation": "10",
         "inspection": "ГОД", "signature": "E2E"}
    w.update(ov)
    return w


def switch_tab(page, tab, timeout=8000):
    page.click(".tab-btn[data-tab=\"" + tab + "\"]")
    page.wait_for_selector("#tab-" + tab, state="visible", timeout=8000)
    expect(page.locator(".tab-btn[data-tab=\"" + tab + "\"]")).to_have_class(re.compile(r"\bactive\b"))


def wait_toast(page, text, timeout=10000):
    """Дождаться появления toast-сообщения (убирается через ~3.3с)."""
    loc = page.locator(".toast").get_by_text(text, exact=False)
    expect(loc).to_be_visible(timeout=timeout)
    return loc


def login_ui(page, username, password):
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("#login-form button.login-submit")
    expect(page.locator("#login-overlay")).to_be_hidden(timeout=15000)


def logout_ui(page):
    page.click("#logout-btn")
    expect(page.locator("#login-overlay")).to_be_visible(timeout=15000)


def open_admin_tab(page):
    switch_tab(page, "admin")
    expect(page.locator("#adminUsersList table")).to_be_visible(timeout=10000)


def prompt_accept(page, value):
    """One-shot: при следующем dialog.prompt принять value, alert/confirm — accept."""
    def handler(dialog):
        page.remove_listener("dialog", handler)
        if dialog.type == "prompt":
            dialog.accept(value)
        else:
            dialog.accept()
    page.on("dialog", handler)


def accept_dialogs(page):
    page.on("dialog", lambda d: d.accept())


def dismiss_dialogs(page):
    page.on("dialog", lambda d: d.dismiss())


def engine_id_by_serial(api, serial):
    r = api.get("/api/engines?search_field=serial_number&search=" + serial)
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["id"]
    return None


def delete_engine_by_serial(api, serial):
    eid = engine_id_by_serial(api, serial)
    if eid:
        api.delete("/api/engine/" + str(eid))
    return eid


def get_user_id(api, username):
    r = api.get("/api/auth/admin/users")
    users = r.json()
    for u in users:
        if u.get("username") == username:
            return u.get("id")
    return None


def delete_user_by_username(api, username):
    uid = get_user_id(api, username)
    if uid:
        api.delete("/api/auth/admin/users/" + str(uid))
    return uid


def create_engine_direct(api, payload=None):
    payload = payload or make_engine()
    r = api.post("/api/engine", data=json.dumps(payload),
                 headers={"Content-Type": "application/json"})
    data = r.json()
    return data.get("id"), payload


def set_local_storage(page, mapping):
    for k, v in mapping.items():
        page.evaluate("localStorage.setItem(" + json.dumps(k) + ", " + json.dumps(v) + ")")


# --- Дополнительные хелперы для тестовых групп 2-11 ---

FORM_FIELDS = [
    ("f_location", "location"), ("f_engine_type", "engine_type"),
    ("f_serial_number", "serial_number"), ("f_manufacturer", "manufacturer"),
    ("f_purpose", "purpose"), ("f_workshop", "workshop"),
    ("f_bearing_front", "bearing_front"), ("f_bearing_rear", "bearing_rear"),
    ("f_shaft_diameter", "shaft_diameter"), ("f_protection_class", "protection_class"),
    ("f_mounting_type", "mounting_type"), ("f_temp_sensor", "temp_sensor"),
    ("f_encoder", "encoder"), ("f_cooling", "cooling"), ("f_note", "note"),
]


def fill_engine_form(page, payload):
    """Заполнить форму добавления двигателя."""
    for field_id, key in FORM_FIELDS:
        val = payload.get(key, "")
        if val:
            page.fill("#" + field_id, str(val))


def reload_catalog(page):
    """Перезагрузить каталог в браузере (вызов loadEngines + ожидание)."""
    page.evaluate("loadEngines()")
    page.wait_for_load_state("networkidle", timeout=15000)


def open_engine_card(page, engine_id):
    """Открыть детальную карточку двигателя по ID."""
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"), timeout=5000)
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)


def close_detail(page):
    """Закрыть детальную карточку."""
    page.evaluate("closeDetail()")
    page.wait_for_selector("#detailModal", state="hidden", timeout=5000)


def open_detail_edit(page):
    """Переключить карточку в режим редактирования характеристик."""
    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_selector("#detailContent .detail-mode-toggle", state="visible", timeout=5000)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_selector("#detailContent .detail-edit-input", state="attached", timeout=5000)


def switch_detail_to_view(page):
    """Переключить карточку в режом просмотра."""
    page.evaluate("toggleDetailMode('view')")
    page.wait_for_selector("#detailContent .detail-mode-toggle", state="visible", timeout=5000)


def make_test_png(path, width=60, height=60, color=(255, 0, 0)):
    """Создать минимальный валидный PNG-файл указанного размера."""
    import struct
    import zlib

    def _chunk(ctype, data):
        c = ctype + data
        return (struct.pack(">I", len(data)) + c +
                struct.pack(">I", zlib.crc32(c) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + bytes(color) * width
    idat = zlib.compress(raw)
    with open(path, "wb") as f:
        f.write(sig + _chunk(b"IHDR", ihdr) +
                _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


def upload_detail_photo(page, image_path):
    """Загрузить фото в карточку двигателя (редактирование)."""
    page.evaluate("openPhotoAddModal()")
    page.wait_for_selector("#photoAddModal.active", state="visible", timeout=5000)
    page.set_input_files("#detailPhotoInput", image_path)
    page.click("#photoAddModal button:has-text('Загрузить')")
    wait_toast(page, "Загружено фото")
    page.wait_for_selector("#photoAddModal", state="hidden", timeout=5000)
    # Wait for gallery to refresh
    page.wait_for_load_state("networkidle", timeout=10000)


def engine_row_exists(page, serial):
    """Проверить, что строка с указанным заводским номером есть в таблице."""
    try:
        return page.locator("tbody tr", has_text=serial).count() > 0
    except Exception:
        return False
