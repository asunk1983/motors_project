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

function editCrewMember(id) {
    const item = _crewDictItems.find(i => i.id === id);
    if (!item) return;
    const full_name = prompt('ФИО:', item.full_name);
    if (full_name === null) return;
    const position = prompt('Должность:', item.position || '');
    if (position === null) return;
    const workshop = prompt('Цех:', item.workshop || '');
    if (workshop === null) return;

    apiFetch(`/api/crew/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: full_name.trim(), position: position.trim(), workshop: workshop.trim() })
    })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                showToast(result.error, 'error', 'icon-cancel');
                return;
            }
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
