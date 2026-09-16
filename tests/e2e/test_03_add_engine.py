"""Группа 3: Создание двигателя — карточка нового двигателя.

Вкладки «Добавить» в UI больше нет (см. index.html: табы catalog/equipment/
incidents/import/search/settings/info/admin/audit). Реальный флоу: кнопка «+»
в шапке дерева мест (.tree-add-btn, появляется по hover) →
locationTree.js::createAndOpenEngine() → POST /api/engine и открытие обычной
карточки в режиме редактирования с тулбаром « Новый двигатель».

Специфика «новой» карточки (engineCard.js::isPendingNew):
  * характеристик 15 полей .detail-edit-input[data-field=<key>];
  * режимы/работы редактируются в таблицах #modesDisplayBody / #worksDisplayBody;
  * кнопок навигации/печати/удаления нет (записи «как бы» ещё не существует);
  * «Сохранить» → PUT + toast «Двигатель добавлен»;
  * «Отмена» или закрытие карточки → DELETE записи (closeDetail через setTimeout).
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    wait_toast, make_engine, make_test_png, delete_engine_by_serial,
    open_new_engine_card, save_detail_card, cancel_detail_card,
    fill_detail_fields, rows_with_inputs,
)


def _discard(admin_api, engine_id):
    """Удалить запись, созданную через «+» (404 при повторном удалении — не ошибка)."""
    if engine_id:
        admin_api.delete("/api/engine/%d" % engine_id)


@pytest.mark.scn("22. Открытие карточки нового двигателя («+» в дереве мест)")
def test_22_open_add_tab(page, admin_api):
    """Кнопка «+» создаёт запись и открывает карточку «Новый двигатель»."""
    engine_id = open_new_engine_card(page)
    try:
        expect(page.locator("#detailToolbar .detail-toolbar-title")).to_contain_text("Новый двигатель")
        # 15 полей DETAIL_CHAR_FIELDS отрисованы как редактируемые инпуты
        assert page.locator("#detailContent .detail-edit-input").count() >= 10
        expect(page.locator("#detailToolbar button:has-text('Сохранить')")).to_be_visible()
        expect(page.locator("#detailToolbar button:has-text('Отмена')")).to_be_visible()
        # у «нового» двигателя нет навигации/печати/удаления (isPendingNew)
        assert page.locator("#detailToolbar button:has-text('Предыдущий')").count() == 0
        assert page.locator("#detailToolbar button:has-text('Печать')").count() == 0
        assert page.locator("#detailToolbar button:has-text('Удалить')").count() == 0
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)


@pytest.mark.scn("23. Заполнение характеристик новой карточки")
def test_23_fill_form(page, admin_api):
    """Поля характеристик принимают значения из payload."""
    engine_id = open_new_engine_card(page)
    payload = make_engine()
    try:
        fill_detail_fields(page, payload)
        for key in ("location", "serial_number", "manufacturer", "purpose"):
            expect(page.locator(".detail-edit-input[data-field='%s']" % key)).to_have_value(
                str(payload[key]))
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)


@pytest.mark.scn("24. Добавление ряда режима работы")
def test_24_add_mode_row(page, admin_api):
    """Кнопка «Добавить режим» добавляет редактируемые строки в #modesDisplayBody."""
    engine_id = open_new_engine_card(page)
    try:
        # пустая таблица режимов рисует строку-заглушку .no-data — считаем только строки с полями
        assert rows_with_inputs(page, "#modesDisplayBody", ".mode-edit-input") == 0
        page.click("#detailContent button:has-text('Добавить режим')")
        assert rows_with_inputs(page, "#modesDisplayBody", ".mode-edit-input") == 1
        page.click("#detailContent button:has-text('Добавить режим')")
        assert rows_with_inputs(page, "#modesDisplayBody", ".mode-edit-input") == 2

        inputs = page.locator("#modesDisplayBody tr:first-child .mode-edit-input")
        inputs.nth(0).fill("50")        # частота
        inputs.nth(1).fill("1.5")       # мощность
        inputs.nth(2).fill("230")       # напряжение
        inputs.nth(3).fill("Звезда")    # тип подключения
        inputs.nth(4).fill("5.2")       # ток
        inputs.nth(5).fill("1425")      # обороты
        expect(inputs.nth(0)).to_have_value("50")
        expect(inputs.nth(5)).to_have_value("1425")
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)


@pytest.mark.scn("25. Добавление записи о работе")
def test_25_add_work_row(page, admin_api):
    """Кнопка «Добавить» под таблицей работ добавляет редактируемую строку."""
    engine_id = open_new_engine_card(page)
    try:
        assert rows_with_inputs(page, "#worksDisplayBody", ".work-edit-input") == 0
        page.click(".detail-subsection-footer button:has-text('Добавить')")
        assert rows_with_inputs(page, "#worksDisplayBody", ".work-edit-input") == 1

        inputs = page.locator("#worksDisplayBody tr:first-child .work-edit-input")
        inputs.nth(0).fill("2025-01-15")            # дата
        inputs.nth(1).fill("ТО")                    # вид работ
        inputs.nth(2).fill("10")                    # сопротивление изоляции
        inputs.nth(3).fill("ГОД")                   # внешний осмотр
        inputs.nth(4).fill("E2E")                   # ФИО
        inputs.nth(5).select_option("repair")       # статус (select)
        expect(inputs.nth(1)).to_have_value("ТО")
        expect(inputs.nth(5)).to_have_value("repair")
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)



