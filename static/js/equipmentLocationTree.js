// static/js/equipmentLocationTree.js — боковое дерево мест на вкладке
// "Оборудование" (ТЗ раздел 3.1). НЕ путать с static/js/locationTree.js
// (старое дерево для engines, построено на текстовых workshop/location) —
// это дерево работает с общим ресурсом location_node (см.
// static/js/incidentLocations.js — та же таблица, тот же API, здесь
// просто другой потребитель: клик по узлу фильтрует список оборудования,
// а не заявки). Требует: common.js, incidentLocations.js (переиспользует
// LOCATION_NODE_TYPE_LABELS), auth.js.

let equipmentActiveLocationId = null;   // выбранный узел (null — фильтр снят)
let equipmentLocationChildrenCache = {}; // {parent_key: [node,...]} — parent_key: 'root' | String(id)
let equipmentLocationCounts = {};       // {location_node_id: count} — с backend, СВОИ узлы, без суммирования по поддереву
let equipmentLocationNodesFlat = [];    // плоский список всех узлов — нужен для суммирования счётчика вверх по дереву

async function loadEquipmentLocationTree() {
    const body = document.getElementById('equipmentLocationTreeBody');
    if (!body) return;
    try {
        const [nodesResp, countsResp] = await Promise.all([
            apiFetch('/api/locations'),
            apiFetch('/api/equipment/location-counts'),
        ]);
        equipmentLocationNodesFlat = await nodesResp.json();
        equipmentLocationCounts = await countsResp.json();
        if (!Array.isArray(equipmentLocationNodesFlat)) equipmentLocationNodesFlat = [];
        if (!equipmentLocationCounts || typeof equipmentLocationCounts !== 'object') equipmentLocationCounts = {};
        renderEquipmentLocationTree();
    } catch (e) {
        body.innerHTML = `<div class="no-data">Не удалось загрузить дерево мест: ${escapeHtml(e.message)}</div>`;
    }
}

// Суммарный счётчик узла = его собственный + всех потомков. Считаем в
// Python-подобном стиле "снизу вверх" по уже загрученному плоскому
// списку (не отдельным запросом на каждый узел) — тот же принцип, что
// summarization счётчиков цехов в старом locationTree.js для engines.
function _equipmentSubtreeCount(nodeId) {
    let total = equipmentLocationCounts[nodeId] || 0;
    const children = equipmentLocationNodesFlat.filter(n => n.parent_id === nodeId);
    children.forEach(c => { total += _equipmentSubtreeCount(c.id); });
    return total;
}

function renderEquipmentLocationTree() {
    const body = document.getElementById('equipmentLocationTreeBody');
    if (!body) return;

    const roots = equipmentLocationNodesFlat.filter(n => n.parent_id === null);
    if (roots.length === 0) {
        body.innerHTML = '<div class="no-data">Мест пока нет — добавьте в форме оборудования</div>';
        return;
    }

    const totalCount = roots.reduce((sum, r) => sum + _equipmentSubtreeCount(r.id), 0);
    const isRootActive = equipmentActiveLocationId === null;
    let html = `
        <div class="tree-root ${isRootActive ? 'active' : ''}" onclick="resetEquipmentLocationFilter()">
            <span class="tree-workshop-label">Все объекты</span>
            <span class="tree-count-chip">${totalCount}</span>
        </div>`;

    function renderNode(node, depth) {
        const children = equipmentLocationNodesFlat.filter(n => n.parent_id === node.id);
        const count = _equipmentSubtreeCount(node.id);
        const isActive = equipmentActiveLocationId === node.id;
        const typeLabel = (typeof LOCATION_NODE_TYPE_LABELS !== 'undefined' && LOCATION_NODE_TYPE_LABELS[node.node_type]) || node.node_type;
        let nodeHtml = `
            <div class="tree-location" style="padding-left:${depth * 16 + 12}px" data-id="${node.id}"
                 title="${escapeHtml(typeLabel)}"
                 onclick="selectEquipmentLocation(${node.id})">
                <span class="tree-workshop-label">${escapeHtml(node.name)}</span>
                <span class="tree-location-right"><span class="tree-count-chip">${count}</span></span>
            </div>`;
        children
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name, 'ru'))
            .forEach(c => { nodeHtml += renderNode(c, depth + 1); });
        return nodeHtml;
    }

    roots
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, 'ru'))
        .forEach(r => { html += renderNode(r, 0); });

    body.innerHTML = html;

    // active-класс на корне уже проставлен через isRootActive в разметке
    // выше; для остальных узлов подсветку делаем через querySelector,
    // чтобы не тащить состояние active через каждый renderNode-вызов.
    if (equipmentActiveLocationId !== null) {
        const activeEl = body.querySelector(`.tree-location[data-id="${equipmentActiveLocationId}"]`);
        if (activeEl) activeEl.classList.add('active');
    }
}

function selectEquipmentLocation(nodeId) {
    equipmentActiveLocationId = nodeId;
    if (typeof loadEquipmentList === 'function') loadEquipmentList();
    renderEquipmentLocationTree();
}

function resetEquipmentLocationFilter() {
    equipmentActiveLocationId = null;
    if (typeof loadEquipmentList === 'function') loadEquipmentList();
    renderEquipmentLocationTree();
}
