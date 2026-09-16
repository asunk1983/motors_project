"""Группа 4: Детальная карточка двигателя — просмотр, редактирование, печать.

Актуализировано под текущий фронт (см. engineCard.js):
  * тулбар карточки вынесен ИЗ #detailContent в #detailToolbar (комментарий
    engineCard.js:87: «Тулбар живёт вне #detailContent — не скроллится») →
    ожидания — "#detailToolbar .detail-toolbar";
  * вместо удалённых toggleDetailMode()/toggleDetailEdit() один режим на всю
    карточку: «Редактировать» → enterEditMode(), «Сохранить» → saveDetailEdit(),
    «Отмена» → cancelDetailEdit() (для существующего двигателя перечитывает данные);
  * сохранение одно на всю карточку — характеристики + режимы + работы одним PUT.
"""
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    reload_catalog, open_detail_edit, close_detail,
    cancel_detail_edit, save_detail_card,
)


def _open(page, engine_id):
    """Открыть карточку двигателя и дождаться отрисованного тулбара."""
    reload_catalog(page)
    page.evaluate(f"showDetail({engine_id})")
    expect(page.locator("#detailModal")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_selector("#detailToolbar .detail-toolbar", state="visible", timeout=10000)


def _field_value(page, label):
    """Значение поля карточки в режиме просмотра (label → .value)."""
    return page.locator("#detailContent .detail-item").filter(
        has=page.locator("label", has_text=label)).locator(".value")


@pytest.mark.scn("32. Открытие детальной карточки")
def test_32_open_detail_card(page, test_engine):
    """Открытие карточки по showDetail(id)."""
    _open(page, test_engine["id"])


@pytest.mark.scn("33. Просмотр характеристик")
def test_33_view_characteristics(page, test_engine):
    """В режиме просмотра отображаются характеристики двигателя."""
    _open(page, test_engine["id"])
    title_el = page.locator("#detailTitle")
    assert title_el.text_content()  # заголовок есть
    assert _field_value(page, "Заводской номер").inner_text().strip() == test_engine["serial_number"]


@pytest.mark.scn("34. Редактирование и сохранение характеристик")
def test_34_edit_and_save(page, test_engine):
    """Правка поля и «Сохранить» в шапке — значение уходит на сервер и видно в просмотре."""
    _open(page, test_engine["id"])
    open_detail_edit(page)

    page.locator(".detail-edit-input[data-field='purpose']").fill("E2E-отредактировано")
    save_detail_card(page, expected_toast="Изменения сохранены")

    assert "E2E-отредактировано" in _field_value(page, "Назначение").inner_text()
    close_detail(page)


@pytest.mark.scn("35. Отмена редактирования")
def test_35_cancel_editing(page, test_engine):
    """«Отмена» не сохраняет изменения (карточка перечитывается с сервера)."""
    _open(page, test_engine["id"])
    original_purpose = test_engine["purpose"]

    open_detail_edit(page)
    page.locator(".detail-edit-input[data-field='purpose']").fill("E2E-отмена-изменений")
    cancel_detail_edit(page)

    purpose_text = _field_value(page, "Назначение").inner_text()
    assert "E2E-отмена-изменений" not in purpose_text
    assert original_purpose in purpose_text
    close_detail(page)


@pytest.mark.scn("36. Переключение режима просмотра/редактирования")
def test_36_toggle_modes(page, test_engine):
    """Просмотр ↔ правка переключаются кнопками «Редактировать»/«Отмена» в шапке."""
    _open(page, test_engine["id"])

    # режим просмотра: значения-текст, кнопки сохранения нет
    expect(page.locator("#detailContent .detail-item .value").first).to_be_visible()
    expect(page.locator("#detailToolbar button:has-text('Редактировать')")).to_be_visible()
    assert page.locator("#detailToolbar button:has-text('Сохранить')").count() == 0

    # в правке появляются инпуты и кнопки «Сохранить»/«Отмена»
    open_detail_edit(page)
    expect(page.locator("#detailToolbar button:has-text('Сохранить')")).to_be_visible()
    expect(page.locator("#detailToolbar button:has-text('Отмена')")).to_be_visible()

    # «Отмена» возвращает просмотр
    cancel_detail_edit(page)
    assert page.locator("#detailContent .detail-edit-input").count() == 0
    close_detail(page)


@pytest.mark.scn("37. Добавление и сохранение режима работы")
def test_37_add_save_mode(page, test_engine, admin_api):
    """Новый режим добавляется в таблице карточки и сохраняется на сервере."""
    _open(page, test_engine["id"])
    open_detail_edit(page)

    page.click("#detailContent button:has-text('Добавить режим')")
    row = page.locator("#modesDisplayBody tr:last-child .mode-edit-input")
    row.nth(0).fill("50")      # частота
    row.nth(1).fill("3.0")     # мощность
    row.nth(2).fill("380")     # напряжение
    row.nth(3).fill("Звезда")  # тип подключения
    row.nth(4).fill("8.5")     # ток
    row.nth(5).fill("1500")    # обороты

    save_detail_card(page, expected_toast="Изменения сохранены")

    # PUT /api/engine/<id> делает полную замену modes — проверяем по API
    data = admin_api.get("/api/engine/%d" % test_engine["id"]).json()
    modes = data.get("modes") or []
    assert any(str(m.get("power")) == "3.0" and str(m.get("rpm")) == "1500" for m in modes), modes
    close_detail(page)


@pytest.mark.scn("38. Добавление и сохранение работы")
def test_38_add_save_work(page, test_engine, admin_api):
    """Новая работа добавляется кнопкой под таблицей и сохраняется на сервере."""
    _open(page, test_engine["id"])
    open_detail_edit(page)

    # Кнопка «Добавить» работ — в футере секции (не в заголовке, см. engineCard.js)
    page.click(".detail-subsection-footer button:has-text('Добавить')")
    inputs = page.locator("#worksDisplayBody tr:last-child .work-edit-input")
    inputs.nth(0).fill("2025-01-20")   # дата
    inputs.nth(1).fill("Ревизия")      # вид работ
    inputs.nth(2).fill("25")           # сопротивление изоляции
    inputs.nth(3).fill("ГОД")          # внешний осмотр
    inputs.nth(4).fill("E2E")          # ФИО

    save_detail_card(page, expected_toast="Изменения сохранены")

    data = admin_api.get("/api/engine/%d" % test_engine["id"]).json()
    works = data.get("works") or []
    assert any(w.get("work_description") == "Ревизия" for w in works), works
    close_detail(page)


@pytest.mark.scn("40. Навигация между двигателями")
def test_40_navigation(page, test_engine):
    """Кнопки навигации между двигателями — в шапке карточки (#detailToolbar)."""
    _open(page, test_engine["id"])
    assert page.locator("#detailToolbar button", has_text="Предыдущий").count() >= 1
    assert page.locator("#detailToolbar button", has_text="Следующий").count() >= 1


@pytest.mark.scn("41. Печать карточки")
def test_41_print_card(page, test_engine):
    """Кнопка печати открывает новую вкладку с печатной версией."""
    _open(page, test_engine["id"])

    with page.expect_popup() as popup_info:
        page.evaluate("printEngineCard()")
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded")
    popup.wait_for_load_state("networkidle", timeout=10000)
    expect(popup.locator("#printRoot")).to_be_visible()
    expect(popup.locator(".print-title")).to_be_visible()
    expect(popup.locator("#printBtn")).to_be_visible()
    popup.close()
    close_detail(page)


@pytest.mark.scn("42. Закрытие карточки")
def test_42_close_card(page, test_engine):
    """closeDetail() закрывает карточку."""
    _open(page, test_engine["id"])
    close_detail(page)
    page.wait_for_selector("#detailModal", state="hidden", timeout=5000)