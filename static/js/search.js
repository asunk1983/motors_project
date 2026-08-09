// static/js/search.js — РАСШИРЕННЫЙ ПОИСК С ДИНАМИЧЕСКИМИ ПОЛЯМИ

// ===== ДОСТУПНЫЕ ПОЛЯ ДЛЯ ПОИСКА =====
const SEARCH_FIELDS = [
    { value: 'id', label: 'ID', type: 'number' },
    { value: 'location', label: 'Место установки', type: 'text' },
    { value: 'engine_type', label: 'Тип двигателя', type: 'text' },
    { value: 'serial_number', label: 'Заводской номер', type: 'text' },
    { value: 'manufacturer', label: 'Производитель', type: 'text' },
    { value: 'purpose', label: 'Назначение', type: 'text' },
    { value: 'workshop', label: 'Цех', type: 'number' },
    { value: 'bearing_front', label: 'Подшипник передний', type: 'text' },
    { value: 'bearing_rear', label: 'Подшипник задний', type: 'text' },
    { value: 'shaft_diameter', label: 'Диаметр вала (мм)', type: 'number' },
    { value: 'protection_class', label: 'Степень защиты', type: 'text' },
    { value: 'mounting_type', label: 'Тип крепления', type: 'text' },
    { value: 'temp_sensor', label: 'Датчик температуры', type: 'text' },
    { value: 'encoder', label: 'Энкодер', type: 'text' },
    { value: 'cooling', label: 'Охлаждение', type: 'text' },
    { value: 'note', label: 'Примечание', type: 'text' },
    { value: 'filename', label: 'Имя файла (импорт)', type: 'text' },
    { value: 'photo_count', label: 'Количество фото', type: 'number' },
    // Поля режимов работы (таблица operating_modes) — подбор двигателя
    // по параметрам режима: мощность, напряжение, обороты и т.д.
    // Если задать несколько таких условий сразу, backend проверяет их
    // в рамках ОДНОГО режима работы, а не вразнобой по всем режимам двигателя.
    { value: 'power', label: '⚡ Режим: мощность (кВт)', type: 'number' },
    { value: 'voltage', label: '⚡ Режим: напряжение (В)', type: 'number' },
    { value: 'frequency', label: '⚡ Режим: частота (Гц)', type: 'number' },
    { value: 'rpm', label: '⚡ Режим: обороты (об/мин)', type: 'number' },
    { value: 'current', label: '⚡ Режим: ток (А)', type: 'number' },
    { value: 'connection_type', label: '⚡ Режим: тип подключения', type: 'text' },
];

// ===== ОПЕРАТОРЫ ПО ТИПУ ПОЛЯ =====
// Числовые операторы (больше/меньше/между) для текстовых полей никогда не
// дают осмысленного результата: backend делает CAST(col AS REAL) — для
// нечислового значения (например, connection_type) это тихо даёт 0/NULL
// и пустую выдачу без единого объяснения пользователю, что оператор был
// несовместим с полем. Поэтому список операторов зависит от f.type.
const OPERATORS_TEXT = [
    { value: 'contains', label: 'содержит' },
    { value: 'equals', label: 'равно' },
    { value: 'starts', label: 'начинается с' },
    { value: 'ends', label: 'заканчивается на' }
];
const OPERATORS_NUMBER = OPERATORS_TEXT.concat([
    { value: 'gt', label: 'больше' },
    { value: 'lt', label: 'меньше' },
    { value: 'between', label: 'между' }
]);

function _searchFieldType(fieldValue) {
    const f = SEARCH_FIELDS.find(f => f.value === fieldValue);
    return f ? f.type : 'text';
}

// ===== КОЛОНКИ ТАБЛИЦЫ РЕЗУЛЬТАТОВ =====
// Поля режима работы возвращаются backend'ом (см. app.py:
// search_engines_advanced) под алиасами mode_* — эти шесть имён общие
// и для проверки "это поле режима?", и для чтения значения из строки
// результата.
const MODE_FIELD_NAMES = ['power', 'voltage', 'frequency', 'rpm', 'current', 'connection_type'];

// Базовый набор колонок, который показывался всегда (раньше — жёстко,
// первыми). Теперь это просто "всё остальное", что добавляется ПОСЛЕ
// колонок, по которым реально искали (см. executeSearch ниже).
const DEFAULT_RESULT_FIELDS = ['id', 'location', 'engine_type', 'serial_number', 'manufacturer', 'purpose'];

function _resultColumnLabel(field) {
    if (field === 'id') return 'ID';
    // Подписи для остальных полей уже есть в SEARCH_FIELDS (включая
    // ⚡-поля режима) — единый источник вместо второго списка меток.
    const f = SEARCH_FIELDS.find(f => f.value === field);
    return f ? f.label : field;
}

