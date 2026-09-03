// static/js/catalog.js — список/фильтры/пагинация/сортировка/поиск.
// Требует: common.js, engines.js (глобальные переменные состояния)

let currentSearchQuery = '';

// ===== СТАТИСТИКА =====
function updateStats() {
    apiFetch('/api/status')
        .then(r => r.json())
        .then(data => {
            document.getElementById('totalEngines').textContent = data.engine_count || 0;
            document.getElementById('totalPhotos').textContent = data.photos_count || 0;
            document.getElementById('filesCount').textContent = data.files_in_folder || 0;
            document.getElementById('photosCount').textContent = data.photos_count || 0;
            document.getElementById('settingsRecords').textContent = data.engine_count || 0;
            document.getElementById('settingsPhotos').textContent = data.photos_count || 0;
            document.getElementById('settingsDbSize').textContent = data.db_size_label || '0 KB';

            // Дашборд-счётчики Инцидентов/Оборудования (ТЗ раздел 4) —
            // элементы могут отсутствовать в DOM на страницах, где эта
            // группа настроек не выведена, поэтому каждый через optional
            // chaining, а не через жёсткий getElementById(...).textContent.
            document.getElementById('settingsEquipmentCount') && (document.getElementById('settingsEquipmentCount').textContent = data.equipment_count ?? 0);
            document.getElementById('settingsEquipmentPhotosCount') && (document.getElementById('settingsEquipmentPhotosCount').textContent = data.equipment_photos_count ?? 0);
            document.getElementById('settingsIncidentCount') && (document.getElementById('settingsIncidentCount').textContent = data.incident_count ?? 0);
            document.getElementById('settingsIncidentOpenCount') && (document.getElementById('settingsIncidentOpenCount').textContent = data.incident_open_count ?? 0);
            document.getElementById('settingsIncidentPhotosCount') && (document.getElementById('settingsIncidentPhotosCount').textContent = data.incident_photos_count ?? 0);
        })
        .catch(() => {});
}

function loadSettings() {
    updateStats();
    loadBackupsList();
}


// ===== ВКЛАДКИ =====
document.addEventListener('DOMContentLoaded', function() {
    const activeTab = document.querySelector('.tab-btn.active') || document.querySelector('.tab-btn');
    if (activeTab) {
        const tabId = activeTab.dataset.tab;
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        const content = document.getElementById(`tab-${tabId}`);
        if (content) content.classList.add('active');
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            switchTab(tabId);
        });
    });

    loadEngines();
    updateStats();
});


function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    const content = document.getElementById(`tab-${tabId}`);
    if (content) content.classList.add('active');

    // Запоминаем активную вкладку — при обычном F5 DOM пересоздаётся из
    // статического index.html, где "Каталог" всегда помечен active в
    // разметке. Без сохранения пользователь после каждого обновления
    // страницы оказывался на Каталоге, даже если работал на другой вкладке.
    try { localStorage.setItem('motors_active_tab', tabId); } catch (e) {}

    if (tabId === 'catalog') {
        const searchInput = document.getElementById('searchInput');
        const searchFieldSelect = document.getElementById('searchFieldSelect');
        searchInput.value = '';
        searchInput.dispatchEvent(new Event('input'));
        searchFieldSelect.value = 'all';
        searchFieldSelect.dispatchEvent(new Event('change'));
        document.getElementById('engineStatusFilter').value = '';
        resetLocationFilter();
    } else {
        if (tabId === 'import') updateStats();
        if (tabId === 'settings') loadSettings();
        if (tabId === 'info') loadInfoTab();
        if (tabId === 'knowledge' && typeof loadKnowledgeTab === 'function') loadKnowledgeTab();
        if (tabId === 'equipment' && typeof loadEquipmentTab === 'function') loadEquipmentTab();
        if (tabId === 'tickets' && typeof loadTicketsTab === 'function') loadTicketsTab();
        if (tabId === 'incidents' && typeof loadIncidentsTab === 'function') loadIncidentsTab();
    }
}
function recalcPageSize() {
    const wrapper = document.querySelector('.table-wrapper');
    const tbody = document.getElementById('tableBody');
    if (!wrapper || !tbody || wrapper.classList.contains('hidden')) return pageSize;

    const headerRow = wrapper.querySelector('thead tr');
    const bodyRow = tbody.querySelector('tr');
    // Пока в DOM нет ни одной РЕАЛЬНОЙ строки данных (самый первый вызов,
    // до первой загрузки, либо пустая таблица) — точную высоту строки
    // измерить не на чем. Используем консервативную оценку по паддингам
    // из style.css (.data-table td: space-3 верт. паддинг ×2 + текст
    // ~18px + border-bottom 1px ≈ 43px), а не отдельную служебную
    // строку-заглушку только ради замера.
    const hasRealRow = bodyRow && !bodyRow.querySelector('.no-data');
    const headerHeight = headerRow ? headerRow.getBoundingClientRect().height : 44;
    const rowHeight = hasRealRow ? bodyRow.getBoundingClientRect().height : 43;

    const available = wrapper.clientHeight - headerHeight;
    const fit = Math.floor(available / rowHeight);
    // Не меньше 5 — иначе при сильно уменьшенном окне/увеличенном zoom
    // пагинация выродится в бесполезные "по 1 записи за раз".
    return Math.max(fit, 5);
}

