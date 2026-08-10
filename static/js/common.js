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