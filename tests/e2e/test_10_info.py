"""Группа 10: Инфо — changelog (read-only) и wishlist."""
import json
import os
from datetime import date

import pytest
from playwright.sync_api import expect

from config.settings import CHANGELOG_JSON_PATH
from tests.e2e.helpers import switch_tab, wait_toast, accept_dialogs


CL_TEST = "E2E changelog entry"
WL_TEST = "E2E wishlist item"


@pytest.mark.scn("72. Переключение на вкладку «Инфо»")
def test_72_switch_info_tab(page):
    """Вкладка «Инфо» отображается с подвкладками changelog/wishlist."""
    switch_tab(page, "info")
    expect(page.locator("#tab-info")).to_be_visible()
    expect(page.locator("#infoSubtabChangelogBtn")).to_be_visible()
    expect(page.locator("#infoSubtabWishlistBtn")).to_be_visible()


@pytest.mark.scn("73. Переключение подвкладок")
def test_73_subtab_switching(page):
    """Кнопки переключения между changelog и wishlist."""
    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Changelog subtab active by default
    expect(page.locator("#infoSubtab-changelog")).to_have_class(
        __import__("re").compile(r"\bactive\b"))
    # Switch to wishlist
    page.evaluate("switchInfoSubtab('wishlist')")
    page.wait_for_timeout(300)
    expect(page.locator("#infoSubtab-wishlist")).to_have_class(
        __import__("re").compile(r"\bactive\b"))
    # Switch back to changelog
    page.evaluate("switchInfoSubtab('changelog')")
    page.wait_for_timeout(300)
    expect(page.locator("#infoSubtab-changelog")).to_have_class(
        __import__("re").compile(r"\bactive\b"))


@pytest.mark.scn("74. Просмотр changelog (read-only, из data/changelog.json)")
def test_74_view_changelog(page, admin_api):
    """GET /api/changelog отдаёт JSON-массив; UI рендерит записи в #changelogList.

    Changelog стал read-only (см. routes/changelog.py): CRUD-эндпоинтов нет,
    источник данных — data/changelog.json. Для проверки рендера подкладываем
    фикстуру в ИЗОЛИРОВАННЫЙ runtime-файл e2e (MOTORS_DATA_DIR переопределён
    conftest'ом), боевой data/changelog.json не затрагивается.
    """
    path = CHANGELOG_JSON_PATH
    original = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            original = f.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([{"date": date.today().isoformat(), "text": CL_TEST}], f,
                  ensure_ascii=False)
    try:
        r = admin_api.get("/api/changelog")
        assert r.status == 200
        entries = r.json()
        assert isinstance(entries, list)
        assert any(e.get("text") == CL_TEST for e in entries)

        switch_tab(page, "info")
        page.wait_for_load_state("networkidle", timeout=10000)
        expect(page.locator("#changelogList")).to_be_visible()
        expect(page.locator(".changelog-item", has_text=CL_TEST)).to_be_visible()
    finally:
        if original is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)
        elif os.path.exists(path):
            os.remove(path)


@pytest.mark.scn("75. Changelog только для чтения (POST удалён)")
def test_75_add_changelog(page, admin_api):
    """Запись в changelog через API/UI недоступна — осознанное продуктовое решение.

    routes/changelog.py: «Запись/удаление через API не поддерживаются — POST
    /api/changelog и DELETE /api/changelog/<id> удалены»; в UI полей ввода и
    кнопок добавления записи больше нет (лог ведётся в data/changelog.json).
    """
    r = admin_api.post("/api/changelog",
                       data=json.dumps({"text": CL_TEST + " 75",
                                        "date": date.today().isoformat()}),
                       headers={"Content-Type": "application/json"})
    assert r.status in (404, 405), "POST /api/changelog должен быть недоступен"

    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("#changelogList")).to_be_visible()
    assert page.locator("#changelogDateInput").count() == 0
    assert page.locator("#changelogTextInput").count() == 0
    assert page.locator("button[onclick*='addChangelogEntry']").count() == 0


@pytest.mark.scn("76. Удаление записи changelog недоступно (read-only)")
def test_76_delete_changelog(page, admin_api):
    """Удаление записи через кнопку ✕ в списке."""
    r = admin_api.delete("/api/changelog/1")
    assert r.status in (404, 405), "DELETE /api/changelog/<id> должен быть недоступен"

    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("#changelogList")).to_be_visible()
    # кнопок удаления записей лога в разметке нет (см. info.js::renderChangelog)
    assert page.locator("#changelogList button").count() == 0


@pytest.mark.scn("77. Просмотр wishlist")
def test_77_view_wishlist(page):
    """Список пожеланий отображается на подвкладке wishlist."""
    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.evaluate("switchInfoSubtab('wishlist')")
    page.wait_for_timeout(500)
    expect(page.locator("#wishlistList")).to_be_visible()


@pytest.mark.scn("78. Добавление элемента в wishlist")
def test_78_add_wishlist(page, admin_api):
    """Добавление пожелания через форму."""
    switch_tab(page, "info")
    page.evaluate("switchInfoSubtab('wishlist')")
    page.wait_for_timeout(500)
    page.fill("#wishlistTextInput", WL_TEST + " 78")
    page.evaluate("addWishlistItem()")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)

    # Verify via API
    items = admin_api.get("/api/wishlist").json()
    item_id = None
    for i in items:
        if "78" in i.get("text", ""):
            item_id = i["id"]
    assert item_id is not None
    admin_api.delete(f"/api/wishlist/{item_id}")


@pytest.mark.scn("79. Редактирование элемента wishlist (toggle done)")
def test_79_edit_wishlist(page, admin_api):
    """Переключение чекбокса done через UI."""
    r = admin_api.post("/api/wishlist",
                       data=json.dumps({"text": WL_TEST + " edit79"}),
                       headers={"Content-Type": "application/json"})
    item_id = r.json()["id"]

    try:
        switch_tab(page, "info")
        page.evaluate("switchInfoSubtab('wishlist')")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(1000)
        # Toggle done checkbox
        page.evaluate(f"toggleWishlistItem({item_id}, true)")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(500)

        # Verify via API
        items = admin_api.get("/api/wishlist").json()
        item = next(i for i in items if i["id"] == item_id)
        assert item["done"] is True

        # Toggle back to false
        page.evaluate(f"toggleWishlistItem({item_id}, false)")
        page.wait_for_load_state("networkidle", timeout=10000)
        items = admin_api.get("/api/wishlist").json()
        item = next(i for i in items if i["id"] == item_id)
        assert item["done"] is False
    finally:
        admin_api.delete(f"/api/wishlist/{item_id}")


@pytest.mark.scn("80. Удаление элемента из wishlist")
def test_80_delete_wishlist(page, admin_api):
    """Удаление пожелания через кнопку ✕ в списке."""
    r = admin_api.post("/api/wishlist",
                       data=json.dumps({"text": WL_TEST + " del80"}),
                       headers={"Content-Type": "application/json"})
    item_id = r.json()["id"]

    switch_tab(page, "info")
    page.evaluate("switchInfoSubtab('wishlist')")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(1000)
    accept_dialogs(page)
    page.evaluate(f"deleteWishlistItem({item_id})")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)

    # Verify via API
    items = admin_api.get("/api/wishlist").json()
    assert not any(i["id"] == item_id for i in items)
