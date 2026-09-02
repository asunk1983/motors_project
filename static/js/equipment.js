// static/js/equipment.js — вкладка "Оборудование".
// Подвкладка "Номенклатура" открыта всем ролям (как каталог двигателей).
// Подвкладка "Конструктор типов" скрыта для не-admin в auth.js, а
// пишущие роуты конструктора на бэкенде защищены _require_admin —
// см. routes/equipment_routes.py. Использует apiFetch/parseJsonResponse/
// showToast/escapeHtml/debounce из auth.js/common.js.

let equipmentTypesCache = [];
let attributeDefinitionsCache = [];
let currentConstructorTypeId = null;
let equipmentFormLocationPicker = null;

// ===== Сортировка/пагинация/динамические колонки (ТЗ 3.2) =====
// Тот же паттерн, что catalog.js (currentSort/currentPage/pageSize/
// applyDynamicPageSize) — сортировка на backend (whitelist колонок),
// пагинация полностью на клиенте (backend возвращает весь
// отфильтрованный список, как и для engines).
let allEquipment = [];
let equipmentCurrentSort = { field: null, order: 'DESC' }; // field=null -> backend сам берёт updated_at DESC
let equipmentCurrentPage = 1;
let equipmentPageSize = 20; // пересчитывается динамически, см. applyDynamicEquipmentPageSize
let equipmentShowInListAttrs = []; // [] когда фильтр "Тип" = "Все типы"

// ===== Фото (ТЗ 3.3) =====
// pendingPhotoFiles — тот же паттерн, что exportManager.js для двигателей:
// очередь File-объектов, ещё НЕ загруженных на сервер, отправляется одним
// проходом после успешного submitEquipment() (что при создании новой
// записи, что при добавлении фото к уже существующей — id известен в
// обоих случаях к моменту загрузки).
// equipmentExistingPhotos — уже сохранённые на сервере фото (только в
// режиме редактирования); удаление такого фото бьёт по API немедленно
// (тот же паттерн, что engineCard.js для карточки двигателя) — отменять
// тут нечего, файл и так уже физически на диске.
let equipmentPendingPhotoFiles = [];
let equipmentExistingPhotos = [];
let equipmentSelectedExportIds = new Set();

// ---------------------------------------------------------------------
// Вкладка / подвкладки
// ---------------------------------------------------------------------

async function loadEquipmentTab() {
    await loadEquipmentTypes();
    await loadAttributeDefinitions();
    if (typeof loadEquipmentLocationTree === 'function') await loadEquipmentLocationTree();
    await loadEquipmentList();
}

function switchEquipmentSubtab(name) {
    document.querySelectorAll('#tab-equipment .info-subtab-content').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('equipmentSubtab-' + name);
    if (target) target.classList.add('active');

    const listBtn = document.getElementById('equipmentSubtabListBtn');
    const constructorBtn = document.getElementById('equipmentSubtabConstructorBtn');
    const stockBtn = document.getElementById('equipmentSubtabStockBtn');
    if (listBtn) listBtn.className = 'btn btn-sm ' + (name === 'list' ? 'btn-primary' : 'btn-secondary');
    if (constructorBtn) constructorBtn.className = 'btn btn-sm ' + (name === 'constructor' ? 'btn-primary' : 'btn-secondary');
    if (stockBtn) stockBtn.className = 'btn btn-sm ' + (name === 'stock' ? 'btn-primary' : 'btn-secondary');

    if (name === 'stock') loadStockSummary();
    // При возврате на "Список" подвкладка только что стала видимой —
    // пока она была скрыта, applyDynamicEquipmentPageSize (дёрнутый
    // ResizeObserver'ом на скрытии/показе) не мог ничего измерить и не
    // трогал pageSize (см. recalcEquipmentPageSize). Явно пересчитываем
    // и перерисовываем сейчас, когда размеры уже реальные — иначе список
    // может остаться со старым/некорректным pageSize до следующего
    // F5 или ухода на другую вкладку.
    if (name === 'list') {
        renderEquipmentTable();
        applyDynamicEquipmentPageSize();
    }
}

// ---------------------------------------------------------------------
// Учёт ЗИП (ТЗ 3.7)
// ---------------------------------------------------------------------

async function loadStockSummary() {
    const body = document.getElementById('stockSummaryBody');
    if (!body) return;
    body.innerHTML = '<tr><td colspan="7" class="no-data">Загрузка...</td></tr>';
    try {
        const resp = await apiFetch('/api/equipment/stock-summary');
        const rows = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(rows.error || 'Ошибка')}</td></tr>`;
            return;
        }
        renderStockSummary(Array.isArray(rows) ? rows : []);
    } catch (e) {
        body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</td></tr>`;
    }
}

function renderStockSummary(rows) {
    const body = document.getElementById('stockSummaryBody');
    if (!body) return;
    if (rows.length === 0) {
        body.innerHTML = '<tr><td colspan="7" class="no-data">Типов оборудования пока нет</td></tr>';
        return;
    }
    // "Не размещено" — колонка показывается только если хотя бы у ОДНОГО
    // типа unlocated > 0 (ТЗ: "показывается только если для типа
    // unlocated > 0" — трактуем как "видна в таблице целиком, когда есть
    // о чём сообщить", а не мигающую разную ширину строк по отдельности).
    const showUnlocated = rows.some(r => r.unlocated > 0);
    const theadRow = document.querySelector('#stockSummaryTable thead tr');
    if (theadRow) {
        theadRow.innerHTML = `
            <th>Тип</th><th>Всего</th><th>В эксплуатации</th><th>В ЗИП</th>
            ${showUnlocated ? '<th>Не размещено</th>' : ''}
            <th>Норма</th><th>Дефицит</th>
        `;
    }

    body.innerHTML = rows.map(r => {
        const hasDeficit = r.deficit !== null && r.deficit > 0;
        const deficitText = r.deficit === null ? '—' : (r.deficit > 0 ? `−${r.deficit} (докупить)` : '0');
        return `
            <tr class="${hasDeficit ? 'stock-deficit-row' : ''}">
                <td>${escapeHtml(r.name)}</td>
                <td>${r.total}</td>
                <td>${r.in_use}</td>
                <td>${r.in_stock}</td>
                ${showUnlocated ? `<td>${r.unlocated > 0 ? r.unlocated : '—'}</td>` : ''}
                <td>
                    <input type="number" min="0" class="stock-min-qty-input" value="${r.min_stock_qty !== null ? r.min_stock_qty : ''}"
                           placeholder="—" onchange="updateMinStockQty(${r.equipment_type_id}, this.value)">
                </td>
                <td class="${hasDeficit ? 'stock-deficit-value' : ''}">${escapeHtml(deficitText)}</td>
            </tr>
        `;
    }).join('');
}

