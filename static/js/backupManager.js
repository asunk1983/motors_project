// static/js/backupManager.js — резервные копии + вкладка "Инфо" (лог изменений, пожелания).
// Требует: common.js (escapeHtml, _formatRuDate, showToast)

// ===== РЕЗЕРВНЫЕ КОПИИ (только вручную — без автобэкапов) =====
function _formatBackupDate(iso) {
    // Экранируем в ЛЮБОЙ ветке, не только fallback — см. аналогичный фикс
    // _formatRuDate() в лог изменений: сейчас backups/ пополняется только
    // доверенным _build_backup_zip_bytes() на бэкенде, но если этот
    // инвариант когда-нибудь сломается (например, появится путь, кладущий
    // туда содержимое из загруженного пользователем файла), рендер уже
    // будет безопасен по умолчанию, а не только "пока никто не завёл
    // такой путь".
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return escapeHtml(iso);
    return escapeHtml(d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }));
}

function _formatBackupSize(bytes) {
    if (!bytes && bytes !== 0) return '—';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function loadBackupsList() {
    apiFetch('/api/backup/list')
        .then(r => r.json())
        .then(data => {
            renderBackupsList(Array.isArray(data) ? data : []);
        })
        .catch(() => {
            const wrap = document.getElementById('backupsList');
            if (wrap) wrap.innerHTML = '<div class="no-data">Не удалось загрузить список резервных копий</div>';
        });
}

function renderBackupsList(backups) {
    const wrap = document.getElementById('backupsList');
    if (!wrap) return;
    if (backups.length === 0) {
        wrap.innerHTML = '<div class="no-data">Резервных копий ещё нет</div>';
        return;
    }
    wrap.innerHTML = `<ul class="backups-items">${backups.map(b => {
        // JS-строковое экранирование для onclick (одинарные кавычки внутри
        // '${...}') — НЕ escapeHtml(), это разные контексты. escapeHtml()
        // экранирует HTML-сущности (годится для видимого текста/атрибутов),
        // но апостроф внутри имени файла всё равно прорвал бы одинарные
        // кавычки JS-аргумента ПОСЛЕ того, как браузер раскодирует HTML-
        // сущности из атрибута обратно в исходный символ — ровно тот же
        // баг, что уже был с p.filename/p.path в галерее фото (см.
        // safeFilename там). Сейчас имя файла бэкапа всегда генерируется
        // на бэкенде по фиксированному шаблону без опасных символов, но
        // полагаться на этот инвариант навсегда не буду.
        const safeFilename = b.filename.replace(/'/g, "\\'");
        return `
        <li class="backup-item">
            <div class="backup-item-info">
                <span class="backup-item-date">${_formatBackupDate(b.created_at)}</span>
                <span class="backup-item-meta">Двигателей: ${b.engine_count ?? '—'} · Фото: ${b.photos_count_files ?? '—'} · ${_formatBackupSize(b.size)}</span>
            </div>
            <div class="backup-item-actions">
                <button type="button" class="btn btn-secondary btn-sm" onclick="downloadBackup('${safeFilename}')" title="Скачать на компьютер"><span class="icon icon-download"></span></button>
                <button type="button" class="btn btn-warning btn-sm" onclick="restoreServerBackup('${safeFilename}', ${b.engine_count ?? 0})" title="Восстановить"><span class="icon icon-restore"></span></button>
                <button type="button" class="btn btn-danger btn-sm" onclick="deleteBackupFile('${safeFilename}')" title="Удалить копию"><span class="icon icon-close"></span></button>
            </div>
        </li>
    `;
    }).join('')}</ul>`;
}

function createBackup() {
    showToast('Создаю резервную копию...', 'info', 'icon-progress-activity');
    apiFetch('/api/backup/create', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Ошибка создания резервной копии'); });
            }
            const disposition = response.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^"]+)"?/);
            const filename = match ? match[1] : `backup_${new Date().toISOString().slice(0, 10)}.zip`;
            return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            // Один клик — оба места: файл уже сохранён на сервере (это сделал
            // сам /api/backup/create), а тут только триггерим скачивание того
            // же самого архива на компьютер пользователя.
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast('Резервная копия сохранена на сервере и скачана', 'success', 'icon-check-circle');
            loadBackupsList();
        })
        .catch(e => showToast(e.message, 'error', 'icon-cancel'));
}

