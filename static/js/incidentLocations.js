// static/js/incidentLocations.js — дерево мест (location_node), общий
// ресурс проекта (ТЗ "Инциденты + Оборудование", раздел 1). НЕ путать со
// старым static/js/locationTree.js — тот работает с текстовыми полями
// workshop/location у engines и трогать его не нужно; это отдельная
// сущность на отдельном API (/api/locations*).
// Требует: common.js (attachEntitySuggest, escapeHtml, showToast),
// auth.js (apiFetch, parseJsonResponse).

const LOCATION_NODE_TYPE_LABELS = {
    workshop: 'Цех', installation: 'Установка', unit: 'Узел',
    zone: 'Зона', warehouse: 'Склад', other: 'Другое'
};

// ---------------------------------------------------------------------
// Пикер одного места — автопоиск с breadcrumb + "+ Создать новое место"
// ---------------------------------------------------------------------

// attachLocationPicker(inputEl, {initialId, initialLabel, onChange, allowEmpty})
// onChange({id, label}) вызывается и при выборе существующего узла, и
// после создания нового через мастер (обе ветки дают одинаковый payload).
// Возвращает {getValue, setValue} — getValue() читает текущий выбранный
// {id, label} (или null), setValue(id, label) программно проставляет поле
// (нужно для режима редактирования, когда место уже известно с сервера).
function attachLocationPicker(inputEl, options) {
    const { onChange, allowEmpty = false } = options || {};
    let selected = options && options.initialId
        ? { id: options.initialId, label: options.initialLabel || '' }
        : null;

    if (selected) inputEl.value = selected.label;
    inputEl.placeholder = allowEmpty ? 'Без родителя (корень дерева)' : 'Начните вводить название места...';

    attachEntitySuggest(inputEl, {
        minChars: 1,
        searchFn: (query) => apiFetch(`/api/locations/search?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(rows => rows.map(row => ({ id: row.id, label: row.path || row.name, sublabel: LOCATION_NODE_TYPE_LABELS[row.node_type] || '' }))),
        onSelect: (item) => {
            selected = { id: item.id, label: item.label };
            inputEl.value = item.label;
            if (onChange) onChange(selected);
        },
        onCreateNew: (query) => {
            openCreateLocationWizard(query, (created) => {
                selected = created;
                inputEl.value = created.label;
                if (onChange) onChange(selected);
            });
        }
    });

    // Ручная очистка поля (например, стёр текст руками, не выбрав пункт) —
    // сбрасывает выбранный id, чтобы форма не ушла на сервер со старым
    // id при изменившемся видимом тексте.
    inputEl.addEventListener('input', () => {
        if (inputEl.value.trim() === '') {
            selected = null;
            if (onChange) onChange(null);
        }
    });

    return {
        getValue: () => selected,
        setValue: (id, label) => {
            selected = id ? { id, label } : null;
            inputEl.value = label || '';
        }
    };
}

// ---------------------------------------------------------------------
// Мастер создания нового места: родитель (через тот же пикер) → тип → имя
// ---------------------------------------------------------------------

function openCreateLocationWizard(prefillName, onCreated) {
    const overlay = document.createElement('div');
    overlay.className = 'modal active';
    overlay.innerHTML = `
        <div class="modal-content" style="max-width:480px">
            <div class="modal-header">
                <h2><span class="icon icon-add"></span> Новое место</h2>
                <button type="button" class="modal-close" data-role="close">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Родительское место</label>
                    <input type="text" id="wizardParentInput" placeholder="Без родителя (корень дерева)">
                </div>
                <div class="form-group">
                    <label>Тип</label>
                    <select id="wizardNodeType">
                        <option value="workshop">Цех</option>
                        <option value="installation">Установка</option>
                        <option value="unit">Узел</option>
                        <option value="zone">Зона</option>
                        <option value="warehouse">Склад</option>
                        <option value="other" selected>Другое</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Название</label>
                    <input type="text" id="wizardName" value="${escapeHtml(prefillName || '')}">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" data-role="close">Отмена</button>
                    <button type="button" class="btn btn-success" data-role="submit"><span class="icon icon-save"></span> Создать</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.body.classList.add('modal-open');

    const parentInput = overlay.querySelector('#wizardParentInput');
    const parentPicker = attachLocationPicker(parentInput, { allowEmpty: true });

    function close() {
        overlay.remove();
        // Не снимаем modal-open безусловно — если мастер был открыт поверх
        // другой уже открытой модалки (форма заявки), тот же паттерн
        // защиты, что и в engineCard.js::_syncModalOpenState.
        if (!document.querySelector('.modal.active, .photo-modal.active')) {
            document.body.classList.remove('modal-open');
        }
    }

    overlay.querySelectorAll('[data-role="close"]').forEach(el => el.addEventListener('click', close));

    overlay.querySelector('[data-role="submit"]').addEventListener('click', () => {
        const name = overlay.querySelector('#wizardName').value.trim();
        const nodeType = overlay.querySelector('#wizardNodeType').value;
        if (!name) {
            showToast('Название обязательно', 'warning', 'icon-warning');
            return;
        }
        const parent = parentPicker.getValue();
        apiFetch('/api/locations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, node_type: nodeType, parent_id: parent ? parent.id : null })
        })
            .then(r => r.json())
            .then(result => {
                if (result.error) {
                    showToast(result.error, 'error', 'icon-cancel');
                    return;
                }
                const label = parent ? `${parent.label} → ${name}` : name;
                showToast('Место создано', 'success', 'icon-check-circle');
                close();
                onCreated({ id: result.id, label });
            })
            .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
    });
}

// ---------------------------------------------------------------------
// Справочник мест (подвкладка "Справочники" на вкладке "Инциденты")
// ---------------------------------------------------------------------

let _locationDictNodes = [];

function loadLocationDictionary() {
    apiFetch('/api/locations')
        .then(r => r.json())
        .then(nodes => {
            _locationDictNodes = Array.isArray(nodes) ? nodes : [];
            renderLocationDictionary();
        })
        .catch(() => {
            const el = document.getElementById('locationDictionaryList');
            if (el) el.innerHTML = '<div class="no-data">Не удалось загрузить дерево мест</div>';
        });
}

function renderLocationDictionary() {
    const el = document.getElementById('locationDictionaryList');
    if (!el) return;
    if (_locationDictNodes.length === 0) {
        el.innerHTML = '<div class="no-data">Мест пока нет</div>';
        return;
    }
    const byParent = {};
    _locationDictNodes.forEach(n => {
        const key = n.parent_id === null ? 'root' : String(n.parent_id);
        (byParent[key] = byParent[key] || []).push(n);
    });

    function renderLevel(parentKey, depth) {
        const children = byParent[parentKey] || [];
        return children.map(n => `
            <div class="knowledge-dict-row" style="padding-left:${depth * 20 + 10}px">
                <div>
                    <div class="knowledge-dict-code">${escapeHtml(LOCATION_NODE_TYPE_LABELS[n.node_type] || n.node_type)}</div>
                    ${escapeHtml(n.name)}
                </div>
                <div style="display:flex;gap:4px">
                    <button class="btn btn-secondary btn-sm" onclick="renameLocationNode(${n.id}, '${n.name.replace(/'/g, "\\'")}')" title="Переименовать"><span class="icon icon-edit"></span></button>
                    <button class="btn btn-danger btn-sm" onclick="deleteLocationNode(${n.id})" title="Удалить"><span class="icon icon-delete"></span></button>
                </div>
            </div>
        `).join('') + children.map(n => renderLevel(String(n.id), depth + 1)).join('');
    }

    el.innerHTML = renderLevel('root', 0);
}

function createRootLocationNode() {
    const nameEl = document.getElementById('newLocationRootName');
    const typeEl = document.getElementById('newLocationRootType');
    const name = nameEl.value.trim();
    if (!name) {
        showToast('Укажите название места', 'warning', 'icon-warning');
        return;
    }
    apiFetch('/api/locations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, node_type: typeEl.value, parent_id: null })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            nameEl.value = '';
            showToast('Место добавлено', 'success', 'icon-check-circle');
            loadLocationDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function renameLocationNode(id, currentName) {
    const name = prompt('Новое название места:', currentName);
    if (name === null) return;
    const trimmed = name.trim();
    if (!trimmed) return;
    apiFetch(`/api/locations/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            loadLocationDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function deleteLocationNode(id) {
    if (!confirm('Удалить это место? Если у него есть дочерние места или привязанные заявки, сервер откажет.')) return;
    apiFetch(`/api/locations/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            showToast('Место удалено', 'success', 'icon-check-circle');
            loadLocationDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}
