"""Группа 1: Аутентификация.

Сценарии (docs/e2e_scenarios.md → «Аутентификация»):
  1. Вход в систему
  2. Выход / logout
  3. Проверка токена при загрузке страницы (валидный / невалидный)
  4. Редирект на экран входа при 401 от apiFetch
  5. Вкладки «Импорт» и «Админ» — только для админа
  6. Список пользователей (таблица, колонки)
  7. Создание пользователя
  8. Смена пароля
  9. Сброс всех сессий пользователя (revoke)
 10. Удаление пользователя
"""
import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import (
    TEST_ADMIN, TEST_ADMIN_PW, TEST_USER, TEST_USER_PW,
    login_ui, wait_toast, prompt_accept, get_user_id,
    delete_user_by_username, open_admin_tab, accept_dialogs,
)

AUTH = "motors_auth_token"


# 1
@pytest.mark.scn("1. Вход в систему")
def test_01_login_success(fresh_page):
    login_ui(fresh_page, TEST_ADMIN, TEST_ADMIN_PW)
    expect(fresh_page.locator("#login-overlay")).to_be_hidden()
    # Имя пользователя в топбаре. Бейдж #auth-user-badge удалён из auth.js
    # (он вставлялся только при наличии .sidebar-stats, которого нет в
    # шаблоне), поэтому проверяем #userName — реальный элемент топбара.
    expect(fresh_page.locator("#userName")).to_be_visible()
    user_name = fresh_page.locator("#userName").inner_text()
    assert TEST_ADMIN in user_name, "в топбаре должно быть имя вошедшего: " + user_name
    token = fresh_page.evaluate("localStorage.getItem('motors_auth_token')")
    assert token, "токен должен быть в localStorage"
    expect(fresh_page.locator("#tab-catalog")).to_be_visible()


# 2
@pytest.mark.scn("2. Выход (logout)")
def test_02_logout(fresh_page):
    login_ui(fresh_page, TEST_ADMIN, TEST_ADMIN_PW)
    fresh_page.click("#logoutBtn")
    expect(fresh_page.locator("#login-overlay")).to_be_visible(timeout=15000)
    token = fresh_page.evaluate("localStorage.getItem('motors_auth_token')")
    assert not token, "токен должен быть удалён после logout"


# 3a (валидный токен)
@pytest.mark.scn("3. Проверка токена при загрузке (валидный)")
def test_03_valid_token_on_reload(fresh_page):
    login_ui(fresh_page, TEST_ADMIN, TEST_ADMIN_PW)
    expect(fresh_page.locator("#userName")).to_be_visible()
    fresh_page.reload()
    fresh_page.wait_for_load_state("networkidle", timeout=15000)
    expect(fresh_page.locator("#login-overlay")).to_be_hidden()
    expect(fresh_page.locator("#userName")).to_be_visible()


# 3b (невалидный токен)
@pytest.mark.scn("3. Проверка токена при загрузке (невалидный)")
def test_03b_invalid_token_on_reload(fresh_page):
    login_ui(fresh_page, TEST_ADMIN, TEST_ADMIN_PW)
    fresh_page.evaluate("localStorage.setItem('motors_auth_token','INVALID_TOKEN')")
    fresh_page.reload()
    fresh_page.wait_for_load_state("networkidle", timeout=15000)
    expect(fresh_page.locator("#login-overlay")).to_be_visible(timeout=10000)


# 4
@pytest.mark.scn("4. Редирект на вход при 401 от apiFetch")
def test_04_401_redirect_to_login(page):
    # page — аутентифицированный admin. Портим токен в этом контексте.
    page.evaluate("localStorage.setItem('motors_auth_token','GARBAGE')")
    res = page.evaluate(
        "async () => { try { const r = await apiFetch('/api/auth/me'); return {ok: r.ok}; } "
        "catch(e){ return {threw: (e && e.message) ? e.message : 'err'}; } }"
    )
    assert res.get("threw"), "apiFetch должен бросить при 401: " + str(res)
    expect(page.locator("#login-overlay")).to_be_visible(timeout=10000)
    # токен должен быть вычищен clearAuth()
    token = page.evaluate("localStorage.getItem('motors_auth_token')")
    assert not token


