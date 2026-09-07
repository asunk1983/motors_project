// static/js/info.js — вкладка "Инфо" (навигация, лог изменений, пожелания).
// Требует: common.js (escapeHtml, _formatRuDate, _formatBackupDate, showToast, apiFetch)

// ===== ВКЛАДКА "ИНФО": лог изменений + пожелания =====
let changelogEntries = [];
let wishlistItems = [];

function switchInfoSubtab(name) {
    const changelogBtn = document.getElementById('infoSubtabChangelogBtn');
    const wishlistBtn = document.getElementById('infoSubtabWishlistBtn');
    const systemBtn = document.getElementById('infoSubtabSystemBtn');
    if (changelogBtn) changelogBtn.className = 'btn btn-sm ' + (name === 'changelog' ? 'btn-primary' : 'btn-secondary');
    if (wishlistBtn) wishlistBtn.className = 'btn btn-sm ' + (name === 'wishlist' ? 'btn-primary' : 'btn-secondary');
    if (systemBtn) systemBtn.className = 'btn btn-sm ' + (name === 'system' ? 'btn-primary' : 'btn-secondary');
    const changelogPane = document.getElementById('infoSubtab-changelog');
    const wishlistPane = document.getElementById('infoSubtab-wishlist');
    const systemPane = document.getElementById('infoSubtab-system');
    if (changelogPane) changelogPane.classList.toggle('active', name === 'changelog');
    if (wishlistPane) wishlistPane.classList.toggle('active', name === 'wishlist');
    if (systemPane) systemPane.classList.toggle('active', name === 'system');
}

function loadInfoTab() {
    loadChangelog();
    loadWishlist();
    loadSystemInfo();
}

function loadSystemInfo() {
    apiFetch('/api/status')
        .then(r => r.json())
        .then(data => {
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = (val === undefined || val === null || val === '') ? '—' : val;
            };
            set('sysAppVersion', data.app_version);
            set('sysPythonVersion', data.python_version);
            set('sysFlaskVersion', data.flask_version);
            set('sysSqliteVersion', data.sqlite_version);
        })
        .catch(() => {});
}

// ---- Лог изменений ----
function loadChangelog() {
    apiFetch('/api/changelog')
        .then(r => r.json())
        .then(data => {
            changelogEntries = Array.isArray(data) ? data : [];
            renderChangelog();
        })
        .catch(() => showToast('Не удалось загрузить лог изменений', 'error', 'icon-cancel'));
}


function renderChangelog() {
    const wrap = document.getElementById('changelogList');
    if (!wrap) return;
    if (changelogEntries.length === 0) {
        wrap.innerHTML = '<div class="no-data">Пока нет записей</div>';
        return;
    }
    // Сервер уже отдаёт записи отсортированными по entry_date DESC, id DESC —
    // здесь только группируем подряд идущие записи с одинаковой датой.
    const groups = [];
    let lastDate = null;
    changelogEntries.forEach(e => {
        if (e.entry_date !== lastDate) {
            groups.push({ date: e.entry_date, items: [] });
            lastDate = e.entry_date;
        }
        groups[groups.length - 1].items.push(e);
    });
    wrap.innerHTML = groups.map(g => `
        <div class="changelog-group">
            <div class="changelog-date">${_formatRuDate(g.date)}</div>
            <ul class="changelog-items">
                ${g.items.map(e => `
                    <li class="changelog-item">
                        <span class="changelog-text">${escapeHtml(e.text)}</span>
                    </li>
                `).join('')}
            </ul>
        </div>
    `).join('');
}

// ---- Пожелания ----
function loadWishlist() {
    apiFetch('/api/wishlist')
        .then(r => r.json())
        .then(data => {
            wishlistItems = Array.isArray(data) ? data : [];
            renderWishlist();
        })
        .catch(() => showToast('Не удалось загрузить пожелания', 'error', 'icon-cancel'));
}

function renderWishlist() {
    const wrap = document.getElementById('wishlistList');
    if (!wrap) return;
    if (wishlistItems.length === 0) {
        wrap.innerHTML = '<div class="no-data">Список пуст</div>';
        return;
    }
    wrap.innerHTML = `<ul class="wishlist-items">${wishlistItems.map(item => `
        <li class="wishlist-item${item.done ? ' done' : ''}">
            <input type="checkbox" ${item.done ? 'checked' : ''} onchange="toggleWishlistItem(${item.id}, this.checked)">
            <span class="wishlist-text">${escapeHtml(item.text)}</span>
            <span class="wishlist-meta">${_formatBackupDate(item.created_at)} — ${escapeHtml(item.author || 'неизвестно')}</span>
            <button type="button" class="link-btn wishlist-delete" title="Удалить пожелание" onclick="deleteWishlistItem(${item.id})"><span class="icon icon-close"></span></button>
        </li>
    `).join('')}</ul>`;
}

function addWishlistItem() {
    const input = document.getElementById('wishlistTextInput');
    const text = input.value.trim();
    if (!text) {
        showToast('Введите текст пожелания', 'warning', 'icon-warning');
        return;
    }
    apiFetch('/api/wishlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            input.value = '';
            loadWishlist();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function toggleWishlistItem(id, done) {
    apiFetch(`/api/wishlist/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                loadWishlist(); // откатить чекбокс, если backend отказал
                return;
            }
            const item = wishlistItems.find(i => i.id === id);
            if (item) item.done = done;
            renderWishlist();
        })
        .catch(e => { showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'); loadWishlist(); });
}

function deleteWishlistItem(id) {
    if (!confirm('Удалить это пожелание?')) return;
    apiFetch(`/api/wishlist/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            loadWishlist();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter') return;
    if (e.target && e.target.id === 'wishlistTextInput') { e.preventDefault(); addWishlistItem(); }
});
