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

// Человекочитаемые подписи полей — раздел, для которого подписи нет,
// покажет field_name как есть (например, ещё не переведённое поле нового
// раздела) — не ломается, только менее красиво.
const AUDIT_FIELD_LABELS = {
    location_node_id: 'Место установки',
    location: 'Место установки',
    workshop: 'Цех',
    name: 'Название',
    full_name: 'ФИО',
    position: 'Должность',
    status: 'Статус',
    note: 'Примечание',
    problem: 'Проблема',
    solution: 'Решение',
    priority: 'Приоритет',
    equipment_id: 'Оборудование',
    equipment_type_id: 'Тип оборудования',
    manufacturer: 'Производитель',
    serial_number: 'Зав. номер',
    engine_type: 'Тип',
    purpose: 'Назначение',
    title: 'Заголовок',
    description: 'Описание',
    symptom: 'Симптом',
    failure_mode_id: 'Режим отказа',
    failure_cause_id: 'Причина отказа',
    reference_note: 'Справочное примечание',
    diagnostic_steps: 'Шаги диагностики',
    recommended_action: 'Рекомендуемое действие',
    parent_id: 'Родительское место',
    node_type: 'Тип узла',
    photo_count: 'Кол-во фото',
    rejection_reason: 'Причина отклонения',
    __created__: 'Создание записи',
    __deleted__: 'Удаление записи',
    // Характеристики двигателя (engine_repo.update — ENGINE_COLUMNS_ORDERED)
    filename: 'Имя файла',
    bearing_front: 'Подшипник передний',
    bearing_rear: 'Подшипник задний',
    shaft_diameter: 'Диаметр вала',
    protection_class: 'Степень защиты',
    mounting_type: 'Тип крепления',
    temp_sensor: 'Датчик температуры',
    encoder: 'Энкодер',
    cooling: 'Охлаждение',
    // Оборудование (equipment_repo.update_equipment)
    article: 'Артикул',
    criticality: 'Критичность',
    specs_json: 'Характеристики',
    // Инциденты (incident_ticket_repo.update)
    closed_at: 'Дата закрытия',
    // Отказы (ticket_repo.update_failure)
    knowledge_article_id: 'Статья базы знаний',
    confirmed: 'Подтверждён',
    occurred_at: 'Дата возникновения',
    restored_at: 'Дата восстановления',
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
    // Конец диапазона включительно. changed_at пишется через
    // datetime.now().isoformat() с разделителем 'T' ('2026-09-08T14:30:00'),
    // поэтому конец суток дописываем тоже через 'T'. Пробел (' 23:59:59')
    // больше 'T' при байтовом сравнении строк, и условие
    // changed_at <= '2026-09-08 23:59:59' исключало бы весь выбранный день.
    if (dateTo) params.set('date_to', dateTo + 'T23:59:59');
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
                <td>${escapeHtml(AUDIT_FIELD_LABELS[e.field_name] || e.field_name)}</td>
                <td>${escapeHtml(e.old_value_display || e.old_value || '') || '—'}</td>
                <td>${escapeHtml(e.new_value_display || e.new_value || '') || '—'}</td>
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
