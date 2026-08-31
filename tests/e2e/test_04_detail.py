"""Группа 4: Детальная карточка двигателя — просмотр, редактирование, печать."""
import json
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    switch_tab, reload_catalog, open_engine_card, close_detail,
    open_detail_edit, switch_detail_to_view, wait_toast,
    accept_dialogs, make_test_png,
)


@pytest.mark.scn("32. Открытие детальной карточки")
def test_32_open_detail_card(page, test_engine):
    """Открытие карточки по клику на строку таблицы."""
    reload_catalog(page)
    page.evaluate("showDetail({})".format(test_engine["id"]))
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)


@pytest.mark.scn("33. Просмотр характеристик")
def test_33_view_characteristics(page, test_engine):
    """В режиме просмотра отображаются характеристики двигателя."""
    reload_catalog(page)
    engine_id = test_engine["id"]
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)
    # В режиме просмотра должно быть поле с характеристиками
    title_el = page.locator("#detailTitle")
    assert title_el.text_content()  # заголовок есть
    serial = page.locator("#detailContent .detail-item").filter(has=page.locator("label", has_text="Заводской номер")).locator(".value")
    assert serial.inner_text().strip() == test_engine["serial_number"]


@pytest.mark.scn("34. Редактирование и сохранение характеристик")
def test_34_edit_and_save(page, test_engine):
    """Редактирование поля и сохранение через API."""
    reload_catalog(page)
    engine_id = test_engine["id"]
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    # Переключаемся в режим редактирования
    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_selector("#detailContent .detail-edit-input", state="attached", timeout=5000)

    # Изменяем поле назначения
    page.locator("#detailContent .detail-edit-input[data-field='purpose']").fill("E2E-отредактировано")
    page.locator("#detailContent .detail-edit-actions button:has-text('💾 Сохранить')").click()
    wait_toast(page, "Изменения сохранены")
    page.wait_for_load_state("networkidle", timeout=10000)

    # Переключаемся в режим просмотра и проверяем
    page.evaluate("toggleDetailMode('view')")
    page.wait_for_timeout(500)
    purpose_el = page.locator("#detailContent .detail-item").filter(has=page.locator("label", has_text="Назначение")).locator(".value")
    assert "E2E-отредактировано" in purpose_el.inner_text()
    close_detail(page)


@pytest.mark.scn("35. Отмена редактирования")
def test_35_cancel_editing(page, test_engine):
    """Отмена редактирования не сохраняет изменения."""
    reload_catalog(page)
    engine_id = test_engine["id"]
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    original_purpose = test_engine["purpose"]
    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_timeout(500)
    page.locator("#detailContent .detail-edit-input[data-field='purpose']").fill("E2E-отмена-изменений")
    page.locator("#detailContent .detail-edit-actions button:has-text('✕ Отмена')").click()
    page.wait_for_timeout(500)
    # Should be back in view mode, original value restored
    page.evaluate("toggleDetailMode('view')")
    page.wait_for_timeout(500)
    purpose_el = page.locator("#detailContent .detail-item").filter(has=page.locator("label", has_text="Назначение")).locator(".value")
    assert original_purpose in purpose_el.inner_text() or "E2E-отмена" not in purpose_el.inner_text()
    close_detail(page)


@pytest.mark.scn("36. Переключение режимов просмотра/редактирования")
def test_36_toggle_modes(page, test_engine):
    """Кнопки «👁 Просмотр» и «✏️ Редактирование» переключают режимы."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    # View mode
    expect(page.locator("#detailContent .detail-mode-toggle button", has_text="👁 Просмотр")).to_be_visible()
    # Switch to edit mode
    page.evaluate("toggleDetailMode('edit')")
    expect(page.locator("#detailContent .detail-mode-toggle button", has_text="✏️ Редактирование")).to_be_visible()
    # Switch back to view mode
    page.evaluate("toggleDetailMode('view')")
    expect(page.locator("#detailContent .detail-mode-toggle button", has_text="👁 Просмотр")).to_be_visible()
    close_detail(page)


@pytest.mark.scn("37. Добавление и сохранение режима работы")
def test_37_add_save_mode(page, test_engine):
    """Добавление режима работы в карточке и сохранение."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_timeout(500)

    # Click "Добавить режим" in the modes subsection
    page.click("#detailContent button:has-text('Добавить режим')")
    page.wait_for_timeout(300)
    assert page.locator("#modesDisplayBody tr").count() >= 1

    # Fill the mode inputs
    inputs = page.locator("#modesDisplayBody tr:last-child input")
    inputs.nth(0).fill("50")      # frequency
    inputs.nth(1).fill("3.0")     # power
    inputs.nth(2).fill("380")     # voltage
    inputs.nth(3).fill("Звезда")  # connection_type
    inputs.nth(4).fill("8.5")     # current
    inputs.nth(5).fill("1500")    # rpm

    page.click("#detailContent button:has-text('💾 Сохранить')")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)
    close_detail(page)


@pytest.mark.scn("38. Добавление и сохранение работы")
def test_38_add_save_work(page, test_engine):
    """Добавление записи о работе в карточке и сохранение."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_timeout(500)

    # Click "Добавить" in the works subsection
    page.locator("#detailContent .detail-subsection-header", has_text="Произведенные работы").locator("button:has-text('➕ Добавить')").click()
    page.wait_for_timeout(300)
    assert page.locator("#worksDisplayBody tr").count() >= 1

    inputs = page.locator("#worksDisplayBody tr:last-child input")
    inputs.nth(0).fill("2025-01-20")
    inputs.nth(1).fill("Ревизия")
    inputs.nth(2).fill("25")
    inputs.nth(3).fill("ГОД")
    inputs.nth(4).fill("E2E")

    page.click("#detailContent button:has-text('💾 Сохранить')")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(500)
    close_detail(page)


@pytest.mark.scn("40. Навигация между двигателями")
def test_40_navigation(page, test_engine):
    """Стрелки навигации между двигателями в карточке."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)
    # Navigation arrows should exist (prev/next on detail toolbar)
    nav_arrows = page.locator("#detailContent button", has_text="Предыдущий")
    assert nav_arrows.count() >= 1


@pytest.mark.scn("41. Печать карточки")
def test_41_print_card(page, test_engine):
    """Кнопка печати открывает новую вкладку с печатной версией."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)

    with page.expect_popup() as popup_info:
        page.evaluate("printEngineCard()")
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded")
    popup.wait_for_load_state("networkidle", timeout=10000)
    expect(popup.locator("#printRoot")).to_be_visible()
    # Should show engine title
    title = popup.locator(".print-title")
    expect(title).to_be_visible()
    # Print button exists
    expect(popup.locator("#printBtn")).to_be_visible()
    popup.close()
    close_detail(page)


@pytest.mark.scn("42. Закрытие карточки")
def test_42_close_card(page, test_engine):
    """Кнопка ✕ и клавиша Escape закрывают карточку."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)
    close_detail(page)
    page.wait_for_selector("#detailModal", state="hidden", timeout=5000)