function _resultColumnValue(row, field) {
    // Поля режима отдаются backend'ом под алиасом mode_<field>, обычные
    // поля двигателя — как есть.
    return MODE_FIELD_NAMES.includes(field) ? row['mode_' + field] : row[field];
}

// ===== СОСТОЯНИЕ =====
let searchFieldIndex = 0;

// Резервная копия исходного списка allEngines (из engines.js), чтобы
// восстанавливать её при очистке поиска. allEngines — глобальная переменная
// из engines.js, которой пользуются пагинация и навигация по карточкам.
// Расширенный поиск должен перенаправлять эти механизмы на найденные
// результаты, а не на полный список из 97 двигателей.
let originalAllEngines = null;

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    addSearchRow();
    
    document.getElementById('addSearchBtn')?.addEventListener('click', addSearchRow);
    document.getElementById('clearSearchBtn')?.addEventListener('click', clearAllSearch);
    document.getElementById('searchBtn')?.addEventListener('click', executeSearch);
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.target.closest('.search-container')) {
            executeSearch();
        }
    });
});

// ===== ДОБАВЛЕНИЕ СТРОКИ ПОИСКА =====
function addSearchRow() {
    const container = document.getElementById('searchConditions');
    if (!container) return;
    
    const index = searchFieldIndex++;
    
    const row = document.createElement('div');
    row.className = 'search-row';
    row.dataset.index = index;
    
    // Поле выбора
    const fieldSelect = document.createElement('select');
    fieldSelect.className = 'search-field-select';
    
    SEARCH_FIELDS.forEach(f => {
        const option = document.createElement('option');
        option.value = f.value;
        option.textContent = f.label;
        fieldSelect.appendChild(option);
    });
    
    // Оператор сравнения — список пересобирается под тип текущего поля
    // (см. _searchFieldType/OPERATORS_TEXT/OPERATORS_NUMBER выше).
    const operatorSelect = document.createElement('select');
    operatorSelect.className = 'search-operator-select';

    function rebuildOperators(fieldType, preserveValue) {
        const list = fieldType === 'number' ? OPERATORS_NUMBER : OPERATORS_TEXT;
        const prev = preserveValue !== undefined ? preserveValue : operatorSelect.value;
        operatorSelect.innerHTML = '';
        list.forEach(op => {
            const option = document.createElement('option');
            option.value = op.value;
            option.textContent = op.label;
            operatorSelect.appendChild(option);
        });
        // Сохраняем прежний оператор, если он остался допустим для нового
        // типа поля (например, "содержит" валиден и для text, и для
        // number) — иначе тихо откатываемся на первый оператор списка.
        if (list.some(op => op.value === prev)) {
            operatorSelect.value = prev;
        }
        valueInput2.classList.toggle('active', operatorSelect.value === 'between');
    }

    // Поле ввода значения — type тоже зависит от типа поля (раньше
    // f.type в SEARCH_FIELDS объявлялся, но нигде не читался, и оба поля
    // всегда были обычным <input type="text">, даже для мощности/оборотов).
    const valueInput = document.createElement('input');
    valueInput.className = 'search-value-input';
    valueInput.placeholder = 'Введите значение...';

    // Второе значение для "между"
    const valueInput2 = document.createElement('input');
    valueInput2.className = 'search-value-input-2';
    valueInput2.placeholder = 'и...';

    function applyFieldType() {
        const fieldType = _searchFieldType(fieldSelect.value);
        valueInput.type = fieldType === 'number' ? 'number' : 'text';
        valueInput2.type = fieldType === 'number' ? 'number' : 'text';
        if (fieldType === 'number') {
            valueInput.step = 'any';
            valueInput2.step = 'any';
        } else {
            valueInput.removeAttribute('step');
            valueInput2.removeAttribute('step');
        }
        rebuildOperators(fieldType);
    }

    fieldSelect.addEventListener('change', applyFieldType);
    applyFieldType();
    
    // Кнопка удаления
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-danger btn-sm';
    removeBtn.textContent = '✕';
    removeBtn.onclick = function() {
        if (document.querySelectorAll('.search-row').length <= 1) {
            showToast('⚠️ Должна быть хотя бы одна строка поиска', 'warning');
            return;
        }
        row.remove();
    };
    
    // Показываем второе поле при выборе "между" — видимость через класс,
    // а не style.display (раньше это же поле ещё и получало
    // 'display:none' из inline cssText при создании — двойное дублирование).
    operatorSelect.addEventListener('change', function() {
        valueInput2.classList.toggle('active', this.value === 'between');
    });
    
    // Собираем строку
    row.appendChild(fieldSelect);
    row.appendChild(operatorSelect);
    row.appendChild(valueInput);
    row.appendChild(valueInput2);
    row.appendChild(removeBtn);
    
    container.appendChild(row);
    
    // Подсказки — общий dropdown из engines.js (та же реализация, что и
    // в карточке двигателя). Поле поиска у строки можно менять
    // (fieldSelect), поэтому имя поля передаём функцией, а не строкой —
    // dropdown всегда спросит актуально выбранное поле.
    attachSuggestDropdown(valueInput, () => fieldSelect.value);
}

