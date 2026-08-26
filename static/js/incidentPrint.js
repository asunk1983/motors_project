// static/js/incidentPrint.js — печатная версия заявки Инцидента.
// Тот же принцип, что и static/js/print.js для двигателей: страница
// самостоятельная (НЕ подключает incidents.js), id заявки берётся из
// URL, единственный fetch — GET /api/incident-tickets/<id> (в отличие
// от двигателя, фото у заявки уже приезжают ВНУТРИ этого ответа, см.
// incident_ticket_routes.py::get_ticket_route — отдельный запрос за
// фото не нужен). Требует: common.js (escapeHtml), auth.js (apiFetch,
// authPhotoUrl, parseJsonResponse).

const INCIDENT_PRINT_PRIORITY_LABEL = { low: 'Низкий', medium: 'Средний', high: 'Высокий' };
const INCIDENT_PRINT_STATUS_LABEL = { in_progress: 'В работе', resolved: 'Решено', rejected: 'Отклонено' };

function getIncidentTicketIdFromUrl() {
    // /print/incident/<id> — путь, а не query string (см. роут в
    // routes/pages.py, зеркало print_engine_page). Берём последний
    // непустой сегмент.
    const parts = window.location.pathname.split('/').filter(Boolean);
    const id = parseInt(parts[parts.length - 1], 10);
    return isNaN(id) ? null : id;
}

function renderIncidentField(label, value) {
    const safeVal = (value !== null && value !== undefined && value !== '') ? escapeHtml(value) : '—';
    return `<div class="print-field"><span class="print-field-label">${escapeHtml(label)}</span><span class="print-field-value">${safeVal}</span></div>`;
}

function renderIncidentLinks(links) {
    if (!links || links.length === 0) return '';
    const items = links.map(l =>
        `<div class="print-field"><span class="print-field-value">${escapeHtml(l.caption || l.url)}${l.caption ? ' — ' + escapeHtml(l.url) : ''}</span></div>`
    ).join('');
    return `<div class="print-section">
        <div class="print-section-title">Ссылки</div>
        ${items}
    </div>`;
}

function renderIncidentPhotos(photos) {
    if (!photos || photos.length === 0) return '';
    const imgs = photos.map(p =>
        `<img class="print-photo" src="${authPhotoUrl(p.path)}" alt="Фото заявки">`
    ).join('');
    return `<div class="print-section">
        <div class="print-section-title">Фото (${photos.length})</div>
        <div class="print-photos">${imgs}</div>
    </div>`;
}

function renderIncidentPage(ticket) {
    const priorityLabel = INCIDENT_PRINT_PRIORITY_LABEL[ticket.priority] || ticket.priority;
    const statusLabel = INCIDENT_PRINT_STATUS_LABEL[ticket.status] || ticket.status;
    const initiators = (ticket.initiators || []).map(i => i.full_name).join(', ') || '—';
    const executors = (ticket.executors || []).map(e => e.full_name).join(', ') || '—';
    const equipment = (ticket.equipment || []).map(e => e.name).join(', ') || '—';

    return `
<div class="print-page">
    <div class="print-header">
        <div>
            <div class="print-title">Заявка №${ticket.id}</div>
            <div class="print-subtitle">${escapeHtml(ticket.location_name || '')}</div>
        </div>
        <div class="print-subtitle">Статус: ${escapeHtml(statusLabel)}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Сведения</div>
        <div class="print-grid">
            ${renderIncidentField('Приоритет', priorityLabel)}
            ${renderIncidentField('Статус', statusLabel)}
            ${renderIncidentField('Инициатор(ы)', initiators)}
            ${renderIncidentField('Исполнитель(и)', executors)}
            ${renderIncidentField('Оборудование', equipment)}
            ${renderIncidentField('Создана', (ticket.created_at || '').slice(0, 16).replace('T', ' '))}
            ${renderIncidentField('Закрыта', (ticket.closed_at || '').slice(0, 16).replace('T', ' '))}
        </div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Проблема</div>
        <div class="print-field-value">${escapeHtml(ticket.problem || '—')}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Решение</div>
        <div class="print-field-value">${escapeHtml(ticket.solution || '—')}</div>
    </div>

    ${renderIncidentLinks(ticket.links)}
    ${renderIncidentPhotos(ticket.photos)}
</div>`;
}

function waitForIncidentImages(timeoutMs) {
    if (!timeoutMs) timeoutMs = 5000;
    return new Promise(function (resolve) {
        const imgs = document.querySelectorAll('.print-photo');
        if (!imgs.length) { resolve(); return; }
        let loaded = 0;
        const onLoaded = function () {
            loaded++;
            if (loaded >= imgs.length) resolve();
        };
        const timer = setTimeout(resolve, timeoutMs);
        imgs.forEach(function (img) {
            if (img.complete) { onLoaded(); }
            else {
                img.addEventListener('load', onLoaded);
                img.addEventListener('error', onLoaded);
            }
        });
    });
}

function loadAndRenderIncident() {
    const root = document.getElementById('printRoot');
    if (!root) return;

    const ticketId = getIncidentTicketIdFromUrl();
    if (!ticketId) {
        root.innerHTML = '<div class="no-data"><span class="icon icon-cancel"></span> Заявка не найдена в URL</div>';
        return;
    }

    root.innerHTML = '<div class="loading">Загрузка данных...</div>';

    apiFetch(`/api/incident-tickets/${ticketId}`)
        .then(parseJsonResponse)
        .then(ticket => {
            if (ticket.error) {
                root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> ${escapeHtml(ticket.error)}</div>`;
                return;
            }
            root.innerHTML = renderIncidentPage(ticket);
            waitForIncidentImages().then(() => {
                const printBtn = document.getElementById('printBtn');
                if (printBtn) {
                    printBtn.onclick = function () { window.print(); };
                }
            });
        })
        .catch(e => {
            root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
        });
}

document.addEventListener('DOMContentLoaded', loadAndRenderIncident);