function applyDynamicPageSize() {
    const next = recalcPageSize();
    if (next === pageSize) return;
    // Сохраняем ту же ПЕРВУЮ видимую запись при пересчёте (а не всегда
    // прыгаем на страницу 1) — иначе список "убегал" бы в начало при
    // каждом ресайзе окна.
    const firstVisibleIndex = (currentPage - 1) * pageSize;
    pageSize = next;
    currentPage = Math.max(1, Math.floor(firstVisibleIndex / pageSize) + 1);
    renderTable();
}

const debouncedApplyDynamicPageSize = debounce(applyDynamicPageSize, 150);

// ResizeObserver вместо гадания "в какой момент замерять". Раньше здесь
// были ручные точки пересчёта (сразу после первой отрисовки, после
// document.fonts.ready, после window.load) — на практике этого всё равно
// не хватило (реальный тест показал pageSize, залипший на заниженном
// значении из-за того, что первый замер поймал ещё не устоявшуюся
// раскладку тулбара). ResizeObserver реагирует на САМ ФАКТ изменения
// размера .table-wrapper — из-за переноса строк в тулбаре, ресайза окна,
// чего угодно — а не на предположение "к этому моменту уже всё готово".
// Наблюдение стартует сразу с одним начальным вызовом (стандартное
// поведение ResizeObserver), так что отдельный вызов при первой загрузке
// в loadEngines() больше не обязателен, но оставлен — он использует уже
// реально отрисованную строку сразу после прихода данных, не дожидаясь
// первого срабатывания observer'а.
const tableWrapperEl = document.querySelector('.table-wrapper');
if (tableWrapperEl && typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(debouncedApplyDynamicPageSize).observe(tableWrapperEl);
} else {
    // Совсем старый браузер без ResizeObserver — откатываемся на ресайз окна.
    window.addEventListener('resize', debouncedApplyDynamicPageSize);
}
// Догрузка веб-шрифта не меняет РАЗМЕР .table-wrapper (он задан
// flex-раскладкой независимо от контента внутри), а значит ResizeObserver
// на wrapper этот случай не поймает — меняется только высота СТРОКИ
// внутри уже неизменного по размеру контейнера. Поэтому отдельный триггер.
if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(applyDynamicPageSize).catch(() => {});
}


// ===== ЗАГРУЗКА ДАННЫХ =====
function loadEngines() {
    const search = document.getElementById('searchInput').value;
    currentSearchQuery = search;   // ← добавлено: используется в renderTable() для подсветки
    const searchField = document.getElementById('searchFieldSelect').value;
    let url = `/api/engines?sort_by=${currentSort.field}&sort_order=${currentSort.order}`;
    
    if (search) {
        if (searchField !== 'all') {
            url += `&search_field=${searchField}&search=${encodeURIComponent(search)}`;
        } else {
            url += `&search=${encodeURIComponent(search)}`;
        }
    }

    // Фильтр от дерева цехов (locationTree.js) — комбинируется с обычным
    // поиском выше. typeof-проверка вместо прямой ссылки на activeWorkshop,
    // чтобы catalog.js не падал, если locationTree.js почему-то не загружен.
    if (typeof activeWorkshop !== 'undefined' && activeWorkshop !== null) {
        url += `&workshop=${encodeURIComponent(activeWorkshop)}`;
    }
    if (typeof activeLocation !== 'undefined' && activeLocation !== null) {
        url += `&location=${encodeURIComponent(activeLocation)}`;
    }

    const statusFilter = document.getElementById('engineStatusFilter').value;
    if (statusFilter) {
        url += `&status=${encodeURIComponent(statusFilter)}`;
    }

    apiFetch(url)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error', 'icon-cancel');
                return;
            }
            allEngines = data;
            renderTable();
            // Первая отрисовка могла использовать ещё не откалиброванный
            // pageSize (до неё в DOM не было ни одной реальной строки,
            // чтобы измерить её высоту) — пересчитываем и, если нужно,
            // перерисовываем уже с точным количеством строк на экран.
            applyDynamicPageSize();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}


