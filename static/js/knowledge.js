// static/js/knowledge.js — вкладка "База знаний" (только role='superadmin').
// Использует apiFetch/parseJsonResponse/showToast/escapeHtml/debounce из
// auth.js/common.js. Вызывается лениво из catalog.js::switchTab при
// переключении на вкладку (см. loadKnowledgeTab ниже), а не на загрузке
// страницы — как settings/info/import.

let knowledgeFailureModesCache = [];
let knowledgeFailureCausesCache = [];

// ---------------------------------------------------------------------
// Вкладка / подвкладки
// ---------------------------------------------------------------------

async function loadKnowledgeTab() {
    await loadKnowledgeDictionaries();
    await loadKnowledgeArticles();
}

function switchKnowledgeSubtab(name) {
    document.querySelectorAll('#tab-knowledge .info-subtab-content').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('knowledgeSubtab-' + name);
    if (target) target.classList.add('active');

    const articlesBtn = document.getElementById('knowledgeSubtabArticlesBtn');
    const dictBtn = document.getElementById('knowledgeSubtabDictionariesBtn');
    if (articlesBtn) articlesBtn.className = 'btn btn-sm ' + (name === 'articles' ? 'btn-primary' : 'btn-secondary');
    if (dictBtn) dictBtn.className = 'btn btn-sm ' + (name === 'dictionaries' ? 'btn-primary' : 'btn-secondary');
}

// ---------------------------------------------------------------------
// Справочники (failure_mode / failure_cause)
// ---------------------------------------------------------------------

async function loadKnowledgeDictionaries() {
    try {
        const [modesResp, causesResp] = await Promise.all([
            apiFetch('/api/knowledge/failure-modes'),
            apiFetch('/api/knowledge/failure-causes'),
        ]);
        const modes = await parseJsonResponse(modesResp);
        const causes = await parseJsonResponse(causesResp);
        knowledgeFailureModesCache = Array.isArray(modes) ? modes : [];
        knowledgeFailureCausesCache = Array.isArray(causes) ? causes : [];
        renderKnowledgeDictList('failureModesList', knowledgeFailureModesCache, deleteFailureMode);
        renderKnowledgeDictList('failureCausesList', knowledgeFailureCausesCache, deleteFailureCause);
    } catch (e) {
        showToast(e && e.message ? e.message : 'Не удалось загрузить справочники', 'error');
    }
}

function renderKnowledgeDictList(containerId, items, onDelete) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!items.length) {
        el.innerHTML = '<div class="no-data">Справочник пуст</div>';
        return;
    }
    el.innerHTML = items.map(item => `
        <div class="knowledge-dict-row">
            <div>
                <div class="knowledge-dict-code">${escapeHtml(item.code)}</div>
                ${escapeHtml(item.name)}
            </div>
            <button class="btn btn-danger btn-sm" onclick="${onDelete.name}(${item.id})" title="Удалить">
                <span class="icon icon-delete"></span>
            </button>
        </div>
    `).join('');
}

