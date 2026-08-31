// static/js/incidents.js — вкладка "Инциденты" (журнал диагностики).
// Отдельный, независимый модуль — НЕ пересекается с ticket.js
// (тот — формализованный протокол ремонта конкретной типизированной
// единицы оборудования; этот — свободная запись "что/где/кто/как
// решили", см. ТЗ "Инциденты" раздел 0). Требует: common.js, auth.js,
// incidentLocations.js, incidentCrew.js.

const INCIDENT_PRIORITY_LABEL = { low: 'Низкий', medium: 'Средний', high: 'Высокий' };
const INCIDENT_STATUS_LABEL = { in_progress: 'В работе', resolved: 'Решено', rejected: 'Отклонено' };

let incidentsList = [];
let currentIncidentId = null;
// Данные открытой заявки (для тулбара: даты/счётчик/навигация) —
// тот же принцип, что currentEngineData в engineCard.js/equipmentDetailData
// в equipment.js. null, пока не загружена (или в режиме создания).
let currentIncidentData = null;
let incidentLocationPicker = null;
let incidentInitiatorsTag = null;
let incidentExecutorsTag = null;
let incidentSelectedPriority = 'medium';
let incidentSelectedStatus = 'in_progress';
let incidentEquipmentSelected = [];   // [{id, name}] — в обоих режимах (create/edit) как единый рабочий список
let incidentPendingLinks = [];        // [{url, caption}] — только в режиме создания (до появления ticket_id)
let incidentPendingPhotoFiles = [];   // File[] — только в режиме создания
let incidentEditPhotos = [];          // [{filename, path}] — только в режиме редактирования (с сервера)
let incidentEditLinks = [];           // [{id, url, caption}] — только в режиме редактирования (с сервера)
let incidentSelectedExportIds = new Set();

// ===== ВКЛАДКА / ПОДВКЛАДКИ =====

function loadIncidentsTab() {
    if (typeof loadIncidentLocationTree === 'function') loadIncidentLocationTree();
    loadIncidentsList();
}

function switchIncidentsSubtab(name) {
    document.querySelectorAll('#tab-incidents .info-subtab-content').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('incidentsSubtab-' + name);
    if (target) target.classList.add('active');

    const journalBtn = document.getElementById('incidentsSubtabJournalBtn');
    const dictBtn = document.getElementById('incidentsSubtabDictionariesBtn');
    if (journalBtn) journalBtn.className = 'btn btn-sm ' + (name === 'journal' ? 'btn-primary' : 'btn-secondary');
    if (dictBtn) dictBtn.className = 'btn btn-sm ' + (name === 'dictionaries' ? 'btn-primary' : 'btn-secondary');

    if (name === 'dictionaries') {
        loadLocationDictionary();
        loadCrewDictionary();
    }
}

// ===== ЖУРНАЛ (список заявок) =====

function loadIncidentsList() {
    const status = document.getElementById('incidentStatusFilter')?.value || '';
    const priority = document.getElementById('incidentPriorityFilter')?.value || '';
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    // incidentActiveLocationId — выбранный узел в боковом дереве
    // (incidentLocationTree.js). null означает "фильтр снят" (корень
    // "Все заявки"), поэтому проверяем именно на null, а не на falsy —
    // 0 тоже валидный id узла (хотя в SQLite автоинкремент начинается
    // с 1, ноль как id теоретически невозможен, но проверка на null,
    // а не truthy, тут просто корректнее по смыслу).
    if (incidentActiveLocationId !== null) params.set('location_node_id', incidentActiveLocationId);

    const body = document.getElementById('incidentsListBody');
    if (body) body.innerHTML = '<tr><td colspan="7" class="no-data">Загрузка...</td></tr>';

    apiFetch('/api/incident-tickets' + (params.toString() ? '?' + params.toString() : ''))
        .then(r => r.json())
        .then(rows => {
            incidentsList = Array.isArray(rows) ? rows : [];
            renderIncidentsList();
        })
        .catch(e => {
            if (body) body.innerHTML = `<tr><td colspan="7" class="no-data">Ошибка: ${escapeHtml(e.message)}</td></tr>`;
        });
}

