"""Группа 5: Фото в карточке двигателя — загрузка, просмотр, удаление.

Актуализировано под текущий фронт (см. engineCard.js/index.html):
  * тулбар карточки — #detailToolbar (вне #detailContent, см. engineCard.js:87);
  * вход в правку — enterEditMode() (toggleDetailMode/toggleDetailEdit удалены);
  * загрузка — модалка #photoAddModal (#detailPhotoInput + «Загрузить» →
    submitDetailPhotoAdd() → toast «Загружено фото», галерея .gallery-thumb);
  * удаление — .gallery-thumb-remove → removeDetailPhoto() с confirm();
  * просмотр — общий лайтбокс #photoModal (#modalImage, #photoCounter,
    #photoPrevBtn/#photoNextBtn, закрытие .modal-close/Escape).
"""
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    reload_catalog, accept_dialogs, make_test_png, wait_toast, close_detail,
)


def _setup_edit_mode(page, engine_id):
    """Открыть карточку и перейти в режим редактирования."""
    reload_catalog(page)
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailToolbar .detail-toolbar", state="visible", timeout=10000)
    page.evaluate("enterEditMode()")
    page.wait_for_selector("#detailContent .detail-edit-input", state="attached", timeout=5000)


def _upload_photo(page, png_path):
    """Загрузить фото через модалку «Добавить фото» и дождаться успеха."""
    page.evaluate("openPhotoAddModal()")
    page.wait_for_selector("#photoAddModal.active", state="visible", timeout=5000)
    page.set_input_files("#detailPhotoInput", png_path)
    page.locator("#photoAddModal button:has-text('Загрузить')").click()
    wait_toast(page, "Загружено фото")
    page.wait_for_selector("#photoAddModal", state="hidden", timeout=5000)
    page.wait_for_load_state("networkidle", timeout=10000)


def _close_photo_modal(page):
    """Закрыть лайтбокс фото кнопкой «×» (.modal-close → closePhotoModal())."""
    page.click("#photoModal .modal-close")
    page.wait_for_selector("#photoModal", state="hidden", timeout=5000)


@pytest.mark.scn("43. Добавление фото в карточку")
def test_43_add_photo(page, test_engine, tmp_path):
    """Фото появляется в галерее после загрузки через UI."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_add_photo.png")
    make_test_png(png_path, color=(0, 128, 255))
    _upload_photo(page, png_path)
    assert page.locator(".gallery-thumb").count() >= 1
    close_detail(page)


@pytest.mark.scn("44. Удаление фото")
def test_44_delete_photo(page, test_engine, tmp_path):
    """Удаление фото из карточки кнопкой «−» (.gallery-thumb-remove)."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_del_photo.png")
    make_test_png(png_path, color=(255, 128, 0))
    _upload_photo(page, png_path)
    assert page.locator(".gallery-thumb").count() >= 1

@pytest.mark.scn("46. Просмотр фото в модальном окне")
def test_46_view_photo_modal(page, test_engine, tmp_path):
    """Клик на миниатюру открывает лайтбокс #photoModal."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_view_photo.png")
    make_test_png(png_path, color=(128, 0, 255))
    _upload_photo(page, png_path)

    page.locator(".gallery-thumb").first.click()
    page.wait_for_selector("#photoModal.active", state="visible", timeout=5000)
    expect(page.locator("#modalImage")).to_be_visible()
    _close_photo_modal(page)
    close_detail(page)


@pytest.mark.scn("47. Навигация между фото в модальном окне")
def test_47_navigate_photos(page, test_engine, tmp_path):
    """Кнопки #photoNextBtn/#photoPrevBtn переключают фото и счётчик."""
    _setup_edit_mode(page, test_engine["id"])
    for i, color in enumerate([(255, 0, 0), (0, 255, 0)]):
        png_path = str(tmp_path / f"test_nav_photo_{i}.png")
        make_test_png(png_path, color=color)
        _upload_photo(page, png_path)

    assert page.locator(".gallery-thumb").count() >= 2
    page.locator(".gallery-thumb").first.click()
    page.wait_for_selector("#photoModal.active", state="visible", timeout=5000)
    expect(page.locator("#photoCounter")).to_have_text(re.compile(r"1\s*/\s*2"))

    expect(page.locator("#photoNextBtn")).to_be_visible()
    page.click("#photoNextBtn")
    expect(page.locator("#photoCounter")).to_have_text(re.compile(r"2\s*/\s*2"))

    expect(page.locator("#photoPrevBtn")).to_be_visible()
    page.click("#photoPrevBtn")
    expect(page.locator("#photoCounter")).to_have_text(re.compile(r"1\s*/\s*2"))

    _close_photo_modal(page)
    close_detail(page)


@pytest.mark.scn("48. Закрытие модального окна фото (Escape)")
def test_48_close_photo_modal(page, test_engine, tmp_path):
    """Клавиша Escape закрывает лайтбокс."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_close_photo.png")
    make_test_png(png_path, color=(0, 255, 128))
    _upload_photo(page, png_path)
    page.locator(".gallery-thumb").first.click()
    page.wait_for_selector("#photoModal.active", state="visible", timeout=5000)

    page.keyboard.press("Escape")
    page.wait_for_selector("#photoModal", state="hidden", timeout=5000)
    close_detail(page)


@pytest.mark.scn("49. Автодополнение полей в редактировании")
def test_49_autocomplete(page, test_engine):
    """Поле «Тип» в правке показывает подсказки из /api/search-suggestions."""
    _setup_edit_mode(page, test_engine["id"])

    type_input = page.locator(".detail-edit-input[data-field='engine_type']")
    expect(type_input).to_be_visible()
    type_input.click()
    type_input.fill("Электр")

    # Дропдаун подсказок (engines.js::attachFieldAutocomplete → .suggest-dropdown/.suggest-item)
    expect(page.locator(".suggest-item").first).to_be_visible(timeout=8000)
    assert page.locator(".suggest-item").count() >= 1
    close_detail(page)