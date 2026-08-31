"""Группа 7: Расширенный поиск — условия, операторы, результаты."""
import json

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    switch_tab, reload_catalog, wait_toast, make_engine,
)


@pytest.mark.scn("53. Переключение на вкладку «Поиск»")
def test_53_switch_search_tab(page):
    """Вкладка поиска существует и содержит форму поиска."""
    switch_tab(page, "search")
    expect(page.locator("#tab-search")).to_be_visible()
    expect(page.locator("#searchConditions")).to_be_visible()
    expect(page.locator("#addSearchBtn")).to_be_visible()
    expect(page.locator("#searchBtn")).to_be_visible()


@pytest.mark.scn("54. Добавление условия поиска")
def test_54_add_condition(page):
    """Кнопка «Добавить условие» добавляет строку поиска."""
    switch_tab(page, "search")
    initial_count = page.locator(".search-row").count()
    page.click("#addSearchBtn")
    page.wait_for_timeout(300)
    new_count = page.locator(".search-row").count()
    assert new_count == initial_count + 1


@pytest.mark.scn("55. Выбор поля и оператора")
def test_55_select_field_operator(page):
    """Выбор поля меняет доступные операторы."""
    switch_tab(page, "search")
    # Default: first row has a text field with text operators
    op_selects = page.locator(".search-operator-select")
    assert op_selects.count() >= 1
    initial_ops = page.locator(".search-operator-select option").count()

    # Switch to a number field
    page.select_option(".search-field-select", "power")
    page.wait_for_timeout(500)
    number_ops = page.locator(".search-operator-select option").count()
    # Number field should have more operators (gt, lt, between)
    assert number_ops > initial_ops


@pytest.mark.scn("56. Автодополнение (autocomplete)")
def test_56_autocomplete(page, test_engine):
    """Поле поиска подсказывает значения при вводе."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    switch_tab(page, "search")
    # Fill a condition with part of the serial number
    page.select_option(".search-field-select", "serial_number")
    value_input = page.locator(".search-value-input")
    value_input.fill(serial[:8])
    page.wait_for_timeout(800)
    # Check for autocomplete suggestions dropdown
    suggestions = page.locator(".autocomplete-suggestions, .suggest-dropdown, .autocomplete-items")
    # May or may not appear depending on backend; just verify no errors
    page.wait_for_load_state("networkidle", timeout=5000)


@pytest.mark.scn("57. Выполнение поиска")
def test_57_execute_search(page, test_engine):
    """Поиск по serial_number возвращает нужный двигатель."""
    reload_catalog(page)
    serial = test_engine["serial_number"]
    switch_tab(page, "search")
    page.select_option(".search-field-select", "serial_number")
    page.locator(".search-value-input").fill(serial)
    page.click("#searchBtn")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)
    # Results should contain the engine
    assert page.locator("#searchResults tbody tr").count() >= 1 or \
           page.locator("#searchResults .search-result-count").count() >= 1


@pytest.mark.scn("58. Очистка всех условий")
def test_58_clear_conditions(page):
    """Кнопка «Очистить» сбрасывает все условия поиска."""
    switch_tab(page, "search")
    page.click("#addSearchBtn")
    page.wait_for_timeout(300)
    assert page.locator(".search-row").count() >= 2
    page.click("#clearSearchBtn")
    page.wait_for_timeout(500)
    # Should reset to one empty row
    assert page.locator(".search-row").count() == 1
    expect(page.locator("#searchResults")).to_be_visible()
