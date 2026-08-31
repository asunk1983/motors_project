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

    const suggest = attachEntitySuggest(inputEl, {
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
            // Если к этому моменту уже было выбрано существующее место
            // (пользователь выбрал его из списка, а затем продолжил
            // печатать/нажал "Создать", не найдя точного совпадения по
            // имени — поиск ищет только по name узла, не по всему пути,
            // так что для уже подставленного breadcrumb'а вида
            // "3506 → Линия Ноймаг → зона б" результатов не будет) — это
            // выбранное место логично считать родителем НОВОГО места, а
            // не пытаться создать узел, буквально названный всем этим
            // путём (баг: узел с именем "3506 → ... → зона б" в корне
            // дерева). При этом реально допечатанный пользователем текст
            // (обычно — новый последний сегмент, например "зона б" вместо
            // старого "зона 1") нельзя просто выбрасывать в пустоту —
            // вытаскиваем именно его как имя нового узла.
            const priorSelection = selected;
            let prefillName = query;
            if (priorSelection) {
                const segments = query.split('→').map(s => s.trim()).filter(Boolean);
                const tail = segments.length ? segments[segments.length - 1] : '';
                const priorSegments = (priorSelection.label || '').split('→').map(s => s.trim()).filter(Boolean);
                const priorTail = priorSegments.length ? priorSegments[priorSegments.length - 1] : '';
                // Если хвост совпадает с последним сегментом уже выбранного
                // места — пользователь ничего не менял (просто нажал
                // "Создать" на существующем месте) — пустое поле безопаснее,
                // чем повтор уже существующего имени.
                prefillName = tail === priorTail ? '' : tail;
            }
            openCreateLocationWizard(prefillName, (created) => {
                selected = created;
                inputEl.value = created.label;
                if (onChange) onChange(selected);
            }, priorSelection || null);
        },
        // "+" у конкретного найденного места — создать НОВОЕ место прямо
        // под ним, не выбирая сам найденный узел (сама строка по-прежнему
        // выбирается обычным кликом через onSelect). Закрывает ровно тот
        // пробел UX, из-за которого раньше пришлось печатать "1" и жать
        // общее "+Создать «1»" без родителя — теперь родитель уже
        // проставлен тем местом, у которого нажали "+".
        onItemAction: (item) => {
            openCreateLocationWizard('', (created) => {
                selected = created;
                inputEl.value = created.label;
                if (onChange) onChange(selected);
            }, { id: item.id, label: item.label });
        },
        itemActionIcon: 'icon-add',
        itemActionTitle: 'Добавить место сюда'
    });

    // Ручная очистка поля (например, стёр текст руками, не выбрав пункт) —
    // сбрасывает выбранный id, чтобы форма не ушла на сервер со старым
    // id при изменившемся видимом тексте.
    function onManualClear() {
        if (inputEl.value.trim() === '') {
            selected = null;
            if (onChange) onChange(null);
        }
    }
    inputEl.addEventListener('input', onManualClear);

    return {
        getValue: () => selected,
        setValue: (id, label) => {
            selected = id ? { id, label } : null;
            inputEl.value = label || '';
        },
        // ВАЖНО: если форма/модалка переиспользует один и тот же inputEl
        // и переинициализирует пикер при каждом открытии (см.
        // clearEquipmentForm в equipment.js, аналогично в incidents.js) —
        // ОБЯЗАТЕЛЬНО вызывать destroy() у предыдущего инстанса ПЕРЕД
        // повторным attachLocationPicker(). Иначе слушатели и dropdown-
        // обёртки накапливаются на одном и том же inputEl (см. разбор
        // бага в attachEntitySuggest, common.js) — клик по пункту списка
        // приходится повторять по несколько раз, пока не попадёшь по
        // актуальному, "живому" слою.
        destroy: function () {
            inputEl.removeEventListener('input', onManualClear);
            if (suggest && suggest.destroy) suggest.destroy();
        }
    };
}

// ---------------------------------------------------------------------
// Мастер создания нового места: родитель (через тот же пикер) → тип → имя
// ---------------------------------------------------------------------