// ===== СТАТУС ДВИГАТЕЛЯ =====
const ENGINE_STATUS_LABELS = {
    work: 'В работе',
    reserve: 'В резерве',
    repair: 'В ремонте',
};

function engineStatusBadgeHtml(status) {
    // status здесь приходит из бэкенда уже пересчитанным:
    // engine_repo.get_all делает LEFT JOIN на CTE last_work и подменяет
    // engines.status на COALESCE(последняя работа по (date, id), 'reserve').
    // Это тот же источник, что и в карточке (engineCard.js::
    // getEngineStatusFromWorks берёт status последней записи works).
    // Fallback на 'work' — защита от мусорных значений (NULL, '', 'lol').
    const key = ENGINE_STATUS_LABELS[status] ? status : 'work';
    return `<span class="engine-status-badge engine-status-${key}">${ENGINE_STATUS_LABELS[key]}</span>`;
}

function onEngineStatusFilterChange() {
    currentPage = 1;
    loadEngines();
}


// ===== ТАБЛИЦА =====
function renderTable() {
    const tbody = document.getElementById('tableBody');
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageData = allEngines.slice(start, end);

    if (!pageData || pageData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="no-data">Нет данных</td></tr>`;
        document.getElementById('pageInfo').textContent = 'Показано 0 из 0';
        return;
    }

    tbody.innerHTML = pageData.map(e => `
        <tr class="clickable-row" onclick="showDetail(${e.id})" data-id="${e.id}">
            <td class="col-checkbox" onclick="event.stopPropagation()"><input type="checkbox" class="row-checkbox" ${selectedEngineIds.has(e.id) ? 'checked' : ''} onchange="toggleEngineSelection(${e.id}, this.checked)"></td>
            <td><span class="badge-id">${e.id}</span></td>
            <td>${engineStatusBadgeHtml(e.status)}</td>
            <td>${highlightMatch(e.location, currentSearchQuery) || '—'}</td>
            <td class="mono">${highlightMatch(e.engine_type, currentSearchQuery) || '—'}</td>
            <td class="mono mono-muted">${highlightMatch(e.serial_number, currentSearchQuery) || '—'}</td>
            <td>${highlightMatch(e.manufacturer, currentSearchQuery) || '—'}</td>
            <td>${highlightMatch(e.purpose, currentSearchQuery) || '—'}</td>
            <td>${formatRuDateTime(e.updated_at)}</td>
            <td class="col-photo">${e.photo_count > 0 ? `<span class="photo-badge"><span class="icon icon-photo-camera"></span> ${e.photo_count}</span>` : '—'}</td>
        </tr>
    `).join('');

    // Диапазон 1-based, а не просто "показано N из M" — конец диапазона
    // считаем от pageData.length (реально отрисованных строк), а не от
    // pageSize, чтобы на последней неполной странице не показать
    // "91-100 из 97".
    const rangeStart = start + 1;
    const rangeEnd = start + pageData.length;
    document.getElementById('pageInfo').textContent = `${rangeStart}-${rangeEnd} из ${allEngines.length}`;
    document.getElementById('pageNumber').textContent = currentPage;
}


function prevPage() {
    if (currentPage > 1) { currentPage--; renderTable(); }
}

function nextPage() {
    if (currentPage * pageSize < allEngines.length) { currentPage++; renderTable(); }
}

function sortTable(field) {
    if (currentSort.field === field) {
        currentSort.order = currentSort.order === 'ASC' ? 'DESC' : 'ASC';
    } else {
        currentSort.field = field;
        currentSort.order = 'ASC';
    }
    loadEngines();
}


// ===== ВЫБОР ДВИГАТЕЛЕЙ ДЛЯ ЭКСПОРТА =====
function toggleEngineSelection(id, checked) {
    if (checked) {
        selectedEngineIds.add(id);
    } else {
        selectedEngineIds.delete(id);
    }
    updateSelectAllState();
    updateExportButton();
}

function toggleSelectAll(checked) {
    // closest('[data-id]') вместо closest('tr') — .row-checkbox теперь
    // стоит и в строках таблицы (<tr data-id>), и в карточках
    // (<div class="equipment-card" data-id>), id-контейнер общий атрибут
    // data-id у обоих, а не тег.
    _visibleRowCheckboxes().forEach(cb => {
        cb.checked = checked;
        const idHolder = cb.closest('[data-id]');
        if (idHolder) {
            const id = parseInt(idHolder.dataset.id);
            if (checked) {
                selectedEngineIds.add(id);
            } else {
                selectedEngineIds.delete(id);
            }
        }
    });
    updateSelectAllState();
    updateExportButton();
}

// Раньше здесь учитывался ещё и карточный вид (переключаемый видом
// #cardWrapper) — вида карточками больше нет, чекбоксы выбора всегда
// только в таблице.
function _visibleRowCheckboxes() {
    const tableWrapper = document.querySelector('.table-wrapper');
    return tableWrapper ? tableWrapper.querySelectorAll('.row-checkbox') : document.querySelectorAll('.row-checkbox');
}

function clearSelection() {
    selectedEngineIds.clear();
    // Полная очистка выбора — сбрасываем чекбоксы в ОБОИХ видах (не только
    // видимом), иначе при следующем переключении вида увидим
// отмеченные чекбоксы, не соответствующие уже опустевшему selectedEngineIds.
    document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
    updateSelectAllState();
    updateExportButton();
    showToast('Выбор снят', 'success', 'icon-check-circle');
}

function updateSelectAllState() {
    const checkboxes = _visibleRowCheckboxes();
    const checkedBoxes = Array.from(checkboxes).filter(cb => cb.checked);
    const selectAll = document.getElementById('selectAllCheckbox');
    if (selectAll) {
        if (checkboxes.length === 0) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        } else if (checkedBoxes.length === checkboxes.length) {
            selectAll.checked = true;
            selectAll.indeterminate = false;
        } else if (checkedBoxes.length > 0) {
            selectAll.checked = false;
            selectAll.indeterminate = true;
        } else {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        }
    }
}

function updateExportButton() {
    const count = selectedEngineIds.size;
    const btn = document.getElementById('exportBtn');
    const info = document.getElementById('selectionInfo');
    const countEl = document.getElementById('selectionCount');
    
    if (btn) {
        btn.disabled = count === 0;
    }
    if (info) {
        info.classList.toggle('hidden', count === 0);
    }
    if (countEl) {
        countEl.textContent = count;
    }
}


// ===== ЭКСПОРТ В EXCEL =====
function exportSelected() {
    const ids = Array.from(selectedEngineIds);
    
    if (ids.length === 0) {
        showToast('Не выбрано ни одного двигателя', 'warning', 'icon-warning');
        return;
    }
    
    showToast('Подготовка экспорта...', 'info', 'icon-progress-activity');
    
    apiFetch('/api/engines/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids })
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
        a.download = `passports_export_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showToast('Экспорт завершен!', 'success', 'icon-check-circle');
    })
    .catch(e => {
        showToast('Ошибка экспорта: ' + e.message, 'error', 'icon-cancel');
    });
}