# 5a (admin)
@pytest.mark.scn("5. Вкладки Импорт/Админ видны для админа")
def test_05_admin_tabs_visible_for_admin(page):
    it = page.locator('.tab-btn[data-tab="import"]')
    ad = page.locator('.tab-btn[data-tab="admin"]')
    expect(it).to_be_visible()
    expect(ad).to_be_visible()


# 5b (user)
@pytest.mark.scn("5. Вкладки Импорт/Админ скрыты для пользователя")
def test_05b_admin_tabs_hidden_for_user(fresh_page):
    login_ui(fresh_page, TEST_USER, TEST_USER_PW)
    # Роль в UI больше не выводится (бейдж #auth-user-badge удалён из auth.js),
    # поэтому проверяем пользователя по имени в топбаре, а скрытость
    # admin-инструментов — по самим вкладкам (ниже).
    expect(fresh_page.locator("#userName")).to_be_visible()
    user_name = fresh_page.locator("#userName").inner_text()
    assert TEST_USER in user_name, "в топбаре должно быть имя вошедшего: " + user_name
    expect(fresh_page.locator('.tab-btn[data-tab="import"]')).not_to_be_visible()
    expect(fresh_page.locator('.tab-btn[data-tab="admin"]')).not_to_be_visible()


# 6
@pytest.mark.scn("6. Список пользователей")
def test_06_list_users(page, admin_api):
    open_admin_tab(page)
    tbl = page.locator(".admin-users-table")
    expect(tbl).to_be_visible()
    header = tbl.locator("thead").inner_text()
    for col in ["ID", "Логин", "Роль", "Активных сессий", "Создан"]:
        assert col in header, "Колонка отсутствует в заголовке: " + col
    body = tbl.locator("tbody").inner_text()
    assert "admin" in body
    assert TEST_ADMIN in body
    assert TEST_USER in body
    # Администраторы (в т.ч. self) не имеют кнопки удаления
    for uname in ("admin", TEST_ADMIN):
        row = tbl.locator("tbody tr", has_text=uname)
        expect(row.locator("button.btn-danger")).to_have_count(0)


# 7
@pytest.mark.scn("7. Создание пользователя")
def test_07_create_user(page, admin_api):
    uname = "e2e_u_" + uuid.uuid4().hex[:8]
    pwd = "Pass1234"
    try:
        open_admin_tab(page)
        page.click("button:has-text('Добавить пользователя')")
        form = page.locator("#addUserForm")
        expect(form).to_be_visible()
        form.locator("#newUsername").fill(uname)
        form.locator("#newPassword").fill(pwd)
        form.locator("#newRole").select_option(value="user")
        form.locator("button:has-text('Создать')").click()
        wait_toast(page, "Пользователь создан")
        # появился в таблице
        page.wait_for_timeout(500)
        expect(page.locator(".admin-users-table tbody tr", has_text=uname)).to_be_visible()
        # проверка через API
        uid = get_user_id(admin_api, uname)
        assert uid is not None, "пользователь должен быть создан в БД/файле"
    finally:
        delete_user_by_username(admin_api, uname)