// initialParent — опционально {id, label}; если задан, поле "Родительское
// место" мастера открывается уже заполненным этим узлом (используется
// кнопкой "Добавить подсущность" в справочнике — см. addChildLocationNode).
function openCreateLocationWizard(prefillName, onCreated, initialParent) {
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
    const parentPicker = attachLocationPicker(parentInput, {
        allowEmpty: true,
        initialId: initialParent ? initialParent.id : null,
        initialLabel: initialParent ? initialParent.label : ''
    });

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

// ID узлов, ветки которых свёрнуты пользователем (по аналогии с
// activeWorkshop в locationTree.js, только тут не выбор фильтра, а
// именно сворачивание — веток может быть свёрнуто сразу несколько,
// независимо друг от друга). По умолчанию всё развёрнуто (пусто) —
// то же поведение, что было до появления сворачивания.
const _collapsedLocationDictIds = new Set();

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

function toggleLocationDictNode(id) {
    if (_collapsedLocationDictIds.has(id)) {
        _collapsedLocationDictIds.delete(id);
    } else {
        _collapsedLocationDictIds.add(id);
    }
    renderLocationDictionary();
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

    // Визуальный язык — тот же, что у дерева цехов на вкладке "Каталог"
    // (locationTree.js: .tree-workshop/.tree-chevron/.tree-count-chip),
    // но глубина здесь произвольная (не 2 фиксированных уровня), поэтому
    // отступ каждого уровня задаём инлайн-стилем (padding-left), а не
    // отдельными CSS-классами под каждый уровень.
    function renderLevel(parentKey, depth) {
        const children = byParent[parentKey] || [];
        return children.map(n => {
            const childKey = String(n.id);
            const hasChildren = !!(byParent[childKey] && byParent[childKey].length);
            const isCollapsed = _collapsedLocationDictIds.has(n.id);
            const chevron = hasChildren
                ? `<span class="tree-chevron" onclick="event.stopPropagation(); toggleLocationDictNode(${n.id})">${isCollapsed ? '▶' : '▼'}</span>`
                : `<span class="tree-chevron"></span>`;
            const rowClickHandler = hasChildren ? ` onclick="toggleLocationDictNode(${n.id})"` : '';

            const row = `
                <div class="tree-workshop" style="padding-left:${depth * 20 + 10}px"${rowClickHandler}>
                    ${chevron}
                    <span class="tree-workshop-label">${escapeHtml(n.name)}</span>
                    <span class="tree-count-chip" title="Тип места">${escapeHtml(LOCATION_NODE_TYPE_LABELS[n.node_type] || n.node_type)}</span>
                    <span style="display:flex;gap:4px" onclick="event.stopPropagation()">
                        <button class="btn btn-secondary btn-sm" onclick="addChildLocationNode(${n.id})" title="Добавить подсущность"><span class="icon icon-add"></span></button>
                        <button class="btn btn-secondary btn-sm" onclick="renameLocationNode(${n.id}, '${escapeAttr(n.name)}')" title="Переименовать"><span class="icon icon-edit"></span></button>
                        <button class="btn btn-danger btn-sm" onclick="deleteLocationNode(${n.id})" title="Удалить"><span class="icon icon-delete"></span></button>
                    </span>
                </div>`;

            const childrenHtml = (hasChildren && !isCollapsed) ? renderLevel(childKey, depth + 1) : '';
            return row + childrenHtml;
        }).join('');
    }

    el.innerHTML = renderLevel('root', 0);
}

// Строит breadcrumb ("Цех 3506 → Секция А") по уже загруженному в память
// _locationDictNodes, без похода на /api/locations/<id>/breadcrumb —
// справочник и так уже держит полный плоский список в памяти.
function _localBreadcrumb(nodeId) {
    const byId = {};
    _locationDictNodes.forEach(n => { byId[n.id] = n; });
    const parts = [];
    let current = byId[nodeId];
    while (current) {
        parts.unshift(current.name);
        current = current.parent_id !== null ? byId[current.parent_id] : null;
    }
    return parts.join(' → ');
}

// Кнопка "Добавить подсущность" в справочнике — открывает тот же мастер,
// что и "+ Создать новое место" в пикере форм, но с уже проставленным
// родителем (сам узел, на котором нажали кнопку).
function addChildLocationNode(parentId) {
    const parentNode = _locationDictNodes.find(n => n.id === parentId);
    if (!parentNode) return;
    const parentLabel = _localBreadcrumb(parentId);
    openCreateLocationWizard('', () => {
        loadLocationDictionary();
    }, { id: parentId, label: parentLabel });
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