function renderIncidentsList() {
    const body = document.getElementById('incidentsListBody');
    if (!body) return;
    if (incidentsList.length === 0) {
        body.innerHTML = '<tr><td colspan="8" class="no-data">Заявок пока нет</td></tr>';
        updateIncidentExportButton();
        return;
    }
    body.innerHTML = incidentsList.map(t => `
        <tr class="clickable-row" data-id="${t.id}">
            <td class="col-checkbox" onclick="event.stopPropagation()"><input type="checkbox" class="incident-row-checkbox" ${incidentSelectedExportIds.has(t.id) ? 'checked' : ''} onchange="toggleIncidentSelection(${t.id}, this.checked)"></td>
            <td onclick="openIncidentModal(${t.id})">${t.id}</td>
            <td onclick="openIncidentModal(${t.id})">${escapeHtml(t.location_name || '—')}</td>
            <td onclick="openIncidentModal(${t.id})">${escapeHtml((t.problem || '').slice(0, 80))}${(t.problem || '').length > 80 ? '…' : ''}</td>
            <td onclick="openIncidentModal(${t.id})"><span class="incident-priority-badge incident-priority-${t.priority}">${escapeHtml(INCIDENT_PRIORITY_LABEL[t.priority] || t.priority)}</span></td>
            <td onclick="openIncidentModal(${t.id})"><span class="incident-status-badge incident-status-${t.status}">${escapeHtml(INCIDENT_STATUS_LABEL[t.status] || t.status)}</span></td>
            <td onclick="openIncidentModal(${t.id})">${escapeHtml((t.initiators || []).map(i => i.full_name).join(', ') || '—')}</td>
            <td onclick="openIncidentModal(${t.id})">${escapeHtml((t.created_at || '').slice(0, 16).replace('T', ' '))}</td>
        </tr>
    `).join('');
    updateIncidentExportButton();
}

// ===== ВЫБОР ЗАЯВОК ДЛЯ ЭКСПОРТА =====

function toggleIncidentSelection(id, checked) {
    if (checked) incidentSelectedExportIds.add(id);
    else incidentSelectedExportIds.delete(id);
    updateIncidentSelectAllState();
    updateIncidentExportButton();
}

function toggleIncidentSelectAll(checked) {
    document.querySelectorAll('.incident-row-checkbox').forEach(cb => {
        cb.checked = checked;
        const id = parseInt(cb.closest('tr').dataset.id, 10);
        if (checked) incidentSelectedExportIds.add(id);
        else incidentSelectedExportIds.delete(id);
    });
    updateIncidentSelectAllState();
    updateIncidentExportButton();
}

function updateIncidentSelectAllState() {
    const checkboxes = document.querySelectorAll('.incident-row-checkbox');
    const checked = Array.from(checkboxes).filter(cb => cb.checked);
    const selectAll = document.getElementById('incidentSelectAllCheckbox');
    if (!selectAll) return;
    if (checkboxes.length === 0) { selectAll.checked = false; selectAll.indeterminate = false; }
    else if (checked.length === checkboxes.length) { selectAll.checked = true; selectAll.indeterminate = false; }
    else if (checked.length > 0) { selectAll.checked = false; selectAll.indeterminate = true; }
    else { selectAll.checked = false; selectAll.indeterminate = false; }
}

function updateIncidentExportButton() {
    const count = incidentSelectedExportIds.size;
    const btn = document.getElementById('incidentExportBtn');
    const info = document.getElementById('incidentSelectionInfo');
    const countEl = document.getElementById('incidentSelectionCount');
    if (btn) btn.disabled = count === 0;
    if (info) info.classList.toggle('hidden', count === 0);
    if (countEl) countEl.textContent = count;
}

