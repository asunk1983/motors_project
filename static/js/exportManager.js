// static/js/exportManager.js — форма создания/редактирования двигателя + экспорт.
// Требует: common.js, engines.js (глобальные переменные состояния)

// ===== ФОТО В ФОРМЕ ДОБАВЛЕНИЯ =====
function renderPhotosPreview() {
    const wrap = document.getElementById('photosPreview');
    if (!wrap) return;
    wrap.innerHTML = '';

    pendingPhotoFiles.forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const box = document.createElement('div');
        box.className = 'photo-thumb is-pending';
        box.innerHTML = `
            <img src="${url}" alt="Новое фото (не загружено)">
            <button type="button" class="photo-thumb-crop" title="Обрезать" onclick="openCropModal('pending', ${idx})">✂️</button>
            <button type="button" class="photo-thumb-remove" title="Убрать из выбора" onclick="removePendingPhoto(${idx})">✕</button>
        `;
        wrap.appendChild(box);
    });
}

function removePendingPhoto(idx) {
    pendingPhotoFiles.splice(idx, 1);
    renderPhotosPreview();
}

function uploadPendingPhotos(engineId) {
    if (pendingPhotoFiles.length === 0) return Promise.resolve();
    const formData = new FormData();
    pendingPhotoFiles.forEach(f => formData.append('photos', f));
    return apiFetch(`/api/engine/${engineId}/photos`, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast('⚠️ Паспорт сохранён, но фото не загрузились: ' + data.error, 'warning');
            }
            pendingPhotoFiles = [];
        })
        .catch(e => showToast('⚠️ Паспорт сохранён, но фото не загрузились: ' + e.message, 'warning'));
}

document.getElementById('f_photos')?.addEventListener('change', function() {
    pendingPhotoFiles = pendingPhotoFiles.concat(Array.from(this.files || []));
    this.value = '';
    renderPhotosPreview();
});

document.getElementById('detailPhotoInput')?.addEventListener('change', function() {
    detailPhotoFiles = detailPhotoFiles.concat(Array.from(this.files || []));
    this.value = '';
    renderDetailPhotoPreview();
});


// ===== ФОРМА =====
function resetForm() {
    document.getElementById('engineForm').reset();
    document.getElementById('modesBody').innerHTML = '';
    document.getElementById('worksBody').innerHTML = '';
    pendingPhotoFiles = [];
    renderPhotosPreview();
    addModeRow();
    addWorkRow();
}

document.getElementById('engineForm').addEventListener('submit', function(e) {
    e.preventDefault();
    saveEngine();
});

function saveEngine() {
    const data = {
        purpose: document.getElementById('f_purpose').value.trim(),
        workshop: document.getElementById('f_workshop').value.trim(),
        location: document.getElementById('f_location').value.trim(),
        engine_type: document.getElementById('f_engine_type').value.trim(),
        manufacturer: document.getElementById('f_manufacturer').value.trim(),
        serial_number: document.getElementById('f_serial_number').value.trim(),
        bearing_front: document.getElementById('f_bearing_front').value.trim(),
        bearing_rear: document.getElementById('f_bearing_rear').value.trim(),
        shaft_diameter: document.getElementById('f_shaft_diameter').value.trim(),
        protection_class: document.getElementById('f_protection_class').value.trim(),
        mounting_type: document.getElementById('f_mounting_type').value.trim(),
        temp_sensor: document.getElementById('f_temp_sensor').value.trim(),
        encoder: document.getElementById('f_encoder').value.trim(),
        cooling: document.getElementById('f_cooling').value.trim(),
        note: document.getElementById('f_note').value.trim(),
        modes: [],
        works: []
    };

    document.querySelectorAll('#modesBody tr').forEach(row => {
        const inputs = row.querySelectorAll('input');
        const freq = inputs[0]?.value?.trim();
        if (freq) {
            data.modes.push({
                frequency: freq,
                power: inputs[1]?.value || '',
                voltage: inputs[2]?.value || '',
                connection_type: inputs[3]?.value || '',
                current: inputs[4]?.value || '',
                rpm: inputs[5]?.value || ''
            });
        }
    });

    document.querySelectorAll('#worksBody tr').forEach(row => {
        const inputs = row.querySelectorAll('input');
        const num = inputs[0]?.value?.trim();
        if (num) {
            data.works.push({
                work_number: num,
                date: inputs[1]?.value || '',
                work_description: inputs[2]?.value || '',
                isolation: inputs[3]?.value || '',
                inspection: inputs[4]?.value || '',
                signature: inputs[5]?.value || ''
            });
        }
    });

    apiFetch('/api/engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            showToast('❌ ' + result.error, 'error');
            return;
        }
        uploadPendingPhotos(result.id).then(() => {
            showToast('✅ ' + result.message, 'success');
            resetForm();
            loadEngines();
            updateStats();
            document.querySelector('[data-tab="catalog"]').click();
        });
    })
    .catch(e => showToast('❌ Ошибка: ' + e.message, 'error'));
}


// ===== СТРОКИ РЕЖИМОВ/РАБОТ =====
function addModeRow(freq = '', power = '', voltage = '', conn = '', current = '', rpm = '', targetId = 'modesBody') {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="number" step="any" value="${escapeHtml(freq)}"></td>
        <td><input type="number" step="any" value="${escapeHtml(power)}"></td>
        <td><input type="number" step="any" value="${escapeHtml(voltage)}"></td>
        <td><input type="text" value="${escapeHtml(conn)}"></td>
        <td><input type="number" step="any" value="${escapeHtml(current)}"></td>
        <td><input type="number" step="any" value="${escapeHtml(rpm)}"></td>
        <td><button type="button" class="btn btn-danger btn-sm" onclick="this.closest('tr').remove()">✕</button></td>
    `;
    document.getElementById(targetId).appendChild(tr);
    attachFieldAutocomplete(tr.children[0].querySelector('input'), 'frequency');
    attachFieldAutocomplete(tr.children[1].querySelector('input'), 'power');
    attachFieldAutocomplete(tr.children[2].querySelector('input'), 'voltage');
    attachFieldAutocomplete(tr.children[3].querySelector('input'), 'connection_type');
    attachFieldAutocomplete(tr.children[4].querySelector('input'), 'current');
    attachFieldAutocomplete(tr.children[5].querySelector('input'), 'rpm');
}

function addWorkRow(num = '', date = '', desc = '', isol = '', insp = '', sign = '', targetId = 'worksBody') {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" value="${escapeHtml(num)}"></td>
        <td><input type="text" value="${escapeHtml(date)}"></td>
        <td><input type="text" value="${escapeHtml(desc)}"></td>
        <td><input type="number" step="any" value="${escapeHtml(isol)}"></td>
        <td><input type="text" value="${escapeHtml(insp)}"></td>
        <td><input type="text" value="${escapeHtml(sign)}"></td>
        <td><button type="button" class="btn btn-danger btn-sm" onclick="this.closest('tr').remove()">✕</button></td>
    `;
    document.getElementById(targetId).appendChild(tr);
}

function collectRows(tbodyId, keys) {
    const rows = [];
    document.querySelectorAll(`#${tbodyId} tr`).forEach(row => {
        const inputs = row.querySelectorAll('input');
        const obj = {};
        keys.forEach((k, i) => { obj[k] = inputs[i]?.value?.trim() || ''; });
        if (Object.values(obj).some(v => v)) rows.push(obj);
    });
    return rows;
}


