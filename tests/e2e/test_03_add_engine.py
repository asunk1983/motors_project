"""Группа 3: Добавление двигателя — форма, режимы, работы, фото, очистка."""
import json
import os

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    switch_tab, wait_toast, fill_engine_form, make_engine,
    make_mode, make_work, make_test_png, delete_engine_by_serial,
)


@pytest.mark.scn("22. Открытие вкладки «Добавить»")
def test_22_open_add_tab(page):
    switch_tab(page, "add")
    expect(page.locator("#tab-add")).to_be_visible()
    expect(page.locator("#engineForm")).to_be_visible()


@pytest.mark.scn("23. Заполнение формы")
def test_23_fill_form(page):
    switch_tab(page, "add")
    payload = make_engine()
    fill_engine_form(page, payload)
    for field_id, key in [
        ("f_location", "location"), ("f_serial_number", "serial_number"),
    ]:
        expect(page.locator("#" + field_id)).to_have_value(str(payload[key]))


@pytest.mark.scn("24. Добавление ряда режима работы")
def test_24_add_mode_row(page):
    switch_tab(page, "add")
    assert page.locator("#modesBody tr").count() == 0
    page.evaluate("addModeRow()")
    expect(page.locator("#modesBody tr")).to_have_count(1)
    page.evaluate("addModeRow()")
    expect(page.locator("#modesBody tr")).to_have_count(2)
    # fill the first mode row
    inputs = page.locator("#modesBody tr:first-child input")
    inputs.nth(0).fill("50")
    inputs.nth(1).fill("1.5")
    inputs.nth(2).fill("230")
    inputs.nth(3).fill("Звезда")
    inputs.nth(4).fill("5.2")
    inputs.nth(5).fill("1425")


@pytest.mark.scn("25. Добавление записи о работе")
def test_25_add_work_row(page):
    switch_tab(page, "add")
    assert page.locator("#worksBody tr").count() == 0
    page.evaluate("addWorkRow()")
    expect(page.locator("#worksBody tr")).to_have_count(1)
    inputs = page.locator("#worksBody tr:first-child input")
    inputs.nth(0).fill("1")
    inputs.nth(1).fill("2025.01.15")
    inputs.nth(2).fill("ТО")
    inputs.nth(3).fill("10")
    inputs.nth(4).fill("ГОД")
    inputs.nth(5).fill("E2E")


@pytest.mark.scn("26. Выбор фото")
def test_26_select_photos(page, tmp_path):
    switch_tab(page, "add")
    png_path = str(tmp_path / "test_upload.png")
    make_test_png(png_path)
    page.set_input_files("#f_photos", png_path)
    page.wait_for_timeout(500)
    expect(page.locator("#photosPreview .photo-thumb")).to_be_visible()
    assert page.locator("#photosPreview .photo-thumb").count() == 1


@pytest.mark.scn("28. Удаление непривязанного фото")
def test_28_remove_pending_photo(page, tmp_path):
    switch_tab(page, "add")
    png_path = str(tmp_path / "test_remove.png")
    make_test_png(png_path, color=(0, 255, 0))
    page.set_input_files("#f_photos", png_path)
    page.wait_for_timeout(500)
    expect(page.locator("#photosPreview .photo-thumb")).to_be_visible()
    page.locator("#photosPreview .photo-thumb-remove").click()
    page.wait_for_timeout(300)
    assert page.locator("#photosPreview .photo-thumb").count() == 0


@pytest.mark.scn("29. Очистка формы")
def test_29_clear_form(page):
    switch_tab(page, "add")
    fill_engine_form(page, make_engine(serial_number="CLEAR-TEST-123"))
    expect(page.locator("#f_serial_number")).to_have_value("CLEAR-TEST-123")
    page.locator("#engineForm button:has-text('Очистить')").click()
    page.wait_for_timeout(300)
    expect(page.locator("#f_serial_number")).to_have_value("")
    expect(page.locator("#f_location")).to_have_value("")


@pytest.mark.scn("30. Кнопка «Применить» (создание двигателя)")
def test_30_apply_creates_engine(page, admin_api):
    """Apply создаёт двигатель через API, сбрасывает форму и переключается на каталог."""
    switch_tab(page, "add")
    payload = make_engine(serial_number="APPLY-E2E-TEST")
    fill_engine_form(page, payload)
    page.click("#applyBtn")
    wait_toast(page, "Двигатель создан")
    page.wait_for_load_state("networkidle", timeout=15000)
    # Should be switched to catalog tab
    expect(page.locator("#tab-catalog")).to_be_visible()
    # Engine visible in catalog
    expect(page.locator("tbody tr", has_text="APPLY-E2E-TEST")).to_be_visible()
    try:
        delete_engine_by_serial(admin_api, "APPLY-E2E-TEST")
    except Exception:
        pass


@pytest.mark.scn("31. Сохранение через кнопку формы (submit)")
def test_31_save_via_form(page, admin_api):
    """Form submit (Enter in a field) triggers saveEngine."""
    switch_tab(page, "add")
    payload = make_engine(serial_number="FORM-SUBMIT-E2E")
    fill_engine_form(page, payload)
    # Trigger form submit by pressing Enter in the serial number field
    page.press("#f_serial_number", "Enter")
    wait_toast(page, "Двигатель создан")
    page.wait_for_load_state("networkidle", timeout=15000)
    expect(page.locator("tbody tr", has_text="FORM-SUBMIT-E2E")).to_be_visible()
    try:
        delete_engine_by_serial(admin_api, "FORM-SUBMIT-E2E")
    except Exception:
        pass
