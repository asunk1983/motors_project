// static/js/importer.js — импорт из папки.
// Требует: common.js, engines.js (updateStats)

// ===== ИМПОРТ =====
function importFiles() {
    if (!confirm('Импортировать все Excel файлы из папки "motors"?')) return;

    const progress = document.getElementById('importProgress');
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');
    const log = document.getElementById('progressLog');

    progress.classList.remove('hidden');
    fill.style.width = '0%';
    text.textContent = '0%';
    log.innerHTML = '<div class="log-line">⏳ Запуск импорта...</div>';

    apiFetch('/api/import-folder', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                fill.style.width = '100%';
                text.textContent = '✅ Завершено!';
                log.innerHTML += `<div class="log-line">✅ ${data.message}</div>`;
                showToast('✅ ' + data.message, 'success');
                loadEngines();
                updateStats();
                document.getElementById('filesCount').textContent = data.total_files || 0;
                document.getElementById('photosCount').textContent = data.total_photos || 0;
            } else {
                fill.style.width = '100%';
                text.textContent = '❌ Ошибка';
                log.innerHTML += `<div class="log-line">❌ ${data.error}</div>`;
                showToast('❌ ' + data.error, 'error');
            }
        })
        .catch(e => {
            fill.style.width = '100%';
            text.textContent = '❌ Ошибка';
            log.innerHTML += `<div class="log-line">❌ ${e.message}</div>`;
            showToast('❌ Ошибка: ' + e.message, 'error');
        });
}

function clearAll() {
    apiFetch('/api/clear', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('✅ ' + data.message, 'success');
                loadEngines();
                updateStats();
                document.getElementById('filesCount').textContent = '0';
                document.getElementById('photosCount').textContent = '0';
            } else {
                showToast('❌ ' + data.error, 'error');
            }
        })
        .catch(e => showToast('❌ Ошибка: ' + e.message, 'error'));
}

function confirmClearDatabase() {
    apiFetch('/api/status')
        .then(r => r.json())
        .then(status => {
            if (status.error) {
                showToast('❌ Не удалось получить статус: ' + status.error, 'error');
                return;
            }
            const engineCount = status.engine_count || 0;
            const photoCount = status.photos_count || 0;
            const confirmation = prompt(
                `Это удалит ${engineCount} двигателей и ${photoCount} фото безвозвратно.\nВведите СТИРАТЬ для подтверждения:`
            );
            if (confirmation === 'СТИРАТЬ') {
                clearAll();
            }
        })
        .catch(e => showToast('❌ Ошибка при получении статуса: ' + e.message, 'error'));
}