function updateMinStockQty(typeId, rawValue) {
    const value = rawValue.trim();
    const payload = { min_stock_qty: value === '' ? null : Number(value) };
    apiFetch(`/api/equipment-types/${typeId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                loadStockSummary(); // откатить инпут, если backend отказал
                return;
            }
            loadStockSummary();
        })
        .catch(e => {
            showToast('Ошибка: ' + e.message, 'error', 'icon-cancel');
            loadStockSummary();
        });
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
        const showInListMap = {};
        (Array.isArray(own) ? own : []).forEach(a => {
            requiredMap[a.id] = !!a.is_required;
            showInListMap[a.id] = !!a.show_in_list;
        });

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
                <label style="display:flex; align-items:center; gap:5px; font-size:11px; color:var(--color-text-muted); font-weight:400" title="Показывать колонкой в таблице номенклатуры, когда выбран этот тип">
                    <input type="checkbox" class="type-attr-show-in-list" data-for="${a.id}" ${showInListMap[a.id] ? 'checked' : ''}>
                    в списке
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
        const showInListCb = document.querySelector(`.type-attr-show-in-list[data-for="${cb.value}"]`);
        return {
            attribute_definition_id: Number(cb.value),
            is_required: requiredCb ? requiredCb.checked : false,
            show_in_list: showInListCb ? showInListCb.checked : false,
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

    body.innerHTML = '<tr><td colspan="7" class="no-data">Загрузка...</td></tr>';
    try {
        const params = new URLSearchParams();
        if (typeFilter) params.set('type', typeFilter);
        if (search) params.set('search', search);
        if (typeof equipmentActiveLocationId !== 'undefined' && equipmentActiveLocationId !== null) {
            // Псевдо-узел "Без места" шлём отдельным флагом unassigned=1, а
            // НЕ через location_node_id='unassigned' — Flask при type=int
            // молча проглатывает строку до None, и фильтр теряется
            // (та же проблема, что зафиксирована в incoming-реализации).
            if (equipmentActiveLocationId === 'unassigned') {
                params.set('unassigned', '1');
            } else {
                params.set('location_node_id', equipmentActiveLocationId);
            }
        }
        if (equipmentCurrentSort.field) {
            params.set('sort', equipmentCurrentSort.field);
            params.set('order', equipmentCurrentSort.order.toLowerCase());
        }
        // Фильтры по атрибутам (ТЗ 3.4) — только когда выбран конкретный
        // тип (см. onEquipmentTypeFilterChange, которая и рендерит поля).
        if (typeFilter) {
            const attrFilters = collectEquipmentAttrFilters();
            Object.keys(attrFilters).forEach(key => params.set(`attr_${key}`, attrFilters[key]));
        }
        const resp = await apiFetch('/api/equipment' + (params.toString() ? '?' + params.toString() : ''));
        const items = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(items.error || 'Ошибка')}</td></tr>`;
            return;
        }
        allEquipment = Array.isArray(items) ? items : [];

        // Динамические колонки (ТЗ 3.2) — только когда выбран КОНКРЕТНЫЙ
        // тип (список однороден); "Все типы" -> обычные 5 колонок.
        if (typeFilter) {
            const attrsResp = await apiFetch(`/api/equipment-types/${typeFilter}/show-in-list-attributes`);
            const attrs = await parseJsonResponse(attrsResp);
            equipmentShowInListAttrs = attrsResp.ok && Array.isArray(attrs) ? attrs : [];
        } else {
            equipmentShowInListAttrs = [];
        }

        equipmentCurrentPage = 1;
        renderEquipmentTableHeaders();
        renderEquipmentTable();
        applyDynamicEquipmentPageSize();
    } catch (e) {
        body.innerHTML = `<tr><td colspan="7" class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</td></tr>`;
    }
}

function sortEquipmentTable(field) {
    if (equipmentCurrentSort.field === field) {
        equipmentCurrentSort.order = equipmentCurrentSort.order === 'ASC' ? 'DESC' : 'ASC';
    } else {
        equipmentCurrentSort.field = field;
        equipmentCurrentSort.order = 'ASC';
    }
    loadEquipmentList();
}

function renderEquipmentTableHeaders() {
    const theadRow = document.querySelector('#equipmentTableWrapper thead tr');
    if (!theadRow) return;
    // Место — намеренно НЕ sortable (ТЗ 3.2): workshop — переходное текстовое
    // поле, не гарантированно заполнено у новых записей; навигация по месту
    // уже полностью закрыта деревом слева (equipmentLocationTree.js).
    let html = `
        <th class="col-checkbox"><input type="checkbox" id="equipmentSelectAllCheckbox" onchange="toggleEquipmentSelectAll(this.checked)"></th>
        <th class="sortable" onclick="sortEquipmentTable('name')">Наименование${_equipmentSortArrow('name')}</th>
        <th class="sortable" onclick="sortEquipmentTable('equipment_type_name')">Тип${_equipmentSortArrow('equipment_type_name')}</th>
        <th class="sortable" onclick="sortEquipmentTable('article')">Артикул${_equipmentSortArrow('article')}</th>
        <th>Место</th>
    `;
    equipmentShowInListAttrs.forEach(a => {
        html += `<th>${escapeHtml(a.label)}${a.unit ? ` (${escapeHtml(a.unit)})` : ''}</th>`;
    });
    html += `
        <th class="sortable" onclick="sortEquipmentTable('criticality')">Критичность${_equipmentSortArrow('criticality')}</th>
        <th class="col-actions">Действия</th>
    `;
    theadRow.innerHTML = html;
}

function _equipmentSortArrow(field) {
    if (equipmentCurrentSort.field !== field) return ' ↕';
    return equipmentCurrentSort.order === 'ASC' ? ' ▲' : ' ▼';
}

