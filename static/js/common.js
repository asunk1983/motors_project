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
//
// Возвращает {close, destroy} — close() прячет список программно (не
// используется сейчас, задел на будущее); destroy() снимает обработчики.
function attachEntitySuggest(inputEl, options) {
    const { searchFn, onSelect, onCreateNew, minChars = 1 } = options;
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
                ${item.sublabel ? `<span class="entity-suggest-sublabel">${escapeHtml(item.sublabel)}</span>` : ''}
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

    inputEl.addEventListener('keydown', function (e) {
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
    });

    // mousedown, а не click — опережает blur (тот же приём, что и в
    // attachSuggestDropdown).
    dropdown.addEventListener('mousedown', function (e) {
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
            dropdown.remove();
        }
    };
}
