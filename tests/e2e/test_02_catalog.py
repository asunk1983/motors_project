"""Группа 2: Каталог двигателей — просмотр, поиск, сортировка, экспорт."""
import json

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    switch_tab, wait_toast, reload_catalog, make_engine,
)


@pytest.mark.scn("11. Просмотр каталога при входе")
def test_11_view_catalog_on_entry(page, test_engine):
    """Каталог виден при входе, тестовый двигатель отображается."""
    reload_catalog(page)
    switch_tab(page, "catalog")
    expect(page.locator("#tab-catalog")).to_be_visible()
    expect(page.locator(".table-wrapper")).to_be_visible()
    serial = test_engine["serial_number"]
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()


@pytest.mark.scn("12. Быстрый поиск")
def test_12_quick_search(page, test_engine):
    """Быстрый поиск по всем полям через #searchInput."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    page.fill("#searchInput", serial)
    page.wait_for_timeout(800)  # debounce 350ms + render
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
    page.fill("#searchInput", "")
    page.wait_for_timeout(800)


@pytest.mark.scn("13. Выбор поля поиска")
def test_13_search_field_selection(page, test_engine):
    """Поиск с явным выбором поля через #searchFieldSelect."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    page.select_option("#searchFieldSelect", "serial_number")
    page.fill("#searchInput", serial)
    page.wait_for_timeout(600)
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
    page.fill("#searchInput", "")
    page.wait_for_timeout(600)
    page.select_option("#searchFieldSelect", "all")


@pytest.mark.scn("14. Сортировка через выпадающий список")
def test_14_sorting(page, test_engine):
    """Сортировка через #sortSelect."""
    reload_catalog(page)
    for opt in ["location_asc", "location_desc", "id_asc", "id_desc", "engine_type_asc", "engine_type_desc", "manufacturer_asc", "manufacturer_desc"]:
        page.select_option("#sortSelect", opt)
        page.wait_for_load_state("networkidle", timeout=10000)
    serial = test_engine["serial_number"]
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()


@pytest.mark.scn("14b. Сортировка по клику на заголовке колонки")
def test_14b_sorting_column_header(page, test_engine):
    """Двойной клик на заголовке колонки переключает порядок сортировки."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    page.click("th[onclick=\"sortTable('serial_number')\"]")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
    page.click("th[onclick=\"sortTable('serial_number')\"]")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("tbody tr", has_text=serial)).to_be_visible()


@pytest.mark.scn("15. Переключение вида (таблица/карточки)")
def test_15_toggle_table_cards(page):
    """Переключение между видом таблицы и карточек."""
    switch_tab(page, "catalog")
    expect(page.locator(".table-wrapper")).to_be_visible()
    page.evaluate("toggleView('cards')")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("#cardWrapper")).to_be_visible()
    page.evaluate("toggleView('table')")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator(".table-wrapper")).to_be_visible()


@pytest.mark.scn("16. Пагинация")
def test_16_pagination(page):
    """Элементы управления пагинацией существуют и работают."""
    switch_tab(page, "catalog")
    expect(page.locator("#pageInfo")).to_be_visible()
    expect(page.locator("#pageNumber")).to_be_visible()
    # next page button exists and is usable
    assert page.locator("button[onclick*='nextPage']").count() == 1


@pytest.mark.scn("17. Выбор двигателей для экспорта")
def test_17_select_for_export(page, test_engine):
    """Выбор движка через чекбокс и экспорт в Excel."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    checkbox = page.locator(f"tbody tr:has-text('{serial}') .row-checkbox")
    checkbox.check()
    assert checkbox.is_checked()
    with page.expect_download() as download_info:
        page.click("#exportBtn")
    download = download_info.value
    assert download.suggested_filename.endswith(".xlsx")


@pytest.mark.scn("18. Выбор всех")
def test_18_select_all(page, test_engine):
    """Кнопка «Выбрать все» отмечает все чекбоксы в текущей странице."""
    reload_catalog(page)
    page.click("#selectAllCheckbox")
    page.wait_for_timeout(300)
    checked = page.locator(".row-checkbox:checked")
    assert checked.count() > 0


@pytest.mark.scn("19. Очистка выбора")
def test_19_clear_selection(page, test_engine):
    """Кнопка «Очистить выбор» снимает все чекбоксы."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    checkbox = page.locator(f"tbody tr:has-text('{serial}') .row-checkbox")
    checkbox.check()
    assert checkbox.is_checked()
    page.evaluate("clearSelection()")
    page.wait_for_timeout(300)
    assert checkbox.is_checked() is False


@pytest.mark.scn("21. Обновление каталога (кнопка Refresh)")
def test_21_refresh_catalog(page, admin_api):
    """Кнопка Refresh перезагружает список двигателей."""
    switch_tab(page, "catalog")
    serial = make_engine()["serial_number"]
    payload = make_engine(serial_number=serial)
    admin_api.post("/api/engine", data=json.dumps(payload),
                   headers={"Content-Type": "application/json"})
    try:
        page.evaluate("loadEngines()")
        page.wait_for_load_state("networkidle", timeout=10000)
        expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
        page.locator("button[onclick*='refreshTable']").click()
        page.wait_for_load_state("networkidle", timeout=10000)
        expect(page.locator("tbody tr", has_text=serial)).to_be_visible()
    finally:
        from tests.e2e.helpers import delete_engine_by_serial
        delete_engine_by_serial(admin_api, serial)
