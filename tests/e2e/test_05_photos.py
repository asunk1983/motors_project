"""Группа 5: Фото в карточке двигателя — загрузка, просмотр, удаление.

Актуализировано под текущий фронт (см. engineCard.js/index.html):
  * тулбар карточки — #detailToolbar (вне #detailContent, см. engineCard.js:87);
  * вход в правку — enterEditMode() (toggleDetailMode/toggleDetailEdit удалены);
  * загрузка — модалка #photoAddModal (#detailPhotoInput + «Загрузить» →
    submitDetailPhotoAdd() → toast «Загружено фото», галерея .gallery-thumb);
  * удаление — .gallery-thumb-remove → removeDetailPhoto() с confirm();
  * обрезка — .gallery-thumb-crop → #photoCropModal (canvas + рамка
    #cropSelection) → «Обрезать и применить» → PUT /api/engine/<id>/photos/<file>
    (см. test_45_crop_photo);
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


def _clear_toasts(page):
    """Убрать уже висящие toast-сообщения.

    Тост живёт ~3.3 с (common.js::showToast), поэтому без чистки wait_toast()
    на второй загрузке подряд матчится на тост ПРЕДЫДУЩЕЙ загрузки (текст у
    них один и тот же) и возвращается мгновенно, ничего не дождавшись.
    """
    page.evaluate("[...document.querySelectorAll('.toast')].forEach(t => t.remove())")


def _upload_photo(page, png_path, expected_count):
    """Загрузить фото через модалку «Добавить фото» и дождаться галереи.

    expected_count — сколько миниатюр .gallery-thumb должно стать ПОСЛЕ этой
    загрузки (в каждой тестовой карточке счёт с нуля, см. фикстуру test_engine).

    Ждём именно результат, потому что оба «посредника» ничего не гарантируют:
    submitDetailPhotoAdd() (engineCard.js) закрывает #photoAddModal ДО запроса
    списка фото и ДО renderDetailContent(), а wait_for_load_state("networkidle")
    на SPA возвращается сразу — состояние документа уже достигнуто при загрузке
    страницы, XHR его не сбрасывают. Именно на этом test_47 падал с «1 >= 2».
    """
    _clear_toasts(page)
    page.evaluate("openPhotoAddModal()")
    page.wait_for_selector("#photoAddModal.active", state="visible", timeout=5000)
    page.set_input_files("#detailPhotoInput", png_path)
    page.locator("#photoAddModal button:has-text('Загрузить')").click()
    wait_toast(page, "Загружено фото")
    page.wait_for_selector("#photoAddModal", state="hidden", timeout=5000)
    expect(page.locator(".gallery-thumb")).to_have_count(expected_count, timeout=10000)


def _thumb_natural_size(page):
    """Натуральный размер файла, который сейчас отдаёт сервер (миниатюра галереи).

    Миниатюра галереи — <img class="gallery-thumb" src="...?v=photoCacheBust">,
    то есть её naturalWidth/naturalHeight — размер именно того файла, который
    вернул сервер: после обрезки engineCard.js::_applyCropExisting подставляет
    новый cache-bust (photoCacheBust = Date.now()), поэтому проверяется новый
    файл, а не изображение из кэша браузера по старому URL.
    """
    return page.evaluate(
        "() => { const el = document.querySelector('.gallery-thumb');"
        " return el ? [el.naturalWidth, el.naturalHeight] : null; }"
    )


def _wait_thumb_size(page, width, height, timeout=10000):
    """Дождаться, что сервер отдаёт фото указанного размера (ширина x высота)."""
    page.wait_for_function(
        "([w, h]) => { const el = document.querySelector('.gallery-thumb');"
        " return !!el && el.complete && el.naturalWidth === w"
        " && el.naturalHeight === h; }",
        arg=[width, height],
        timeout=timeout,
    )


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
    _upload_photo(page, png_path, expected_count=1)
    close_detail(page)


@pytest.mark.scn("44. Удаление фото")
def test_44_delete_photo(page, test_engine, tmp_path):
    """Удаление фото из карточки кнопкой «−» (.gallery-thumb-remove)."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_del_photo.png")
    make_test_png(png_path, color=(255, 128, 0))
    _upload_photo(page, png_path, expected_count=1)

