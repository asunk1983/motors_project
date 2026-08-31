// static/js/engines.js — ПОЛНАЯ ВЕРСИЯ
let currentPage = 1;
let pageSize = 20; // стартовое значение — пересчитывается в catalog.js::applyDynamicPageSize() под реальную высоту экрана сразу после первой загрузки данных
let allEngines = [];
let currentSort = { field: 'location', order: 'ASC' };
let currentSearchField = 'all';

// ===== ПЕРЕМЕННЫЕ ДЛЯ НАВИГАЦИИ =====
let currentEngineId = null;
let currentPhotos = [];
let currentPhotoIndex = 0;
let currentEngineData = null;
let detailEditMode = false;
let detailMode = 'view';
let detailPhotoFiles = [];
// Кэш-бастинг превью уже загруженных фото. renderDetailContent()
// вызывается очень часто (на каждое изменение режима/сохранение работ),
// поэтому нельзя генерировать новый ${Date.now()} на каждый рендер —
// картинки будут перезагружаться с сервера без необходимости. Обновляем
// это значение только там, где фото на диске реально изменилось:
// загрузка, удаление, обрезка.
let photoCacheBust = Date.now();


// Числовые поля характеристик — влияют на type инпута в инлайн-редактировании
// карточки (см. DETAIL_CHAR_FIELDS.forEach ниже) и на клавиатуру/валидацию
// на мобильных устройствах.

let pendingPhotoFiles = [];
let selectedEngineIds = new Set();



