// static/js/incidentLocationTree.js — боковое дерево мест на вкладке
// "Инциденты" (подвкладка "Журнал"). Ровно та же схема, что и
// static/js/equipmentLocationTree.js для "Оборудования" — общий ресурс
// location_node (см. incidentLocations.js), другой потребитель: клик по
// узлу фильтрует список ЗАЯВОК, а не оборудование.
// Требует: common.js, incidentLocations.js (LOCATION_NODE_TYPE_LABELS),
// auth.js. Функции ниже дёргаются из incidents.js (loadIncidentsList,
// submitIncident, deleteCurrentIncident) — держать оба файла синхронно
// подключёнными в index.html.

let incidentActiveLocationId = null;   // выбранный узел (null — фильтр снят)
let incidentLocationCounts = {};       // {location_node_id: count} — СВОИ узлы, без суммы по поддереву
let incidentLocationNodesFlat = [];    // плоский список всех узлов — для суммирования счётчика вверх по дереву

// Свёрнутые ветки — по умолчанию всё развёрнуто (тот же паттерн, что
// equipmentCollapsedLocationIds/_collapsedLocationDictIds).
let incidentCollapsedLocationIds = new Set();

async function loadIncidentLocationTree() {
    const body = document.getElementById('incidentLocationTreeBody');
    if (!body) return;
    try {
        const [nodesResp, countsResp] = await Promise.all([
            apiFetch('/api/locations'),
            apiFetch('/api/incident-tickets/location-counts'),
        ]);
        const nodesData = await nodesResp.json();
        const countsData = await countsResp.json();
        // См. комментарий в equipmentLocationTree.js/incident_ticket_repo.py::
        // get_location_counts про "{error: ...}" как правдивый объект —
        // без явной проверки все чипы молча показали бы 0.
        if (countsData && countsData.error) {
            throw new Error(countsData.error);
        }
        if (nodesData && nodesData.error) {
            throw new Error(nodesData.error);
        }
        incidentLocationNodesFlat = Array.isArray(nodesData) ? nodesData : [];
        incidentLocationCounts = (countsData && typeof countsData === 'object') ? countsData : {};
        renderIncidentLocationTree();
    } catch (e) {
        body.innerHTML = `<div class="no-data">Не удалось загрузить дерево мест: ${escapeHtml(e.message)}</div>`;
    }
}

function renderIncidentLocationTree() {
    const body = document.getElementById('incidentLocationTreeBody');
    if (!body) return;

    const childrenByParent = new Map();
    incidentLocationNodesFlat.forEach(n => {
        if (!childrenByParent.has(n.parent_id)) childrenByParent.set(n.parent_id, []);
        childrenByParent.get(n.parent_id).push(n);
    });
    childrenByParent.forEach(list => list.sort((a, b) => a.name.localeCompare(b.name, 'ru')));

    const subtreeCountCache = new Map();
    function subtreeCount(nodeId) {
        if (subtreeCountCache.has(nodeId)) return subtreeCountCache.get(nodeId);
        let total = incidentLocationCounts[nodeId] || 0;
        (childrenByParent.get(nodeId) || []).forEach(c => { total += subtreeCount(c.id); });
        subtreeCountCache.set(nodeId, total);
        return total;
    }

    const roots = childrenByParent.get(null) || [];
    // Заявки без места (location_node_id = null) — отдельный ключ
    // 'unassigned' от backend (get_location_counts), не входят ни в один
    // узел дерева, но должны учитываться в итоге "Все заявки".
    const unassignedCount = incidentLocationCounts['unassigned'] || 0;
    const totalCount = roots.reduce((sum, r) => sum + subtreeCount(r.id), 0) + unassignedCount;
    const isRootActive = incidentActiveLocationId === null;
    let html = `
        <div class="tree-root ${isRootActive ? 'active' : ''}" onclick="resetIncidentLocationFilter()">
            <span class="tree-workshop-label">Все заявки</span>
            <span class="tree-count-chip">${totalCount}</span>
        </div>`;

    if (roots.length === 0) {
        body.innerHTML = html + '<div class="no-data">Мест пока нет — добавьте в справочнике или прямо из заявки</div>';
        return;
    }

    function renderNode(node, depth) {
        const children = childrenByParent.get(node.id) || [];
        const hasChildren = children.length > 0;
        const count = subtreeCount(node.id);
        const isActive = incidentActiveLocationId === node.id;
        const isCollapsed = incidentCollapsedLocationIds.has(node.id);
        const typeLabel = (typeof LOCATION_NODE_TYPE_LABELS !== 'undefined' && LOCATION_NODE_TYPE_LABELS[node.node_type]) || node.node_type;
        const rowClass = hasChildren ? 'tree-workshop' : 'tree-location';
        const chevronHtml = hasChildren
            ? `<span class="tree-chevron" onclick="event.stopPropagation(); toggleIncidentLocationNode(${node.id})">${isCollapsed ? '▶' : '▼'}</span>`
            : '';
        const rowHtml = `
                <div class="${rowClass} ${isActive ? 'active' : ''}" style="padding-left:${depth * 16 + 12}px" data-id="${node.id}"
                     title="${escapeHtml(typeLabel)}"
                     onclick="selectIncidentLocation(${node.id})">
                    ${chevronHtml}
                    <span class="tree-workshop-label">${escapeHtml(node.name)}</span>
                    <span class="tree-location-right">
                        <span class="tree-count-chip">${count}</span>
                        <button type="button" class="tree-add-btn write-action" title="Создать заявку по этому месту"
                                onclick="event.stopPropagation(); createIncidentAtLocation(${node.id}, '${escapeAttr(node.name)}')">+</button>
                    </span>
                </div>`;

        if (!hasChildren) return rowHtml;
        return `
            <div class="tree-workshop-group">${rowHtml}
                <div class="tree-locations ${isCollapsed ? 'hidden' : ''}">${children.map(c => renderNode(c, depth + 1)).join('')}</div>
            </div>`;
    }

    roots.forEach(r => { html += renderNode(r, 0); });

    body.innerHTML = html;

    if (incidentActiveLocationId !== null) {
        const activeEl = body.querySelector(`[data-id="${incidentActiveLocationId}"]`);
        if (activeEl) activeEl.classList.add('active');
    }
}

function toggleIncidentLocationNode(nodeId) {
    if (incidentCollapsedLocationIds.has(nodeId)) {
        incidentCollapsedLocationIds.delete(nodeId);
    } else {
        incidentCollapsedLocationIds.add(nodeId);
    }
    renderIncidentLocationTree();
}

function selectIncidentLocation(nodeId) {
    incidentActiveLocationId = nodeId;
    // Разворачивание/сворачивание теперь тоже по клику на всю строку
    // узла, а не только по шеврону — та же логика, что и в
    // toggleIncidentLocationNode() (шеврон по-прежнему работает сам по
    // себе отдельно, с event.stopPropagation() — переключает раскрытие
    // без смены текущего фильтра). Идентичный фикс сделан и в
    // equipmentLocationTree.js::selectEquipmentLocation.
    if (incidentCollapsedLocationIds.has(nodeId)) {
        incidentCollapsedLocationIds.delete(nodeId);
    } else {
        incidentCollapsedLocationIds.add(nodeId);
    }
    if (typeof loadIncidentsList === 'function') loadIncidentsList();
    renderIncidentLocationTree();
}

function resetIncidentLocationFilter() {
    incidentActiveLocationId = null;
    if (typeof loadIncidentsList === 'function') loadIncidentsList();
    renderIncidentLocationTree();
}
