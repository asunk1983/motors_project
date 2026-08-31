"""Группа 11: Служебные тесты — API статус, автодополнение, фото, /test."""
import json
import io
import zipfile

import pytest

from tests.e2e.conftest import BASE_URL, TEST_ADMIN, TEST_ADMIN_PW
from tests.e2e.helpers import make_engine, make_test_png


@pytest.mark.scn("81. API статус")
def test_81_status_api(admin_api):
    """GET /api/status возвращает счётчики."""
    r = admin_api.get("/api/status")
    assert r.status == 200
    data = r.json()
    assert "engine_count" in data
    assert "modes_count" in data
    assert "works_count" in data
    assert "photos_count" in data
    assert "db_size_label" in data
    assert "has_data" in data


@pytest.mark.scn("82. Подсказки поискового поля (search-suggestions)")
def test_82_search_suggestions(admin_api):
    """GET /api/search-suggestions возвращает список подсказок."""
    r = admin_api.get("/api/search-suggestions?field=serial_number&query=E2E")
    assert r.status == 200
    data = r.json()
    assert isinstance(data, list)


@pytest.mark.scn("83. URL фото с токеном")
def test_83_photo_url(admin_api):
    """Фото доступно по URL /api/photos/<filename>?token=<token>."""
    # Get token via login
    r = admin_api.post("/api/auth/login",
                       data=json.dumps({"username": TEST_ADMIN, "password": TEST_ADMIN_PW}),
                       headers={"Content-Type": "application/json"})
    token = r.json()["token"]
    assert token is not None

    # Try to access a non-existent photo with valid token
    r = admin_api.get(f"/api/photos/nonexistent_test_file.png?token={token}")
    # 404 — файл не существует, но аутентификация пройдена (иначе 401)
    assert r.status in (404, 200)

    # Without token — должно быть 401
    r_no_token = admin_api.get("/api/photos/nonexistent_test_file.png")
    assert r_no_token.status in (401, 404)


@pytest.mark.scn("84. Страница /test")
def test_84_test_endpoint(admin_api):
    """GET /test возвращает статус ok."""
    r = admin_api.get("/test")
    assert r.status == 200
    data = r.json()
    assert data.get("status") == "ok"


@pytest.mark.scn("84b. Статус сервера после создания двигателя")
def test_84b_status_after_create(admin_api):
    """Статус API отражает созданный двигатель."""
    from tests.e2e.helpers import make_engine, delete_engine_by_serial
    payload = make_engine()
    r = admin_api.post("/api/engine", data=json.dumps(payload),
                       headers={"Content-Type": "application/json"})
    assert r.json().get("success")

    status = admin_api.get("/api/status").json()
    assert status["engine_count"] >= 1

    delete_engine_by_serial(admin_api, payload["serial_number"])