function exportSelectedIncidents() {
    const ids = Array.from(incidentSelectedExportIds);
    if (ids.length === 0) {
        showToast('Не выбрано ни одной заявки', 'warning', 'icon-warning');
        return;
    }
    showToast('Подготовка экспорта...', 'info', 'icon-progress-activity');
    apiFetch('/api/incident-tickets/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Ошибка экспорта'); });
            }
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `incidents_export_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast('Экспорт завершён', 'success', 'icon-check-circle');
        })
        .catch(e => showToast('Ошибка экспорта: ' + e.message, 'error', 'icon-cancel'));
}

// ===== МОДАЛКА ЗАЯВКИ (создание/просмотр/редактирование) =====

function openIncidentModal(id) {
    currentIncidentId = id || null;
    currentIncidentData = null;
    resetIncidentForm();

    const titleEl = document.getElementById('incidentModalTitle');
    const photosSection = document.getElementById('incidentPhotosEditSection');
    const photosCreateSection = document.getElementById('incidentPhotosCreateSection');
    const linksEditSection = document.getElementById('incidentLinksEditSection');
    const linksCreateSection = document.getElementById('incidentLinksCreateSection');

    const isEdit = !!currentIncidentId;
    if (photosSection) photosSection.style.display = isEdit ? '' : 'none';
    if (photosCreateSection) photosCreateSection.style.display = isEdit ? 'none' : '';
    if (linksEditSection) linksEditSection.style.display = isEdit ? '' : 'none';
    if (linksCreateSection) linksCreateSection.style.display = isEdit ? 'none' : '';

    if (!isEdit) {
        titleEl.innerHTML = '<span class="icon icon-warning"></span> Новая заявка';
        // Ещё не сохранённая заявка — листать/печатать/датировать нечего
        // (тот же принцип, что и у "🆕 Новый двигатель"/нового оборудования).
        renderIncidentDetailToolbar();
        document.getElementById('incidentTicketModal').classList.add('active');
        document.body.classList.add('modal-open');
        return;
    }

    titleEl.innerHTML = `<span class="icon icon-warning"></span> Заявка №${id}`;
    renderIncidentDetailToolbar();
    document.getElementById('incidentTicketModal').classList.add('active');
    document.body.classList.add('modal-open');

    apiFetch(`/api/incident-tickets/${id}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error', 'icon-cancel');
                closeIncidentModal();
                return;
            }
            currentIncidentData = data;
            fillIncidentForm(data);
            renderIncidentDetailToolbar();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

// ===== ТУЛБАР КАРТОЧКИ (счётчик/даты/навигация) =====
// По образцу renderDetailContent() в engineCard.js / renderEquipmentDetailToolbar()
// в equipment.js. incidentsList — уже загруженный (текущим фильтром: статус/
// приоритет/место) список заявок, тот же источник, что renderIncidentsList()
// использует для таблицы журнала — навигация идёт по нему.
function renderIncidentDetailToolbar() {
    const toolbar = document.getElementById('incidentDetailToolbar');
    if (!toolbar) return;
    if (!currentIncidentId || !currentIncidentData) {
        toolbar.innerHTML = '';
        return;
    }

    const data = currentIncidentData;
    const currentIndex = incidentsList.findIndex(t => t.id === data.id);
    const total = incidentsList.length;
    const currentUser = (typeof getAuthUser === 'function') ? getAuthUser() : {};
    const canDelete = currentUser.role === 'superadmin';

    const infoHtml = `
        <span class="detail-toolbar-title"><span class="icon icon-warning"></span> Карточка заявки</span>
        <span class="detail-toolbar-position">${currentIndex + 1} / ${total}</span>
        <span class="detail-toolbar-dates">Изменено: ${formatRuDateTime(data.updated_at)} · Создано: ${formatRuDateTime(data.created_at)}</span>
    `;

    const navHtml = `
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateIncident(-1)" ${currentIndex <= 0 ? 'disabled' : ''}>◀ Предыдущий</button>
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateIncident(1)" ${currentIndex === total - 1 ? 'disabled' : ''}>Следующий ▶</button>
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); printIncident()"><span class="icon icon-print"></span> Печать</button>
        ${canDelete ? '<button class="btn btn-danger btn-sm write-action" onclick="event.stopPropagation(); deleteCurrentIncident()"><span class="icon icon-delete"></span> Удалить</button>' : ''}
    `;

    toolbar.innerHTML = `<div class="detail-toolbar">
        <div class="detail-toolbar-info">${infoHtml}</div>
        <div class="detail-toolbar-nav">${navHtml}</div>
    </div>`;
}

