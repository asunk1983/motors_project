// static/js/locationTree.js — боковое дерево "Цех → Место установки" на вкладке Каталог.
// Требует: common.js, catalog.js (loadEngines, currentPage)

let activeWorkshop = null;
let activeLocation = null;

// ID двигателя, созданного через "+", но ещё ни разу не сохранённого
// кнопкой "Сохранить" в карточке. Используется в engineCard.js (closeDetail,
// renderDetailContent — прячет кнопки навигации/печати/удаления для такой
// карточки и подставляет DELETE при закрытии без сохранения).
let pendingNewEngineId = null;

// Создаёт двигатель сразу как настоящую запись (POST /api/engine) и
// открывает её в обычной карточке (showDetail), сразу в режиме
// редактирования. Если закрыть карточку без нажатия "Сохранить" —
// engineCard.js::closeDetail() удалит эту запись (см. pendingNewEngineId).
//
// createAndOpenEngine() — пустая карточка (клик по "+" в шапке дерева)
// createAndOpenEngine(workshop, null) — предзаполнен только цех
// createAndOpenEngine(workshop, location) — предзаполнены цех и место
function createAndOpenEngine(workshop, location) {
    const payload = {};
    if (workshop !== undefined && workshop !== null) payload.workshop = workshop;
    if (location !== undefined && location !== null) payload.location = location;

    apiFetch('/api/engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error', 'icon-cancel');
                return;
            }
            pendingNewEngineId = data.id;
            showDetail(data.id, true);
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function loadLocationTree() {
    apiFetch('/api/locations-tree')
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                document.getElementById('locationTreeBody').innerHTML =
                    `<div class="no-data">Ошибка: ${escapeHtml(data.error)}</div>`;
                return;
            }
            renderLocationTree(data);
        })
        .catch(e => {
            document.getElementById('locationTreeBody').innerHTML =
                `<div class="no-data">Не удалось загрузить: ${escapeHtml(e.message)}</div>`;
        });
}

function renderLocationTree(tree) {
    const body = document.getElementById('locationTreeBody');
    const workshops = Object.keys(tree).sort((a, b) => a.localeCompare(b, 'ru'));

    if (workshops.length === 0) {
        body.innerHTML = '<div class="no-data">Нет данных</div>';
        return;
    }

    // Общий счётчик по всем цехам — для корневого пункта "Все объекты"
    // (см. .tree-root в style.css). Считаем один раз до рендера дерева.
    const totalCount = workshops.reduce((sum, w) => {
        const locations = tree[w];
        return sum + Object.values(locations).reduce((s, c) => s + c, 0);
    }, 0);
    const isRootActive = activeWorkshop === null && activeLocation === null;
    const rootHtml = `
        <div class="tree-root ${isRootActive ? 'active' : ''}" onclick="resetLocationFilter()">
            <span class="tree-workshop-label">Все объекты</span>
            <span class="tree-count-chip">${totalCount}</span>
        </div>`;

    const workshopsHtml = workshops.map(workshop => {
        const locations = tree[workshop];
        const locKeys = Object.keys(locations).sort((a, b) => a.localeCompare(b, 'ru'));
        // Счётчик цеха — сумма количеств по всем его местам установки.
        // Раньше показывался только у мест внутри развёрнутого цеха —
        // теперь виден всегда, даже когда цех свёрнут (по референсу).
        const workshopCount = locKeys.reduce((s, loc) => s + locations[loc], 0);
        const isOpen = workshop === activeWorkshop;
        const workshopLabel = workshop || 'Без цеха';

        const locHtml = locKeys.map(loc => {
            const count = locations[loc];
            const locLabel = loc || 'Без места установки';
            const isActive = workshop === activeWorkshop && loc === activeLocation;
            return `
                <div class="tree-location ${isActive ? 'active' : ''}"
                     data-workshop="${escapeHtml(workshop)}"
                     data-location="${escapeHtml(loc)}"
                     onclick="selectTreeLocation('${escapeAttr(workshop)}', '${escapeAttr(loc)}')">
                    <span class="tree-workshop-label">${escapeHtml(locLabel)}</span>
                    <span class="tree-location-right">
                        <span class="tree-count-chip">${count}</span>
                        <button type="button" class="tree-add-btn write-action" title="Добавить двигатель в это место"
                                onclick="event.stopPropagation(); createAndOpenEngine('${escapeAttr(workshop)}', '${escapeAttr(loc)}')">+</button>
                    </span>
                </div>`;
        }).join('');

        return `
            <div class="tree-workshop-group">
                <div class="tree-workshop ${isOpen ? 'active' : ''}" onclick="toggleTreeWorkshop('${escapeAttr(workshop)}')">
                    <span class="tree-chevron">${isOpen ? '▼' : '▶'}</span>
                    <span class="tree-workshop-label">${escapeHtml(workshopLabel)}</span>
                    <span class="tree-count-chip">${workshopCount}</span>
                    <button type="button" class="tree-add-btn write-action" title="Добавить двигатель в этот цех"
                            onclick="event.stopPropagation(); createAndOpenEngine('${escapeAttr(workshop)}', null)">+</button>
                </div>
                <div class="tree-locations ${isOpen ? '' : 'hidden'}">${locHtml}</div>
            </div>`;
    }).join('');

    body.innerHTML = rootHtml + workshopsHtml;
}

function toggleTreeWorkshop(workshop) {
    if (activeWorkshop === workshop) {
        if (activeLocation !== null) {
            // Уже отфильтрован по конкретному месту — снимаем выбор места,
            // остаёмся на уровне цеха (показываем все записи цеха).
            activeLocation = null;
        } else {
            // Цех уже активен без выбора места — снимаем фильтр цеха.
            activeWorkshop = null;
        }
    } else {
        // Новый цех — показываем все записи, относящиеся к нему.
        activeWorkshop = workshop;
        activeLocation = null;
    }
    currentPage = 1;
    loadEngines();
    loadLocationTree();
}

function selectTreeLocation(workshop, location) {
    activeWorkshop = workshop;
    activeLocation = location;
    currentPage = 1;
    loadEngines();
    loadLocationTree();
}

function resetLocationFilter() {
    activeWorkshop = null;
    activeLocation = null;
    currentPage = 1;
    loadEngines();
    loadLocationTree();
}

// escapeAttr — общая утилита из common.js (экранирование для onclick-атрибута
// в одинарных кавычках). Раньше была определена здесь локально, а её же
// использовал equipmentLocationTree.js (другая вкладка, независимый файл) без
// гарантии, что оба файла всегда загружены вместе. См. common.js.

document.addEventListener('DOMContentLoaded', function() {
    loadLocationTree();
});