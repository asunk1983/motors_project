// static/js/ticket.js — вкладка "Заявки". Открыта всем ролям.
// ticket != failure: заявка может не подтвердиться как отказ — см.
// PROJECT_CORE / обсуждение с пользователем. Использует apiFetch/
// parseJsonResponse/showToast/escapeHtml из auth.js/common.js.

let ticketEquipmentCache = [];
let ticketFailureModesCache = [];
let ticketFailureCausesCache = [];
let ticketActionTypesCache = [];
let currentTicketDetailId = null;

const TICKET_STATUS_LABEL = {
    new: 'Новая', in_progress: 'В работе', waiting: 'Ожидание',
    resolved: 'Решена', closed: 'Закрыта', rejected: 'Отклонена', cancelled: 'Отменена',
};
const TICKET_PRIORITY_LABEL = { high: 'Высокий', normal: 'Обычный', low: 'Низкий' };

function statusBadge(status) {
    return `<span class="badge-pill status-${status}">${escapeHtml(TICKET_STATUS_LABEL[status] || status)}</span>`;
}
function priorityBadge(priority) {
    return `<span class="badge-pill priority-${priority}">${escapeHtml(TICKET_PRIORITY_LABEL[priority] || priority)}</span>`;
}

// ---------------------------------------------------------------------
// Загрузка вкладки
// ---------------------------------------------------------------------

async function loadTicketsTab() {
    await loadTicketAuxData();
    await loadTicketsList();
}

async function loadTicketAuxData() {
    try {
        const [eqResp, modeResp, causeResp, actionResp] = await Promise.all([
            apiFetch('/api/equipment'),
            apiFetch('/api/knowledge/failure-modes'),
            apiFetch('/api/knowledge/failure-causes'),
            apiFetch('/api/maintenance-action-types'),
        ]);
        ticketEquipmentCache = await parseJsonResponse(eqResp);
        ticketFailureModesCache = await parseJsonResponse(modeResp);
        ticketFailureCausesCache = await parseJsonResponse(causeResp);
        ticketActionTypesCache = await parseJsonResponse(actionResp);
        if (!Array.isArray(ticketEquipmentCache)) ticketEquipmentCache = [];
        if (!Array.isArray(ticketFailureModesCache)) ticketFailureModesCache = [];
        if (!Array.isArray(ticketFailureCausesCache)) ticketFailureCausesCache = [];
        if (!Array.isArray(ticketActionTypesCache)) ticketActionTypesCache = [];

        const eqOptions = ticketEquipmentCache
            .map(e => `<option value="${e.id}">${escapeHtml(e.name)} (${escapeHtml(e.equipment_type_name || '')})</option>`)
            .join('');
        const eqSelect = document.getElementById('ticketEquipmentSelect');
        if (eqSelect) eqSelect.innerHTML = '<option value="">— не указано —</option>' + eqOptions;
    } catch (e) {
        showToast(e && e.message ? e.message : 'Не удалось загрузить вспомогательные данные', 'error');
    }
}

// ---------------------------------------------------------------------
// Список заявок
// ---------------------------------------------------------------------

