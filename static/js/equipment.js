// static/js/equipment.js — вкладка "Оборудование".
// Подвкладка "Номенклатура" открыта всем ролям (как каталог двигателей).
// Подвкладка "Конструктор типов" скрыта для не-admin в auth.js, а
// пишущие роуты конструктора на бэкенде защищены _require_admin —
// см. routes/equipment_routes.py. Использует apiFetch/parseJsonResponse/
// showToast/escapeHtml/debounce из auth.js/common.js.

let equipmentTypesCache = [];
let attributeDefinitionsCache = [];
let currentConstructorTypeId = null;

// ---------------------------------------------------------------------
// Вкладка / подвкладки
// ---------------------------------------------------------------------

async function loadEquipmentTab() {
    await loadEquipmentTypes();
    await loadAttributeDefinitions();
    await loadEquipmentList();
}

function switchEquipmentSubtab(name) {
    document.querySelectorAll('#tab-equipment .info-subtab-content').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('equipmentSubtab-' + name);
    if (target) target.classList.add('active');

    const listBtn = document.getElementById('equipmentSubtabListBtn');
    const constructorBtn = document.getElementById('equipmentSubtabConstructorBtn');
    if (listBtn) listBtn.className = 'btn btn-sm ' + (name === 'list' ? 'btn-primary' : 'btn-secondary');
    if (constructorBtn) constructorBtn.className = 'btn btn-sm ' + (name === 'constructor' ? 'btn-primary' : 'btn-secondary');
}

// ---------------------------------------------------------------------
// Типы оборудования
// ---------------------------------------------------------------------

async function loadEquipmentTypes() {
    try {
        const resp = await apiFetch('/api/equipment-types');
        const types = await parseJsonResponse(resp);
        equipmentTypesCache = Array.isArray(types) ? types : [];
        populateEquipmentTypeSelects();
        renderEquipmentTypesList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Не удалось загрузить типы оборудования', 'error');
    }
}

function equipmentTypeLabel(t) {
    return t.parent_name ? `${t.parent_name} → ${t.name}` : t.name;
}

function populateEquipmentTypeSelects() {
    const optionsHtml = equipmentTypesCache
        .map(t => `<option value="${t.id}">${escapeHtml(equipmentTypeLabel(t))}</option>`)
        .join('');

    const filterEl = document.getElementById('equipmentTypeFilter');
    if (filterEl) {
        const current = filterEl.value;
        filterEl.innerHTML = '<option value="">Все типы</option>' + optionsHtml;
        filterEl.value = current;
    }

    const modalSelectEl = document.getElementById('equipmentTypeSelect');
    if (modalSelectEl) {
        const current = modalSelectEl.value;
        modalSelectEl.innerHTML = '<option value="">— выбрать тип —</option>' + optionsHtml;
        modalSelectEl.value = current;
    }

    const parentSelectEl = document.getElementById('newEquipmentTypeParent');
    if (parentSelectEl) {
        parentSelectEl.innerHTML = '<option value="">— без родителя —</option>' + optionsHtml;
    }
}

function renderEquipmentTypesList() {
    const el = document.getElementById('equipmentTypesList');
    if (!el) return;
    if (!equipmentTypesCache.length) {
        el.innerHTML = '<div class="no-data">Типов пока нет — добавьте первый выше</div>';
        return;
    }
    el.innerHTML = equipmentTypesCache.map(t => `
        <div class="knowledge-dict-row" style="cursor:pointer" onclick="selectConstructorType(${t.id})">
            <div>
                <div class="knowledge-dict-code">${escapeHtml(t.code)}${t.parent_name ? ' · ' + escapeHtml(t.parent_name) : ''}</div>
                ${escapeHtml(t.name)}
            </div>
            <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteEquipmentType(${t.id})" title="Удалить">
                <span class="icon icon-delete"></span>
            </button>
        </div>
    `).join('');
}

