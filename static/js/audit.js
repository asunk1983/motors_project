// static/js/audit.js — вкладка "Журнал" (audit_log, только admin/superadmin).
// Требует: common.js (escapeHtml, apiFetch, showToast), engines.js (formatRuDateTime)

let auditEntries = [];
let auditTotal = 0;
let auditPage = 1;
const AUDIT_PAGE_SIZE = 50;
let auditEntityTypesLoaded = false;

// Человекочитаемые подписи разделов — дополняется по мере того, как
// логирование добавляется в новые repo (см. modules/audit.py).
// Раздел, для которого подписи нет (появится в списке фильтра из
// /api/audit/entity-types раньше, чем сюда добавят перевод), просто
// покажет entity_type как есть — не ломается, только менее красиво.
const AUDIT_ENTITY_LABELS = {
    engine: 'Двигатели',
    equipment: 'Оборудование',
    incident_ticket: 'Инциденты',
    crew: 'Люди',
    location_node: 'Места',
    ticket: 'Заявки',
    failure: 'Отказы',
    knowledge_article: 'База знаний',
};

function loadAuditTab() {
    if (!auditEntityTypesLoaded) {
        loadAuditEntityTypes();
        auditEntityTypesLoaded = true;
    }
    auditPage = 1;
    loadAuditEntries();
}

function loadAuditEntityTypes() {
    apiFetch('/api/audit/entity-types')
        .then(r => r.json())
        .then(types => {
            const select = document.getElementById('auditEntityTypeFilter');
            if (!select || !Array.isArray(types)) return;
            types.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = AUDIT_ENTITY_LABELS[t] || t;
                select.appendChild(opt);
            });
        })
        .catch(() => {});
}

function _auditFilterParams() {
    const params = new URLSearchParams();
    const entityType = document.getElementById('auditEntityTypeFilter').value;
    const actor = document.getElementById('auditActorFilter').value.trim();
    const dateFrom = document.getElementById('auditDateFromFilter').value;
    const dateTo = document.getElementById('auditDateToFilter').value;
    if (entityType) params.set('entity_type', entityType);
    if (actor) params.set('actor', actor);
    if (dateFrom) params.set('date_from', dateFrom);
    // Конец диапазона включительно — без времени date_to сравнился бы как
    // '2026-09-08' <= '2026-09-08T14:30:00', что исключило бы весь день
    // (кроме ровно полуночи). Дописываем конец суток.
    if (dateTo) params.set('date_to', dateTo + ' 23:59:59');
    params.set('limit', AUDIT_PAGE_SIZE);
    params.set('offset', (auditPage - 1) * AUDIT_PAGE_SIZE);
    return params;
}

function loadAuditEntries() {
    const tbody = document.getElementById('auditTableBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="no-data">Загрузка...</td></tr>';

    apiFetch('/api/audit/log?' + _auditFilterParams().toString())
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error', 'icon-cancel');
                return;
            }
            auditEntries = data.entries || [];
            auditTotal = data.total || 0;
            renderAuditTable();
        })
        .catch(e => showToast('Не удалось загрузить журнал: ' + e.message, 'error', 'icon-cancel'));
}

function renderAuditTable() {
    const tbody = document.getElementById('auditTableBody');
    if (!tbody) return;

    if (auditEntries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">Ничего не найдено</td></tr>';
    } else {
        tbody.innerHTML = auditEntries.map(e => `
            <tr>
                <td class="mono">${formatRuDateTime(e.changed_at)}</td>
                <td>${escapeHtml(AUDIT_ENTITY_LABELS[e.entity_type] || e.entity_type)}</td>
                <td class="mono">${e.entity_id}</td>
                <td class="mono">${escapeHtml(e.field_name)}</td>
                <td>${escapeHtml(e.old_value || '') || '—'}</td>
                <td>${escapeHtml(e.new_value || '') || '—'}</td>
                <td>${escapeHtml(e.changed_by_display_name || '—')}</td>
            </tr>
        `).join('');
    }

    const start = auditTotal === 0 ? 0 : (auditPage - 1) * AUDIT_PAGE_SIZE + 1;
    const end = Math.min(auditPage * AUDIT_PAGE_SIZE, auditTotal);
    const pageInfo = document.getElementById('auditPageInfo');
    if (pageInfo) pageInfo.textContent = `Показано ${start}-${end} из ${auditTotal}`;
    const pageNumber = document.getElementById('auditPageNumber');
    if (pageNumber) pageNumber.textContent = auditPage;
}

function applyAuditFilters() {
    auditPage = 1;
    loadAuditEntries();
}

function resetAuditFilters() {
    document.getElementById('auditEntityTypeFilter').value = '';
    document.getElementById('auditActorFilter').value = '';
    document.getElementById('auditDateFromFilter').value = '';
    document.getElementById('auditDateToFilter').value = '';
    auditPage = 1;
    loadAuditEntries();
}

function auditPrevPage() {
    if (auditPage > 1) { auditPage--; loadAuditEntries(); }
}

function auditNextPage() {
    if (auditPage * AUDIT_PAGE_SIZE < auditTotal) { auditPage++; loadAuditEntries(); }
}

document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter') return;
    if (e.target && e.target.id === 'auditActorFilter') { e.preventDefault(); applyAuditFilters(); }
});