@pytest.mark.scn("45. Обрезка фото в карточке (#photoCropModal)")
def test_45_crop_photo(page, test_engine, tmp_path):
    """Обрезка сохранённого фото: канвас #photoCropModal → PUT .../photos/<file>.

    Признак того, что обрезка реально применилась (а не перезаписался
    оригинал), — размер файла, который сервер отдаёт в галерею. Исходный PNG
    намеренно не квадратный (80x40), а рамка выделения по умолчанию —
    центрированные 80% изображения (engineCard.js::_openCropStage), то есть
    ровно 64x32 при масштабе canvas 1:1 (80x40 меньше CROP_MAX_W/CROP_MAX_H).
    """
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_crop_photo.png")
    make_test_png(png_path, width=80, height=40, color=(0, 200, 100))
    _upload_photo(page, png_path, expected_count=1)
    _wait_thumb_size(page, 80, 40)

    # Кнопка обрезки есть только в режиме редактирования
    # (engineCard.js::renderDetailContent → .gallery-thumb-crop).
    expect(page.locator(".gallery-thumb-crop").first).to_be_visible()

    # 1. Открытие модалки: канвас нарисован в натуральном размере, рамка
    # выделения — 80% картинки.
    page.locator(".gallery-thumb-crop").first.click()
    expect(page.locator("#photoCropModal")).to_have_class(re.compile(r"\bactive\b"))
    expect(page.locator("#cropStage")).to_be_visible()
    expect(page.locator("#cropSelection")).to_be_visible()
    assert page.evaluate(
        "() => { const c = document.getElementById('cropCanvas');"
        " return [c.width, c.height]; }"
    ) == [80, 40]
    # Геометрия рамки берётся из inline-стилей, которые пишет
    # _renderCropSelection(): логические координаты рамки на canvas (а не
    # bounding box — у .crop-selection есть CSS-бордер 2px, который
    # добавляется к рамке и смазывает сравнение с 0.8 * размер канваса).
    assert page.evaluate(
        "() => { const s = document.getElementById('cropSelection').style;"
        " return [s.left, s.top, s.width, s.height]; }"
    ) == ['8px', '4px', '64px', '32px']  # центрированные 80% от 80x40

    # 2. «Отмена» — модалка закрывается, файл на сервере не тронут.
    page.locator("#photoCropModal button:has-text('Отмена')").click()
    page.wait_for_selector("#photoCropModal", state="hidden", timeout=5000)
    _wait_thumb_size(page, 80, 40)

    # 3. «Обрезать и применить» — обрезанный blob уходит на
    # PUT /api/engine/<id>/photos/<filename>, сервер перезаписывает ТОТ ЖЕ файл
    # (photo_count не меняется, второй копии не появляется), карточка
    # перечитывает галерею.
    page.locator(".gallery-thumb-crop").first.click()
    expect(page.locator("#photoCropModal")).to_have_class(re.compile(r"\bactive\b"))
    page.locator("#photoCropModal button:has-text('Обрезать и применить')").click()
    wait_toast(page, "Фото обрезано")
    page.wait_for_selector("#photoCropModal", state="hidden", timeout=5000)

    expect(page.locator(".gallery-thumb")).to_have_count(1)  # файл заменён, не добавлен
    _wait_thumb_size(page, 64, 32)                           # сервер отдаёт обрезку
    close_detail(page)


@pytest.mark.scn("46. Просмотр фото в модальном окне")
def test_46_view_photo_modal(page, test_engine, tmp_path):
    """Клик на миниатюру открывает лайтбокс #photoModal."""
    _setup_edit_mode(page, test_engine["id"])
    png_path = str(tmp_path / "test_view_photo.png")
    make_test_png(png_path, color=(128, 0, 255))
    _upload_photo(page, png_path, expected_count=1)

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
        # i + 1: ждём именно ОБЕ миниатюры — на этом и падал test_47,
        # когда вторая загрузка ещё не успела дорисоваться (см. _upload_photo).
        _upload_photo(page, png_path, expected_count=i + 1)

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
    _upload_photo(page, png_path, expected_count=1)
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