async function createEquipmentType() {
    const codeEl = document.getElementById('newEquipmentTypeCode');
    const nameEl = document.getElementById('newEquipmentTypeName');
    const parentEl = document.getElementById('newEquipmentTypeParent');
    const code = codeEl.value.trim().toUpperCase();
    const name = nameEl.value.trim();
    if (!code || !name) {
        showToast('Укажите код и название типа', 'error');
        return;
    }
    try {
        const resp = await apiFetch('/api/equipment-types', {
            method: 'POST',
            body: JSON.stringify({
                code, name,
                parent_type_id: parentEl.value ? Number(parentEl.value) : null,
            }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания типа', 'error');
            return;
        }
        codeEl.value = '';
        nameEl.value = '';
        parentEl.value = '';
        showToast('Тип оборудования создан', 'success');
        await loadEquipmentTypes();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteEquipmentType(id) {
    if (!confirm('Удалить тип оборудования? Если есть оборудование этого типа или дочерние типы, сервер откажет.')) return;
    try {
        const resp = await apiFetch(`/api/equipment-types/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Тип удалён', 'success');
        if (currentConstructorTypeId === id) {
            currentConstructorTypeId = null;
            document.getElementById('typeAttributesAssignmentBlock').style.display = 'none';
        }
        await loadEquipmentTypes();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Пул атрибутов
// ---------------------------------------------------------------------

async function loadAttributeDefinitions() {
    try {
        const resp = await apiFetch('/api/attribute-definitions');
        const attrs = await parseJsonResponse(resp);
        attributeDefinitionsCache = Array.isArray(attrs) ? attrs : [];
        renderAttributeDefinitionsList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Не удалось загрузить атрибуты', 'error');
    }
}

function renderAttributeDefinitionsList() {
    const el = document.getElementById('attributeDefinitionsList');
    if (!el) return;
    if (!attributeDefinitionsCache.length) {
        el.innerHTML = '<div class="no-data">Пул атрибутов пуст — добавьте первый выше</div>';
        return;
    }
    el.innerHTML = attributeDefinitionsCache.map(a => `
        <div class="knowledge-dict-row">
            <div>
                <div class="knowledge-dict-code">${escapeHtml(a.key)} · ${escapeHtml(a.value_type)}${a.group_name ? ' · ' + escapeHtml(a.group_name) : ''}</div>
                ${escapeHtml(a.label)}${a.unit ? ' (' + escapeHtml(a.unit) + ')' : ''}
            </div>
            <button class="btn btn-danger btn-sm" onclick="deleteAttributeDefinition(${a.id})" title="Удалить">
                <span class="icon icon-delete"></span>
            </button>
        </div>
    `).join('');
}

async function createAttributeDefinition() {
    const keyEl = document.getElementById('newAttrKey');
    const labelEl = document.getElementById('newAttrLabel');
    const groupEl = document.getElementById('newAttrGroup');
    const typeEl = document.getElementById('newAttrType');
    const unitEl = document.getElementById('newAttrUnit');
    const optionsEl = document.getElementById('newAttrOptions');

    const key = keyEl.value.trim().toLowerCase();
    const label = labelEl.value.trim();
    const value_type = typeEl.value;
    if (!key || !label) {
        showToast('Укажите ключ и подпись атрибута', 'error');
        return;
    }
    const options = optionsEl.value.trim()
        ? optionsEl.value.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    if (value_type === 'select' && !options.length) {
        showToast('Для типа "список" укажите варианты через запятую', 'error');
        return;
    }

    try {
        const resp = await apiFetch('/api/attribute-definitions', {
            method: 'POST',
            body: JSON.stringify({
                key, label, value_type,
                group_name: groupEl.value.trim() || null,
                unit: unitEl.value.trim() || null,
                options,
            }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания атрибута', 'error');
            return;
        }
        keyEl.value = ''; labelEl.value = ''; groupEl.value = ''; unitEl.value = ''; optionsEl.value = '';
        typeEl.value = 'text';
        showToast('Атрибут добавлен в пул', 'success');
        await loadAttributeDefinitions();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteAttributeDefinition(id) {
    if (!confirm('Удалить атрибут из пула? Если он назначен хотя бы одному типу, сервер откажет.')) return;
    try {
        const resp = await apiFetch(`/api/attribute-definitions/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Атрибут удалён', 'success');
        await loadAttributeDefinitions();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Назначение атрибутов типу (конструктор)
// ---------------------------------------------------------------------

async function selectConstructorType(typeId) {
    currentConstructorTypeId = typeId;
    const type = equipmentTypesCache.find(t => t.id === typeId);
    const block = document.getElementById('typeAttributesAssignmentBlock');
    const nameEl = document.getElementById('assignmentTypeName');
    const checklistEl = document.getElementById('typeAttributesChecklist');
    if (!block || !type) return;

    nameEl.textContent = equipmentTypeLabel(type);
    block.style.display = 'block';
    checklistEl.innerHTML = '<div class="no-data">Загрузка...</div>';

    try {
        const resp = await apiFetch(`/api/equipment-types/${typeId}/own-attributes`);
        const own = await parseJsonResponse(resp);
        const ownIds = new Set((Array.isArray(own) ? own : []).map(a => a.id));
        const requiredMap = {};
        (Array.isArray(own) ? own : []).forEach(a => { requiredMap[a.id] = !!a.is_required; });

        if (!attributeDefinitionsCache.length) {
            checklistEl.innerHTML = '<div class="no-data">Пул атрибутов пуст — сначала добавьте атрибуты слева</div>';
            return;
        }

        checklistEl.innerHTML = attributeDefinitionsCache.map(a => `
            <div class="knowledge-dict-row">
                <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-weight:400">
                    <input type="checkbox" class="type-attr-checkbox" value="${a.id}" ${ownIds.has(a.id) ? 'checked' : ''}>
                    ${escapeHtml(a.label)} <span class="knowledge-dict-code" style="margin-left:4px">${escapeHtml(a.key)}</span>
                </label>
                <label style="display:flex; align-items:center; gap:5px; font-size:11px; color:var(--color-text-muted); font-weight:400">
                    <input type="checkbox" class="type-attr-required" data-for="${a.id}" ${requiredMap[a.id] ? 'checked' : ''}>
                    обязательный
                </label>
            </div>
        `).join('');
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function saveTypeAttributes() {
    if (!currentConstructorTypeId) return;
    const checkboxes = document.querySelectorAll('.type-attr-checkbox:checked');
    const assignments = Array.from(checkboxes).map(cb => {
        const requiredCb = document.querySelector(`.type-attr-required[data-for="${cb.value}"]`);
        return {
            attribute_definition_id: Number(cb.value),
            is_required: requiredCb ? requiredCb.checked : false,
        };
    });

    try {
        const resp = await apiFetch(`/api/equipment-types/${currentConstructorTypeId}/attributes`, {
            method: 'PUT',
            body: JSON.stringify({ assignments }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения', 'error');
            return;
        }
        showToast('Атрибуты типа сохранены', 'success');
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Номенклатура (сами записи оборудования)
// ---------------------------------------------------------------------

async function loadEquipmentList() {
    const body = document.getElementById('equipmentListBody');
    if (!body) return;
    const typeFilter = document.getElementById('equipmentTypeFilter').value;
    const search = document.getElementById('equipmentSearchInput').value.trim();

    body.innerHTML = '<tr><td colspan="6" class="no-data">Загрузка...</td></tr>';
    try {
        const params = new URLSearchParams();
        if (typeFilter) params.set('type', typeFilter);
        if (search) params.set('search', search);
        const resp = await apiFetch('/api/equipment' + (params.toString() ? '?' + params.toString() : ''));
        const items = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<tr><td colspan="6" class="no-data">${escapeHtml(items.error || 'Ошибка')}</td></tr>`;
            return;
        }
        if (!Array.isArray(items) || !items.length) {
            body.innerHTML = '<tr><td colspan="6" class="no-data">Оборудования пока нет</td></tr>';
            return;
        }
        body.innerHTML = items.map(e => `
            <tr>
                <td>${escapeHtml(e.name)}</td>
                <td>${escapeHtml(e.equipment_type_name || '—')}</td>
                <td>${escapeHtml(e.article || '—')}</td>
                <td>${escapeHtml([e.workshop, e.location].filter(Boolean).join(' / ') || '—')}</td>
                <td>${e.criticality ? '●'.repeat(e.criticality) + '○'.repeat(5 - e.criticality) : '—'}</td>
                <td class="col-actions">
                    <button class="btn btn-secondary btn-sm" onclick="openEquipmentModal(${e.id})" title="Редактировать">
                        <span class="icon icon-edit"></span>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteEquipmentEntry(${e.id})" title="Удалить">
                        <span class="icon icon-delete"></span>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        body.innerHTML = `<tr><td colspan="6" class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</td></tr>`;
    }
}

const debouncedLoadEquipmentList = typeof debounce === 'function' ? debounce(loadEquipmentList, 300) : loadEquipmentList;
const equipmentSearchInputEl = document.getElementById('equipmentSearchInput');
if (equipmentSearchInputEl) {
    equipmentSearchInputEl.addEventListener('input', debouncedLoadEquipmentList);
}

// ---------------------------------------------------------------------
// Динамические поля specs — сердце вкладки
// ---------------------------------------------------------------------

function renderDynamicSpecsFields(attrs, values) {
    const container = document.getElementById('equipmentSpecsFields');
    values = values || {};
    if (!attrs.length) {
        container.innerHTML = '';
        return;
    }

    let currentGroup = null;
    let html = '';
    attrs.forEach(a => {
        if (a.group_name !== currentGroup) {
            currentGroup = a.group_name;
            if (currentGroup) {
                html += `<div class="section-title" style="margin-top:16px">${escapeHtml(currentGroup)}</div>`;
            }
        }
        const val = values[a.key] !== undefined ? values[a.key] : (a.default_value || '');
        const label = `${escapeHtml(a.label)}${a.unit ? ' (' + escapeHtml(a.unit) + ')' : ''}${a.is_required ? ' *' : ''}`;

        html += '<div class="form-group">';
        html += `<label>${label}</label>`;
        if (a.value_type === 'textarea') {
            html += `<textarea class="equipment-spec-field" data-key="${a.key}">${escapeHtml(val)}</textarea>`;
        } else if (a.value_type === 'select') {
            const opts = (a.options || []).map(o =>
                `<option value="${escapeHtml(o)}" ${o === val ? 'selected' : ''}>${escapeHtml(o)}</option>`
            ).join('');
            html += `<select class="equipment-spec-field" data-key="${a.key}"><option value="">— не выбрано —</option>${opts}</select>`;
        } else if (a.value_type === 'boolean') {
            html += `<input type="checkbox" class="equipment-spec-field" data-key="${a.key}" data-type="boolean" ${val ? 'checked' : ''}>`;
        } else {
            const inputType = a.value_type === 'number' ? 'number' : 'text';
            html += `<input type="${inputType}" class="equipment-spec-field" data-key="${a.key}" value="${escapeHtml(String(val))}">`;
        }
        html += '</div>';
    });
    container.innerHTML = html;
}

function collectSpecsFromForm() {
    const specs = {};
    document.querySelectorAll('.equipment-spec-field').forEach(field => {
        const key = field.dataset.key;
        if (field.dataset.type === 'boolean') {
            specs[key] = field.checked;
        } else if (field.value !== '') {
            specs[key] = field.value;
        }
    });
    return specs;
}

async function onEquipmentTypeChange(existingSpecs) {
    const typeId = document.getElementById('equipmentTypeSelect').value;
    if (!typeId) {
        renderDynamicSpecsFields([], {});
        return;
    }
    try {
        const resp = await apiFetch(`/api/equipment-types/${typeId}/attributes`);
        const attrs = await parseJsonResponse(resp);
        renderDynamicSpecsFields(Array.isArray(attrs) ? attrs : [], existingSpecs || {});
    } catch (e) {
        showToast(e && e.message ? e.message : 'Не удалось загрузить поля типа', 'error');
    }
}

// ---------------------------------------------------------------------
// Модалка добавления/редактирования
// ---------------------------------------------------------------------

function clearEquipmentForm() {
    document.getElementById('equipmentId').value = '';
    document.getElementById('equipmentTypeSelect').value = '';
    document.getElementById('equipmentName').value = '';
    document.getElementById('equipmentArticle').value = '';
    document.getElementById('equipmentManufacturer').value = '';
    document.getElementById('equipmentSerialNumber').value = '';
    document.getElementById('equipmentWorkshop').value = '';
    document.getElementById('equipmentLocation').value = '';
    document.getElementById('equipmentFirmware').value = '';
    document.getElementById('equipmentCriticality').value = '';
    document.getElementById('equipmentNote').value = '';
    renderDynamicSpecsFields([], {});
}

async function openEquipmentModal(id) {
    clearEquipmentForm();
    const titleEl = document.getElementById('equipmentModalTitle');

    if (id) {
        titleEl.innerHTML = '<span class="icon icon-package-2"></span> Редактирование оборудования';
        try {
            const resp = await apiFetch(`/api/equipment/${id}`);
            const item = await parseJsonResponse(resp);
            if (!resp.ok) {
                showToast(item.error || 'Не удалось загрузить оборудование', 'error');
                return;
            }
            document.getElementById('equipmentId').value = item.id;
            document.getElementById('equipmentName').value = item.name || '';
            document.getElementById('equipmentArticle').value = item.article || '';
            document.getElementById('equipmentManufacturer').value = item.manufacturer || '';
            document.getElementById('equipmentSerialNumber').value = item.serial_number || '';
            document.getElementById('equipmentWorkshop').value = item.workshop || '';
            document.getElementById('equipmentLocation').value = item.location || '';
            document.getElementById('equipmentFirmware').value = item.firmware_version || '';
            document.getElementById('equipmentCriticality').value = item.criticality || '';
            document.getElementById('equipmentNote').value = item.note || '';
            document.getElementById('equipmentTypeSelect').value = item.equipment_type_id;
            await onEquipmentTypeChange(item.specs || {});
        } catch (e) {
            showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
            return;
        }
    } else {
        titleEl.innerHTML = '<span class="icon icon-package-2"></span> Новое оборудование';
    }

    document.getElementById('equipmentModal').classList.add('active');
}

function closeEquipmentModal() {
    document.getElementById('equipmentModal').classList.remove('active');
}

async function submitEquipment() {
    const id = document.getElementById('equipmentId').value;
    const equipment_type_id = document.getElementById('equipmentTypeSelect').value;
    const name = document.getElementById('equipmentName').value.trim();

    if (!equipment_type_id) {
        showToast('Выберите тип оборудования', 'error');
        return;
    }
    if (!name) {
        showToast('Наименование обязательно', 'error');
        return;
    }

    const criticalityRaw = document.getElementById('equipmentCriticality').value;
    const payload = {
        equipment_type_id: Number(equipment_type_id),
        name,
        article: document.getElementById('equipmentArticle').value.trim(),
        manufacturer: document.getElementById('equipmentManufacturer').value.trim(),
        serial_number: document.getElementById('equipmentSerialNumber').value.trim(),
        workshop: document.getElementById('equipmentWorkshop').value.trim(),
        location: document.getElementById('equipmentLocation').value.trim(),
        firmware_version: document.getElementById('equipmentFirmware').value.trim(),
        criticality: criticalityRaw ? Number(criticalityRaw) : null,
        note: document.getElementById('equipmentNote').value.trim(),
        specs: collectSpecsFromForm(),
    };

    try {
        const resp = id
            ? await apiFetch(`/api/equipment/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
            : await apiFetch('/api/equipment', { method: 'POST', body: JSON.stringify(payload) });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения', 'error');
            return;
        }
        showToast(id ? 'Оборудование обновлено' : 'Оборудование добавлено', 'success');
        closeEquipmentModal();
        await loadEquipmentList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteEquipmentEntry(id) {
    if (!confirm('Удалить запись оборудования?')) return;
    try {
        const resp = await apiFetch(`/api/equipment/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Оборудование удалено', 'success');
        await loadEquipmentList();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}
