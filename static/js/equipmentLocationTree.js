// static/js/equipmentLocationTree.js — боковое дерево мест на вкладке
// "Оборудование" (ТЗ раздел 3.1). НЕ путать с static/js/locationTree.js
// (старое дерево для engines, построено на текстовых workshop/location) —
// это дерево работает с общим ресурсом location_node (см.
// static/js/incidentLocations.js — та же таблица, тот же API, здесь
// просто другой потребитель: клик по узлу фильтрует список оборудования,
// а не заявки). Требует: common.js, incidentLocations.js (переиспользует
// LOCATION_NODE_TYPE_LABELS), auth.js.

let equipmentActiveLocationId = null;   // выбранный узел (null — фильтр снят)
let equipmentLocationCounts = {};       // {location_node_id: count} — с backend, СВОИ узлы, без суммирования по поддереву
let equipmentLocationNodesFlat = [];    // плоский список всех узлов — нужен для суммирования счётчика вверх по дереву

// Свёрнутые ветки дерева (по умолчанию всё развёрнуто, как и раньше —
// множество пустое). Тот же паттерн, что _collapsedLocationDictIds в
// incidentLocations.js. Раньше дерево оборудования вообще не умело
// сворачиваться и не имело шевронов — визуально отличалось от
// locationTree.js (дерево "Цех → Место" на вкладке Каталог), где узлы с
// дочерними элементами кликабельно раскрываются/сворачиваются.
let equipmentCollapsedLocationIds = new Set();

async function loadEquipmentLocationTree() {
    const body = document.getElementById('equipmentLocationTreeBody');
    if (!body) return;
    try {
        const [nodesResp, countsResp] = await Promise.all([
            apiFetch('/api/locations'),
            apiFetch('/api/equipment/location-counts'),
        ]);
        const nodesData = await nodesResp.json();
        const countsData = await countsResp.json();
        // Бэкенд при ошибке отвечает {"error": "..."} (см.
        // get_equipment_location_counts_route в equipment_routes.py) — это
        // всё ещё "правдивый" объект (typeof === 'object', не null), так
        // что старая проверка ниже принимала его как валидные счётчики.
        // В итоге для ЛЮБОГО узла equipmentLocationCounts[nodeId] был
        // undefined → '|| 0' → все чипы показывали 0 без единой видимой
        // ошибки, неотличимо от "оборудования и правда нигде нет".
        if (countsData && countsData.error) {
            throw new Error(countsData.error);
        }
        if (nodesData && nodesData.error) {
            throw new Error(nodesData.error);
        }
        equipmentLocationNodesFlat = Array.isArray(nodesData) ? nodesData : [];
        equipmentLocationCounts = (countsData && typeof countsData === 'object') ? countsData : {};
        renderEquipmentLocationTree();
    } catch (e) {
        body.innerHTML = `<div class="no-data">Не удалось загрузить дерево мест: ${escapeHtml(e.message)}</div>`;
    }
}

// Суммарный счётчик узла = его собственный + всех потомков (реализация —
// subtreeCount внутри renderEquipmentLocationTree(): общий индекс
// childrenByParent + мемоизация на один рендер, вместо filter() по
// всему плоскому списку для каждого узла).

