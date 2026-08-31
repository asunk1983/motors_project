"""Группа 10: Инфо — changelog и wishlist."""
import json
from datetime import date

import pytest
from playwright.sync_api import expect

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


@pytest.mark.scn("74. Просмотр changelog")
def test_74_view_changelog(page, admin_api):
    """Список записей лога изменений отображается."""
    # Create an entry via API
    today = date.today().isoformat()
    r = admin_api.post("/api/changelog",
                       data=json.dumps({"text": CL_TEST, "date": today}),
                       headers={"Content-Type": "application/json"})
    entry_id = r.json().get("id")
    assert entry_id is not None

    try:
        switch_tab(page, "info")
        page.wait_for_load_state("networkidle", timeout=10000)
        expect(page.locator("#changelogList")).to_be_visible()
        expect(page.locator(".changelog-item", has_text=CL_TEST)).to_be_visible()
    finally:
        admin_api.delete(f"/api/changelog/{entry_id}")


@pytest.mark.scn("75. Добавление записи в changelog")
def test_75_add_changelog(page, admin_api):
    """Добавление записи через форму на вкладке Инфо."""
    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Set date
    today = date.today().isoformat()
    page.evaluate(f"document.getElementById('changelogDateInput').value = '{today}';")
    page.fill("#changelogTextInput", CL_TEST + " 75")
    page.evaluate("addChangelogEntry()")
    wait_toast(page, "Запись добавлена")
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify via API
    entries = admin_api.get("/api/changelog").json()
    entry_id = None
    for e in entries:
        if "75" in e.get("text", "") and CL_TEST in e.get("text", ""):
            entry_id = e["id"]
    assert entry_id is not None
    admin_api.delete(f"/api/changelog/{entry_id}")


@pytest.mark.scn("76. Удаление записи из changelog")
def test_76_delete_changelog(page, admin_api):
    """Удаление записи через кнопку ✕ в списке."""
    today = date.today().isoformat()
    r = admin_api.post("/api/changelog",
                       data=json.dumps({"text": CL_TEST + " del76", "date": today}),
                       headers={"Content-Type": "application/json"})
    entry_id = r.json()["id"]

    switch_tab(page, "info")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(1000)
    accept_dialogs(page)
    # Find and click the delete button for our entry
    page.evaluate(f"deleteChangelogEntry({entry_id})")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)

    # Verify via API
    entries = admin_api.get("/api/changelog").json()
    assert not any(e["id"] == entry_id for e in entries)


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
