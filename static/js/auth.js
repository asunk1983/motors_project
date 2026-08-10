// static/js/auth.js — клиентская часть авторизации (opaque-token).
// Токен хранится в localStorage и шлётся в заголовке Authorization: Bearer.

const AUTH_TOKEN_KEY = 'motors_auth_token';
const AUTH_USER_KEY = 'motors_auth_user';

function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY) || '';
}

function setAuthToken(token, user) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user || {}));
}

function clearAuth() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
}

function getAuthUser() {
    try {
        return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || '{}');
    } catch (e) {
        return {};
    }
}

// Возвращает URL фото с токеном в query-параметре ?token=..., чтобы
// браузер мог загрузить его в <img>/<video> (заголовок Authorization
// браузер в тег <img> добавить не может). Только если токен есть.
function authPhotoUrl(path) {
    const token = getAuthToken();
    if (!token) return path;
    const sep = path.indexOf('?') === -1 ? '?' : '&';
    return path + sep + 'token=' + encodeURIComponent(token);
}

// Обёртка над fetch: подставляет Bearer-токен и при 401 выкидывает на логин.
async function apiFetch(url, options = {}) {
    const token = getAuthToken();
    const headers = Object.assign({}, options.headers || {});
    if (token) headers['Authorization'] = 'Bearer ' + token;
    // Не перезаписываем Content-Type, если тело — FormData (браузер сам
    // проставит boundary).
    if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    let resp;
    try {
        resp = await fetch(url, Object.assign({}, options, { headers }));
    } catch (e) {
        throw new Error('Сетевая ошибка: ' + (e && e.message ? e.message : 'не удалось выполнить запрос'));
    }

    if (resp.status === 401) {
        // Токен недействителен/отозван — чистим и показываем логин.
        clearAuth();
        showLoginScreen();
        throw new Error('Требуется авторизация');
    }

    return resp;
}

async function parseJsonResponse(resp) {
    const contentType = resp.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        return resp.json();
    }
    const text = await resp.text();
    if (!text) {
        return { error: 'Пустой ответ сервера' };
    }
    try {
        return JSON.parse(text);
    } catch (e) {
        return { error: text.slice(0, 300) };
    }
}

// Убирает экран загрузки после того, как authInit() определился с
// состоянием (логин или уже загруженный интерфейс). Идемпотентна —
// повторные вызовы (например, showLoginScreen() после logout) безопасны.
function hideAppLoadingOverlay() {
    const overlay = document.getElementById('appLoadingOverlay');
    if (!overlay) return;
    overlay.classList.add('overlay-hidden');
    setTimeout(() => overlay.remove(), 350);
}

// ----- Экран логина / регистрации -----