function renderEquipmentLocationTree() {
    const body = document.getElementById('equipmentLocationTreeBody');
    if (!body) return;

    // Индекс "родитель -> дети" строим один раз за рендер вместо того,
    // чтобы гонять equipmentLocationNodesFlat.filter(...) по всему
    // плоскому списку для КАЖДОГО узла (раньше это делали и здесь, и
    // отдельно внутри _equipmentSubtreeCount — на дереве из n узлов
    // давало O(n²) работы на рендер). Тот же приём, что byParent в
    // incidentLocations.js::renderLocationDictionary.
    const childrenByParent = new Map();
    equipmentLocationNodesFlat.forEach(n => {
        if (!childrenByParent.has(n.parent_id)) childrenByParent.set(n.parent_id, []);
        childrenByParent.get(n.parent_id).push(n);
    });
    childrenByParent.forEach(list => list.sort((a, b) => a.name.localeCompare(b.name, 'ru')));

    // Суммарный счётчик узла = его собственный + всех потомков.
    // Мемоизируем по nodeId в пределах одного рендера — раньше пересчёт
    // шёл заново при каждом обращении (и для totalCount, и повторно
    // внутри renderNode для того же узла).
    const subtreeCountCache = new Map();
    function subtreeCount(nodeId) {
        if (subtreeCountCache.has(nodeId)) return subtreeCountCache.get(nodeId);
        let total = equipmentLocationCounts[nodeId] || 0;
        (childrenByParent.get(nodeId) || []).forEach(c => { total += subtreeCount(c.id); });
        subtreeCountCache.set(nodeId, total);
        return total;
    }

    const roots = childrenByParent.get(null) || [];
    // Оборудование без места (ни одного placement, ни legacy
    // location_node_id) не входит ни в один узел дерева — backend отдаёт
    // его отдельным ключом 'unassigned' (см. get_equipment_location_counts,
    // equipment_repo.py). Бэкенд отдельно валит клик в equipment_routes.py
    // через явный флаг unassigned=1 (а не через location_node_id='unassigned',
    // который Flask при type=int молча проглатывает до None — отдельный
    // баг, который в этой реализации обходится с самого начала). Показываем
    // ВСЕГДА, даже при 0 — чтобы пункт не прыгал в списке при каждом
    // добавлении/удалении места (решение по ТЗ).
    const unassignedCount = equipmentLocationCounts['unassigned'] || 0;
    const totalCount = roots.reduce((sum, r) => sum + subtreeCount(r.id), 0) + unassignedCount;
    const isRootActive = equipmentActiveLocationId === null;
    const isUnassignedActive = equipmentActiveLocationId === 'unassigned';
    let html = `
        <div class="tree-root ${isRootActive ? 'active' : ''}" onclick="resetEquipmentLocationFilter()">
            <span class="tree-workshop-label">Все объекты</span>
            <span class="tree-count-chip">${totalCount}</span>
        </div>
        <div class="tree-location tree-location-unassigned ${isUnassignedActive ? 'active' : ''}" onclick="selectEquipmentLocation('unassigned')">
            <span class="tree-workshop-label"><em>Без места</em></span>
            <span class="tree-count-chip">${unassignedCount}</span>
        </div>`;

    if (roots.length === 0) {
        body.innerHTML = html + '<div class="no-data">Мест пока нет — добавьте в форме оборудования</div>';
        return;
    }

    function renderNode(node, depth) {
        const children = childrenByParent.get(node.id) || [];
        const hasChildren = children.length > 0;
        const count = subtreeCount(node.id);
        const isActive = equipmentActiveLocationId === node.id;
        const isCollapsed = equipmentCollapsedLocationIds.has(node.id);
        const typeLabel = (typeof LOCATION_NODE_TYPE_LABELS !== 'undefined' && LOCATION_NODE_TYPE_LABELS[node.node_type]) || node.node_type;
        // Визуально — тот же приём, что и в locationTree.js: узлы с
        // дочерними элементами получают класс tree-workshop и шеврон
        // (раскрытие/сворачивание), листья — tree-location, без шеврона.
        // escapeAttr — общая утилита из common.js (locationTree.js и
        // equipmentLocationTree.js — независимые файлы разных вкладок,
        // без гарантии совместной загрузки друг с другом).
        const rowClass = hasChildren ? 'tree-workshop' : 'tree-location';
        const chevronHtml = hasChildren
            ? `<span class="tree-chevron" onclick="event.stopPropagation(); toggleEquipmentLocationNode(${node.id})">${isCollapsed ? '▶' : '▼'}</span>`
            : '';
        const rowHtml = `
                <div class="${rowClass} ${isActive ? 'active' : ''}" style="padding-left:${depth * 16 + 12}px" data-id="${node.id}"
                     title="${escapeHtml(typeLabel)}"
                     onclick="selectEquipmentLocation(${node.id})">
                    ${chevronHtml}
                    <span class="tree-workshop-label">${escapeHtml(node.name)}</span>
                    <span class="tree-location-right">
                        <span class="tree-count-chip">${count}</span>
                        <button type="button" class="tree-add-btn write-action" title="Добавить оборудование в это место"
                                onclick="event.stopPropagation(); createEquipmentAtLocation(${node.id}, '${escapeAttr(node.name)}')">+</button>
                    </span>
                </div>`;

        // .tree-workshop-group — обёртка только для узлов С детьми (как в
        // locationTree.js: она держит вместе заголовок цеха и его
        // раскрывающийся список мест). Раньше в неё оборачивался КАЖДЫЙ
        // узел, включая листья без единого дочернего элемента — стили
        // этого класса рассчитаны на пару "заголовок + список" и на
        // одиночном листе могли перекрывать/смещать кнопку "+" декоративной
        // разметкой группы, из-за чего клик до неё не долетал.
        if (!hasChildren) return rowHtml;
        return `
            <div class="tree-workshop-group">${rowHtml}
                <div class="tree-locations ${isCollapsed ? 'hidden' : ''}">${children.map(c => renderNode(c, depth + 1)).join('')}</div>
            </div>`;
    }

    // roots уже отсортированы — childrenByParent.forEach(list => list.sort(...))
    // выше отсортировал и список под ключом null тоже.
    roots.forEach(r => { html += renderNode(r, 0); });

    body.innerHTML = html;

    // active-класс на корне уже проставлен через isRootActive в разметке
    // выше; для остальных узлов подсветку делаем через querySelector,
    // чтобы не тащить состояние active через каждый renderNode-вызов.
    // Ищем и среди .tree-workshop (узлы с детьми), и среди .tree-location
    // (листья) — раньше все узлы рендерились как .tree-location.
    if (equipmentActiveLocationId !== null) {
        const activeEl = body.querySelector(`[data-id="${equipmentActiveLocationId}"]`);
        if (activeEl) activeEl.classList.add('active');
    }
}

function toggleEquipmentLocationNode(nodeId) {
    if (equipmentCollapsedLocationIds.has(nodeId)) {
        equipmentCollapsedLocationIds.delete(nodeId);
    } else {
        equipmentCollapsedLocationIds.add(nodeId);
    }
    renderEquipmentLocationTree();
}

function selectEquipmentLocation(nodeId) {
    equipmentActiveLocationId = nodeId;
    // Разворачивание/сворачивание теперь тоже по клику на всю строку
    // узла, а не только по шеврону — та же логика, что и в
    // toggleEquipmentLocationNode() (шеврон по-прежнему работает сам по
    // себе отдельно, с event.stopPropagation() — переключает раскрытие
    // без смены текущего фильтра). Псевдо-узел 'unassigned' ("Без места")
    // не участвует в дереве и не имеет детей/шеврона — сворачивать
    // нечего, пропускаем эту часть для него.
    if (nodeId !== 'unassigned') {
        if (equipmentCollapsedLocationIds.has(nodeId)) {
            equipmentCollapsedLocationIds.delete(nodeId);
        } else {
            equipmentCollapsedLocationIds.add(nodeId);
        }
    }
    if (typeof loadEquipmentList === 'function') loadEquipmentList();
    renderEquipmentLocationTree();
}

function resetEquipmentLocationFilter() {
    equipmentActiveLocationId = null;
    if (typeof loadEquipmentList === 'function') loadEquipmentList();
    renderEquipmentLocationTree();
}