async function createFailureMode() {
    const codeEl = document.getElementById('newFailureModeCode');
    const nameEl = document.getElementById('newFailureModeName');
    const code = codeEl.value.trim().toUpperCase();
    const name = nameEl.value.trim();
    if (!code || !name) {
        showToast('Укажите код и название', 'error');
        return;
    }
    try {
        const resp = await apiFetch('/api/knowledge/failure-modes', {
            method: 'POST',
            body: JSON.stringify({ code, name }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания', 'error');
            return;
        }
        codeEl.value = '';
        nameEl.value = '';
        showToast('Режим отказа добавлен', 'success');
        await loadKnowledgeDictionaries();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function createFailureCause() {
    const codeEl = document.getElementById('newFailureCauseCode');
    const nameEl = document.getElementById('newFailureCauseName');
    const code = codeEl.value.trim().toUpperCase();
    const name = nameEl.value.trim();
    if (!code || !name) {
        showToast('Укажите код и название', 'error');
        return;
    }
    try {
        const resp = await apiFetch('/api/knowledge/failure-causes', {
            method: 'POST',
            body: JSON.stringify({ code, name }),
        });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка создания', 'error');
            return;
        }
        codeEl.value = '';
        nameEl.value = '';
        showToast('Причина добавлена', 'success');
        await loadKnowledgeDictionaries();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteFailureMode(id) {
    if (!confirm('Удалить режим отказа? Если он используется в статьях, сервер откажет.')) return;
    try {
        const resp = await apiFetch(`/api/knowledge/failure-modes/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Режим отказа удалён', 'success');
        await loadKnowledgeDictionaries();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteFailureCause(id) {
    if (!confirm('Удалить причину? Если она используется в статьях, сервер откажет.')) return;
    try {
        const resp = await apiFetch(`/api/knowledge/failure-causes/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Причина удалена', 'success');
        await loadKnowledgeDictionaries();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// ---------------------------------------------------------------------
// Статьи
// ---------------------------------------------------------------------

async function loadKnowledgeArticles() {
    const body = document.getElementById('knowledgeArticlesBody');
    if (!body) return;
    const searchInput = document.getElementById('knowledgeSearchInput');
    const search = searchInput ? searchInput.value.trim() : '';

    body.innerHTML = '<tr><td colspan="5" class="no-data">Загрузка...</td></tr>';
    try {
        const url = '/api/knowledge/articles' + (search ? '?search=' + encodeURIComponent(search) : '');
        const resp = await apiFetch(url);
        const articles = await parseJsonResponse(resp);
        if (!resp.ok) {
            body.innerHTML = `<tr><td colspan="5" class="no-data">${escapeHtml(articles.error || 'Ошибка')}</td></tr>`;
            return;
        }
        if (!Array.isArray(articles) || !articles.length) {
            body.innerHTML = `<tr><td colspan="5" class="no-data">${search ? 'Ничего не найдено' : 'Статей пока нет'}</td></tr>`;
            return;
        }
        body.innerHTML = articles.map(a => {
            const symptomShort = (a.symptom || '').length > 90
                ? escapeHtml(a.symptom.slice(0, 90)) + '…'
                : escapeHtml(a.symptom || '');
            const updated = (a.updated_at || '').slice(0, 16).replace('T', ' ');
            return `
                <tr>
                    <td>${escapeHtml(a.title)}</td>
                    <td>${symptomShort}</td>
                    <td>${escapeHtml(a.failure_mode_name || '—')}</td>
                    <td>${escapeHtml(updated)}</td>
                    <td class="col-actions">
                        <button class="btn btn-secondary btn-sm" onclick="openKnowledgeArticleModal(${a.id})" title="Редактировать">
                            <span class="icon icon-edit"></span>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteKnowledgeArticle(${a.id})" title="Удалить">
                            <span class="icon icon-delete"></span>
                        </button>
                    </td>
                </tr>`;
        }).join('');
    } catch (e) {
        body.innerHTML = `<tr><td colspan="5" class="no-data">${escapeHtml(e && e.message ? e.message : 'Сетевая ошибка')}</td></tr>`;
    }
}

function clearKnowledgeArticleForm() {
    document.getElementById('knowledgeArticleId').value = '';
    document.getElementById('knowledgeArticleTitle').value = '';
    document.getElementById('knowledgeArticleSymptom').value = '';
    document.getElementById('knowledgeArticleDiagnostics').value = '';
    document.getElementById('knowledgeArticleAction').value = '';
    document.getElementById('knowledgeArticleReference').value = '';
}

function renderKnowledgeArticleFormOptions(selectedFailureModeId, selectedCauseIds) {
    const modeSelect = document.getElementById('knowledgeArticleFailureMode');
    modeSelect.innerHTML = '<option value="">— не выбран —</option>' +
        knowledgeFailureModesCache.map(m =>
            `<option value="${m.id}">${escapeHtml(m.name)}</option>`
        ).join('');
    modeSelect.value = selectedFailureModeId || '';

    const causesEl = document.getElementById('knowledgeArticleCauses');
    if (!knowledgeFailureCausesCache.length) {
        causesEl.innerHTML = '<div class="no-data">Справочник причин пуст — добавьте на вкладке «Справочники»</div>';
        return;
    }
    const selected = new Set(selectedCauseIds || []);
    causesEl.innerHTML = knowledgeFailureCausesCache.map(c => `
        <label>
            <input type="checkbox" value="${c.id}" class="knowledge-cause-checkbox" ${selected.has(c.id) ? 'checked' : ''}>
            ${escapeHtml(c.name)}
        </label>
    `).join('');
}

async function openKnowledgeArticleModal(id) {
    // Справочники нужны для селектов формы — на случай, если пользователь
    // открыл модалку раньше, чем успела отработать loadKnowledgeDictionaries
    // (например, сразу после первого переключения на вкладку).
    if (!knowledgeFailureModesCache.length && !knowledgeFailureCausesCache.length) {
        await loadKnowledgeDictionaries();
    }

    const titleEl = document.getElementById('knowledgeArticleModalTitle');
    clearKnowledgeArticleForm();

    if (id) {
        titleEl.innerHTML = '<span class="icon icon-lightbulb"></span> Редактирование статьи';
        try {
            const resp = await apiFetch(`/api/knowledge/article/${id}`);
            const article = await parseJsonResponse(resp);
            if (!resp.ok) {
                showToast(article.error || 'Не удалось загрузить статью', 'error');
                return;
            }
            document.getElementById('knowledgeArticleId').value = article.id;
            document.getElementById('knowledgeArticleTitle').value = article.title || '';
            document.getElementById('knowledgeArticleSymptom').value = article.symptom || '';
            document.getElementById('knowledgeArticleDiagnostics').value = article.diagnostic_steps || '';
            document.getElementById('knowledgeArticleAction').value = article.recommended_action || '';
            document.getElementById('knowledgeArticleReference').value = article.reference_note || '';
            renderKnowledgeArticleFormOptions(
                article.failure_mode_id,
                (article.causes || []).map(c => c.id)
            );
        } catch (e) {
            showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
            return;
        }
    } else {
        titleEl.innerHTML = '<span class="icon icon-lightbulb"></span> Новая статья';
        renderKnowledgeArticleFormOptions(null, []);
    }

    document.getElementById('knowledgeArticleModal').classList.add('active');
}

function closeKnowledgeArticleModal() {
    document.getElementById('knowledgeArticleModal').classList.remove('active');
}

async function submitKnowledgeArticle() {
    const id = document.getElementById('knowledgeArticleId').value;
    const title = document.getElementById('knowledgeArticleTitle').value.trim();
    const symptom = document.getElementById('knowledgeArticleSymptom').value.trim();
    if (!title || !symptom) {
        showToast('Заголовок и симптом обязательны', 'error');
        return;
    }
    const failureModeRaw = document.getElementById('knowledgeArticleFailureMode').value;
    const causeIds = Array.from(document.querySelectorAll('.knowledge-cause-checkbox:checked'))
        .map(cb => Number(cb.value));

    const payload = {
        title,
        symptom,
        failure_mode_id: failureModeRaw ? Number(failureModeRaw) : null,
        cause_ids: causeIds,
        diagnostic_steps: document.getElementById('knowledgeArticleDiagnostics').value.trim(),
        recommended_action: document.getElementById('knowledgeArticleAction').value.trim(),
        reference_note: document.getElementById('knowledgeArticleReference').value.trim(),
    };

    try {
        const resp = id
            ? await apiFetch(`/api/knowledge/article/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
            : await apiFetch('/api/knowledge/article', { method: 'POST', body: JSON.stringify(payload) });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка сохранения', 'error');
            return;
        }
        showToast(id ? 'Статья обновлена' : 'Статья создана', 'success');
        closeKnowledgeArticleModal();
        await loadKnowledgeArticles();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

async function deleteKnowledgeArticle(id) {
    if (!confirm('Удалить статью базы знаний?')) return;
    try {
        const resp = await apiFetch(`/api/knowledge/article/${id}`, { method: 'DELETE' });
        const data = await parseJsonResponse(resp);
        if (!resp.ok) {
            showToast(data.error || 'Ошибка удаления', 'error');
            return;
        }
        showToast('Статья удалена', 'success');
        await loadKnowledgeArticles();
    } catch (e) {
        showToast(e && e.message ? e.message : 'Сетевая ошибка', 'error');
    }
}

// Поиск с debounce — тот же паттерн, что searchInput в catalog.js
// (debounce определён в common.js). Слушатель вешается сразу при загрузке
// скрипта, а не в DOMContentLoaded — script-тег подключён в конце body,
// разметка уже в DOM (см. index.html).
const debouncedLoadKnowledgeArticles = typeof debounce === 'function'
    ? debounce(loadKnowledgeArticles, 300)
    : loadKnowledgeArticles;
const knowledgeSearchInputEl = document.getElementById('knowledgeSearchInput');
if (knowledgeSearchInputEl) {
    knowledgeSearchInputEl.addEventListener('input', debouncedLoadKnowledgeArticles);
}