function renderEquipmentTable() {
    const body = document.getElementById('equipmentListBody');
    if (!body) return;
    if (!allEquipment.length) {
        const colspan = 7 + equipmentShowInListAttrs.length;
        body.innerHTML = `<tr><td colspan="${colspan}" class="no-data">Оборудования пока нет</td></tr>`;
        const pageInfoEmpty = document.getElementById('equipmentPageInfo');
        if (pageInfoEmpty) pageInfoEmpty.textContent = 'Показано 0 из 0';
        return;
    }

    const start = (equipmentCurrentPage - 1) * equipmentPageSize;
    const end = start + equipmentPageSize;
    const pageData = allEquipment.slice(start, end);

    body.innerHTML = pageData.map(e => {
        // Место в таблице списка — сначала placements (equipment_placement,
        // ТЗ "Места установки"), только если их нет вообще — старое
        // legacy location_name/workshop/location (переходный период, обе
        // колонки не показываются одновременно, чтобы не дублировать
        // смысл). placement_count/placement_location_name — из
        // list_equipment (equipment_repo.py), первое место + "+N", если
        // мест несколько (полный список — в самой карточке).
        let locationDisplay = '—';
        if (e.placement_count > 0) {
            locationDisplay = escapeHtml(e.placement_location_name || '—') +
                (e.placement_count > 1 ? ` <span class="placement-count-badge">+${e.placement_count - 1}</span>` : '');
        } else {
            locationDisplay = escapeHtml(e.location_name || [e.workshop, e.location].filter(Boolean).join(' / ') || '—');
        }
        let dynamicCells = '';
        equipmentShowInListAttrs.forEach(a => {
            const val = e.specs && e.specs[a.key] !== undefined && e.specs[a.key] !== '' ? e.specs[a.key] : null;
            dynamicCells += `<td>${val !== null ? escapeHtml(String(val)) + (a.unit ? ' ' + escapeHtml(a.unit) : '') : '—'}</td>`;
        });
        return `
            <tr class="clickable-row" data-id="${e.id}" onclick="openEquipmentModal(${e.id})">
                <td class="col-checkbox" onclick="event.stopPropagation()"><input type="checkbox" class="equipment-row-checkbox" ${equipmentSelectedExportIds.has(e.id) ? 'checked' : ''} onchange="toggleEquipmentSelection(${e.id}, this.checked)"></td>
                <td>${escapeHtml(e.name)}</td>
                <td>${escapeHtml(e.equipment_type_name || '—')}</td>
                <td>${escapeHtml(e.article || '—')}</td>
                <td>${locationDisplay}</td>
                ${dynamicCells}
                <td>${e.criticality ? '●'.repeat(e.criticality) + '○'.repeat(5 - e.criticality) : '—'}</td>
                <td class="col-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-secondary btn-sm" onclick="openEquipmentModal(${e.id}, true)" title="Редактировать">
                        <span class="icon icon-edit"></span>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteEquipmentEntry(${e.id})" title="Удалить">
                        <span class="icon icon-delete"></span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    const pageInfoEl = document.getElementById('equipmentPageInfo');
    const pageNumberEl = document.getElementById('equipmentPageNumber');
    if (pageInfoEl) {
        const rangeStart = start + 1;
        const rangeEnd = start + pageData.length;
        pageInfoEl.textContent = `${rangeStart}-${rangeEnd} из ${allEquipment.length}`;
    }
    if (pageNumberEl) pageNumberEl.textContent = equipmentCurrentPage;
    updateEquipmentSelectAllState();
}

// ===== ВЫБОР ОБОРУДОВАНИЯ ДЛЯ ЭКСПОРТА (ТЗ 3.6) =====
function toggleEquipmentSelection(id, checked) {
    if (checked) equipmentSelectedExportIds.add(id);
    else equipmentSelectedExportIds.delete(id);
    updateEquipmentSelectAllState();
    updateEquipmentExportButton();
}

function toggleEquipmentSelectAll(checked) {
    document.querySelectorAll('.equipment-row-checkbox').forEach(cb => {
        cb.checked = checked;
        const id = parseInt(cb.closest('tr').dataset.id, 10);
        if (checked) equipmentSelectedExportIds.add(id);
        else equipmentSelectedExportIds.delete(id);
    });
    updateEquipmentSelectAllState();
    updateEquipmentExportButton();
}

function updateEquipmentSelectAllState() {
    const checkboxes = document.querySelectorAll('.equipment-row-checkbox');
    const checked = Array.from(checkboxes).filter(cb => cb.checked);
    const selectAll = document.getElementById('equipmentSelectAllCheckbox');
    if (!selectAll) return;
    if (checkboxes.length === 0) { selectAll.checked = false; selectAll.indeterminate = false; }
    else if (checked.length === checkboxes.length) { selectAll.checked = true; selectAll.indeterminate = false; }
    else if (checked.length > 0) { selectAll.checked = false; selectAll.indeterminate = true; }
    else { selectAll.checked = false; selectAll.indeterminate = false; }
}

function updateEquipmentExportButton() {
    const count = equipmentSelectedExportIds.size;
    const btn = document.getElementById('equipmentExportBtn');
    const info = document.getElementById('equipmentSelectionInfo');
    const countEl = document.getElementById('equipmentSelectionCount');
    if (btn) btn.disabled = count === 0;
    if (info) info.classList.toggle('hidden', count === 0);
    if (countEl) countEl.textContent = count;
}

function exportSelectedEquipment() {
    const ids = Array.from(equipmentSelectedExportIds);
    if (ids.length === 0) {
        showToast('Не выбрано ни одной записи', 'warning', 'icon-warning');
        return;
    }
    showToast('Подготовка экспорта...', 'info', 'icon-progress-activity');
    apiFetch('/api/equipment/export', {
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
            a.download = `equipment_export_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast('Экспорт завершён', 'success', 'icon-check-circle');
        })
        .catch(e => showToast('Ошибка экспорта: ' + e.message, 'error', 'icon-cancel'));
}

function prevEquipmentPage() {
    if (equipmentCurrentPage > 1) { equipmentCurrentPage--; renderEquipmentTable(); }
}

function nextEquipmentPage() {
    if (equipmentCurrentPage * equipmentPageSize < allEquipment.length) { equipmentCurrentPage++; renderEquipmentTable(); }
}

// ===== Динамический pageSize (ТЗ 3.2, тот же паттерн, что catalog.js) =====
// ВАЖНО: скоуп СТРОГО по #equipmentTableWrapper (id, не общий класс
// .table-wrapper) — на странице одновременно присутствует .table-wrapper
// каталога двигателей; document.querySelector('.table-wrapper') без
// уточнения id вернул бы ЧУЖУЮ обёртку (первую в DOM), что дало бы
// equipmentPageSize, посчитанный по высоте таблицы каталога, а не
// оборудования.
function recalcEquipmentPageSize() {
    const wrapper = document.getElementById('equipmentTableWrapper');
    const tbody = document.getElementById('equipmentListBody');
    if (!wrapper || !tbody) return equipmentPageSize;

    const headerRow = wrapper.querySelector('thead tr');
    const bodyRow = tbody.querySelector('tr');
    const hasRealRow = bodyRow && !bodyRow.querySelector('.no-data');
    const headerHeight = headerRow ? headerRow.getBoundingClientRect().height : 44;
    const rowHeight = hasRealRow ? bodyRow.getBoundingClientRect().height : 43;

    // Подвкладка "Список" скрыта через display:none (см.
    // switchEquipmentSubtab) — ResizeObserver на #equipmentTableWrapper
    // всё равно срабатывает при таком скрытии (высота падает до 0), и
    // тогда wrapper.clientHeight/headerHeight/rowHeight все = 0.
    // Math.floor(0 / 0) даёт NaN, а Math.max(NaN, 5) возвращает NaN (а не
    // 5!) — из-за этого equipmentPageSize/equipmentCurrentPage превращались
    // в NaN, и таблица рендерилась пустой ЕЩЁ ПОКА подвкладка была скрыта.
    // При возврате на "Список" уже испорченное состояние просто
    // показывалось как есть (switchEquipmentSubtab не перерисовывает
    // таблицу) — отсюда пустой equipmentTableWrapper, пока не сделать F5.
    // Если измерить нечего (скрыто/ещё не отрисовано) — не трогаем текущий
    // pageSize.
    if (!wrapper.clientHeight || !headerHeight || !rowHeight) {
        return equipmentPageSize;
    }

    const available = wrapper.clientHeight - headerHeight;
    const fit = Math.floor(available / rowHeight);
    return Math.max(fit, 5);
}

function applyDynamicEquipmentPageSize() {
    const next = recalcEquipmentPageSize();
    if (next === equipmentPageSize) return;
    const firstVisibleIndex = (equipmentCurrentPage - 1) * equipmentPageSize;
    equipmentPageSize = next;
    equipmentCurrentPage = Math.max(1, Math.floor(firstVisibleIndex / equipmentPageSize) + 1);
    renderEquipmentTable();
}

const debouncedApplyDynamicEquipmentPageSize = typeof debounce === 'function'
    ? debounce(applyDynamicEquipmentPageSize, 150)
    : applyDynamicEquipmentPageSize;

document.addEventListener('DOMContentLoaded', function () {
    const equipmentTableWrapperEl = document.getElementById('equipmentTableWrapper');
    if (equipmentTableWrapperEl && typeof ResizeObserver !== 'undefined') {
        new ResizeObserver(debouncedApplyDynamicEquipmentPageSize).observe(equipmentTableWrapperEl);
    }
});

const debouncedLoadEquipmentList = typeof debounce === 'function' ? debounce(loadEquipmentList, 300) : loadEquipmentList;
const equipmentSearchInputEl = document.getElementById('equipmentSearchInput');
if (equipmentSearchInputEl) {
    equipmentSearchInputEl.addEventListener('input', debouncedLoadEquipmentList);
}

// ---------------------------------------------------------------------
// Динамические поля specs — сердце вкладки
// ---------------------------------------------------------------------