// Листание ◀ Предыдущий / Следующий ▶ по уже загруженному списку заявок
// (incidentsList) — тот же принцип, что navigateEngine/navigateEquipment.
function navigateIncident(direction) {
    if (!currentIncidentData) return;
    const currentIndex = incidentsList.findIndex(t => t.id === currentIncidentData.id);
    if (currentIndex === -1) return;
    const newIndex = currentIndex + direction;
    if (newIndex < 0 || newIndex >= incidentsList.length) return;
    openIncidentModal(incidentsList[newIndex].id);
}

// Кнопка "+" у узла в боковом дереве мест (incidentLocationTree.js) —
// тот же приём, что createEquipmentAtLocation в equipment.js: открыть
// форму создания сразу с предзаполненным местом. openIncidentModal(null)
// (ветка создания) синхронно возвращает управление после
// resetIncidentForm() — attachLocationPicker уже готов к моменту вызова
// setValue ниже (в отличие от openEquipmentModal, эта функция не async).
function createIncidentAtLocation(nodeId, label) {
    openIncidentModal(null);
    if (incidentLocationPicker) {
        incidentLocationPicker.setValue(nodeId, label);
    }
}

function resetIncidentForm() {
    document.getElementById('incidentProblem').value = '';
    document.getElementById('incidentSolution').value = '';
    document.getElementById('incidentClosedAtInput').value = '';
    incidentSelectedPriority = 'medium';
    incidentSelectedStatus = 'in_progress';
    incidentEquipmentSelected = [];
    incidentPendingLinks = [];
    incidentPendingPhotoFiles = [];
    incidentEditPhotos = [];
    incidentEditLinks = [];
    renderIncidentPriorityPicker();
    renderIncidentStatusPicker();
    renderIncidentEquipmentChips();
    renderIncidentPendingLinks();
    renderIncidentPendingPhotos();

    const locationInput = document.getElementById('incidentLocationInput');
    // Модалка заявки переиспользует один и тот же <input> при каждом
    // открытии — если не снять слушатели/DOM-обёртку предыдущего пикера,
    // они накапливаются на inputEl (см. фикс в
    // attachEntitySuggest/attachLocationPicker, common.js /
    // incidentLocations.js), и клик по пункту списка приходится повторять
    // по несколько раз, пока не попадёшь по актуальному "живому" слою.
    if (incidentLocationPicker && incidentLocationPicker.destroy) {
        incidentLocationPicker.destroy();
    }
    locationInput.value = '';
    incidentLocationPicker = attachLocationPicker(locationInput, {});

    const initiatorsContainer = document.getElementById('incidentInitiatorsContainer');
    initiatorsContainer.innerHTML = '';
    incidentInitiatorsTag = attachCrewTagInput(initiatorsContainer, {});

    const executorsContainer = document.getElementById('incidentExecutorsContainer');
    executorsContainer.innerHTML = '';
    incidentExecutorsTag = attachCrewTagInput(executorsContainer, {});

    attachIncidentEquipmentPicker();
}

