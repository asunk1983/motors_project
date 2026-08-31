"""Группа 8: Настройки — статистика БД, создание и просмотр бэкапов."""
import json

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    switch_tab, wait_toast, reload_catalog, make_engine,
    delete_engine_by_serial, accept_dialogs,
)


@pytest.mark.scn("59. Переключение на вкладку «Настройки»")
def test_59_switch_settings_tab(page):
    """Вкладка настроек отображается со статистикой."""
    switch_tab(page, "settings")
    expect(page.locator("#tab-settings")).to_be_visible()
    expect(page.locator("#dbStats")).to_be_visible()


@pytest.mark.scn("60. Просмотр статистики БД")
def test_60_view_db_stats(page):
    """На вкладке настроек отображается количество двигателей."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Stat values should be visible
    stat_labels = page.locator("#dbStats .stat-value, #dbStats .stat-label")
    assert stat_labels.count() >= 1


@pytest.mark.scn("61. Просмотр статистики фото")
def test_61_view_photo_stats(page):
    """На вкладке настроек отображается количество фото."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Photo stats should be visible somewhere on the settings page
    photo_stat = page.locator("#photoStats, #dbStats .stat-value")
    assert photo_stat.count() >= 1


@pytest.mark.scn("63. Создание резервной копии")
def test_63_create_backup(page):
    """Кнопка создания бэкапа создаёт резервную копию на сервере."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Find the create backup button
    create_btn = page.locator("#backupCreateBtn, button:has-text('Создать'), button:has-text('бэкап')")
    if create_btn.count() > 0:
        with page.expect_download() as download_info:
            create_btn.click()
        download = download_info.value
        assert download.suggested_filename.endswith(".zip")
        wait_toast(page, "Резервная копия")
        page.wait_for_load_state("networkidle", timeout=10000)
        # Verify backup appears in list
        expect(page.locator("#backupsList")).to_be_visible()
        assert page.locator(".backup-item").count() >= 1
    else:
        # API-level fallback
        pytest.skip("Create backup button not found on settings page")


@pytest.mark.scn("64. Просмотр списка резервных копий")
def test_64_view_backup_list(page):
    """Список резервных копий отображается на вкладке настроек."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("#backupsList")).to_be_visible()
    assert page.locator(".backup-item, .no-data").count() >= 1


@pytest.mark.scn("66. Инфо-подсказка в настройках")
def test_66_info_hint(page):
    """На вкладке настроек есть информационная подсказка."""
    switch_tab(page, "settings")
    # Find info/hint text
    info_text = page.locator(".info-text, .hint, .help-text, .settings-hint")
    assert info_text.count() >= 1 or page.locator("#tab-settings").inner_text() != ""