// ===== НАВИГАЦИЯ ПО ДВИГАТЕЛЯМ (С АНИМАЦИЕЙ) =====
function navigateEngine(direction) {
    if (!currentEngineId) return;
    const currentIndex = allEngines.findIndex(e => e.id === currentEngineId);
    if (currentIndex === -1) return;
    const newIndex = currentIndex + direction;
    if (newIndex < 0 || newIndex >= allEngines.length) {
        showToast('Двигателей больше нет', 'warning', 'icon-warning');
        return;
    }
    
    const modalContent = document.querySelector('.modal-content');
    if (modalContent) {
        modalContent.classList.add('slide-out');
    }
    
    setTimeout(() => {
        const newEngine = allEngines[newIndex];
        showDetail(newEngine.id);
    }, 300);
}


// ===== РЕДАКТИРОВАНИЕ =====
function editEngine(id) {
    showDetail(id, true);
}

function deleteEngine(id) {
    if (!confirm(`Удалить двигатель ID=${id}?`)) return;

    apiFetch(`/api/engine/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error', 'icon-cancel');
            } else {
                showToast(data.message, 'success', 'icon-check-circle');
                loadEngines();
                updateStats();
            }
        });
}


// ===== СОРТИРОВКА =====
document.getElementById('sortSelect').addEventListener('change', function() {
    // Было this.value.split('_') — для значений вроде "engine_type_asc"
    // это давало 3 части ('engine', 'type', 'asc'), и field/order
    // получались неверными (field='engine', order='type' — не ASC/DESC,
    // бэкенд молча откатывался на сортировку по умолчанию). Граница
    // между полем и направлением — всегда ПОСЛЕДНЕЕ подчёркивание,
    // само поле (engine_type, created_at, updated_at...) может их
    // содержать сколько угодно.
    const sep = this.value.lastIndexOf('_');
    const field = this.value.slice(0, sep);
    const order = this.value.slice(sep + 1);
    currentSort.field = field;
    currentSort.order = order.toUpperCase();
    loadEngines();
});


// ===== ПОИСК =====
const debouncedLoadEngines = debounce(function() {
    currentPage = 1;
    loadEngines();
}, 350);
document.getElementById('searchInput').addEventListener('input', debouncedLoadEngines);

document.getElementById('searchFieldSelect').addEventListener('change', function() {
    currentPage = 1;
    loadEngines();
});