function fillIncidentForm(data) {
    document.getElementById('incidentProblem').value = data.problem || '';
    document.getElementById('incidentSolution').value = data.solution || '';
    document.getElementById('incidentClosedAtInput').value = (data.closed_at || '').slice(0, 16).replace(' ', 'T');
    incidentSelectedPriority = data.priority || 'medium';
    incidentSelectedStatus = data.status || 'in_progress';
    renderIncidentPriorityPicker();
    renderIncidentStatusPicker();

    incidentLocationPicker.setValue(data.location_node_id, data.location_name || '');
    incidentInitiatorsTag.setItems(data.initiators || []);
    incidentExecutorsTag.setItems(data.executors || []);

    incidentEquipmentSelected = (data.equipment || []).map(e => ({ id: e.id, name: e.name }));
    renderIncidentEquipmentChips();

    incidentEditLinks = data.links || [];
    renderIncidentEditLinks();

    incidentEditPhotos = data.photos || [];
    renderIncidentEditPhotos();
}

function closeIncidentModal() {
    document.getElementById('incidentTicketModal').classList.remove('active');
    if (!document.querySelector('.modal.active, .photo-modal.active')) {
        document.body.classList.remove('modal-open');
    }
    currentIncidentId = null;
    currentIncidentData = null;
    const toolbar = document.getElementById('incidentDetailToolbar');
    if (toolbar) toolbar.innerHTML = '';
}

// ===== ПРИОРИТЕТ (3 кружка) / СТАТУС (3 пилюли) =====

function renderIncidentPriorityPicker() {
    const el = document.getElementById('incidentPriorityPicker');
    if (!el) return;
    el.innerHTML = ['low', 'medium', 'high'].map(p => `
        <button type="button" class="incident-priority-dot incident-priority-${p}${p === incidentSelectedPriority ? ' selected' : ''}"
                onclick="selectIncidentPriority('${p}')" title="${escapeHtml(INCIDENT_PRIORITY_LABEL[p])}"></button>
    `).join('');
}

function selectIncidentPriority(p) {
    incidentSelectedPriority = p;
    renderIncidentPriorityPicker();
}

function renderIncidentStatusPicker() {
    const el = document.getElementById('incidentStatusPicker');
    if (!el) return;
    el.innerHTML = ['in_progress', 'resolved', 'rejected'].map(s => `
        <button type="button" class="incident-status-pill incident-status-${s}${s === incidentSelectedStatus ? ' selected' : ''}"
                onclick="selectIncidentStatus('${s}')">${escapeHtml(INCIDENT_STATUS_LABEL[s])}</button>
    `).join('');
}

function selectIncidentStatus(s) {
    incidentSelectedStatus = s;
    renderIncidentStatusPicker();
}

// ===== ОБОРУДОВАНИЕ =====