function renderDynamicSpecsFields(attrs, values, containerId = 'equipmentSpecsFields', fieldClass = 'equipment-spec-field') {
    const container = document.getElementById(containerId);
    if (!container) return;
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
            html += `<textarea class="${fieldClass}" data-key="${a.key}">${escapeHtml(val)}</textarea>`;
        } else if (a.value_type === 'select') {
            const opts = (a.options || []).map(o =>
                `<option value="${escapeHtml(o)}" ${o === val ? 'selected' : ''}>${escapeHtml(o)}</option>`
            ).join('');
            html += `<select class="${fieldClass}" data-key="${a.key}"><option value="">— не выбрано —</option>${opts}</select>`;
        } else if (a.value_type === 'boolean') {
            html += `<input type="checkbox" class="${fieldClass}" data-key="${a.key}" data-type="boolean" ${val ? 'checked' : ''}>`;
        } else {
            const inputType = a.value_type === 'number' ? 'number' : 'text';
            html += `<input type="${inputType}" class="${fieldClass}" data-key="${a.key}" value="${escapeHtml(String(val))}">`;
        }
        html += '</div>';
    });
    container.innerHTML = html;
}

// ===== Фильтры по значениям атрибутов (ТЗ 3.4) =====
// Отдельный класс equipment-filter-field (НЕ equipment-spec-field) — оба
// набора полей могут одновременно присутствовать в DOM (тулбар списка +
// скрытая модалка формы), и collectSpecsFromForm() ниже перебирает ИМЕННО
// .equipment-spec-field через querySelectorAll БЕЗ скоупа на модалку —
// общий класс подхватил бы и поля фильтра тоже.
function onEquipmentTypeFilterChange() {
    const typeId = document.getElementById('equipmentTypeFilter').value;
    if (!typeId) {
        renderDynamicSpecsFields([], {}, 'equipmentAttrFiltersContainer', 'equipment-filter-field');
        loadEquipmentList();
        return;
    }
    apiFetch(`/api/equipment-types/${typeId}/attributes`)
        .then(r => r.json())
        .then(attrs => {
            renderDynamicSpecsFields(Array.isArray(attrs) ? attrs : [], {}, 'equipmentAttrFiltersContainer', 'equipment-filter-field');
            _wireEquipmentAttrFilterListeners();
            loadEquipmentList();
        })
        .catch(() => loadEquipmentList());
}

// Живые обработчики на только что отрисованные поля фильтра — без этого
// значения применялись бы только при следующей смене типа/поиска, а не
// сразу при вводе (та же debounce-логика, что и у обычного поискового
// инпута ниже).
function _wireEquipmentAttrFilterListeners() {
    const debouncedReload = typeof debounce === 'function' ? debounce(loadEquipmentList, 350) : loadEquipmentList;
    document.querySelectorAll('#equipmentAttrFiltersContainer .equipment-filter-field').forEach(field => {
        const eventName = (field.tagName === 'SELECT' || field.dataset.type === 'boolean') ? 'change' : 'input';
        field.addEventListener(eventName, debouncedReload);
    });
}

function collectEquipmentAttrFilters() {
    const filters = {};
    document.querySelectorAll('#equipmentAttrFiltersContainer .equipment-filter-field').forEach(field => {
        const key = field.dataset.key;
        let value;
        if (field.dataset.type === 'boolean') {
            value = field.checked ? 'true' : '';
        } else {
            value = field.value;
        }
        if (value !== '' && value !== undefined && value !== null) {
            filters[key] = value;
        }
    });
    return filters;
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

// Кнопка "+" у узла в боковом дереве мест (equipmentLocationTree.js) —
// открыть форму создания сразу с предзаполненным «основным» местом.
//
// До правки: предзаполнение через пикер equipmentLocationInput (setValue).
// После правки: пикер на одиночном поле удалён, setValue стал no-op.
// Поведение сохранено косвенно: selectEquipmentLocation (дерево) уже
// выставил equipmentActiveLocationId = nodeId к моменту клика «+», а
// submitEquipment для новой записи берёт location_node_id именно оттуда
// (см. submitEquipment). То есть «+» у узла X по-прежнему приводит к
// созданию записи с location_node_id = X. Явная передача label здесь
// больше не нужна — она никуда не записывается.
function createEquipmentAtLocation(nodeId, label) {
    openEquipmentModal(null).then(() => {
        // no-op: пикера нет, location_node_id возьмётся из
        // equipmentActiveLocationId в submitEquipment.
    });
}

function clearEquipmentForm() {
    document.getElementById('equipmentId').value = '';
    document.getElementById('equipmentDetailView').innerHTML = '';
    document.getElementById('equipmentTypeSelect').value = '';
    document.getElementById('equipmentName').value = '';
    document.getElementById('equipmentArticle').value = '';
    document.getElementById('equipmentManufacturer').value = '';
    document.getElementById('equipmentCriticality').value = '';
    document.getElementById('equipmentNote').value = '';
    renderDynamicSpecsFields([], {});

    // Пикер места (ТЗ 3.1) — больше НЕ создаём на старом одиночном поле
    // «Место» (input#equipmentLocationInput удалён из HTML; location_node_id
    // теперь формируется в submitEquipment из equipmentActiveLocationId —
    // см. комментарий там же). Если по какой-то причине старый инстанс
    // пикера ещё жив (например, форма открывалась до этой правки), снимаем
    // с него слушатели/DOM-обёртку и забываем — чтобы destroy() в incidents
    // и пр. случайно не дёрнули обработчики удалённого inputEl.
    if (equipmentFormLocationPicker && equipmentFormLocationPicker.destroy) {
        equipmentFormLocationPicker.destroy();
        equipmentFormLocationPicker = null;
    }

    equipmentPendingPhotoFiles = [];
    equipmentExistingPhotos = [];
    renderEquipmentPendingPhotos();
    renderEquipmentExistingPhotos();

    // Места — тот же повод переинициализировать пикер, что и у
    // equipmentFormLocationPicker чуть выше: форма/модалка переоткрывается
    // на одном и том же DOM, старый инстанс пикера (если форма добавления
    // места была открыта в прошлый раз) нужно снять явно.
    if (equipmentPlacementFormPicker && equipmentPlacementFormPicker.destroy) {
        equipmentPlacementFormPicker.destroy();
        equipmentPlacementFormPicker = null;
    }
    equipmentPlacements = [];
    // Секцию мест целиком убираем из DOM здесь, а не просто чистим
    // innerHTML — при открытии "Новое оборудование" (create-режим)
    // _fillEquipmentEditFields() вообще не вызывается (equipment_id ещё
    // нет), значит секция без этого продолжала бы висеть в форме с
    // данными ПРЕДЫДУЩЕЙ открытой карточки до следующего edit существующей
    // записи.
    const placementsMount = document.getElementById('equipmentPlacementsSection');
    if (placementsMount) placementsMount.remove();
}

function renderEquipmentPendingPhotos() {
    const wrap = document.getElementById('equipmentPhotosPreview');
    if (!wrap) return;
    wrap.innerHTML = '';
    equipmentPendingPhotoFiles.forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const box = document.createElement('div');
        box.className = 'photo-thumb is-pending';
        box.innerHTML = `<img src="${url}" alt="Новое фото (не загружено)"><button type="button" class="photo-thumb-crop" title="Обрезать" onclick="openCropModal('equipmentPending', ${idx})"><span class="icon icon-content-cut"></span></button><button type="button" class="photo-thumb-remove" title="Убрать из выбора" onclick="removeEquipmentPendingPhoto(${idx})"><span class="icon icon-close"></span></button>`;
        wrap.appendChild(box);
    });
}

function removeEquipmentPendingPhoto(idx) {
    equipmentPendingPhotoFiles.splice(idx, 1);
    renderEquipmentPendingPhotos();
}