// ===== АВТОДОПОЛНЕНИЕ =====
// Кастомный выпадающий список подсказок — замена нативного
// <input list="datalist">. Причины отказа от datalist (см. CLAUDE.md):
// 1) в разных браузерах он рисует собственный, нестилизуемый
//    треугольник-индикатор справа от поля;
// 2) список подсказок не открывается по одному клику на пустое поле —
//    нужно either начать печатать, either кликать дважды.
// Ниже — свой dropdown: наполняется по фокусу/вводу и открывается сразу.
function attachSuggestDropdown(inputEl, fieldNameOrFn) {
    if (!inputEl || inputEl.dataset.autocompleteBound) return;
    inputEl.dataset.autocompleteBound = '1';

    const wrap = document.createElement('div');
    wrap.className = 'suggest-wrap';
    inputEl.insertAdjacentElement('beforebegin', wrap);
    wrap.appendChild(inputEl);

    const dropdown = document.createElement('div');
    dropdown.className = 'suggest-dropdown hidden';
    wrap.appendChild(dropdown);

    let items = [];
    let activeIndex = -1;

    function positionDropdown() {
        const rect = inputEl.getBoundingClientRect();
        dropdown.style.top = rect.bottom + 'px';
        dropdown.style.left = rect.left + 'px';
        dropdown.style.width = rect.width + 'px';
    }

    function renderDropdown() {
        dropdown.innerHTML = items.length
            ? items.map((v, i) => `<div class="suggest-item${i === activeIndex ? ' active' : ''}" data-idx="${i}">${escapeHtml(v)}</div>`).join('')
            : '<div class="suggest-empty">Нет совпадений</div>';
        positionDropdown();
        dropdown.classList.remove('hidden');
    }

    function closeDropdown() {
        dropdown.classList.add('hidden');
        activeIndex = -1;
    }

    function selectItem(value) {
        inputEl._ignoreInput = true;
        inputEl.value = value;
        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
        closeDropdown();
        inputEl.focus();
    }

    const fetchSuggestions = debounce(function() {
        if (inputEl._ignoreInput) {
            inputEl._ignoreInput = false;
            return;
        }
        const fieldName = typeof fieldNameOrFn === 'function' ? fieldNameOrFn() : fieldNameOrFn;
        if (!fieldName) { closeDropdown(); return; }
        const query = inputEl.value.trim();
        apiFetch(`/api/search-suggestions?field=${encodeURIComponent(fieldName)}&query=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(values => {
                items = values || [];
                activeIndex = -1;
                renderDropdown();
            })
            .catch(() => {});
    }, 200);

    // По фокусу — сразу же (даже с пустым значением, backend вернёт
    // топ-50 значений поля без фильтра), и по вводу — с фильтром.
    inputEl.addEventListener('focus', fetchSuggestions);
    inputEl.addEventListener('input', fetchSuggestions);

    inputEl.addEventListener('keydown', function(e) {
        if (dropdown.classList.contains('hidden')) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            renderDropdown();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            renderDropdown();
        } else if (e.key === 'Enter' && activeIndex >= 0 && items[activeIndex] !== undefined) {
            e.preventDefault();
            selectItem(items[activeIndex]);
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    // mousedown, а не click — опережает blur инпута (см. ниже), иначе
    // dropdown успевает закрыться раньше, чем сработает выбор пункта.
    dropdown.addEventListener('mousedown', function(e) {
        const itemEl = e.target.closest('.suggest-item');
        if (!itemEl) return;
        e.preventDefault();
        const idx = parseInt(itemEl.dataset.idx, 10);
        if (!isNaN(idx) && items[idx] !== undefined) selectItem(items[idx]);
    });

    // Задержка перед закрытием по blur — чтобы mousedown по пункту
    // списка успел отработать первым.
    inputEl.addEventListener('blur', function() {
        setTimeout(closeDropdown, 150);
    });

    // Закрываем выпадающий список при скролле страницы — список
    // position:fixed не привязан к полю при прокрутке, поэтому
    // лучше закрыть его. capture:true ловит скролл внутри любого
    // вложенного контейнера с overflow (modal-body, table-wrapper).
    document.addEventListener('scroll', function(e) {
        if (!dropdown.classList.contains('hidden') && !dropdown.contains(e.target)) {
            closeDropdown();
        }
    }, true);
}

// Обёртка с фиксированным именем поля — сохранён прежний контракт вызова
// (attachFieldAutocomplete(inputEl, fieldName)), используется во всех
// местах карточки/формы добавления, где поле известно заранее.
function attachFieldAutocomplete(inputEl, fieldName) {
    attachSuggestDropdown(inputEl, fieldName);
}


// ===== КЛАВИАТУРА =====
document.addEventListener('keydown', function(e) {
    const photoModal = document.getElementById('photoModal');
    const detailModal = document.getElementById('detailModal');
    // equipmentModal/incidentTicketModal — та же листалка ◀/▶, что и у
    // карточки двигателя (запрошено вместе с унификацией шапки карточек,
    // см. renderEquipmentDetailToolbar/renderIncidentDetailToolbar).
    const equipmentModal = document.getElementById('equipmentModal');
    const incidentModal = document.getElementById('incidentTicketModal');

    // Если стрелками двигают курсор внутри текстового поля (input/textarea/
    // contenteditable) — не перехватываем событие для листания карточек/фото,
    // иначе введённый текст не сохраняется при смене карточки.
    const activeTag = e.target.tagName;
    const isEditableTarget = activeTag === 'INPUT' || activeTag === 'TEXTAREA' || e.target.isContentEditable;
    if (isEditableTarget && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
        return;
    }

    if (photoModal && photoModal.classList.contains('active')) {
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            navigatePhotoModal(-1);
            return;
        }
        if (e.key === 'ArrowRight') {
            e.preventDefault();
            navigatePhotoModal(1);
            return;
        }
    }
    
    if (detailModal && detailModal.classList.contains('active')) {
        if (!photoModal || !photoModal.classList.contains('active')) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                navigateEngine(-1);
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                navigateEngine(1);
                return;
            }
        }
    }

    if (equipmentModal && equipmentModal.classList.contains('active')) {
        if (!photoModal || !photoModal.classList.contains('active')) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                navigateEquipment(-1);
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                navigateEquipment(1);
                return;
            }
        }
    }

    if (incidentModal && incidentModal.classList.contains('active')) {
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            navigateIncident(-1);
            return;
        }
        if (e.key === 'ArrowRight') {
            e.preventDefault();
            navigateIncident(1);
            return;
        }
    }
    
    if (e.key === 'Escape') {
        if (photoModal && photoModal.classList.contains('active')) {
            closePhotoModal();
            return;
        }
        if (detailModal && detailModal.classList.contains('active')) {
            closeDetail();
            return;
        }
        if (equipmentModal && equipmentModal.classList.contains('active')) {
            closeEquipmentModal();
            return;
        }
        if (incidentModal && incidentModal.classList.contains('active')) {
            closeIncidentModal();
        }
    }
});