function ensureLoginScreen() {
    if (document.getElementById('login-overlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'login-overlay';
    overlay.innerHTML = `
        <div class="login-card">
            <div class="login-brand"><span class="icon icon-settings"></span> Паспорта двигателей</div>
            <div class="login-hint">Доступ только для сотрудников. Учётные записи выдаёт администратор.</div>
            <form id="login-form" class="login-form">
                <label>Логин
                    <input type="text" id="login-username" autocomplete="username" required>
                </label>
                <label>Пароль
                    <input type="password" id="login-password" autocomplete="current-password" required>
                </label>
                <div class="login-error" id="login-error"></div>
                <button type="submit" class="login-submit">Войти</button>
            </form>
        </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        const errEl = document.getElementById('login-error');
        errEl.textContent = '';
        try {
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await parseJsonResponse(resp);
            if (!resp.ok) {
                errEl.textContent = data.error || 'Ошибка входа';
                return;
            }
            setAuthToken(data.token, data.user);
            hideLoginScreen();
            onLoggedIn();
        } catch (err) {
            errEl.textContent = err && err.message ? err.message : 'Сетевая ошибка';
        }
    });
}

function showLoginScreen() {
    hideAppLoadingOverlay();
    ensureLoginScreen();
    document.getElementById('login-overlay').style.display = 'flex';
}

function hideLoginScreen() {
    const el = document.getElementById('login-overlay');
    if (el) el.style.display = 'none';
}

// Вызывается после успешного логина (обновляет UI, права, списки).
function onLoggedIn() {
    hideAppLoadingOverlay();
    applyRoleUI();
    if (typeof loadEngines === 'function') loadEngines();
    if (typeof updateStats === 'function') updateStats();
    if (typeof loadChangelog === 'function') loadChangelog();
    if (typeof loadWishlist === 'function') loadWishlist();
    if ((getAuthUser().role === 'admin' || getAuthUser().role === 'superadmin') && typeof loadAdminUsers === 'function') loadAdminUsers();
}

function applyRoleUI() {
    const user = getAuthUser();
    const isAdmin = user.role === 'admin' || user.role === 'superadmin';
    const isReader = user.role === 'reader';
    // Единая метка на body — все кнопки записи (см. .write-action в
    // style.css) скрываются одним CSS-правилом от неё, а не разбросанными
    // по коду проверками роли в каждом месте рендера.
    document.body.classList.toggle('role-reader', isReader);

    const adminTab = document.querySelector('.tab-btn[data-tab="admin"]');
    if (adminTab) adminTab.style.display = isAdmin ? '' : 'none';
    // Вкладка "Импорт" — только для администрататора (обычные пользователи
    // не должны массово заливать/очищать БД).
    const importTab = document.querySelector('.tab-btn[data-tab="import"]');
    if (importTab) importTab.style.display = isAdmin ? '' : 'none';
    // Вкладка "Настройки" — read-only роли в ней делать нечего, там нет
    // ничего, кроме операций записи.
    const settingsTab = document.querySelector('.tab-btn[data-tab="settings"]');
    if (settingsTab) settingsTab.style.display = isReader ? 'none' : '';

    // Восстанавливаем вкладку, на которой пользователь был до перезагрузки
    // страницы (см. catalog.js::switchTab). Делаем это здесь, а не раньше:
    // видимость вкладок admin/import определяется выше в этой же функции,
    // и восстанавливать пользователя на вкладку, которая ему не положена
    // по роли, нельзя.
    restoreActiveTab();

    // Обновляем кнопку выхода и имя пользователя в топбаре.
    const userNameEl = document.getElementById('userName');
    if (userNameEl) {
        userNameEl.textContent = user.username || '';
    }
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.style.display = 'inline-flex';
        logoutBtn.addEventListener('click', logout);
    }

    // Бейдж пользователя в сайдбаре (для админки).
    let badge = document.getElementById('auth-user-badge');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'auth-user-badge';
        badge.className = 'auth-user-badge';
        const sidebar = document.querySelector('.sidebar-stats');
        if (sidebar) sidebar.parentNode.insertBefore(badge, sidebar.nextSibling);
    }
    const roleLabel = user.role === 'superadmin' ? 'суперадмин'
        : user.role === 'admin' ? 'админ'
        : user.role === 'reader' ? 'читатель'
        : 'пользователь';
    badge.innerHTML = `<span class="icon icon-person"></span> ${escapeHtml(user.username || '')} <span class="auth-role">${roleLabel}</span> <button id="logout-btn" class="logout-btn">Выйти</button>`;
    const lb = document.getElementById('logout-btn');
    if (lb) lb.addEventListener('click', logout);
    // Опции admin/superadmin в #newRole видимы только суперадмину.
    const newRole = document.getElementById('newRole');
    if (newRole) {
        const adminOpt = newRole.querySelector('option[value="admin"]');
        const superOpt = newRole.querySelector('option[value="superadmin"]');
        if (adminOpt) adminOpt.style.display = user.role === 'superadmin' ? '' : 'none';
        if (superOpt) superOpt.style.display = user.role === 'superadmin' ? '' : 'none';
    }
}

function restoreActiveTab() {
    let saved;
    try { saved = localStorage.getItem('motors_active_tab'); } catch (e) { saved = null; }
    if (!saved) return;
    const btn = document.querySelector(`.tab-btn[data-tab="${saved}"]`);
    if (!btn || btn.style.display === 'none') return;
    if (typeof switchTab === 'function') switchTab(saved);
}

async function logout() {
    try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch (e) { /* игнорируем — токен всё равно чистим */ }
    clearAuth();
    showLoginScreen();
}

function authInit() {
    if (getAuthToken()) {
        // Есть сохранённый токен — проверим его валидность.
        apiFetch('/api/auth/me').then(parseJsonResponse).then(data => {
            if (data && data.username) {
                setAuthToken(getAuthToken(), data);
                hideLoginScreen();
                onLoggedIn();
            } else {
                clearAuth();
                showLoginScreen();
            }
        }).catch(() => {
            clearAuth();
            showLoginScreen();
        });
    } else {
        showLoginScreen();
    }
}

// ----- Админка: управление пользователями -----

function showAddUserForm() {
    const f = document.getElementById('addUserForm');
    f.style.display = f.style.display === 'none' ? '' : 'none';
}

async function loadAdminUsers() {
    const list = document.getElementById('adminUsersList');
    if (!list) return;
    try {
        const resp = await apiFetch('/api/auth/admin/users');
        const users = await parseJsonResponse(resp);
        if (!resp.ok) {
            list.innerHTML = `<div class="no-data">${escapeHtml(users.error || 'Ошибка')}</div>`;
            return;
        }
        if (!Array.isArray(users) || !users.length) {
            list.innerHTML = '<div class="no-data">Нет пользователей</div>';
            return;
        }
        const me = getAuthUser();
        list.innerHTML = `<table class="data-table admin-users-table">
            <thead><tr><th>ID</th><th>Логин</th><th>Роль</th><th>Активных сессий</th><th>Создан</th><th>Последний вход</th><th>Последнее изменение</th><th></th></tr></thead>
            <tbody>
            ${users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${escapeHtml(u.username)}</td>
                    <td>${u.role === 'superadmin' ? '<span class="icon icon-workspace-premium"></span> суперадмин' : (u.role === 'admin' ? '<span class="icon icon-shield"></span> админ' : (u.role === 'reader' ? '<span class="icon icon-visibility"></span> читатель' : 'пользователь'))}</td>
                    <td>${u.active_sessions || 0}</td>
                    <td>${escapeHtml((u.created_at || '').slice(0, 10))}</td>
                    <td>${escapeHtml((u.last_login || '').slice(0, 10))}</td>
                    <td>${escapeHtml((u.last_edit || '').slice(0, 10))}</td>
                    <td class="col-action-narrow">
                        <button class="btn btn-warning btn-sm" onclick="adminRevokeUser(${u.id})" title="Сбросить все сессии"><span class="icon icon-sync"></span></button>
                        <button class="btn btn-secondary btn-sm" onclick="promptChangePassword(${u.id}, '${escapeHtml(u.username)}')" title="Сменить пароль"><span class="icon icon-lock"></span></button>
                        ${u.id !== me.id && (me.role === 'superadmin' || u.role === 'user') ? `<button class="btn btn-danger btn-sm" onclick="adminDeleteUser(${u.id})"><span class="icon icon-delete"></span></button>` : ''}
                    </td>
                </tr>`).join('')}
            </tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = `<div class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</div>`;
    }
}

function promptChangePassword(userId, username) {
    const password = prompt(`Новый пароль для ${username || 'пользователя'}:`);
    if (!password) return;
    if (password.length < 6) {
        showToast('Пароль должен быть не короче 6 символов', 'error');
        return;
    }
    adminChangePassword(userId, password);
}

async function adminChangePassword(userId, password) {
    try {
        const resp = await apiFetch(`/api/auth/admin/users/${userId}/password`, {
            method: 'POST',
            body: JSON.stringify({ password })
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка смены пароля', 'error');
            return;
        }
        showToast('Пароль изменён', 'success');
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function adminCreateUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;
    if (!username || !password) {
        showToast('Укажите логин и пароль', 'error');
        return;
    }
    try {
        const resp = await apiFetch('/api/auth/admin/users', {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания', 'error');
            return;
        }
        document.getElementById('newUsername').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('addUserForm').style.display = 'none';
        showToast('Пользователь создан', 'success');
        loadAdminUsers();
    } catch (e) {
        showToast('Сетевая ошибка', 'error');
    }
}

async function adminDeleteUser(id) {
    if (!confirm('Удалить пользователя? Это также отзовёт все его сессии.')) return;
    try {
        const resp = await apiFetch(`/api/auth/admin/users/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка', 'error');
            return;
        }
        showToast('Пользователь удалён', 'success');
        loadAdminUsers();
    } catch (e) {
        showToast('Сетевая ошибка', 'error');
    }
}

async function adminRevokeUser(id) {
    try {
        const resp = await apiFetch(`/api/auth/admin/users/${id}/revoke`, { method: 'POST' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка', 'error');
            return;
        }
        showToast('Все сессии пользователя сброшены', 'success');
        loadAdminUsers();
    } catch (e) {
        showToast('Сетевая ошибка', 'error');
    }
}