// ===== ОЧИСТКА ВСЕХ УСЛОВИЙ =====
function clearAllSearch() {
    const container = document.getElementById('searchConditions');
    if (!container) return;
    
    container.innerHTML = '';
    searchFieldIndex = 0;
    addSearchRow();
    document.getElementById('searchResults').innerHTML = '<div class="no-data">Введите параметры поиска</div>';
    
    // Восстанавливаем исходный список allEngines, если поиск уже
    // перезаписал его результатами. Без этого после очистки пагинация
    // и навигация по карточкам продолжали бы работать с последними
    // результатами поиска вместо полного каталога.
    if (originalAllEngines !== null) {
        allEngines = originalAllEngines;
        originalAllEngines = null;
    }
    currentPage = 1;
}

// ===== ВЫПОЛНЕНИЕ ПОИСКА =====
function executeSearch() {
    const rows = document.querySelectorAll('.search-row');
    const conditions = [];
    
    rows.forEach(row => {
        const field = row.querySelector('.search-field-select')?.value;
        const operator = row.querySelector('.search-operator-select')?.value;
        const value = row.querySelector('.search-value-input')?.value.trim();
        const value2 = row.querySelector('.search-value-input-2')?.value.trim();
        
        if (!field || !value) return;
        
        conditions.push({
            field: field,
            operator: operator || 'contains',
            value: value,
            value2: value2 || null
        });
    });
    
    if (conditions.length === 0) {
        showToast('⚠️ Введите хотя бы одно условие поиска', 'warning');
        return;
    }
    
    // Формируем JSON и отправляем POST запросом
    apiFetch('/api/engines/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ conditions: conditions })
    })
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('searchResults');
            if (data.error) {
                container.innerHTML = `<div class="no-data">${data.error}</div>`;
                return;
            }
            if (!data || data.length === 0) {
                container.innerHTML = '<div class="no-data">Ничего не найдено</div>';
                return;
            }
            
            // Перезаписываем allEngines результатами поиска, чтобы
            // пагинация, showDetail() и навигация по карточкам (кнопки
            // ◀/▶ в детальной карточке) работали именно с найденными
            // двигателями, а не с полным списком из 97 записей.
            // Исходный список сохраняем в originalAllEngines для
            // восстановления при очистке поиска.
            if (originalAllEngines === null) {
                originalAllEngines = allEngines;
            }
            allEngines = data;
            currentPage = 1;

            // Рендерим результаты в контейнере #searchResults (на вкладке
            // "Поиск"), не переключая пользователя на вкладку "catalog".
            // Колонки таблицы результатов: сначала поля, по которым реально
            // искали (в порядке добавления условий, без повторов — если
            // искали и по 'location', и по 'power', то Location и ⚡Мощность
            // идут первыми), затем — остальные базовые поля из
            // DEFAULT_RESULT_FIELDS, которых ещё нет среди уже добавленных.
            const searchedFields = [];
            conditions.forEach(c => {
                if (!searchedFields.includes(c.field)) searchedFields.push(c.field);
            });
            const restFields = DEFAULT_RESULT_FIELDS.filter(f => !searchedFields.includes(f));
            const columns = searchedFields.concat(restFields);

            let html = `<div class="table-wrapper"><table class="data-table"><thead><tr>
                ${columns.map(f => `<th>${escapeHtml(_resultColumnLabel(f))}</th>`).join('')}
            </tr></thead><tbody>`;

            data.forEach(e => {
                // escapeHtml определена в engines.js (грузится раньше) и
                // используется здесь же — та же защита от XSS, что и
                // в основной таблице каталога.
                const cells = columns.map(f => {
                    const value = _resultColumnValue(e, f);
                    if (f === 'id') return `<td><span class="badge-id">${e.id}</span></td>`;
                    if (f === 'location') return `<td><strong>${escapeHtml(value) || '—'}</strong></td>`;
                    return `<td>${escapeHtml(value) || '—'}</td>`;
                }).join('');
                html += `<tr class="clickable-row" onclick="showDetail(${e.id})">${cells}</tr>`;
            });

            html += `</tbody></table></div>
                     <div class="search-result-count">
                        Найдено: ${data.length} записей
                     </div>`;

            container.innerHTML = html;
            showToast(`🔍 Найдено ${data.length} записей`, 'success');
        })
        .catch(e => {
            document.getElementById('searchResults').innerHTML = `<div class="no-data">Ошибка: ${e.message}</div>`;
        });
}