@pytest.mark.scn("26. Загрузка фото в новую карточку")
def test_26_select_photos(page, admin_api, tmp_path):
    """Фото выбирается в модалке добавления и сразу загружается на сервер."""
    engine_id = open_new_engine_card(page)
    try:
        png_path = str(tmp_path / "test_upload.png")
        make_test_png(png_path)
        page.evaluate("openPhotoAddModal()")
        page.wait_for_selector("#photoAddModal.active", state="visible", timeout=5000)
        page.set_input_files("#detailPhotoInput", png_path)
        page.wait_for_timeout(500)
        # до загрузки фото показано в превью модалки (#detailPhotoPreview)
        expect(page.locator("#detailPhotoPreview .photo-thumb")).to_be_visible()
        page.locator("#photoAddModal button:has-text('Загрузить')").click()
        wait_toast(page, "Загружено фото")
        page.wait_for_selector("#photoAddModal", state="hidden", timeout=5000)
        page.wait_for_load_state("networkidle", timeout=10000)
        assert page.locator(".gallery-thumb").count() == 1
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)


@pytest.mark.scn("28. «Отмена» удаляет незасохранённый двигатель")
def test_28_remove_pending_photo(page, admin_api):
    """Закрытие новой карточки без «Сохранить» удаляет созданную запись."""
    engine_id = open_new_engine_card(page)
    expect(page.locator(".detail-edit-input[data-field='serial_number']")).to_be_visible()
    cancel_detail_card(page)
    assert engine_id, "не удалось получить id новой записи"
    # closeDetail() удаляет pending-запись (DELETE через setTimeout ~300 мс)
    r = admin_api.get("/api/engine/%d" % engine_id)
    assert r.status == 404, "незасохранённый двигатель должен быть удалён из БД"


@pytest.mark.scn("29. Новая карточка открывается пустой")
def test_29_empty_new_card(page, admin_api):
    """Аналог старой «Очистки формы»: у нового двигателя поля пустые, фото нет."""
    engine_id = open_new_engine_card(page)
    try:
        for key in ("location", "serial_number", "manufacturer", "purpose"):
            expect(page.locator(".detail-edit-input[data-field='%s']" % key)).to_have_value("")
        expect(page.locator("#detailContent .no-data", has_text="Нет фото")).to_be_visible()
        # статус считается по работам: у новой записи работ нет → «В резерве»
        expect(page.locator("#detailToolbar .engine-status-badge")).to_have_text("В резерве")
    finally:
        if page.locator("#detailModal.active").count():
            cancel_detail_card(page)
        _discard(admin_api, engine_id)


@pytest.mark.scn("30. Кнопка «Сохранить» создаёт двигатель")
def test_30_apply_creates_engine(page, admin_api):
    """«Сохранить» создаёт двигатель, переводит карточку в просмотр и обновляет каталог."""
    engine_id = open_new_engine_card(page)
    payload = make_engine(serial_number="APPLY-E2E-TEST")
    try:
        fill_detail_fields(page, payload)
        save_detail_card(page, expected_toast="Двигатель добавлен")
        # карточка перечитывается с сервера в режиме просмотра
        expect(page.locator("#detailContent .detail-item").first).to_be_visible()
        assert page.locator("#detailContent .detail-edit-input").count() == 0
        expect(page.locator("tbody tr", has_text="APPLY-E2E-TEST")).to_be_visible()
    finally:
        if page.locator("#detailModal.active").count():
            page.evaluate("closeDetail()")
            page.wait_for_selector("#detailModal", state="hidden", timeout=10000)
        delete_engine_by_serial(admin_api, "APPLY-E2E-TEST")
        _discard(admin_api, engine_id)


@pytest.mark.scn("31. Сохранение карточки по Enter в поле режима")
def test_31_save_via_form(page, admin_api):
    """Enter в поле режима вызывает saveDetailEdit() (см. engineCard.js)."""
    engine_id = open_new_engine_card(page)
    payload = make_engine(serial_number="ENTER-E2E-TEST")
    try:
        # ВАЖНО: addModeRowInline() перерисовывает карточку из currentEngineData,
        # поэтому характеристики заполняем ПОСЛЕ добавления строки режима — иначе
        # введённые значения будут стёрты перерисовкой.
        page.click("#detailContent button:has-text('Добавить режим')")
        fill_detail_fields(page, payload)
        freq = page.locator("#modesDisplayBody tr:first-child .mode-edit-input").nth(0)
        freq.fill("50")
        freq.press("Enter")
        wait_toast(page, "Двигатель добавлен")
        page.wait_for_load_state("networkidle", timeout=15000)
        expect(page.locator("tbody tr", has_text="ENTER-E2E-TEST")).to_be_visible()
    finally:
        if page.locator("#detailModal.active").count():
            page.evaluate("closeDetail()")
            page.wait_for_selector("#detailModal", state="hidden", timeout=10000)
        delete_engine_by_serial(admin_api, "ENTER-E2E-TEST")
        _discard(admin_api, engine_id)