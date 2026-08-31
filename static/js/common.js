// static/js/common.js — общие утилиты, используемые в engines.js и print.js.
// Подключать ПЕРВЫМ (до engines.js / print.js), чтобы функции и константы
// были доступны в глобальном scope.

// Используем \u0026 вместо & в строках-замен, чтобы редактор не
// "прооптимизировал" HTML-сущности в пустые строки.
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '\u0026amp;')
        .replace(/</g, '\u0026lt;')
        .replace(/>/g, '\u0026gt;')
        .replace(/"/g, '\u0026quot;')
        .replace(/'/g, '\u0026#39;');
}

// Экранирование для использования ВНУТРИ одинарных кавычек onclick-атрибута
// (апострофы, например, в названии цеха/места/узла дерева сломали бы
// разметку) — escapeHtml для этого не подходит, он не трогает апострофы
// в HTML-безопасном виде, нужном именно для JS-строки внутри атрибута.
// Раньше была определена только в locationTree.js и использовалась оттуда
// же в equipmentLocationTree.js — рабочая, но случайная зависимость: два
// файла живут на разных вкладках без гарантированного порядка загрузки
// или совместного присутствия на странице. Перенесена сюда как общая
// утилита common.js, доступная обоим (и любому будущему потребителю)
// независимо друг от друга.
function escapeAttr(str) {
    // Порядок важен: сначала удваиваем СУЩЕСТВУЮЩИЕ обратные слэши,
    // потом экранируем кавычки — иначе строка, заканчивающаяся на \,
    // "съедала" бы закрывающую кавычку JS-строки внутри onclick
    // (например, 'Тест\' — обратный слэш экранирует кавычку, строка не
    // закрывается, весь onclick-атрибут ломается).
    return String(str || '')
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '&quot;');
}

function debounce(fn, delay) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// Подсвечивает вхождения query в str, экранируя HTML в обеих частях
// (совпавшей и нет) — используется в catalog.js::renderTable() для
// подсветки быстрого поиска прямо в ячейках таблицы. Регистронезависимо,
// т.к. backend ищет через LIKE '%query%' без учёта регистра (SQLite LIKE
// по умолчанию case-insensitive для ASCII).
function highlightMatch(str, query) {
    const text = str === null || str === undefined ? '' : String(str);
    if (!query) return escapeHtml(text);
    // Экранируем спецсимволы regex в самом запросе — иначе ввод вроде
    // "3.5" или "(1)" сломал бы регулярку или дал неверные совпадения.
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    let regex;
    try {
        regex = new RegExp('(' + escapedQuery + ')', 'ig');
    } catch (e) {
        return escapeHtml(text);
    }
    // split с одной capture-группой даёт [до, совпадение, до, совпадение, ...] —
    // совпадения всегда оказываются на нечётных индексах.
    return text.split(regex).map((part, i) =>
        i % 2 === 1
            ? '<mark class="search-highlight">' + escapeHtml(part) + '</mark>'
            : escapeHtml(part)
    ).join('');
}

// Список полей характеристик двигателя.
// Используется в engines.js (renderDetailContent, saveDetailEdit) и print.js
// (renderCharacteristics). Раньше дублировался как PRINT_CHAR_FIELDS в print.js —
// теперь единый источник правды.
const DETAIL_CHAR_FIELDS = [
    { label: 'Назначение', key: 'purpose' },
    { label: 'Цех', key: 'workshop' },
    { label: 'Место установки', key: 'location' },
    { label: 'Тип', key: 'engine_type' },
    { label: 'Производитель', key: 'manufacturer' },
    { label: 'Заводской номер', key: 'serial_number' },
    { label: 'Подшипник передний', key: 'bearing_front' },
    { label: 'Подшипник задний', key: 'bearing_rear' },
    { label: 'Диаметр вала (мм)', key: 'shaft_diameter' },
    { label: 'Степень защиты', key: 'protection_class' },
    { label: 'Тип крепления', key: 'mounting_type' },
    { label: 'Датчик температуры', key: 'temp_sensor' },
    { label: 'Энкодер', key: 'encoder' },
    { label: 'Охлаждение', key: 'cooling' },
    { label: 'Примечание', key: 'note' }
];