async function loadTicketsList() {
    const body = document.getElementById('ticketsListBody');
    if (!body) return;
    const status = document.getElementById('ticketStatusFilter').value;

    body.innerHTML = '<tr><td colspan="7" class="no-data">Загрузка...</td></tr>';
    try {
        const params = new URLSearchParams();
        if (status) params.set('status', status);
        const resp = await apiFetch('/api/tickets' + (params.toString() ? '?' + params.toString() : ''));
        const tickets = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(tickets.error || 'Ошибка')}</td></tr>`;
            return;
        }
        if (!Array.isArray(tickets) || !tickets.length) {
            body.innerHTML = '<tr><td colspan="7" class="no-data">Заявок пока нет</td></tr>';
            return;
        }
        body.innerHTML = tickets.map(t => `
            <tr class="clickable-row" onclick="openTicketDetail(${t.id})">
                <td>${t.id}</td>
                <td>${escapeHtml(t.title)}</td>
                <td>${escapeHtml(t.equipment_name || '—')}</td>
                <td>${priorityBadge(t.priority)}</td>
                <td>${statusBadge(t.status)}</td>
                <td>${escapeHtml((t.created_at || '').slice(0, 16).replace('T', ' '))}</td>
                <td class="col-actions">
                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteTicketEntry(${t.id})" title="Удалить">
                        <span class="icon icon-delete"></span>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</td></tr>`;
    }
}

async function deleteTicketEntry(id) {
    if (!confirm('Удалить заявку вместе со связанным отказом и работами?')) return;
    try {
        const resp = await apiFetch(`/api/ticket/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Заявка удалена', 'success');
        await loadTicketsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Новая заявка
// ---------------------------------------------------------------------

function openNewTicketModal() {
    document.getElementById('ticketEquipmentSelect').value = '';
    document.getElementById('ticketPrioritySelect').value = 'normal';
    document.getElementById('ticketTitle').value = '';
    document.getElementById('ticketDescription').value = '';
    document.getElementById('newTicketModal').classList.add('active');
}
function closeNewTicketModal() {
    document.getElementById('newTicketModal').classList.remove('active');
}

async function submitNewTicket() {
    const title = document.getElementById('ticketTitle').value.trim();
    if (!title) {
        showToast('Тема заявки обязательна', 'error');
        return;
    }
    const equipmentRaw = document.getElementById('ticketEquipmentSelect').value;
    const payload = {
        equipment_id: equipmentRaw ? Number(equipmentRaw) : null,
        priority: document.getElementById('ticketPrioritySelect').value,
        title,
        description: document.getElementById('ticketDescription').value.trim(),
    };
    try {
        const resp = await apiFetch('/api/ticket', { method: 'POST', body: JSON.stringify(payload) });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания заявки', 'error');
            return;
        }
        showToast('Заявка создана', 'success');
        closeNewTicketModal();
        await loadTicketsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Детальная карточка заявки
// ---------------------------------------------------------------------

async function openTicketDetail(id) {
    currentTicketDetailId = id;
    const body = document.getElementById('ticketDetailBody');
    body.innerHTML = '<div class="no-data">Загрузка...</div>';
    document.getElementById('ticketDetailModal').classList.add('active');
    await refreshTicketDetail();
}

function closeTicketDetailModal() {
    document.getElementById('ticketDetailModal').classList.remove('active');
    currentTicketDetailId = null;
}

async function refreshTicketDetail() {
    if (!currentTicketDetailId) return;
    const body = document.getElementById('ticketDetailBody');
    try {
        const resp = await apiFetch(`/api/ticket/${currentTicketDetailId}`);
        const ticket = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<div class="no-data">${escapeHtml(ticket.error || 'Ошибка')}</div>`;
            return;
        }
        document.getElementById('ticketDetailTitle').innerHTML =
            `<span class="icon icon-warning"></span> Заявка №${ticket.id}`;

        let failure = null;
        if (ticket.failure_ids && ticket.failure_ids.length) {
            const fResp = await apiFetch(`/api/failure/${ticket.failure_ids[0]}`);
            failure = await parseJsonResponse(fResp);
        }
        renderTicketDetail(ticket, failure);
    } catch (e) {
        body.innerHTML = `<div class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</div>`;
    }
}

function renderTicketDetail(ticket, failure) {
    const body = document.getElementById('ticketDetailBody');
    const isFinal = ['closed', 'rejected', 'cancelled'].includes(ticket.status);

    let html = `
        <div class="ticket-detail-row"><span class="k">Тема</span><span>${escapeHtml(ticket.title)}</span></div>
        <div class="ticket-detail-row"><span class="k">Оборудование</span><span>${escapeHtml(ticket.equipment_name || '—')}</span></div>
        <div class="ticket-detail-row"><span class="k">Инициатор</span><span>${escapeHtml(ticket.created_by_username || '—')}</span></div>
        <div class="ticket-detail-row"><span class="k">Приоритет</span>${priorityBadge(ticket.priority)}</div>
        <div class="ticket-detail-row"><span class="k">Статус</span>${statusBadge(ticket.status)}</div>
        <div class="ticket-detail-row"><span class="k">Создана</span><span>${escapeHtml((ticket.created_at || '').slice(0, 16).replace('T', ' '))}</span></div>
    `;
    if (ticket.description) {
        html += `<div class="ticket-detail-section"><div class="k" style="font-size:11px;margin-bottom:4px">Описание</div>${escapeHtml(ticket.description)}</div>`;
    }
    if (ticket.status === 'rejected' && ticket.rejection_reason) {
        html += `<div class="ticket-detail-section"><div class="k" style="font-size:11px;margin-bottom:4px">Причина отклонения</div>${escapeHtml(ticket.rejection_reason)}</div>`;
    }

    // --- Блок отказа ---
    if (failure) {
        html += `<div class="ticket-detail-section"><div class="section-title">Подтверждённый отказ</div>`;
        html += `<div class="ticket-detail-row"><span class="k">Симптом</span><span>${escapeHtml(failure.symptom || '—')}</span></div>`;
        html += `<div class="ticket-detail-row"><span class="k">Режим отказа</span><span>${escapeHtml(failure.failure_mode_name || '—')}</span></div>`;
        html += `<div class="ticket-detail-row"><span class="k">Причина</span><span>${escapeHtml(failure.failure_cause_name || '—')}</span></div>`;
        if (failure.downtime_minutes != null) {
            html += `<div class="ticket-detail-row"><span class="k">Простой</span><span>${failure.downtime_minutes} мин</span></div>`;
        }
        html += `</div>`;

        html += `<div class="ticket-detail-section"><div class="section-title">Выполненные работы</div>`;
        if (failure.work && failure.work.length) {
            html += failure.work.map(w => `
                <div class="work-entry">
                    <div class="w-title">${escapeHtml(w.action_type_name || 'Работа')}${w.successful === 1 ? ' ✓' : w.successful === 0 ? ' ✗' : ''}</div>
                    ${w.description ? `<div>${escapeHtml(w.description)}</div>` : ''}
                    ${w.version_from || w.version_to ? `<div class="w-meta">Версия: ${escapeHtml(w.version_from || '?')} → ${escapeHtml(w.version_to || '?')}</div>` : ''}
                    <div class="w-meta">${escapeHtml(w.executor_username || '—')} · ${escapeHtml((w.created_at || '').slice(0, 16).replace('T', ' '))}</div>
                </div>
            `).join('');
        } else {
            html += '<div class="no-data" style="padding:8px 0">Работ пока нет</div>';
        }
        if (!isFinal) {
            html += `
                <button class="btn btn-secondary btn-sm" style="margin-top:6px" onclick="toggleAddWorkForm()">
                    <span class="icon icon-add"></span> Добавить работу
                </button>
                <div id="addWorkForm" style="display:none; margin-top:10px">
                    <div class="form-group">
                        <label>Тип действия</label>
                        <select id="workActionType">
                            ${ticketActionTypesCache.map(a => `<option value="${a.id}">${escapeHtml(a.name)}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Описание</label><textarea id="workDescription"></textarea></div>
                    <div class="form-group"><label>Версия ПО: с</label><input type="text" id="workVersionFrom" placeholder="если применимо"></div>
                    <div class="form-group"><label>Версия ПО: на</label><input type="text" id="workVersionTo" placeholder="если применимо"></div>
                    <div class="form-group">
                        <label><input type="checkbox" id="workSuccessful" checked style="width:auto"> Работа выполнена успешно</label>
                    </div>
                    <button class="btn btn-success btn-sm" onclick="submitWork(${failure.id})"><span class="icon icon-save"></span> Сохранить работу</button>
                </div>
            `;
        }
        html += `</div>`;
    } else if (!isFinal) {
        // --- Заявка ещё не подтверждена как отказ ---
        html += `
            <div class="ticket-detail-section">
                <button class="btn btn-secondary btn-sm" onclick="toggleConfirmFailureForm()">
                    <span class="icon icon-warning"></span> Подтвердить как отказ
                </button>
                <div id="confirmFailureForm" style="display:none; margin-top:10px">
                    <div class="form-group"><label>Симптом</label><textarea id="failureSymptom"></textarea></div>
                    <div class="form-group">
                        <label>Режим отказа</label>
                        <select id="failureModeSelect">
                            <option value="">— не выбран —</option>
                            ${ticketFailureModesCache.map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Причина</label>
                        <select id="failureCauseSelect">
                            <option value="">— не выбрана —</option>
                            ${ticketFailureCausesCache.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}
                        </select>
                    </div>
                    <button class="btn btn-success btn-sm" onclick="submitConfirmFailure()"><span class="icon icon-save"></span> Подтвердить</button>
                </div>
            </div>
        `;
    }

    // --- Действия со статусом ---
    if (!isFinal) {
        html += `<div class="ticket-action-row">`;
        if (ticket.status !== 'resolved') {
            html += `<button class="btn btn-secondary btn-sm" onclick="changeTicketStatus('resolved')">Отметить решённой</button>`;
        }
        html += `<button class="btn btn-secondary btn-sm" onclick="changeTicketStatus('closed')">Закрыть</button>`;
        html += `<button class="btn btn-danger btn-sm" onclick="rejectTicket()">Отклонить</button>`;
        html += `</div>`;
    }

    body.innerHTML = html;
}

function toggleConfirmFailureForm() {
    const el = document.getElementById('confirmFailureForm');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
function toggleAddWorkForm() {
    const el = document.getElementById('addWorkForm');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function submitConfirmFailure() {
    const symptom = document.getElementById('failureSymptom').value.trim();
    const modeRaw = document.getElementById('failureModeSelect').value;
    const causeRaw = document.getElementById('failureCauseSelect').value;
    try {
        const resp = await apiFetch(`/api/ticket/${currentTicketDetailId}/confirm-failure`, {
            method: 'POST',
            body: JSON.stringify({
                symptom,
                failure_mode_id: modeRaw ? Number(modeRaw) : null,
                failure_cause_id: causeRaw ? Number(causeRaw) : null,
            }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка подтверждения', 'error');
            return;
        }
        showToast('Отказ подтверждён', 'success');
        await refreshTicketDetail();
        await loadTicketsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function submitWork(failureId) {
    const payload = {
        action_type_id: Number(document.getElementById('workActionType').value),
        description: document.getElementById('workDescription').value.trim(),
        version_from: document.getElementById('workVersionFrom').value.trim(),
        version_to: document.getElementById('workVersionTo').value.trim(),
        successful: document.getElementById('workSuccessful').checked,
    };
    try {
        const resp = await apiFetch(`/api/failure/${failureId}/work`, { method: 'POST', body: JSON.stringify(payload) });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения работы', 'error');
            return;
        }
        showToast('Работа добавлена', 'success');
        await refreshTicketDetail();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function changeTicketStatus(status) {
    try {
        const resp = await apiFetch(`/api/ticket/${currentTicketDetailId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка смены статуса', 'error');
            return;
        }
        showToast('Статус обновлён', 'success');
        await refreshTicketDetail();
        await loadTicketsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function rejectTicket() {
    const reason = prompt('Причина отклонения заявки:');
    if (reason === null) return;
    if (!reason.trim()) {
        showToast('Причина отклонения обязательна', 'error');
        return;
    }
    try {
        const resp = await apiFetch(`/api/ticket/${currentTicketDetailId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'rejected', rejection_reason: reason.trim() }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка отклонения', 'error');
            return;
        }
        showToast('Заявка отклонена', 'success');
        await refreshTicketDetail();
        await loadTicketsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}
