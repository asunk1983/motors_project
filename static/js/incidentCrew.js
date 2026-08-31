// static/js/incidentCrew.js — справочник людей (crew), модуль "Инциденты".
// Требует: common.js (attachEntitySuggest, escapeHtml, showToast),
// auth.js (apiFetch).

// ---------------------------------------------------------------------
// Тег-инпут: несколько выбранных людей (Инициаторы / Исполнители)
// ---------------------------------------------------------------------

// attachCrewTagInput(containerEl, {initialItems, onChange})
// containerEl — пустой <div>, внутрь рендерятся чипы уже выбранных людей
// + один текстовый input для добора новых через attachEntitySuggest.
// initialItems — [{id, full_name}], как отдаёт incident_ticket_repo.
// onChange(ids) вызывается при любом изменении набора (добавление,
// удаление чипа, создание нового человека "на лету").
// Возвращает {getIds, setItems}.
function attachCrewTagInput(containerEl, options) {
    const { onChange } = options || {};
    let selected = (options && options.initialItems || []).map(i => ({ id: i.id, label: i.full_name }));

    containerEl.classList.add('crew-tag-input');
    const chipsWrap = document.createElement('div');
    chipsWrap.className = 'crew-tag-chips';
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Добавить человека...';
    containerEl.appendChild(chipsWrap);
    containerEl.appendChild(input);

    function renderChips() {
        chipsWrap.innerHTML = selected.map(item => `
            <span class="crew-tag-chip" data-id="${item.id}">
                ${escapeHtml(item.label)}
                <button type="button" class="crew-tag-remove" data-id="${item.id}" title="Убрать">&times;</button>
            </span>
        `).join('');
        chipsWrap.querySelectorAll('.crew-tag-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id, 10);
                selected = selected.filter(i => i.id !== id);
                renderChips();
                if (onChange) onChange(selected.map(i => i.id));
            });
        });
    }
    renderChips();

    attachEntitySuggest(input, {
        minChars: 1,
        searchFn: (query) => apiFetch(`/api/crew/search?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(rows => rows
                .filter(row => !selected.some(s => s.id === row.id))
                .map(row => ({ id: row.id, label: row.full_name, sublabel: row.position || '' }))),
        onSelect: (item) => {
            selected.push({ id: item.id, label: item.label });
            input.value = '';
            renderChips();
            if (onChange) onChange(selected.map(i => i.id));
        },
        onCreateNew: (query) => {
            apiFetch('/api/crew', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: query })
            })
                .then(r => r.json())
                .then(result => {
                    if (result.error) {
                        showToast(result.error, 'error', 'icon-cancel');
                        return;
                    }
                    selected.push({ id: result.id, label: query });
                    input.value = '';
                    renderChips();
                    showToast('Человек добавлен в справочник', 'success', 'icon-check-circle');
                    if (onChange) onChange(selected.map(i => i.id));
                })
                .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
        }
    });

    return {
        getIds: () => selected.map(i => i.id),
        setItems: (items) => {
            selected = (items || []).map(i => ({ id: i.id, label: i.full_name }));
            renderChips();
        }
    };
}

// ---------------------------------------------------------------------
// Справочник людей (подвкладка "Справочники" на вкладке "Инциденты")
// ---------------------------------------------------------------------

let _crewDictItems = [];

function loadCrewDictionary() {
    apiFetch('/api/crew')
        .then(r => r.json())
        .then(rows => {
            _crewDictItems = Array.isArray(rows) ? rows : [];
            renderCrewDictionary();
        })
        .catch(() => {
            const el = document.getElementById('crewDictionaryList');
            if (el) el.innerHTML = '<div class="no-data">Не удалось загрузить справочник людей</div>';
        });
}

function renderCrewDictionary() {
    const el = document.getElementById('crewDictionaryList');
    if (!el) return;
    if (_crewDictItems.length === 0) {
        el.innerHTML = '<div class="no-data">Справочник пуст</div>';
        return;
    }
    el.innerHTML = _crewDictItems.map(item => `
        <div class="knowledge-dict-row">
            <div>
                <div class="knowledge-dict-code">${escapeHtml(item.position || '—')}${item.workshop ? ' · ' + escapeHtml(item.workshop) : ''}</div>
                ${escapeHtml(item.full_name)}
            </div>
            <div style="display:flex;gap:4px">
                <button class="btn btn-secondary btn-sm" onclick="editCrewMember(${item.id})" title="Изменить"><span class="icon icon-edit"></span></button>
                <button class="btn btn-danger btn-sm" onclick="deleteCrewMember(${item.id})" title="Удалить"><span class="icon icon-delete"></span></button>
            </div>
        </div>
    `).join('');
}

function createCrewMember() {
    const nameEl = document.getElementById('newCrewName');
    const posEl = document.getElementById('newCrewPosition');
    const workshopEl = document.getElementById('newCrewWorkshop');
    const full_name = nameEl.value.trim();
    if (!full_name) {
        showToast('Укажите ФИО', 'warning', 'icon-warning');
        return;
    }
    apiFetch('/api/crew', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name, position: posEl.value.trim(), workshop: workshopEl.value.trim() })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            nameEl.value = ''; posEl.value = ''; workshopEl.value = '';
            showToast('Человек добавлен', 'success', 'icon-check-circle');
            loadCrewDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

// ---------------------------------------------------------------------
// Модалка редактирования человека (ФИО + должность + цех одной формой)
// ---------------------------------------------------------------------

// Модалка создаётся один раз и переиспользуется (как #detailModal и
// прочие модалки проекта — см. .modal/.modal-content в style.css).
function _ensureEditCrewModal() {
    let modal = document.getElementById('editCrewModal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'editCrewModal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width:480px">
            <div class="modal-header">
                <h2>Изменить человека</h2>
                <button type="button" class="modal-close" onclick="_closeEditCrewModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="editCrewId">
                <div class="form-group">
                    <label for="editCrewName">ФИО</label>
                    <input type="text" id="editCrewName">
                </div>
                <div class="form-group">
                    <label for="editCrewPosition">Должность</label>
                    <input type="text" id="editCrewPosition">
                </div>
                <div class="form-group">
                    <label for="editCrewWorkshop">Цех</label>
                    <input type="text" id="editCrewWorkshop">
                </div>
                <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:var(--space-4)">
                    <button type="button" class="btn btn-secondary btn-sm" onclick="_closeEditCrewModal()">Отмена</button>
                    <button type="button" class="btn btn-primary btn-sm" onclick="_saveEditCrewMember()">Сохранить</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) _closeEditCrewModal();
    });
    return modal;
}

function _closeEditCrewModal() {
    const modal = document.getElementById('editCrewModal');
    if (modal) modal.classList.remove('active');
}

function editCrewMember(id) {
    const item = _crewDictItems.find(i => i.id === id);
    if (!item) return;

    const modal = _ensureEditCrewModal();
    document.getElementById('editCrewId').value = item.id;
    document.getElementById('editCrewName').value = item.full_name || '';
    document.getElementById('editCrewPosition').value = item.position || '';
    document.getElementById('editCrewWorkshop').value = item.workshop || '';
    modal.classList.add('active');
}

function _saveEditCrewMember() {
    const id = document.getElementById('editCrewId').value;
    const full_name = document.getElementById('editCrewName').value.trim();
    const position = document.getElementById('editCrewPosition').value.trim();
    const workshop = document.getElementById('editCrewWorkshop').value.trim();

    if (!full_name) {
        showToast('Укажите ФИО', 'warning', 'icon-warning');
        return;
    }

    apiFetch(`/api/crew/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name, position, workshop })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            _closeEditCrewModal();
            showToast('Сохранено', 'success', 'icon-check-circle');
            loadCrewDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}

function deleteCrewMember(id) {
    if (!confirm('Удалить этого человека? Если он указан хотя бы в одной заявке, сервер откажет.')) return;
    apiFetch(`/api/crew/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
            showToast('Удалено', 'success', 'icon-check-circle');
            loadCrewDictionary();
        })
        .catch(e => showToast('Ошибка: ' + e.message, 'error', 'icon-cancel'));
}