// Числовые поля характеристик — влияют на type инпута в инлайн-редактировании
// карточки и на клавиатуру/валидацию на мобильных устройствах.
const DETAIL_NUMERIC_FIELDS = new Set(['workshop', 'shaft_diameter']);

// Обратная совместимость: print.js раньше использовал PRINT_CHAR_FIELDS.
// Перенаправляем на общий список, чтобы не менять логику print.js.
const PRINT_CHAR_FIELDS = DETAIL_CHAR_FIELDS;

function _formatRuDate(isoDate) {
    const parts = (isoDate || '').split('-');
    // Экранируем результат в ЛЮБОЙ ветке, а не только в fallback — date
    // приходит из POST-тела без строгой server-side валидации формата
    // (см. create_changelog_entry в app.py), так что даже "похожая на
    // дату" строка с ровно двумя дефисами теоретически может нести
    // произвольный HTML в одной из частей.
    if (parts.length !== 3) return escapeHtml(isoDate || '');
    return escapeHtml(`${parts[2]}.${parts[1]}.${parts[0]}`);
}

// created_at/updated_at приходят с бэкенда как datetime.now().isoformat()
// (иногда с 6-значными микросекундами — это не строгий ISO 8601, часть
// браузеров может не распарсить). Обрезаем дробную часть секунд до
// миллисекунд перед new Date(), чтобы не зависеть от лояльности парсера.
// Общий хелпер для всех карточек (двигатель/оборудование/заявка) —
// раньше жил только в engineCard.js, вынесен сюда при добавлении дат
// в шапки карточек оборудования и инцидентов, чтобы не копипастить.
function formatRuDateTime(iso) {
    if (!iso) return '—';
    const normalized = iso.replace(/(\.\d{3})\d*$/, '$1');
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return escapeHtml(iso);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ===== РАЗВОРОТ МОДАЛКИ КАРТОЧКИ НА ВЕСЬ ЭКРАН =====
// Как в обычном оконном приложении: первое нажатие разворачивает,
// повторное — возвращает размер, который был до разворачивания. Если
// пользователь до этого сам потянул за угол (нативный CSS resize — см.
// .modal-content { resize: both } в style.css), эти изменения хранятся
// браузером прямо в element.style.width/height; здесь просто читаем и
// на время разворота откладываем их, а не пересчитываем заново.
// Раньше это была отдельная функция toggleDetailMaximize() только для
// #detailModal (карточка двигателя), сидевшая в engineCard.js. Обобщена
// сюда при добавлении такой же кнопки в карточки оборудования и заявок
// Инцидентов — состояние размера хранится per-modal в _modalMaximizeState
// по modalId, чтобы разворот одной карточки не путался с другой, если
// они вдруг окажутся открыты одновременно.
const _modalMaximizeState = {};

function toggleModalMaximize(modalId, btnId) {
    const modalContent = document.querySelector(`#${modalId} .modal-content`);
    const btn = document.getElementById(btnId);
    if (!modalContent) return;
    if (modalContent.classList.contains('maximized')) {
        modalContent.classList.remove('maximized');
        const prev = _modalMaximizeState[modalId];
        modalContent.style.width = prev ? prev.width : '';
        modalContent.style.height = prev ? prev.height : '';
        delete _modalMaximizeState[modalId];
        if (btn) { btn.innerHTML = '<span class="icon icon-open-in-full"></span>'; btn.title = 'Развернуть на весь экран'; }
    } else {
        _modalMaximizeState[modalId] = {
            width: modalContent.style.width || '',
            height: modalContent.style.height || ''
        };
        modalContent.classList.add('maximized');
        if (btn) { btn.innerHTML = '<span class="icon icon-close-fullscreen"></span>'; btn.title = 'Восстановить размер'; }
    }
}

// showToast(message, type, iconClass) — iconClass опционален.
// ВАЖНО: сообщение по-прежнему добавляется через createTextNode, а не
// innerHTML — это защита от XSS (message может содержать текст ошибки
// от сервера без серверной санитизации). Иконка собирается отдельным
// DOM-узлом, а не строкой, поэтому textContent-подход не нарушается.
function showToast(message, type = 'info', iconClass = null) {
    const toast = document.createElement('div');
    toast.className = 'toast' + (type !== 'info' ? ` toast-${type}` : '');
    if (iconClass) {
        const icon = document.createElement('span');
        icon.className = 'icon ' + iconClass;
        toast.appendChild(icon);
        toast.appendChild(document.createTextNode(' '));
    }
    toast.appendChild(document.createTextNode(message));
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-hide');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== УНИВЕРСАЛЬНЫЙ ПОИСК ПО СУЩНОСТЯМ (модуль "Инциденты") =====
// attachSuggestDropdown (см. engines.js) заточен под ОДНО текстовое
// поле engines/modes (field name -> /api/search-suggestions), результат
// подстановки — сама строка. Здесь другая задача: результат поиска —
// объект с id (Место, Crew, Equipment), который нужно ЗАПОМНИТЬ (id
// уходит в payload), а в поле показать только человекочитаемую метку.
// Не трогаем attachSuggestDropdown — общая инфраструктура развивается
// отдельной функцией, чтобы не тащить в старый код условные ветки под
// новый контракт (объект с id вместо голой строки).
//
// options:
//   searchFn(query) -> Promise<Array<{id, label, sublabel?}>>
//   onSelect(item)   -> вызывается при выборе пункта (item — как из searchFn)
//   onCreateNew(query) -> опционально; если задан, в списке снизу всегда
//                         показывается пункт "+ Создать «query»", клик по
//                         нему вызывает onCreateNew(query) вместо onSelect
//   minChars (default 1) — с скольки символов начинать поиск
//   onItemAction(item) -> опционально; если задан, у КАЖДОГО найденного
//                         пункта (не у "+ Создать...") появляется отдельная
//                         маленькая кнопка-действие сбоку от строки. Клик по
//                         ней вызывает onItemAction(item) ВМЕСТО onSelect —
//                         строка при этом остаётся кликабельной как обычно
//                         (выбор через onSelect), кнопка не мешает основному
//                         клику (своя зона клика, stopPropagation). Задел под
//                         "выбрать" vs "создать нечто на основе этого пункта"
//                         одновременно — см. attachLocationPicker в
//                         incidentLocations.js ("+" = добавить дочернее место
//                         сюда, не выбирая сам пункт).
//   itemActionIcon (default 'icon-add'), itemActionTitle (default 'Добавить')
//                         — иконка/тултип кнопки-действия.
//
// Возвращает {close, destroy} — close() прячет список программно (не
// используется сейчас, задел на будущее); destroy() снимает обработчики.
function attachEntitySuggest(inputEl, options) {
    const {
        searchFn, onSelect, onCreateNew, minChars = 1,
        onItemAction, itemActionIcon = 'icon-add', itemActionTitle = 'Добавить'
    } = options;
    if (!inputEl) return null;

    const wrap = document.createElement('div');
    wrap.className = 'suggest-wrap';
    inputEl.insertAdjacentElement('beforebegin', wrap);
    wrap.appendChild(inputEl);

    const dropdown = document.createElement('div');
    dropdown.className = 'suggest-dropdown hidden';
    wrap.appendChild(dropdown);

    let items = [];
    let activeIndex = -1;
    let currentQuery = '';

    function positionDropdown() {
        const rect = inputEl.getBoundingClientRect();
        dropdown.style.top = rect.bottom + 'px';
        dropdown.style.left = rect.left + 'px';
        dropdown.style.width = rect.width + 'px';
    }

    function renderDropdown() {
        const rows = items.map((item, i) => `
            <div class="suggest-item entity-suggest-item${i === activeIndex ? ' active' : ''}" data-idx="${i}">
                <span class="entity-suggest-label">${escapeHtml(item.label)}</span>
                <span class="entity-suggest-meta">
                    ${item.sublabel ? `<span class="entity-suggest-sublabel">${escapeHtml(item.sublabel)}</span>` : ''}
                    ${onItemAction ? `<button type="button" class="entity-suggest-action" data-action-idx="${i}" title="${escapeHtml(itemActionTitle)}"><span class="icon ${itemActionIcon}"></span></button>` : ''}
                </span>
            </div>
        `).join('');
        const createRow = (onCreateNew && currentQuery.trim())
            ? `<div class="suggest-item entity-suggest-create${activeIndex === items.length ? ' active' : ''}" data-idx="${items.length}">
                   <span class="icon icon-add"></span> Создать «${escapeHtml(currentQuery.trim())}»
               </div>`
            : '';
        dropdown.innerHTML = rows + createRow || '<div class="suggest-empty">Нет совпадений</div>';
        positionDropdown();
        dropdown.classList.remove('hidden');
    }

    function closeDropdown() {
        dropdown.classList.add('hidden');
        activeIndex = -1;
    }

    function pickIndex(idx) {
        if (idx === items.length && onCreateNew && currentQuery.trim()) {
            onCreateNew(currentQuery.trim());
            closeDropdown();
            return;
        }
        const item = items[idx];
        if (!item) return;
        onSelect(item);
        closeDropdown();
    }

    const runSearch = debounce(function () {
        currentQuery = inputEl.value;
        if (currentQuery.trim().length < minChars) {
            items = [];
            closeDropdown();
            return;
        }
        Promise.resolve(searchFn(currentQuery.trim())).then(results => {
            items = results || [];
            activeIndex = -1;
            renderDropdown();
        }).catch(() => {
            items = [];
            closeDropdown();
        });
    }, 200);

    inputEl.addEventListener('focus', runSearch);
    inputEl.addEventListener('input', runSearch);

    function onKeydown(e) {
        if (dropdown.classList.contains('hidden')) return;
        const maxIdx = items.length + (onCreateNew && currentQuery.trim() ? 1 : 0) - 1;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, maxIdx);
            renderDropdown();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            renderDropdown();
        } else if (e.key === 'Enter' && activeIndex >= 0) {
            e.preventDefault();
            pickIndex(activeIndex);
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    }
    inputEl.addEventListener('keydown', onKeydown);

    // mousedown, а не click — опережает blur (тот же приём, что и в
    // attachSuggestDropdown).
    dropdown.addEventListener('mousedown', function (e) {
        const actionEl = e.target.closest('.entity-suggest-action');
        if (actionEl) {
            e.preventDefault();
            e.stopPropagation();
            const item = items[parseInt(actionEl.dataset.actionIdx, 10)];
            if (item && onItemAction) onItemAction(item);
            closeDropdown();
            return;
        }
        const itemEl = e.target.closest('.suggest-item');
        if (!itemEl) return;
        e.preventDefault();
        pickIndex(parseInt(itemEl.dataset.idx, 10));
    });

    function onBlur() { setTimeout(closeDropdown, 150); }
    inputEl.addEventListener('blur', onBlur);

    function onScroll(e) {
        if (!dropdown.classList.contains('hidden') && !dropdown.contains(e.target)) closeDropdown();
    }
    document.addEventListener('scroll', onScroll, true);

    return {
        close: closeDropdown,
        destroy: function () {
            document.removeEventListener('scroll', onScroll, true);
            inputEl.removeEventListener('focus', runSearch);
            inputEl.removeEventListener('input', runSearch);
            inputEl.removeEventListener('keydown', onKeydown);
            inputEl.removeEventListener('blur', onBlur);
            // Возвращаем inputEl туда, где стоял wrap, и убираем саму
            // обёртку — иначе при повторном attachEntitySuggest на том же
            // inputEl (форма открывается заново без пересоздания DOM)
            // обёртки/dropdown-элементы вкладывались бы друг в друга.
            // Старые, невидимые (но живые и подписанные) dropdown-слои
            // оказывались в DOM ПОЗЖЕ новых и визуально перекрывали
            // актуальный список — отсюда баг "клик не закрывает список
            // сразу, надо кликать по несколько раз, пока не доберёшься до
            // рабочего слоя".
            if (wrap.parentNode) {
                wrap.parentNode.insertBefore(inputEl, wrap);
                wrap.remove();
            }
        }
    };
}

// ===== ВЕРТИКАЛЬНЫЙ РЕЗАЙЗЕР БОКОВОЙ ПАНЕЛИ =====
// Общая утилита для трёх похожих боковых панелей с деревом мест:
// locationTree.js (Каталог), equipmentLocationTree.js (Оборудование),
// incidentLocations.js (справочник мест). Раньше ширина панели была
// фиксирована в CSS — теперь пользователь может тянуть границу зажатой
// ЛКМ. Один общий модуль вместо трёх копий drag-логики.
//
// initPanelResizer({
//     panelEl,           // элемент, чью ширину меняем (сама боковая панель)
//     handleEl,          // элемент-разделитель, за который тянут (тонкая
//                         // полоса между панелью и содержимым)
//     storageKey,        // ключ в localStorage для запоминания ширины
//                         // между сессиями (у каждой из трёх панелей свой)
//     minWidth = 180,     // ограничения по ширине в px
//     maxWidth = 600,
//     defaultWidth = 260
// })
//
// Ожидания к разметке: panelEl должен допускать явную ширину через
// inline style.width (т.е. не должен быть жёстко зафиксирован через CSS
// !important или через grid-template-columns без возможности override
// инлайн-стилем на самой panelEl). handleEl обычно — соседний узкий div
// между panelEl и остальным контентом (flex-контейнер).
//
// Возвращает {destroy} — снимает слушатели и восстанавливает исходную
// ширину (на случай, если понадобится демонтировать резайзер динамически,
// например при пересборке панели).
function initPanelResizer(options) {
    const {
        panelEl, handleEl, storageKey,
        minWidth = 180, maxWidth = 600, defaultWidth = 260
    } = options;
    if (!panelEl || !handleEl) return null;

    // Восстанавливаем сохранённую ширину (если есть и валидна), иначе —
    // либо текущая ширина из разметки, либо defaultWidth.
    let savedWidth = null;
    if (storageKey) {
        try {
            const raw = localStorage.getItem(storageKey);
            const parsed = raw ? parseInt(raw, 10) : NaN;
            if (!isNaN(parsed) && parsed >= minWidth && parsed <= maxWidth) savedWidth = parsed;
        } catch (e) { /* localStorage может быть недоступен (приватный режим) — не критично */ }
    }
    const originalWidth = panelEl.style.width;
    panelEl.style.width = (savedWidth !== null ? savedWidth : defaultWidth) + 'px';
    // flex-shrink: 0 обязателен — иначе flex-контейнер сам сожмёт панель
    // при нехватке места, независимо от заданной ширины.
    panelEl.style.flexShrink = '0';

    let dragging = false;
    let startX = 0;
    let startWidth = 0;

    function onMouseDown(e) {
        dragging = true;
        startX = e.clientX;
        startWidth = panelEl.getBoundingClientRect().width;
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
    }

    // mousemove/mouseup — на document, а не на handleEl: иначе drag
    // обрывается, как только курсор на быстром движении выходит за
    // границы узкой полосы-разделителя (тот же принцип, что и в
    // attachEntitySuggest — слушать шире точки первого клика).
    function onMouseMove(e) {
        if (!dragging) return;
        const delta = e.clientX - startX;
        const next = Math.min(maxWidth, Math.max(minWidth, startWidth + delta));
        panelEl.style.width = next + 'px';
    }

    function onMouseUp() {
        if (!dragging) return;
        dragging = false;
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        if (storageKey) {
            try {
                localStorage.setItem(storageKey, Math.round(panelEl.getBoundingClientRect().width));
            } catch (e) { /* см. выше — не критично */ }
        }
    }

    handleEl.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    return {
        destroy: function () {
            handleEl.removeEventListener('mousedown', onMouseDown);
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            panelEl.style.width = originalWidth;
        }
    };
}
