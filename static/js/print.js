// static/js/print.js — печатная версия карточки двигателя.
// Страница самостоятельная (НЕ подключает engines.js): раньше
// продублированы escapeHtml(), _formatRuDate() и PRINT_CHAR_FIELDS
// прямо здесь. Теперь они вынесены в static/js/common.js, который
// подключается перед print.js в templates/print.html.

function getEngineIdFromUrl() {
    // /print/<id> — путь, а не query string (см. роут print_engine_page
    // в app.py). Берём последний непустой сегмент.
    const parts = window.location.pathname.split('/').filter(Boolean);
    const id = parseInt(parts[parts.length - 1], 10);
    return isNaN(id) ? null : id;
}

function renderCharacteristics(engine) {
    return PRINT_CHAR_FIELDS.map(f => {
        const val = engine[f.key];
        const safeVal = (val && val !== 'nan') ? escapeHtml(val) : '—';
        return `<div class="print-field"><span class="print-field-label">${escapeHtml(f.label)}</span><span class="print-field-value">${safeVal}</span></div>`;
    }).join('');
}

function renderModesTable(modes) {
    if (!modes || modes.length === 0) {
        return '<div class="no-data">Нет режимов работы</div>';
    }
    const rows = modes.map((m, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${escapeHtml(m.frequency) || '—'}</td>
            <td>${escapeHtml(m.power) || '—'}</td>
            <td>${escapeHtml(m.voltage) || '—'}</td>
            <td>${escapeHtml(m.connection_type) || '—'}</td>
            <td>${escapeHtml(m.current) || '—'}</td>
            <td>${escapeHtml(m.rpm) || '—'}</td>
        </tr>
    `).join('');
    return `<table class="print-table">
        <thead><tr><th>#</th><th>Частота (Гц)</th><th>Мощность (кВт)</th><th>Напряжение (В)</th><th>Тип подключения</th><th>Ток (А)</th><th>Обороты (об/мин)</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

function renderWorksTable(works) {
    if (!works || works.length === 0) {
        return '<div class="no-data">Нет записей о работах</div>';
    }
    const rows = works.map((w, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${escapeHtml(w.work_number) || '—'}</td>
            <td>${_formatRuDate(w.date) || '—'}</td>
            <td>${escapeHtml(w.work_description) || '—'}</td>
            <td>${escapeHtml(w.isolation) || '—'}</td>
            <td>${escapeHtml(w.inspection) || '—'}</td>
            <td>${escapeHtml(w.signature) || '—'}</td>
        </tr>
    `).join('');
    return `<table class="print-table">
        <thead><tr><th>#</th><th>№ работы</th><th>Дата</th><th>Вид работ</th><th>Сопр. изоляции</th><th>Осмотр</th><th>ФИО</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

function renderPhotos(photos) {
    if (!photos || photos.length === 0) {
        return '<div class="no-data">Нет фото</div>';
    }
    const imgs = photos.map(p =>
        `<img class="print-photo" src="${authPhotoUrl(p.path)}" alt="Фото двигателя">`
    ).join('');
    return `<div class="print-photos">${imgs}</div>`;
}

function renderPage(engine, photos) {
    const titleParts = [engine.engine_type, engine.serial_number ? '№' + engine.serial_number : '']
        .filter(Boolean);
    const subtitleParts = [engine.location, engine.purpose]
        .filter(Boolean);

    return `
<div class="print-page">
    <div class="print-header">
        <div>
            <div class="print-title">${escapeHtml(titleParts.join(' ')) || 'Двигатель'}</div>
            <div class="print-subtitle">${escapeHtml(subtitleParts.join(' · ')) || ''}</div>
        </div>
        <div class="print-subtitle">ID: ${engine.id}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Характеристики</div>
        <div class="print-grid">${renderCharacteristics(engine)}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title modes">Режимы работы</div>
        ${renderModesTable(engine.modes)}
    </div>

    <div class="print-section">
        <div class="print-section-title works">Произведенные работы</div>
        ${renderWorksTable(engine.works)}
    </div>

    <div class="print-section">
        <div class="print-section-title">Фото (${photos ? photos.length : 0})</div>
        ${renderPhotos(photos)}
    </div>
</div>`;
}

function waitForImages(timeoutMs) {
    if (!timeoutMs) timeoutMs = 5000;
    return new Promise(function(resolve) {
        const imgs = document.querySelectorAll('.print-photo');
        if (!imgs.length) { resolve(); return; }
        let loaded = 0;
        const onLoaded = function() {
            loaded++;
            if (loaded >= imgs.length) resolve();
        };
        const timer = setTimeout(resolve, timeoutMs);
        imgs.forEach(function(img) {
            if (img.complete) { onLoaded(); }
            else {
                img.addEventListener('load', onLoaded);
                img.addEventListener('error', onLoaded);
            }
        });
    });
}

function loadAndRender() {
    const root = document.getElementById('printRoot');
    if (!root) return;

    const engineId = getEngineIdFromUrl();
    if (!engineId) {
        root.innerHTML = '<div class="no-data"><span class="icon icon-cancel"></span> Двигатель не найден в URL</div>';
        return;
    }

    const fetchEngineData = (url) => {
        return apiFetch(url).then(parseJsonResponse);
    };

    root.innerHTML = '<div class="loading">Загрузка данных...</div>';

    Promise.all([
        fetchEngineData(`/api/engine/${engineId}`),
        fetchEngineData(`/api/engine/${engineId}/photos`)
    ])
        .then(([engine, photos]) => {
            if (engine.error) {
                root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> ${escapeHtml(engine.error)}</div>`;
                return;
            }
            root.innerHTML = renderPage(engine, photos || []);
            waitForImages().then(() => {
                const printBtn = document.getElementById('printBtn');
                if (printBtn) {
                    printBtn.onclick = function() { window.print(); };
                }
            });
        })
        .catch(e => {
            root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
        });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', loadAndRender);