# 8
def _change_password_via_ui(page, user_id, new_password):
    """Сменить пароль пользователя через UI и дождаться ответа ИМЕННО этого POST.

    Опираться на toast нельзя: он живёт ~3.3с, поэтому второй wait_toast()
    в тесте «успевал» на ещё видимом тосте от первой смены пароля, тест уходил
    дальше, не дождавшись второй операции, и падал на проверке старого пароля.
    Ждём сетевой ответ конкретного запроса + перед действием убеждаемся, что
    предыдущий тост уже исчез (тогда и последующий wait_toast относится к
    текущей операции, а не к предыдущей).
    """
    expected_text = page.locator(".toast").get_by_text("Пароль изменён", exact=False)
    expect(expected_text).to_be_hidden(timeout=10000)
    prompt_accept(page, new_password)
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/api/auth/admin/users/%d/password" % user_id)
    ) as resp_info:
        page.locator(".admin-users-table tbody tr", has_text=TEST_USER) \
            .locator("button[title='Сменить пароль']").click()
    assert resp_info.value.status == 200, \
        "смена пароля: HTTP %s" % resp_info.value.status
    wait_toast(page, "Пароль изменён")
    return resp_info.value


@pytest.mark.scn("8. Смена пароля")
def test_08_change_password(page, admin_api):
    new_pw = "Ch_" + uuid.uuid4().hex[:8] + "_12"
    open_admin_tab(page)
    uid = get_user_id(admin_api, TEST_USER)
    assert uid is not None, "тестовый пользователь должен существовать"

    _change_password_via_ui(page, uid, new_pw)

    # вход под новым паролем
    r = admin_api.post("/api/auth/login",
                       data='{"username":"' + TEST_USER + '","password":"' + new_pw + '"}',
                       headers={"Content-Type": "application/json"})
    assert r.status == 200, "логин под новым паролем должен работать"

    # restore original password
    _change_password_via_ui(page, uid, TEST_USER_PW)
    r2 = admin_api.post("/api/auth/login",
                        data='{"username":"' + TEST_USER + '","password":"' + TEST_USER_PW + '"}',
                        headers={"Content-Type": "application/json"})
    assert r2.status == 200, "пароль должен быть восстановлен"


# 9
@pytest.mark.scn("9. Сброс всех сессий пользователя")
def test_09_revoke_user_sessions(page, admin_api):
    # создаём активную сессию для TEST_USER
    r = admin_api.post("/api/auth/login",
                       data='{"username":"' + TEST_USER + '","password":"' + TEST_USER_PW + '"}',
                       headers={"Content-Type": "application/json"})
    assert r.status == 200
    open_admin_tab(page)

    def active_sessions(uname=TEST_USER):
        users = admin_api.get("/api/auth/admin/users").json()
        for u in users:
            if u.get("username") == uname:
                return u.get("active_sessions", 0)
        return -1

    before = active_sessions()
    assert before >= 1, "должна быть хотя бы одна активная сессия"

    row = page.locator(".admin-users-table tbody tr", has_text=TEST_USER)
    row.locator("button[title='Сбросить все сессии']").click()
    wait_toast(page, "Все сессии пользователя сброшены")

    after = active_sessions()
    assert after == 0, f"после revoke активных сессий должно быть 0, а не {after}"


# 10
@pytest.mark.scn("10. Удаление пользователя")
def test_10_delete_user(page, admin_api):
    uname = "del_" + uuid.uuid4().hex[:8]
    pwd = "Pass1234"
    open_admin_tab(page)

    page.click("button:has-text('Добавить пользователя')")
    form = page.locator("#addUserForm")
    form.locator("#newUsername").fill(uname)
    form.locator("#newPassword").fill(pwd)
    form.locator("button:has-text('Создать')").click()
    wait_toast(page, "Пользователь создан")
    page.wait_for_timeout(500)
    expect(page.locator(".admin-users-table tbody tr", has_text=uname)).to_be_visible()

    # удаляем через UI 🗑 + confirm
    accept_dialogs(page)
    row = page.locator(".admin-users-table tbody tr", has_text=uname)
    row.locator("button.btn-danger").click()
    wait_toast(page, "Пользователь удалён")

    # исчез со страницы
    page.wait_for_timeout(500)
    expect(page.locator(".admin-users-table tbody tr", has_text=uname)).to_have_count(0)
    # и в БД/файле
    assert get_user_id(admin_api, uname) is None