function attachIncidentEquipmentPicker() {
    const input = document.getElementById('incidentEquipmentInput');
    input.value = '';
    attachEntitySuggest(input, {
        minChars: 1,
        searchFn: (query) => apiFetch(`/api/equipment?search=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(rows => (Array.isArray(rows) ? rows : [])
                .filter(row => !incidentEquipmentSelected.some(s => s.id === row.id))
                .map(row => ({ id: row.id, label: row.name, sublabel: row.equipment_type_name || '' }))),
        onSelect: (item) => {
            input.value = '';
            if (currentIncidentId) {
                apiFetch(`/api/incident-tickets/${currentIncidentId}/equipment`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ equipment_id: item.id })
                })
                    .then(r => r.json())
                    .then(result => {
                        if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
                        incidentEquipmentSelected.push({ id: item.id, name: item.label });
                        renderIncidentEquipmentChips();
                    })
                    .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
            } else {
                incidentEquipmentSelected.push({ id: item.id, name: item.label });
                renderIncidentEquipmentChips();
            }
        }
    });
}

function renderIncidentEquipmentChips() {
    const el = document.getElementById('incidentEquipmentChips');
    if (!el) return;
    el.innerHTML = incidentEquipmentSelected.map(item => `
        <span class="crew-tag-chip" data-id="${item.id}">
            ${escapeHtml(item.name)}
            <button type="button" onclick="removeIncidentEquipment(${item.id})" class="crew-tag-remove" title="Убрать">&times;</button>
        </span>
    `).join('') || '<span class="settings-hint">Оборудование не привязано</span>';
}

function removeIncidentEquipment(equipmentId) {
    if (currentIncidentId) {
        apiFetch(`/api/incident-tickets/${currentIncidentId}/equipment/${equipmentId}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(result => {
                if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
                incidentEquipmentSelected = incidentEquipmentSelected.filter(i => i.id !== equipmentId);
                renderIncidentEquipmentChips();
            })
            .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
    } else {
        incidentEquipmentSelected = incidentEquipmentSelected.filter(i => i.id !== equipmentId);
        renderIncidentEquipmentChips();
    }
}

// ===== ССЫЛКИ =====

// Режим создания — очередь в памяти, отправляется одним проходом сразу
// после успешного создания заявки (тот же принцип, что pendingPhotoFiles
// у формы добавления двигателя в exportManager.js).
function addPendingIncidentLink() {
    const urlInput = document.getElementById('incidentLinkUrlInput');
    const captionInput = document.getElementById('incidentLinkCaptionInput');
    const url = urlInput.value.trim();
    if (!url) {
        showToast('Введите URL', 'warning', 'icon-warning');
        return;
    }
    incidentPendingLinks.push({ url, caption: captionInput.value.trim() });
    urlInput.value = '';
    captionInput.value = '';
    renderIncidentPendingLinks();
}

function renderIncidentPendingLinks() {
    const el = document.getElementById('incidentPendingLinksList');
    if (!el) return;
    el.innerHTML = incidentPendingLinks.map((l, idx) => `
        <li class="wishlist-item">
            <span class="wishlist-text">${escapeHtml(l.caption || l.url)}</span>
            <button type="button" class="link-btn" onclick="removePendingIncidentLink(${idx})"><span class="icon icon-close"></span></button>
        </li>
    `).join('');
}

function removePendingIncidentLink(idx) {
    incidentPendingLinks.splice(idx, 1);
    renderIncidentPendingLinks();
}

// Режим редактирования — сразу на сервер (заявка уже существует).
function addIncidentLink() {
    if (!currentIncidentId) return;
    const urlInput = document.getElementById('incidentLinkUrlInput');
    const captionInput = document.getElementById('incidentLinkCaptionInput');
    const url = urlInput.value.trim();
    if (!url) {
        showToast('Введите URL', 'warning', 'icon-warning');
        return;
    }
    apiFetch(`/api/incident-tickets/${currentIncidentId}/links`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, caption: captionInput.value.trim() })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
            incidentEditLinks.push({ id: result.id, url, caption: captionInput.value.trim() });
            urlInput.value = '';
            captionInput.value = '';
            renderIncidentEditLinks();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function renderIncidentEditLinks() {
    const el = document.getElementById('incidentEditLinksList');
    if (!el) return;
    el.innerHTML = incidentEditLinks.map(l => `
        <li class="wishlist-item">
            <a href="${escapeHtml(l.url)}" target="_blank" rel="noopener" class="wishlist-text">${escapeHtml(l.caption || l.url)}</a>
            <button type="button" class="link-btn" onclick="deleteIncidentLink(${l.id})"><span class="icon icon-close"></span></button>
        </li>
    `).join('') || '<div class="no-data">Ссылок нет</div>';
}

function deleteIncidentLink(linkId) {
    if (!currentIncidentId) return;
    apiFetch(`/api/incident-tickets/${currentIncidentId}/links/${linkId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
            incidentEditLinks = incidentEditLinks.filter(l => l.id !== linkId);
            renderIncidentEditLinks();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

// ===== ФОТО =====

document.addEventListener('DOMContentLoaded', function () {
    const createInput = document.getElementById('incidentPhotoCreateInput');
    if (createInput) {
        createInput.addEventListener('change', function () {
            incidentPendingPhotoFiles = incidentPendingPhotoFiles.concat(Array.from(this.files || []));
            this.value = '';
            renderIncidentPendingPhotos();
        });
    }
    const editInput = document.getElementById('incidentPhotoEditInput');
    if (editInput) {
        editInput.addEventListener('change', function () {
            if (!currentIncidentId || !this.files || !this.files.length) return;
            const formData = new FormData();
            Array.from(this.files).forEach(f => formData.append('photos', f));
            this.value = '';
            apiFetch(`/api/incident-tickets/${currentIncidentId}/photos`, { method: 'POST', body: formData })
                .then(r => r.json())
                .then(result => {
                    if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
                    return apiFetch(`/api/incident-tickets/${currentIncidentId}/photos`).then(r => r.json());
                })
                .then(photos => {
                    if (!photos) return;
                    incidentEditPhotos = photos;
                    renderIncidentEditPhotos();
                    showToast('Фото загружено', 'success', 'icon-check-circle');
                })
                .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
        });
    }
});

function renderIncidentPendingPhotos() {
    const wrap = document.getElementById('incidentPhotosCreatePreview');
    if (!wrap) return;
    wrap.innerHTML = '';
    incidentPendingPhotoFiles.forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const box = document.createElement('div');
        box.className = 'photo-thumb is-pending';
        box.innerHTML = `<img src="${url}" alt="Новое фото"><button type="button" class="photo-thumb-remove" onclick="removePendingIncidentPhoto(${idx})"><span class="icon icon-close"></span></button>`;
        wrap.appendChild(box);
    });
}

function removePendingIncidentPhoto(idx) {
    incidentPendingPhotoFiles.splice(idx, 1);
    renderIncidentPendingPhotos();
}

function renderIncidentEditPhotos() {
    const wrap = document.getElementById('incidentPhotosEditGallery');
    if (!wrap) return;
    if (incidentEditPhotos.length === 0) {
        wrap.innerHTML = '<div class="no-data">Нет фото</div>';
        return;
    }
    wrap.innerHTML = incidentEditPhotos.map(p => `
        <div class="photo-thumb">
            <img src="${authPhotoUrl(p.path)}" alt="Фото заявки">
            <button type="button" class="photo-thumb-remove" onclick="deleteIncidentPhoto('${escapeAttr(p.filename)}')" title="Удалить"><span class="icon icon-close"></span></button>
        </div>
    `).join('');
}

function deleteIncidentPhoto(filename) {
    if (!currentIncidentId) return;
    if (!confirm('Удалить это фото?')) return;
    apiFetch(`/api/incident-tickets/${currentIncidentId}/photos/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
            incidentEditPhotos = incidentEditPhotos.filter(p => p.filename !== filename);
            renderIncidentEditPhotos();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

// ===== СОХРАНЕНИЕ =====

function uploadPendingIncidentPhotos(ticketId) {
    if (incidentPendingPhotoFiles.length === 0) return Promise.resolve();
    const formData = new FormData();
    incidentPendingPhotoFiles.forEach(f => formData.append('photos', f));
    return apiFetch(`/api/incident-tickets/${ticketId}/photos`, { method: 'POST', body: formData })
        .catch(() => showToast('Заявка сохранена, но фото не загрузились', 'warning', 'icon-warning'));
}

function uploadPendingIncidentLinks(ticketId) {
    return Promise.all(incidentPendingLinks.map(l =>
        apiFetch(`/api/incident-tickets/${ticketId}/links`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(l)
        })
    )).catch(() => showToast('Заявка сохранена, но не все ссылки добавились', 'warning', 'icon-warning'));
}

function submitIncident() {
    const location = incidentLocationPicker.getValue();
    if (!location) {
        showToast('Укажите место', 'warning', 'icon-warning');
        return;
    }
    const problem = document.getElementById('incidentProblem').value.trim();
    if (!problem) {
        showToast('Поле "Проблема" обязательно', 'warning', 'icon-warning');
        return;
    }
    const initiatorIds = incidentInitiatorsTag.getIds();
    if (initiatorIds.length === 0) {
        showToast('Нужен хотя бы один инициатор', 'warning', 'icon-warning');
        return;
    }

    const closedAtRaw = document.getElementById('incidentClosedAtInput').value;
    const payload = {
        location_node_id: location.id,
        problem,
        solution: document.getElementById('incidentSolution').value.trim(),
        priority: incidentSelectedPriority,
        status: incidentSelectedStatus,
        initiator_ids: initiatorIds,
        executor_ids: incidentExecutorsTag.getIds(),
    };
    // closed_at — только если пользователь тронул поле руками; иначе не
    // передаём ключ вовсе, чтобы backend применил авто-логику по статусу
    // (см. services/incident_service.py::_resolve_closed_at).
    if (closedAtRaw) payload.closed_at = closedAtRaw.replace('T', ' ') + ':00';

    if (currentIncidentId) {
        apiFetch(`/api/incident-tickets/${currentIncidentId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(r => r.json())
            .then(result => {
                if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
                showToast('Заявка обновлена', 'success', 'icon-check-circle');
                closeIncidentModal();
                loadIncidentsList();
                if (typeof loadIncidentLocationTree === 'function') loadIncidentLocationTree();
            })
            .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
    } else {
        apiFetch('/api/incident-tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(r => r.json())
            .then(result => {
                if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
                const ticketId = result.id;
                const equipmentCalls = incidentEquipmentSelected.map(e =>
                    apiFetch(`/api/incident-tickets/${ticketId}/equipment`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ equipment_id: e.id })
                    })
                );
                Promise.all([
                    uploadPendingIncidentPhotos(ticketId),
                    uploadPendingIncidentLinks(ticketId),
                    ...equipmentCalls
                ]).then(() => {
                    showToast('Заявка создана', 'success', 'icon-check-circle');
                    closeIncidentModal();
                    loadIncidentsList();
                    if (typeof loadIncidentLocationTree === 'function') loadIncidentLocationTree();
                });
            })
            .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
    }
}

function deleteCurrentIncident() {
    if (!currentIncidentId) return;
    if (!confirm(`Удалить заявку №${currentIncidentId}? Действие необратимо.`)) return;
    apiFetch(`/api/incident-tickets/${currentIncidentId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) { showToast(result.error, 'error', 'icon-cancel'); return; }
            showToast('Заявка удалена', 'success', 'icon-check-circle');
            closeIncidentModal();
            loadIncidentsList();
            if (typeof loadIncidentLocationTree === 'function') loadIncidentLocationTree();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function printIncident() {
    if (!currentIncidentId) return;
    window.open(`/print/incident/${currentIncidentId}`, '_blank');
}

// Enter сохраняет заявку — тот же принцип, что и Enter-сохранение для
// оборудования (equipment.js) и для строк режимов/работ в engineCard.js.
// Два исключения:
// 1) e.defaultPrevented — Enter уже обработан автодополнением места
//    (attachSuggestDropdown/attachEntitySuggest в common.js сами вызывают
//    preventDefault при выборе подсказки из списка).
// 2) поля добавления ссылки (incidentLinkUrlInput/incidentLinkCaptionInput) —
//    у них своей кнопки/Enter-обработчика на добавление пока нет, но раз
//    это обычный <input>, Enter в них не должен проваливаться в общий
//    submit и случайно сохранять/закрывать всю заявку вместо (пока
//    ручного, через кнопку) добавления ссылки.
document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || e.defaultPrevented) return;
    if (e.target.tagName !== 'INPUT') return; // не трогаем textarea (перенос строки) и select
    const modal = document.getElementById('incidentTicketModal');
    if (!modal || !modal.classList.contains('active')) return;
    if (e.target.id === 'incidentLinkUrlInput' || e.target.id === 'incidentLinkCaptionInput') return;
    e.preventDefault();
    submitIncident();
});
