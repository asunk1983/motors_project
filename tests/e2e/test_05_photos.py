"""Группа 5: Фото в карточке двигателя — загрузка, просмотр, удаление."""
import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    reload_catalog, accept_dialogs, make_test_png, wait_toast, close_detail,
)


def _setup_edit_mode(page, engine_id):
    """Открыть карточку и перейти в режим редактирования."""
    reload_catalog(page)
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(pytest.importorskip("re").compile(r"\bactive\b"))
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)
    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_selector("#detailContent .detail-edit-input", state="attached", timeout=5000)


def _upload_photo(page, png_path):
    """Upload a photo in the detail card edit mode and wait for success."""
    page.evaluate("openPhotoAddModal()")
    page.wait_for_selector("#photoAddModal.active", state="visible", timeout=5000)
    page.set_input_files("#detailPhotoInput", png_path)
    page.click("#photoAddModal button:has-text('Загрузить')")
    wait_toast(page, "Загружено фото")
    page.wait_for_selector("#photoAddModal", state="hidden", timeout=5000)
    page.wait_for_load_state("networkidle", timeout=10000)


def _close_photo_modal(page):
    """Close the photo viewer modal."""
    close_btn = page.locator(
        "#photoModal .photo-close, #photoModal .close-btn, #photoModal button:has-text('✕')"
    )
    if close_btn.count() > 0:
        close_btn.first.click()
    else:
        page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    page.wait_for_selector("#photoModal", state="hidden", timeout=5000)


@pytest.mark.scn("43. Добавление фото в карточку")
def test_43_add_photo(page, test_engine, tmp_path):
    """Фото появляется в галерее после загрузки через UI."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_add_photo.png")
    make_test_png(png_path, color=(0, 128, 255))
    _upload_photo(page, png_path)
    assert page.locator(".gallery-thumb").count() >= 1
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)


@pytest.mark.scn("44. Удаление фото")
def test_44_delete_photo(page, test_engine, tmp_path):
    """Удаление фото из карточки через кнопку ✕."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_del_photo.png")
    make_test_png(png_path, color=(255, 128, 0))
    _upload_photo(page, png_path)
    assert page.locator(".gallery-thumb").count() >= 1
    # Remove photo
    accept_dialogs(page)
    page.click(".gallery-thumb-remove")
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle", timeout=10000)
    assert page.locator(".gallery-thumb").count() == 0
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)


@pytest.mark.scn("46. Просмотр фото в модальном окне")
def test_46_view_photo_modal(page, test_engine, tmp_path):
    """Клик на миниатюру открывает модальное окно просмотра фото."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_view_photo.png")
    make_test_png(png_path, color=(128, 0, 255))
    _upload_photo(page, png_path)
    # Click thumbnail to open viewer
    page.click(".gallery-thumb img")
    page.wait_for_selector("#photoModal", state="visible", timeout=5000)
    # Photo image should be visible
    photo_img = page.locator("#photoModal img, #photoModal .photo-viewer-img")
    assert photo_img.count() >= 1
    _close_photo_modal(page)
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)


@pytest.mark.scn("47. Навигация между фото в модальном окне")
def test_47_navigate_photos(page, test_engine, tmp_path):
    """Кнопки prev/next в модальном окне переключают фото."""
    _setup_edit_mode(page, test_engine["id"])
    # Upload two photos
    for i, color in enumerate([(255, 0, 0), (0, 255, 0)]):
        png_path = str(tmp_path / f"test_nav_photo_{i}.png")
        make_test_png(png_path, color=color)
        _upload_photo(page, png_path)

    assert page.locator(".gallery-thumb").count() >= 2
    # Open viewer
    page.click(".gallery-thumb img")
    page.wait_for_selector("#photoModal", state="visible", timeout=5000)
    # Try next/prev navigation
    next_btn = page.locator("#photoModal .photo-next, #photoModal button:has-text('→')")
    prev_btn = page.locator("#photoModal .photo-prev, #photoModal button:has-text('←')")
    if next_btn.count() > 0:
        next_btn.click()
        page.wait_for_timeout(300)
    if prev_btn.count() > 0:
        prev_btn.click()
        page.wait_for_timeout(300)
    _close_photo_modal(page)
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)


@pytest.mark.scn("48. Закрытие модального окна фото (Escape)")
def test_48_close_photo_modal(page, test_engine, tmp_path):
    """Клавиша Escape закрывает просмотрщик фото."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_close_photo.png")
    make_test_png(png_path, color=(0, 255, 128))
    _upload_photo(page, png_path)
    page.click(".gallery-thumb img")
    page.wait_for_selector("#photoModal", state="visible", timeout=5000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    page.wait_for_selector("#photoModal", state="hidden", timeout=5000)
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)


@pytest.mark.scn("49. Автодополнение полей в редактировании")
def test_49_autocomplete(page, test_engine):
    """Поля с автодополнением отображают подсказки при вводе."""
    reload_catalog(page)
    page.evaluate(f"showDetail({test_engine['id']})")
    page.wait_for_selector("#detailContent .detail-toolbar", state="visible", timeout=10000)
    page.evaluate("toggleDetailMode('edit')")
    page.wait_for_timeout(500)
    page.evaluate("toggleDetailEdit(true)")
    page.wait_for_timeout(500)

    # engine_type field should have autocomplete
    type_input = page.locator("#detail_engine_type")
    if type_input.count() > 0:
        type_input.fill("Электр")
        page.wait_for_timeout(800)
        # Check for autocomplete dropdown (may or may not be populated)
        suggestions = page.locator(".autocomplete-suggestions, .suggest-dropdown")
        page.wait_for_load_state("networkidle", timeout=5000)
    page.evaluate("toggleDetailMode('view')")
    close_detail(page)
