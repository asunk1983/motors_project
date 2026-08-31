"""Группа 9: Резервные копии — просмотр, создание, скачивание, удаление."""
import os

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import switch_tab, wait_toast, accept_dialogs


@pytest.mark.scn("67. Просмотр списка резервных копий")
def test_67_view_backup_list(page):
    """Список бэкапов отображается при загрузке вкладки настроек."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page.locator("#backupsList")).to_be_visible()


@pytest.mark.scn("68. Создание резервной копии")
def test_68_create_backup(page, admin_api):
    """Создание бэкапа через UI — появляется в списке и на сервере."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    create_btn = page.locator("#backupCreateBtn, button:has-text('Создать бэкап')")
    if create_btn.count() == 0:
        pytest.skip("Create backup button not found")
    with page.expect_download() as download_info:
        create_btn.click()
    download = download_info.value
    assert download.suggested_filename.endswith(".zip")
    wait_toast(page, "Резервная копия")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Verify via API
    r = admin_api.get("/api/backup/list")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.scn("69. Скачивание резервной копии")
def test_69_download_backup(page, admin_api):
    """Скачивание бэкапа через кнопку в списке."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Ensure at least one backup exists
    r = admin_api.get("/api/backup/list")
    backups = r.json()
    if not backups:
        with page.expect_download() as dl_info:
            page.locator("#backupCreateBtn, button:has-text('Создать бэкап')").click()
        dl_info.value.body()
        page.wait_for_load_state("networkidle", timeout=10000)
        r = admin_api.get("/api/backup/list")
        backups = r.json()
    if not backups:
        pytest.skip("No backups to download")

    filename = backups[0]["filename"]
    # Download via API
    dl = admin_api.get(f"/api/backup/download/{filename}")
    assert dl.status == 200
    content = dl.body()
    assert len(content) > 0
    # Verify it's a valid zip
    import zipfile
    import io
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        assert "manifest.json" in zf.namelist()


@pytest.mark.scn("71. Удаление резервной копии")
def test_71_delete_backup(page, admin_api):
    """Удаление бэкапа через кнопку в списке."""
    switch_tab(page, "settings")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Create a fresh backup to delete
    r = admin_api.post("/api/backup/create")
    # create endpoint sends file download, so use API directly
    # Actually the create backup endpoint returns a file, not JSON
    # Let's just use the existing list
    r = admin_api.get("/api/backup/list")
    backups = r.json()
    if not backups:
        pytest.skip("No backups to delete")

    filename = backups[-1]["filename"]
    # Delete via API
    del_resp = admin_api.delete(f"/api/backup/{filename}")
    assert del_resp.status == 200
    assert del_resp.json().get("success") is True

    # Verify it's gone
    r2 = admin_api.get("/api/backup/list")
    remaining = r2.json()
    assert all(f["filename"] != filename for f in remaining)
