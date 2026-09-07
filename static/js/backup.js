// static/js/backup.js — резервные копии.
// Требует: common.js (escapeHtml, showToast, apiFetch, _formatBackupDate)

// ===== РЕЗЕРВНЫЕ КОПИИ (только вручную — без автобэкапов) =====
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