function renderEquipmentExistingPhotos() {
    const wrap = document.getElementById('equipmentPhotosGallery');
    if (!wrap) return;
    if (equipmentExistingPhotos.length === 0) {
        wrap.innerHTML = '';
        return;
    }
    wrap.innerHTML = equipmentExistingPhotos.map(p => {
        const safeFilename = escapeAttr(p.filename);
        const safePath = escapeAttr(p.path);
        return `<div class="photo-thumb">
            <img src="${authPhotoUrl(p.path)}" alt="Фото оборудования">
            <button type="button" class="photo-thumb-crop" title="Обрезать" onclick="openCropModal('existing', '${safeFilename}', '${safePath}', 'equipment')"><span class="icon icon-content-cut"></span></button>
            <button type="button" class="photo-thumb-remove" title="Удалить фото" onclick="deleteEquipmentExistingPhoto('${safeFilename}')"><span class="icon icon-close"></span></button>
        </div>`;
    }).join('');
}

function deleteEquipmentExistingPhoto(filename) {
    const equipmentId = document.getElementById('equipmentId').value;
    if (!equipmentId) return;
    if (!confirm('Удалить это фото?')) return;
    apiFetch(`/api/equipment/${equipmentId}/photos/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            equipmentExistingPhotos = equipmentExistingPhotos.filter(p => p.filename !== filename);
            currentPhotos = equipmentExistingPhotos; // общий лайтбокс (#photoModal) из engineCard.js держит свою ссылку — держим её в актуальном состоянии
            renderEquipmentExistingPhotos();
            // detail-photos (#equipmentDetailView) рисуется отдельной функцией
            // и не обновляется автоматически при удалении фото в галерее
            // редактирования — без этого возврат к просмотру (или общий
            // лайтбокс #photoModal, currentPhotos) продолжает показывать уже
            // удалённый файл, пока карточка не будет переоткрыта заново.
            if (equipmentDetailData) renderEquipmentDetailView(equipmentDetailData);
            showToast('Фото удалено', 'success', 'icon-delete');
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function uploadPendingEquipmentPhotos(equipmentId) {
    if (equipmentPendingPhotoFiles.length === 0) return Promise.resolve();
    const formData = new FormData();
    equipmentPendingPhotoFiles.forEach(f => formData.append('photos', f));
    return apiFetch(`/api/equipment/${equipmentId}/photos`, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast('Оборудование сохранено, но фото не загрузились: ' + data.error, 'warning', 'icon-warning');
            }
            equipmentPendingPhotoFiles = [];
        })
        .catch(e => showToast('Оборудование сохранено, но фото не загрузились: ' + e.message, 'warning', 'icon-warning'));
}

document.addEventListener('DOMContentLoaded', function () {
    const photoInput = document.getElementById('equipmentPhotoInput');
    if (photoInput) {
        photoInput.addEventListener('change', function () {
            equipmentPendingPhotoFiles = equipmentPendingPhotoFiles.concat(Array.from(this.files || []));
            this.value = '';
            renderEquipmentPendingPhotos();
        });
    }
});

// Enter сохраняет карточку оборудования — тот же принцип "удобства", что
// Enter-сохранение для строк режимов/работ в engineCard.js, только на
// уровне всей формы (у equipment нет построчного инлайн-редактора, форма
// одна целиком). Слушатель на document, а не на каждом поле — полей
// динамические (специфичные атрибуты типа), навешивать на каждое по
// отдельности пришлось бы перевешивать при каждой смене типа.
// e.defaultPrevented — ключевая проверка: attachSuggestDropdown/
// attachEntitySuggest (common.js) сами обрабатывают Enter, когда открыт
// список подсказок (выбирают пункт и вызывают preventDefault) — если это
// уже произошло, форму сохранять не нужно, иначе выбор подсказки
// одновременно с этим сохранял бы всю карточку.
document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || e.defaultPrevented) return;
    if (e.target.tagName !== 'INPUT') return; // не трогаем textarea (перенос строки) и select
    const editFields = document.getElementById('equipmentEditFields');
    if (!editFields || editFields.style.display === 'none') return;
    if (!editFields.contains(e.target)) return;
    e.preventDefault();
    submitEquipment();
});

let equipmentDetailData = null;   // кэш последнего открытого item — для переключения view->edit без повторного fetch
let equipmentDetailMode = 'view'; // 'view' | 'edit' | 'create'

// ===== Места установки (equipment_placement) =====
// НЕ путать с item.location_node_id/equipmentFormLocationPicker выше —
// то "основное" место записи (дерево слева, фильтр списка), не меняется.
// Это дополнительная детализация: одно оборудование может стоять в
// нескольких местах, а в пределах одного места — несколько экземпляров
// с разными схемными обозначениями (шкаф +E021: КМ1, КМ2, КМ3).
// Управляется сразу против API (как фото — apiFetch на add/delete),
// не через основную форму/submitEquipment, доступно только для уже
// сохранённой записи (в режиме 'create' equipment_id ещё не существует).
let equipmentPlacements = [];
let equipmentPlacementFormPicker = null;

async function openEquipmentModal(id, startInEdit = false) {
    clearEquipmentForm();
    const titleEl = document.getElementById('equipmentModalTitle');

    if (!id) {
        equipmentDetailMode = 'create';
        equipmentDetailData = null;
        titleEl.innerHTML = '<span class="icon icon-package-2"></span> Новое оборудование';
        _showEquipmentEditMode();
        // Ещё не сохранённая запись — листать/печатать/датировать нечего,
        // тот же принцип, что и у "🆕 Новый двигатель" в engineCard.js.
        renderEquipmentDetailToolbar();
        document.getElementById('equipmentModal').classList.add('active');
        return;
    }

    try {
        const resp = await apiFetch(`/api/equipment/${id}`);
        const item = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(item.error || 'Не удалось загрузить оборудование', 'error');
            return;
        }
        equipmentDetailData = item;

        const photosResp = await apiFetch(`/api/equipment/${id}/photos`);
        equipmentExistingPhotos = await parseJsonResponse(photosResp);
        if (!Array.isArray(equipmentExistingPhotos)) equipmentExistingPhotos = [];

        const placementsResp = await apiFetch(`/api/equipment/${id}/placements`);
        equipmentPlacements = await parseJsonResponse(placementsResp);
        if (!Array.isArray(equipmentPlacements)) equipmentPlacements = [];

        document.getElementById('equipmentModal').classList.add('active');

        if (startInEdit) {
            titleEl.innerHTML = '<span class="icon icon-package-2"></span> Редактирование оборудования';
            await _fillEquipmentEditFields(item);
            _showEquipmentEditMode();
        } else {
            titleEl.innerHTML = `<span class="icon icon-package-2"></span> ${escapeHtml(item.name)}`;
            await renderEquipmentDetailView(item);
            _showEquipmentViewMode();
        }
        renderEquipmentDetailToolbar();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ===== ТУЛБАР КАРТОЧКИ (счётчик/даты/навигация) =====
// По образцу renderDetailContent() в engineCard.js (тулбар карточки
// двигателя) — вынесен в отдельную функцию и рендерится в отдельный
// #equipmentDetailToolbar (вне .modal-body, не скроллится вместе с
// формой). allEquipment — уже загруженный (текущим фильтром/сортировкой)
// полный список, тот же источник, что использует renderEquipmentTable()
// для постраничного вывода — навигация идёт по нему, а не по одной
// странице таблицы.
function renderEquipmentDetailToolbar() {
    const toolbar = document.getElementById('equipmentDetailToolbar');
    if (!toolbar) return;
    if (!equipmentDetailData || equipmentDetailMode === 'create') {
        toolbar.innerHTML = '';
        return;
    }

    const item = equipmentDetailData;
    const currentIndex = allEquipment.findIndex(e => e.id === item.id);
    const total = allEquipment.length;
    const isEdit = equipmentDetailMode === 'edit';

    const infoHtml = `
        <span class="detail-toolbar-title"><span class="icon icon-package-2"></span> Карточка оборудования</span>
        <span class="detail-toolbar-position">${currentIndex + 1} / ${total}</span>
        <span class="detail-toolbar-dates">Изменено: ${formatRuDateTime(item.updated_at)} · Создано: ${formatRuDateTime(item.created_at)}</span>
    `;

    // "Редактировать" скрыта, пока уже в режиме редактирования — сама
    // форма (equipmentEditFields) уже даёт свои Сохранить/Отмена внизу,
    // дублировать их в шапке не нужно. Остальные кнопки (навигация/
    // печать/удаление) доступны в обоих режимах, как и в карточке
    // двигателя.
    const navHtml = `
        ${!isEdit ? '<button class="btn btn-warning btn-sm write-action" onclick="event.stopPropagation(); switchEquipmentToEdit()"><span class="icon icon-edit"></span> Редактировать</button>' : ''}
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateEquipment(-1)" ${currentIndex <= 0 ? 'disabled' : ''}>◀ Предыдущий</button>
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateEquipment(1)" ${currentIndex === total - 1 ? 'disabled' : ''}>Следующий ▶</button>
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); printEquipment(${item.id})"><span class="icon icon-print"></span> Печать</button>
        <button class="btn btn-danger btn-sm write-action" onclick="event.stopPropagation(); deleteEquipmentEntry(${item.id})"><span class="icon icon-delete"></span> Удалить</button>
    `;

    toolbar.innerHTML = `<div class="detail-toolbar">
        <div class="detail-toolbar-info">${infoHtml}</div>
        <div class="detail-toolbar-nav">${navHtml}</div>
    </div>`;
}

// Листание ◀ Предыдущий / Следующий ▶ — тот же принцип, что navigateEngine
// в engineCard.js: ищем текущую позицию в уже загруженном списке
// (allEquipment) и открываем соседа в режиме просмотра.
function navigateEquipment(direction) {
    if (!equipmentDetailData) return;
    const currentIndex = allEquipment.findIndex(e => e.id === equipmentDetailData.id);
    if (currentIndex === -1) return;
    const newIndex = currentIndex + direction;
    if (newIndex < 0 || newIndex >= allEquipment.length) return;
    openEquipmentModal(allEquipment[newIndex].id);
}

// Переключение уже открытой карточки из просмотра в редактирование БЕЗ
// повторного запроса — используем уже закэшированный equipmentDetailData
// (тот же принцип, что у cancelDetailEdit/enterEditMode в engineCard.js,
// только без перезагрузки с сервера при входе в режим — она там нужна на
// ВЫХОДЕ из edit для отката несохранённых правок, здесь просто вход).
async function switchEquipmentToEdit() {
    if (!equipmentDetailData) return;
    document.getElementById('equipmentModalTitle').innerHTML =
        '<span class="icon icon-package-2"></span> Редактирование оборудования';
    await _fillEquipmentEditFields(equipmentDetailData);
    _showEquipmentEditMode();
    renderEquipmentDetailToolbar();
}

function _showEquipmentEditMode() {
    equipmentDetailMode = equipmentDetailData ? 'edit' : 'create';
    document.getElementById('equipmentDetailView').style.display = 'none';
    document.getElementById('equipmentEditFields').style.display = '';
}

function _showEquipmentViewMode() {
    equipmentDetailMode = 'view';
    document.getElementById('equipmentEditFields').style.display = 'none';
    document.getElementById('equipmentDetailView').style.display = '';
}

async function _fillEquipmentEditFields(item) {
    document.getElementById('equipmentId').value = item.id;
    document.getElementById('equipmentName').value = item.name || '';
    document.getElementById('equipmentArticle').value = item.article || '';
    document.getElementById('equipmentManufacturer').value = item.manufacturer || '';
    document.getElementById('equipmentCriticality').value = item.criticality || '';
    document.getElementById('equipmentNote').value = item.note || '';
    document.getElementById('equipmentTypeSelect').value = item.equipment_type_id;
    // location_node_id: поле «Место» (equipmentLocationInput) удалено из
    // модалки — «основное» место записи больше не редактируется через эту
    // форму. При сохранении (submitEquipment) location_node_id переотправляется
    // с ПРЕЖНИМ значением (из equipmentDetailData) при редактировании, чтобы
    // бэкенд не записал NULL; при создании берётся из
    // equipmentActiveLocationId. См. submitEquipment.
    await onEquipmentTypeChange(item.specs || {});
    renderEquipmentExistingPhotos();
    _renderEquipmentPlacementsSection();
}

// ===== Режим просмотра (ТЗ 3.5) =====
async function renderEquipmentDetailView(item) {
    const container = document.getElementById('equipmentDetailView');

    // Полный breadcrumb места (не только последний узел, как в списке) —
    // тот же уровень детализации, что и в пикере при выборе места.
    let locationText = '—';
    if (item.location_node_id) {
        try {
            const bcResp = await apiFetch(`/api/locations/${item.location_node_id}/breadcrumb`);
            const bc = await parseJsonResponse(bcResp);
            if (Array.isArray(bc) && bc.length) locationText = bc.map(n => n.name).join(' → ');
        } catch (e) {
            locationText = item.location_name || '—';
        }
    } else if (item.workshop || item.location) {
        locationText = [item.workshop, item.location].filter(Boolean).join(' / ');
    }

    // Атрибуты типа (с наследованием) — те же labels/units, что форма
    // редактирования использует для полей ввода (GET .../attributes).
    let attrsHtml = '';
    try {
        const attrsResp = await apiFetch(`/api/equipment-types/${item.equipment_type_id}/attributes`);
        const attrs = await parseJsonResponse(attrsResp);
        if (Array.isArray(attrs) && attrs.length) {
            attrsHtml = attrs.map(a => {
                const val = item.specs && item.specs[a.key] !== undefined && item.specs[a.key] !== ''
                    ? escapeHtml(String(item.specs[a.key])) + (a.unit ? ' ' + escapeHtml(a.unit) : '')
                    : '—';
                return `<div class="detail-item"><label>${escapeHtml(a.label)}</label><div class="value">${val}</div></div>`;
            }).join('');
        }
    } catch (e) { /* атрибуты необязательны для показа карточки */ }

    // Фото с лайтбоксом — переиспользуем существующую инфраструктуру
    // #photoModal/openPhotoModalWithNav из engineCard.js (currentPhotos/
    // currentPhotoIndex — те же глобальные переменные, что и у двигателей;
    // единственный на всё приложение лайтбокс, а не второй свой).
    currentPhotos = equipmentExistingPhotos;
    let photosHtml = '<div class="no-data">Нет фото</div>';
    if (equipmentExistingPhotos.length > 0) {
        photosHtml = '<div class="detail-photos">' + equipmentExistingPhotos.map(p => `
            <div class="gallery-thumb-wrap">
                <img src="${authPhotoUrl(p.path)}" class="gallery-thumb" onclick="openPhotoModalWithNav('${escapeAttr(p.path)}')" loading="lazy">
            </div>
        `).join('') + '</div>';
    }

    container.innerHTML = `
        <div class="detail-subsection-header"><h4><span class="icon icon-table-chart"></span> Характеристики</h4></div>
        <div class="detail-grid">
            <div class="detail-item"><label>Тип</label><div class="value">${escapeHtml(item.equipment_type_name || '—')}</div></div>
            <div class="detail-item"><label>Артикул</label><div class="value">${escapeHtml(item.article) || '—'}</div></div>
            <div class="detail-item"><label>Производитель</label><div class="value">${escapeHtml(item.manufacturer) || '—'}</div></div>
            <div class="detail-item"><label>Место</label><div class="value">${escapeHtml(locationText)}</div></div>
            <div class="detail-item"><label>Критичность</label><div class="value">${item.criticality ? '●'.repeat(item.criticality) + '○'.repeat(5 - item.criticality) : '—'}</div></div>
            ${attrsHtml}
        </div>

        <div class="detail-subsection-header"><h4><span class="icon icon-folder-open"></span> Места установки${equipmentPlacements.length ? ' (' + equipmentPlacements.length + ')' : ''}</h4></div>
        ${_renderEquipmentPlacementsReadonlyTable()}

        <div class="detail-subsection-header"><h4><span class="icon icon-photo-camera"></span> Фото${equipmentExistingPhotos.length ? ' (' + equipmentExistingPhotos.length + ')' : ''}</h4></div>
        ${photosHtml}

        <div class="detail-subsection-header"><h4>Примечание</h4></div>
        <div class="detail-item-edit"><div class="value">${escapeHtml(item.note) || '—'}</div></div>
    `;
}

// Группируем плоский список placements по месту — одно место с
// несколькими designation превращается в одну строку таблицы с
// несколькими чипами (визуально это ровно пример из ТЗ: шкаф +E021 —
// одна строка, чипы КМ1/КМ2/КМ3 внутри неё).
function _renderEquipmentPlacementsTable() {
    if (!equipmentPlacements.length) {
        return '<div class="no-data">Мест установки пока нет</div>';
    }
    const byLocation = new Map();
    equipmentPlacements.forEach(p => {
        if (!byLocation.has(p.location_node_id)) {
            byLocation.set(p.location_node_id, { path: p.location_path, items: [] });
        }
        byLocation.get(p.location_node_id).items.push(p);
    });
    let rows = '';
    byLocation.forEach((group, locationNodeId) => {
        const chips = group.items.map(p => `
            <span class="chip">
                ${p.designation ? escapeHtml(p.designation) : '<em>без обозначения</em>'}
                <button type="button" class="chip-remove" title="Удалить" onclick="deleteEquipmentPlacementRow(${p.id})">&times;</button>
            </span>
        `).join('');
        rows += `
            <div class="placement-row">
                <span class="placement-location">${escapeHtml(group.path)}</span>
                <span class="placement-chips">${chips}</span>
                <button type="button" class="placement-add-btn write-action" title="Добавить ещё обозначение в это место"
                        onclick="showEquipmentPlacementAddForm(${locationNodeId}, '${escapeAttr(group.path)}')">+</button>
            </div>`;
    });
    return rows;
}

// Read-only вариант той же таблицы — для режима просмотра карточки
// (renderEquipmentDetailView). Тот же набор данных
// (equipment_placement — место + designation + note), та же группировка
// по месту, те же CSS-классы (.placement-row / .placement-location /
// .placement-chips / .chip) — но БЕЗ кнопок удаления чипов (chip-remove)
// и без кнопки «+» (placement-add-btn). Чип остаётся визуально тот же,
// просто внутри только текст/designation, никаких onclick'ов.
//
// Шкафа с одним NULL-designation (placement без схемного обозначения)
// быть не может в read-only тоже — placement создаётся в edit-режиме
// и сохраняется на сервере, в read-only мы просто показываем то, что
// пришло из БД.
function _renderEquipmentPlacementsReadonlyTable() {
    if (!equipmentPlacements.length) {
        return '<div class="no-data">Мест установки пока нет</div>';
    }
    const byLocation = new Map();
    equipmentPlacements.forEach(p => {
        if (!byLocation.has(p.location_node_id)) {
            byLocation.set(p.location_node_id, { path: p.location_path, items: [] });
        }
        byLocation.get(p.location_node_id).items.push(p);
    });
    let rows = '';
    byLocation.forEach((group) => {
        const chips = group.items.map(p => `
            <span class="chip">
                ${p.designation ? escapeHtml(p.designation) : '<em>без обозначения</em>'}
            </span>
        `).join('');
        rows += `
            <div class="placement-row">
                <span class="placement-location">${escapeHtml(group.path)}</span>
                <span class="placement-chips">${chips}</span>
            </div>`;
    });
    return rows;
}

// Секция "Места установки" — живёт ТОЛЬКО в форме редактирования
// (#equipmentEditFields), не в режиме просмотра: место — это то, что
// заполняется/правится, а не витрина карточки, и физически equipment_id
// уже должен существовать (при создании оборудования секция не нужна —
// _fillEquipmentEditFields вызывается только для уже сохранённой записи,
// см. openEquipmentModal/switchEquipmentToEdit; ветка "создать новое" в
// openEquipmentModal её не вызывает).
//
// #equipmentEditFields — статичная форма из HTML-шаблона (id полей типа
// equipmentName и т.д. уже существуют в разметке), а не то, что JS
// рисует с нуля. Секцию мест примонтировать некуда заранее, поэтому
// mount-контейнер с фиксированным id создаём здесь же при первом
// рендере и переиспользуем при последующих — идемпотентно, без
// накопления дублей при повторном входе в edit одной и той же карточки.
function _renderEquipmentPlacementsSection() {
    const editFields = document.getElementById('equipmentEditFields');
    if (!editFields) return;
    let mount = document.getElementById('equipmentPlacementsSection');
    if (!mount) {
        mount = document.createElement('div');
        mount.id = 'equipmentPlacementsSection';
        // Точка монтирования секции «Места установки» — на месте бывшего
        // одиночного поля «Место» (equipmentLocationInput, удалён из HTML):
        // между «Производитель» и «Критичность». Якорь — ближайший общий
        // предок (.form-group с #equipmentCriticality), вставляемся ПЕРЕД ним.
        // Раньше секция добавлялась в конец editFields (editFields.appendChild),
        // из-за чего блок визуально оказывался ПОСЛЕ всех полей и кнопок
        // действий — что и исправляем этой правкой.
        const criticalityGroup = document.getElementById('equipmentCriticality')
            ? document.getElementById('equipmentCriticality').closest('.form-group')
            : null;
        if (criticalityGroup && criticalityGroup.parentNode === editFields) {
            editFields.insertBefore(mount, criticalityGroup);
        } else {
            // fallback на случай, если разметка изменилась: ведём себя как раньше
            editFields.appendChild(mount);
        }
    }
    mount.innerHTML = `
        <div class="detail-subsection-header">
            <h4><span class="icon icon-folder-open"></span> Места установки${equipmentPlacements.length ? ' (' + equipmentPlacements.length + ')' : ''}</h4>
            <button type="button" class="btn btn-secondary btn-sm write-action" onclick="showEquipmentPlacementAddForm()"><span class="icon icon-add"></span> Добавить место</button>
        </div>
        <div id="equipmentPlacementsTable">${_renderEquipmentPlacementsTable()}</div>
        <div id="equipmentPlacementAddForm" class="detail-item-edit" style="display:none">
            <label>Место</label>
            <input type="text" id="equipmentPlacementLocationInput" placeholder="Начните вводить название места...">
            <label style="margin-top:8px">Схемные обозначения (через запятую, необязательно)</label>
            <input type="text" id="equipmentPlacementDesignationsInput" placeholder="КМ1, КМ2, КМ3">
            <div style="margin-top:8px">
                <button type="button" class="btn btn-primary btn-sm write-action" onclick="submitEquipmentPlacementAdd()">Сохранить</button>
                <button type="button" class="btn btn-secondary btn-sm" onclick="hideEquipmentPlacementAddForm()">Отмена</button>
            </div>
        </div>
    `;

    // Пикер места для формы добавления — переинициализируем на каждый
    // рендер секции (тот же повод, что и у equipmentFormLocationPicker):
    // mount.innerHTML только что пересоздал #equipmentPlacementLocationInput,
    // старый инстанс пикера (если был) уже держит ссылку на удалённый узел
    // DOM и не среагирует на клики.
    if (equipmentPlacementFormPicker && equipmentPlacementFormPicker.destroy) {
        equipmentPlacementFormPicker.destroy();
    }
    const placementLocationInput = document.getElementById('equipmentPlacementLocationInput');
    if (placementLocationInput) {
        equipmentPlacementFormPicker = attachLocationPicker(placementLocationInput, {});
    }
}

function showEquipmentPlacementAddForm(prefillLocationId, prefillLabel) {
    const form = document.getElementById('equipmentPlacementAddForm');
    if (!form) return;
    form.style.display = '';
    document.getElementById('equipmentPlacementDesignationsInput').value = '';
    if (prefillLocationId && equipmentPlacementFormPicker) {
        equipmentPlacementFormPicker.setValue(prefillLocationId, prefillLabel || '');
    } else if (equipmentPlacementFormPicker) {
        equipmentPlacementFormPicker.setValue(null, '');
    }
    form.scrollIntoView({ block: 'nearest' });
}

function hideEquipmentPlacementAddForm() {
    const form = document.getElementById('equipmentPlacementAddForm');
    if (form) form.style.display = 'none';
}

async function submitEquipmentPlacementAdd() {
    if (!equipmentDetailData) return;
    const locationValue = equipmentPlacementFormPicker ? equipmentPlacementFormPicker.getValue() : null;
    if (!locationValue) {
        showToast('Выберите место', 'error');
        return;
    }
    const designations = document.getElementById('equipmentPlacementDesignationsInput').value.trim();
    try {
        const resp = await apiFetch(`/api/equipment/${equipmentDetailData.id}/placements`, {
            method: 'POST',
            body: JSON.stringify({ location_node_id: locationValue.id, designations })
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения места', 'error');
            return;
        }
        equipmentPlacements = Array.isArray(data.placements) ? data.placements : equipmentPlacements;
        // Частичный успех (часть обозначений уже занята в этом месте) —
        // созданное не откатывается, только сообщаем, что именно не
        // прошло, тем же способом, что и предупреждение о фото
        // (showToast('warning'), см. uploadPendingEquipmentPhotos).
        if (data.errors && data.errors.length) {
            showToast(data.errors.join('; '), 'warning', 'icon-warning');
        } else {
            showToast('Место добавлено', 'success');
        }
        hideEquipmentPlacementAddForm();
        // Число новых physical-единиц могло измениться (каждое designation
        // — отдельный экземпляр, см. equipment_repo.get_stock_summary) —
        // если открыта вкладка ЗИП/сводки, её счётчики устареют до
        // следующей загрузки; здесь не трогаем (сводка не в этой же
        // модалке), но полный ре-рендер секции ниже как минимум обновляет
        // заголовок с количеством мест в самой карточке.
        _renderEquipmentPlacementsSection();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteEquipmentPlacementRow(placementId) {
    if (!equipmentDetailData) return;
    if (!confirm('Удалить это место установки?')) return;
    try {
        const resp = await apiFetch(`/api/equipment/${equipmentDetailData.id}/placements/${placementId}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        equipmentPlacements = equipmentPlacements.filter(p => p.id !== placementId);
        showToast('Место удалено', 'success', 'icon-delete');
        _renderEquipmentPlacementsSection();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

function printEquipment(id) {
    window.open(`/print/equipment/${id}`, '_blank');
}

function closeEquipmentModal() {
    document.getElementById('equipmentModal').classList.remove('active');
    const toolbar = document.getElementById('equipmentDetailToolbar');
    if (toolbar) toolbar.innerHTML = '';
    equipmentDetailData = null;
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
        criticality: criticalityRaw ? Number(criticalityRaw) : null,
        note: document.getElementById('equipmentNote').value.trim(),
        specs: collectSpecsFromForm(),
    };

    // location_node_id: единичное поле «Место» (equipmentLocationInput) в этой
    // форме больше не редактируется — пользователь работает с множественными
    // «местами установки» (equipment_placement) ниже. Бэкенд-поле
    // location_node_id остаётся «основным» местом записи (используется в
    // дереве слева, фильтре списка, breadcrumb в карточке просмотра), но
    // через эту модалку больше не меняется.
    //
    // Правила:
    // - При редактировании (id !== ''): переотправляем location_node_id равным
    //   ПРЕЖНЕМУ значению (берём из кэша equipmentDetailData). Это нужно,
    //   потому что бэкенд (update_equipment) делает UPDATE по всем полям и
    //   запишет NULL, если ключа location_node_id нет в payload — а нам
    //   нужно сохранить прежнее «основное» место как есть.
    // - При создании (id === ''): берём location_node_id из текущего узла
    //   дерева слева (equipmentActiveLocationId). Если фильтр снят
    //   (null) или выбран псевдо-узел «Без места» ('unassigned' — см.
    //   комментарий в loadEquipmentList про отдельный флаг unassigned=1) —
    //   отправляем null. Это совпадает с поведением кнопки «+» у узла
    //   дерева (createEquipmentAtLocation): «+» обычно нажимают на
    //   активном узле, поэтому location_node_id подставится корректно.
    if (id) {
        payload.location_node_id = equipmentDetailData ? equipmentDetailData.location_node_id : null;
    } else {
        const activeId = (typeof equipmentActiveLocationId !== 'undefined')
            ? equipmentActiveLocationId
            : null;
        payload.location_node_id = (activeId && activeId !== 'unassigned')
            ? activeId
            : null;
    }

    try {
        const resp = id
            ? await apiFetch(`/api/equipment/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
            : await apiFetch('/api/equipment', { method: 'POST', body: JSON.stringify(payload) });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения', 'error');
            return;
        }
        const savedId = id || data.id;
        await uploadPendingEquipmentPhotos(savedId);
        showToast(id ? 'Оборудование обновлено' : 'Оборудование добавлено', 'success');
        closeEquipmentModal();
        await loadEquipmentList();
        // Место оборудования могло измениться (создание, редактирование
        // с новым location_node_id) — счётчики в боковом дереве
        // (equipmentLocationTreeBody) считаются отдельным запросом
        // (/api/equipment/location-counts) и без явного обновления
        // остаются устаревшими до следующей полной загрузки вкладки.
        if (typeof loadEquipmentLocationTree === 'function') await loadEquipmentLocationTree();
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
        // Кнопка "Удалить" теперь есть и в шапке открытой карточки
        // (renderEquipmentDetailToolbar), не только в таблице — если
        // удалили именно открытую запись, закрываем модалку, иначе она
        // осталась бы висеть с данными уже удалённого оборудования.
        if (equipmentDetailData && equipmentDetailData.id === id) {
            closeEquipmentModal();
        }
        await loadEquipmentList();
        // Та же причина, что и в submitEquipment — удалённая запись
        // могла быть привязана к месту, счётчик которого иначе останется
        // завышенным до перезагрузки вкладки.
        if (typeof loadEquipmentLocationTree === 'function') await loadEquipmentLocationTree();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}