function downloadBackup(filename) {
    window.open(`/api/backup/download/${encodeURIComponent(filename)}`, '_blank');
}

function deleteBackupFile(filename) {
    if (!confirm('Удалить эту резервную копию с сервера? Файл, уже скачанный на компьютер (если скачивали), не пострадает.')) return;
    apiFetch(`/api/backup/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            loadBackupsList();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function restoreServerBackup(filename, engineCount) {
    if (!confirm(`Восстановить резервную копию от ${filename}?\n\nВ ней двигателей: ${engineCount}.\n\nТЕКУЩЕЕ состояние базы и фото будет ПОЛНОСТЬЮ заменено содержимым этой копии. Подстраховочная копия текущего состояния перед восстановлением НЕ создаётся. Продолжить?`)) return;
    showToast('Восстанавливаю из резервной копии...', 'info', 'icon-progress-activity');
    apiFetch(`/api/backup/restore/${encodeURIComponent(filename)}`, { method: 'POST' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            showToast('Восстановлено. Страница сейчас перезагрузится...', 'success', 'icon-check-circle');
            // Весь клиентский кэш (allEngines, currentEngineData и т.д.) теперь
            // относится к УЖЕ ЗАМЕНЁННЫМ данным — перезагрузка страницы дешевле
            // и надёжнее, чем вручную сбрасывать десяток переменных состояния.
            setTimeout(() => location.reload(), 1500);
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

document.getElementById('backupUploadInput')?.addEventListener('change', function() {
    const file = this.files && this.files[0];
    const nameEl = document.getElementById('backupUploadFileName');
    if (!file) return;
    if (nameEl) nameEl.textContent = file.name;

    const formData = new FormData();
    formData.append('backup', file);

    showToast('Проверяю файл резервной копии...', 'info', 'icon-progress-activity');
    apiFetch('/api/backup/inspect-upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(result => {
            this.value = '';
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            const m = result.manifest || {};
            const confirmed = confirm(
                `Загруженный файл похож на резервную копию.\n\n` +
                `Дата создания: ${_formatBackupDate(m.created_at)}\n` +
                `Двигателей: ${m.engine_count ?? '—'}\n` +
                `Фото: ${m.photos_count_files ?? '—'}\n\n` +
                `ТЕКУЩЕЕ состояние базы и фото будет ПОЛНОСТЬЮ заменено содержимым этого файла. ` +
                `Подстраховочная копия текущего состояния перед восстановлением НЕ создаётся. Восстановить именно этот файл?`
            );
            if (!confirmed) {
                showToast('Восстановление отменено', 'info');
                return;
            }
            showToast('Восстанавливаю из загруженного файла...', 'info', 'icon-progress-activity');
            return apiFetch('/api/backup/confirm-restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ staging_id: result.staging_id })
            })
                .then(r => r.json())
                .then(confirmResult => {
                    if (confirmResult.error) {
                        showToast(confirmResult.error, 'error', 'icon-cancel');
                        return;
                    }
                    showToast('Восстановлено. Страница сейчас перезагрузится...', 'success', 'icon-check-circle');
                    setTimeout(() => location.reload(), 1500);
                });
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
});


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
    const dateInput = document.getElementById('changelogDateInput');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().slice(0, 10);
    }
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
                        <button type="button" class="link-btn changelog-delete" title="Удалить запись" onclick="deleteChangelogEntry(${e.id})"><span class="icon icon-close"></span></button>
                    </li>
                `).join('')}
            </ul>
        </div>
    `).join('');
}

function addChangelogEntry() {
    const dateInput = document.getElementById('changelogDateInput');
    const textInput = document.getElementById('changelogTextInput');
    const text = textInput.value.trim();
    if (!text) {
        showToast('Введите текст записи', 'warning', 'icon-warning');
        return;
    }
    const date = dateInput.value || new Date().toISOString().slice(0, 10);
    apiFetch('/api/changelog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, text })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            textInput.value = '';
            loadChangelog();
            showToast('Запись добавлена в лог изменений', 'success', 'icon-check-circle');
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function deleteChangelogEntry(id) {
    if (!confirm('Удалить эту запись из лога изменений?')) return;
    apiFetch(`/api/changelog/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            loadChangelog();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
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
    if (e.target && e.target.id === 'changelogTextInput') { e.preventDefault(); addChangelogEntry(); }
    if (e.target && e.target.id === 'wishlistTextInput') { e.preventDefault(); addWishlistItem(); }
});