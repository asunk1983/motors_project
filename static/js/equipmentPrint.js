// static/js/equipmentPrint.js — печатная версия карточки оборудования.
// Страница самостоятельная (НЕ подключает equipment.js). В отличие от
// incidentPrint.js (у заявок фото приезжают ВНУТРИ ответа GET
// /api/incident-tickets/<id>), у оборудования фото — отдельный запрос
// (GET /api/equipment/<id>/photos, тот же паттерн, что и print.js для
// двигателей: engine + photos раздельно). Плюс третий/четвёртый запрос —
// эффективные атрибуты типа (для labels/units) и breadcrumb места, оба
// зависят от данных первого ответа, поэтому идут вторым шагом.
// Требует: common.js (escapeHtml), auth.js (apiFetch, authPhotoUrl,
// parseJsonResponse).

function getEquipmentIdFromUrl() {
    // /print/equipment/<id> — путь, а не query string (см. роут
    // print_equipment_page в routes/pages.py, зеркало print_engine_page).
    const parts = window.location.pathname.split('/').filter(Boolean);
    const id = parseInt(parts[parts.length - 1], 10);
    return isNaN(id) ? null : id;
}

function renderEquipmentField(label, value) {
    const safeVal = (value !== null && value !== undefined && value !== '') ? escapeHtml(value) : '—';
    return `<div class="print-field"><span class="print-field-label">${escapeHtml(label)}</span><span class="print-field-value">${safeVal}</span></div>`;
}

function renderEquipmentCharacteristics(item, effectiveAttrs, locationText) {
    const criticalityText = item.criticality ? '●'.repeat(item.criticality) + '○'.repeat(5 - item.criticality) : '';

    // Базовые поля — ВСЕГДА (пустые как "—"), тот же принцип, что и у
    // двигателей (print.js::renderCharacteristics). Атрибуты типа ниже —
    // только заполненные (тот же компромисс ради компактности, что и в
    // export_equipment_to_xlsx — печать и экспорт из одних данных, не
    // должны расходиться в этом решении).
    let fields = [
        ['Тип оборудования', item.equipment_type_name],
        ['Артикул', item.article],
        ['Производитель', item.manufacturer],
        ['Серийный номер', item.serial_number],
        ['Место', locationText],
        ['Версия прошивки', item.firmware_version],
        ['Критичность', criticalityText],
    ].map(([label, value]) => renderEquipmentField(label, value)).join('');

    const specs = item.specs || {};
    (effectiveAttrs || []).forEach(a => {
        const val = specs[a.key];
        if (val === undefined || val === null || val === '' || val === false) return;
        const label = a.label + (a.unit ? ` (${a.unit})` : '');
        fields += renderEquipmentField(label, val);
    });

    return fields;
}

function renderEquipmentPhotos(photos) {
    if (!photos || photos.length === 0) {
        return '<div class="no-data">Нет фото</div>';
    }
    const imgs = photos.map(p =>
        `<img class="print-photo" src="${authPhotoUrl(p.path)}" alt="Фото оборудования">`
    ).join('');
    return `<div class="print-photos">${imgs}</div>`;
}

function renderEquipmentPage(item, photos, effectiveAttrs, locationText) {
    return `
<div class="print-page">
    <div class="print-header">
        <div>
            <div class="print-title">${escapeHtml(item.name) || 'Оборудование'}</div>
            <div class="print-subtitle">${escapeHtml(item.equipment_type_name || '')}</div>
        </div>
        <div class="print-subtitle">ID: ${item.id}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Характеристики</div>
        <div class="print-grid">${renderEquipmentCharacteristics(item, effectiveAttrs, locationText)}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Примечание</div>
        <div class="print-field-value">${item.note ? escapeHtml(item.note) : '—'}</div>
    </div>

    <div class="print-section">
        <div class="print-section-title">Фото (${photos ? photos.length : 0})</div>
        ${renderEquipmentPhotos(photos)}
    </div>
</div>`;
}

function waitForEquipmentImages(timeoutMs) {
    if (!timeoutMs) timeoutMs = 5000;
    return new Promise(function (resolve) {
        const imgs = document.querySelectorAll('.print-photo');
        if (!imgs.length) { resolve(); return; }
        let loaded = 0;
        const onLoaded = function () {
            loaded++;
            if (loaded >= imgs.length) resolve();
        };
        const timer = setTimeout(resolve, timeoutMs);
        imgs.forEach(function (img) {
            if (img.complete) { onLoaded(); }
            else {
                img.addEventListener('load', onLoaded);
                img.addEventListener('error', onLoaded);
            }
        });
    });
}

function loadAndRenderEquipment() {
    const root = document.getElementById('printRoot');
    if (!root) return;

    const equipmentId = getEquipmentIdFromUrl();
    if (!equipmentId) {
        root.innerHTML = '<div class="no-data"><span class="icon icon-cancel"></span> Оборудование не найдено в URL</div>';
        return;
    }

    root.innerHTML = '<div class="loading">Загрузка данных...</div>';

    apiFetch(`/api/equipment/${equipmentId}`)
        .then(parseJsonResponse)
        .then(item => {
            if (item.error) {
                root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> ${escapeHtml(item.error)}</div>`;
                return;
            }

            const photosPromise = apiFetch(`/api/equipment/${equipmentId}/photos`).then(parseJsonResponse).catch(() => []);
            const attrsPromise = apiFetch(`/api/equipment-types/${item.equipment_type_id}/attributes`).then(parseJsonResponse).catch(() => []);
            const locationPromise = item.location_node_id
                ? apiFetch(`/api/locations/${item.location_node_id}/breadcrumb`).then(parseJsonResponse).then(bc => Array.isArray(bc) ? bc.map(n => n.name).join(' → ') : '—').catch(() => item.location_name || '—')
                : Promise.resolve([item.workshop, item.location].filter(Boolean).join(' / ') || '—');

            return Promise.all([photosPromise, attrsPromise, locationPromise]).then(([photos, effectiveAttrs, locationText]) => {
                root.innerHTML = renderEquipmentPage(item, Array.isArray(photos) ? photos : [], Array.isArray(effectiveAttrs) ? effectiveAttrs : [], locationText);
                waitForEquipmentImages().then(() => {
                    const printBtn = document.getElementById('printBtn');
                    if (printBtn) {
                        printBtn.onclick = function () { window.print(); };
                    }
                });
            });
        })
        .catch(e => {
            root.innerHTML = `<div class="no-data"><span class="icon icon-cancel"></span> Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
        });
}

document.addEventListener('DOMContentLoaded', loadAndRenderEquipment);
