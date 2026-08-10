// static/js/engineCard.js — детальная карточка двигателя, фото, обрезка, режимы/работы.
// Требует: common.js, engines.js (глобальные переменные состояния)

// created_at/updated_at приходят с бэкенда как datetime.now().isoformat()
// (иногда с 6-значными микросекундами — это не строгий ISO 8601, часть
// браузеров может не распарсить). Обрезаем дробную часть секунд до
// миллисекунд перед new Date(), чтобы не зависеть от лояльности парсера.
function formatRuDateTime(iso) {
    if (!iso) return '—';
    const normalized = iso.replace(/(\.\d{3})\d*$/, '$1');
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return escapeHtml(iso);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ===== РАЗВОРОТ КАРТОЧКИ ДВИГАТЕЛЯ НА ВЕСЬ ЭКРАН =====
// Как в обычном оконном приложении: первое нажатие разворачивает,
// повторное — возвращает размер, который был до разворачивания. Если
// пользователь до этого сам потянул за угол (нативный CSS resize — см.
// #detailModal .modal-content в style.css), эти изменения хранятся
// браузером прямо в element.style.width/height; здесь просто читаем и
// на время разворота откладываем их в переменную, а не пересчитываем
// заново.
// Состояние (detailModalPrevSize) живёт, пока не перезагрузили страницу:
// .modal-content — статический элемент в index.html, его никогда не
// перерисовывает renderDetailContent() (та трогает только #detailContent
// и #detailToolbar внутри), поэтому размер/разворот сохраняются и при
// переключении карточек кнопками Предыдущий/Следующий, и при закрытии/
// повторном открытии модалки — как и ожидаешь от окна, которое помнишь,
// что развернул.
let detailModalPrevSize = null;

function toggleDetailMaximize() {
    const modalContent = document.querySelector('#detailModal .modal-content');
    const btn = document.getElementById('detailMaximizeBtn');
    if (!modalContent) return;
    if (modalContent.classList.contains('maximized')) {
        // Восстановить: снять класс, вернуть запомненные inline-размеры
        // (пустая строка — если пользователь никогда не тянул за угол,
        // тогда просто сработают дефолтные max-width/max-height из CSS).
        modalContent.classList.remove('maximized');
        modalContent.style.width = detailModalPrevSize ? detailModalPrevSize.width : '';
        modalContent.style.height = detailModalPrevSize ? detailModalPrevSize.height : '';
        detailModalPrevSize = null;
        if (btn) { btn.innerHTML = '<span class="icon icon-open-in-full"></span>'; btn.title = 'Развернуть на весь экран'; }
    } else {
        detailModalPrevSize = {
            width: modalContent.style.width || '',
            height: modalContent.style.height || ''
        };
        modalContent.classList.add('maximized');
        if (btn) { btn.innerHTML = '<span class="icon icon-close-fullscreen"></span>'; btn.title = 'Восстановить размер'; }
      }
}

// ===== ДЕТАЛЬНАЯ МОДАЛКА =====
function showDetail(id, startInEdit = false) {
    if (window.closeTimeout) {
        clearTimeout(window.closeTimeout);
        window.closeTimeout = null;
    }

    currentEngineId = id;
    detailMode = 'view';
    const modal = document.getElementById('detailModal');
    const title = document.getElementById('detailTitle');
    const content = document.getElementById('detailContent');
    const toolbar = document.getElementById('detailToolbar');

    modal.classList.add('active');
    // Раньше detailModal был единственной модалкой без document.body.
    // classList.add('modal-open') — photoAddModal/photoCropModal/photoModal
    // это уже делали, а самая используемая модалка (карточка двигателя) —
    // нет. Итог: страница каталога позади карточки оставалась прокручиваемой,
    // и после того как .modal-body упирался в свой предел прокрутки, колесо
    // мыши "продолжало" крутить именно её (см. также overscroll-behavior
    // в style.css — это вторая половина того же фикса).
    document.body.classList.add('modal-open');
    title.textContent = '⏳ Загрузка...';
    toolbar.innerHTML = '';
    content.innerHTML = '<div class="loading">Загрузка данных...</div>';

    const modalContent = document.querySelector('.modal-content');
    if (modalContent) {
        modalContent.classList.remove('slide-out');
    }

    Promise.all([
        apiFetch(`/api/engine/${id}`).then(r => r.json()),
        apiFetch(`/api/engine/${id}/photos`).then(r => r.json())
    ]).then(([data, photos]) => {
        if (data.error) {
            toolbar.innerHTML = '';
            content.innerHTML = `<div class="no-data">${data.error}</div>`;
            title.textContent = 'Ошибка';
            return;
        }
        currentEngineData = data;
        currentPhotos = photos || [];
        currentPhotoIndex = 0;
        title.textContent = (id === pendingNewEngineId)
            ? '🆕 Новый двигатель'
            : `${data.engine_type || 'Тип не указан'} · ${data.location || 'Без места'} · Зав. № ${data.serial_number || '—'}`;
        detailMode = startInEdit ? 'edit' : 'view';
        renderDetailContent();
        
    }).catch(e => {
        toolbar.innerHTML = '';
        content.innerHTML = `<div class="no-data">Ошибка: ${e.message}</div>`;
    });
}


// ===== РЕНДЕР КАРТОЧКИ =====
function renderDetailContent() {
    const content = document.getElementById('detailContent');
    const toolbar = document.getElementById('detailToolbar');
    const data = currentEngineData;
    if (!data) return;

    const currentIndex = allEngines.findIndex(e => e.id === data.id);
    const total = allEngines.length;
    const isEdit = detailMode === 'edit';
    // Карточка, созданная через "+" в дереве и ещё ни разу не сохранённая —
    // навигация/печать/удаление для неё бессмысленны (записи ещё как будто
    // не существует для пользователя), и "Отмена" здесь означает отказ от
    // создания, а не откат правок (см. cancelDetailEdit).
    const isPendingNew = currentEngineId !== null && currentEngineId === pendingNewEngineId;

    // Тулбар живёт вне #detailContent (см. index.html) — не скроллится
    // вместе с содержимым, поэтому ему не нужен position: sticky и он не
    // может "потерять" прилипание, из-за которого фото раньше проглядывали
    // между шапкой модалки и этой панелью.
    const infoHtml = isPendingNew
        ? `<span class="detail-toolbar-title">🆕 Новый двигатель</span>`
        : `<span class="detail-toolbar-title"><span class="icon icon-description"></span> Карточка двигателя</span>
           <span class="detail-toolbar-position">${currentIndex + 1} / ${total}</span>
           <span class="detail-toolbar-dates">Изменено: ${formatRuDateTime(data.updated_at)} · Создано: ${formatRuDateTime(data.created_at)}</span>`;

    const editButtonsHtml = isEdit
        ? `<button class="btn btn-success btn-sm" onclick="event.stopPropagation(); saveDetailEdit()"><span class="icon icon-save"></span> Сохранить</button>
           <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); cancelDetailEdit()"><span class="icon icon-close"></span> Отмена</button>`
        : `<button class="btn btn-warning btn-sm write-action" onclick="event.stopPropagation(); enterEditMode()"><span class="icon icon-edit"></span> Редактировать</button>`;

    const navButtonsHtml = isPendingNew ? '' : `
           <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateEngine(-1)" ${currentIndex <= 0 ? 'disabled' : ''}>◀ Предыдущий</button>
           <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); navigateEngine(1)" ${currentIndex === total - 1 ? 'disabled' : ''}>Следующий ▶</button>
           <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); printEngineCard()"><span class="icon icon-print"></span> Печать</button>
           <button class="btn btn-danger btn-sm write-action" onclick="event.stopPropagation(); deleteCurrentEngine()"><span class="icon icon-delete"></span> Удалить</button>`;

    toolbar.innerHTML = `<div class="detail-toolbar">
        <div class="detail-toolbar-info">${infoHtml}</div>
        <div class="detail-toolbar-nav">${editButtonsHtml}${navButtonsHtml}</div>
    </div>`;

    let html = '';

    // ---- Фото ----
    html += `<div class="detail-subsection-header">
        <h4><span class="icon icon-photo-camera"></span> Фото${currentPhotos.length ? ' (' + currentPhotos.length + ')' : ''}</h4>
        ${isEdit ? '<button class="btn btn-success btn-sm" onclick="openPhotoAddModal()"><span class="icon icon-add"></span> Добавить</button>' : ''}
    </div>`;
    if (currentPhotos.length > 0) {
        html += '<div class="detail-photos" id="photoGallery">';
        currentPhotos.forEach((p) => {
            const safeFilename = p.filename.replace(/'/g, "\\'");
            // p.path тоже строится из имени файла, которое может содержать
            // апостроф (санитизация на бэкенде убирает <>:"/\|?*, но не ');
            // экранируем так же, как safeFilename — иначе апостроф в
            // filename ломает JS-строку внутри onclick.
            const safePath = p.path.replace(/'/g, "\\'");
            html += `<div class="gallery-thumb-wrap">
                <img src="${authPhotoUrl(p.path)}?v=${photoCacheBust}" class="gallery-thumb" onclick="event.stopPropagation(); openPhotoModalWithNav('${safePath}')" loading="lazy">
                ${isEdit ? `<button type="button" class="gallery-thumb-crop" title="Обрезать" onclick="event.stopPropagation(); openCropModal('existing', '${safeFilename}', '${safePath}')"><span class="icon icon-content-cut"></span></button>` : ''}
                ${isEdit ? `<button type="button" class="gallery-thumb-remove" title="Удалить фото" onclick="event.stopPropagation(); removeDetailPhoto('${safeFilename}')">−</button>` : ''}
            </div>`;
        });
        html += '</div>';
    } else {
        html += '<div class="no-data">Нет фото</div>';
    }

    // ---- Характеристики ----
    html += `<div class="detail-subsection-header"><h4><span class="icon icon-table-chart"></span> Характеристики</h4></div><div class="detail-grid">`;
    DETAIL_CHAR_FIELDS.forEach(f => {
        const val = data[f.key];
        const safeVal = val && val !== 'nan' ? escapeHtml(val) : '';
        if (isEdit) {
            let inputHtml;
            if (f.key === 'note') {
                inputHtml = `<textarea class="detail-edit-input" data-field="${f.key}">${safeVal}</textarea>`;
            } else if (DETAIL_NUMERIC_FIELDS.has(f.key)) {
                inputHtml = `<input type="number" step="any" class="detail-edit-input" data-field="${f.key}" value="${safeVal}">`;
            } else {
                inputHtml = `<input type="text" class="detail-edit-input" data-field="${f.key}" value="${safeVal}">`;
            }
            html += `<div class="detail-item detail-item-edit"><label>${escapeHtml(f.label)}</label>${inputHtml}</div>`;
        } else {
            html += `<div class="detail-item"><label>${escapeHtml(f.label)}</label><div class="value">${safeVal || '—'}</div></div>`;
        }
    });
    html += '</div>';

    // ---- Режимы работы ----
    // В режиме редактирования карточки (isEdit) все строки сразу
    // редактируемые (не только новые, как у "Произведённых работ") —
    // режимы это не исторический лог, а список техпараметров, который
    // логично уметь поправить целиком. "Сохранить режимы" шлёт весь
    // список на PUT /api/engine/:id/modes — он и раньше делал полную
    // замену (DELETE+INSERT), так что backend не менялся.
    html += `<div class="detail-subsection-header"><h4><span class="icon icon-bolt"></span> Режимы работы</h4>
        ${isEdit ? '<button class="btn btn-success btn-sm" onclick="addModeRowInline()"><span class="icon icon-add"></span> Добавить режим</button>' : ''}
    </div>`;
    if (isEdit) {
        html += '<div class="table-wrapper"><table class="data-table modes-table"><thead><tr>';
        html += '<th>Частота (Гц)</th><th>Mощность (кВт)</th><th>Напряжение (В)</th><th>Тип подключения</th><th>Ток (А)</th><th>Обороты (об/мин)</th><th class="col-mode-action"></th>';
        html += '</tr></thead><tbody id="modesDisplayBody">';
        const modes = data.modes || [];
        if (modes.length > 0) {
            modes.forEach((m, idx) => {
                html += `<tr>
                    <td><input type="number" step="any" class="mode-edit-input" data-field="frequency" value="${escapeHtml(m.frequency) || ''}"></td>
                    <td><input type="number" step="any" class="mode-edit-input" data-field="power" value="${escapeHtml(m.power) || ''}"></td>
                    <td><input type="number" step="any" class="mode-edit-input" data-field="voltage" value="${escapeHtml(m.voltage) || ''}"></td>
                    <td><input type="text" class="mode-edit-input" data-field="connection_type" value="${escapeHtml(m.connection_type) || ''}"></td>
                    <td><input type="number" step="any" class="mode-edit-input" data-field="current" value="${escapeHtml(m.current) || ''}"></td>
                    <td><input type="number" step="any" class="mode-edit-input" data-field="rpm" value="${escapeHtml(m.rpm) || ''}"></td>
                    <td class="work-cell-action"><button type="button" class="btn btn-danger btn-sm work-remove-btn" onclick="removeModeRowInline(${idx})" title="Удалить режим">−</button></td>
                </tr>`;
            });
        } else {
            html += '<tr><td colspan="7" class="no-data">Нет режимов работы</td></tr>';
        }
        html += '</tbody></table></div>';
    } else if (data.modes && data.modes.length > 0) {
        html += '<div class="table-wrapper"><table class="data-table"><thead><tr>';
        html += '<th>#</th><th>Частота (Гц)</th><th>Мощность (кВт)</th><th>Напряжение (В)</th><th>Тип подключения</th><th>Ток (А)</th><th>Обороты (об/мин)</th>';
        html += '</tr></thead><tbody>';
        data.modes.forEach((m, i) => {
            html += `<tr><td>${i + 1}</td><td>${escapeHtml(m.frequency) || '—'}</td><td>${escapeHtml(m.power) || '—'}</td><td>${escapeHtml(m.voltage) || '—'}</td><td>${escapeHtml(m.connection_type) || '—'}</td><td>${escapeHtml(m.current) || '—'}</td><td>${escapeHtml(m.rpm) || '—'}</td></tr>`;
        });
        html += '</tbody></table></div>';
    } else {
        html += '<div class="no-data">Нет режимов работы</div>';
    }

    // ---- Произведенные работы ----
    // Раньше редактируемыми были только новые (_isNew) строки, а
    // "Сохранить работы" собирала данные ИСКЛЮЧИТЕЛЬНО из них (у
    // существующих строк не было .work-edit-input вообще) — при этом
    // backend делает полную замену (DELETE ALL + INSERT). Итог: каждое
    // сохранение стирало всю историю, оставляя только то, что было
    // добавлено в этом заходе. Исправлено по той же схеме, что и
    // "Режимы работы": деления на новые/старые больше нет, в isEdit
    // редактируемы ВСЕ строки сразу, "№ п/п" — не хранимое и не
    // редактируемое поле, а чистая позиция в списке (как и было у
    // read-only строк) — это заодно убирает баг с задвоением номера
    // при добавлении нескольких строк подряд без сохранения.
    html += `<div class="detail-subsection-header"><h4><span class="icon icon-build"></span> Произведенные работы</h4>
        ${isEdit ? '<button class="btn btn-success btn-sm" onclick="addWorkRowInline()"><span class="icon icon-add"></span> Добавить</button>' : ''}
    </div>`;
    if (isEdit) {
        html += '<div class="table-wrapper"><table class="data-table works-table"><thead><tr>';
        html += '<th class="col-work-num">№ п/п</th><th class="col-work-date">Дата</th><th>Вид производимых работ</th><th class="col-work-isolation">Сопротивление изоляции</th><th class="col-work-inspection">Внешний осмотр и проверка работы</th><th class="col-work-signature">ФИО исполнителя</th>';
        html += '<th class="col-work-action"></th>';
        html += '</tr></thead><tbody id="worksDisplayBody">';
        const works = data.works || [];
        if (works.length > 0) {
            works.forEach((w, idx) => {
                html += `<tr>
                    <td class="work-cell-num">${idx + 1}</td>
                    <td><input type="date" class="work-edit-input" data-field="date" value="${escapeHtml(w.date) || ''}"></td>
                    <td><input type="text" class="work-edit-input" data-field="work_description" value="${escapeHtml(w.work_description) || ''}" placeholder="Введите описание"></td>
                    <td><input type="number" step="any" class="work-edit-input" data-field="isolation" value="${escapeHtml(w.isolation) || ''}" placeholder="МОм"></td>
                    <td><input type="text" class="work-edit-input" data-field="inspection" value="${escapeHtml(w.inspection) || ''}" placeholder="Результат"></td>
                    <td><input type="text" class="work-edit-input" data-field="signature" value="${escapeHtml(w.signature) || ''}" placeholder="ФИО"></td>
                    <td class="work-cell-action"><button type="button" class="btn btn-danger btn-sm work-remove-btn" onclick="removeWorkRowInline(${idx})" title="Удалить работу">−</button></td>
                </tr>`;
            });
        } else {
            html += '<tr><td colspan="7" class="no-data">Не было произведено работ</td></tr>';
        }
        html += '</tbody></table></div>';
    } else if (data.works && data.works.length > 0) {
        html += '<div class="table-wrapper"><table class="data-table"><thead><tr>';
        html += '<th>№ п/п</th><th>Дата</th><th>Вид производимых работ</th><th>Сопротивление изоляции</th><th>Внешний осмотр и проверка работы</th><th>ФИО исполнителя</th>';
        html += '</tr></thead><tbody>';
        data.works.forEach((w, idx) => {
            html += `<tr>
                <td>${idx + 1}</td>
                <td>${_formatRuDate(w.date) || '—'}</td>
                <td>${escapeHtml(w.work_description) || '—'}</td>
                <td>${escapeHtml(w.isolation) || '—'}</td>
                <td>${escapeHtml(w.inspection) || '—'}</td>
                <td>${escapeHtml(w.signature) || '—'}</td>
            </tr>`;
        });
        html += '</tbody></table></div>';
    } else {
        html += '<div class="no-data">Не было произведено работ</div>';
    }

    content.innerHTML = html;

    if (isEdit) {
        content.querySelectorAll('.detail-edit-input[data-field]').forEach(el => {
            attachFieldAutocomplete(el, el.dataset.field);
        });
        content.querySelectorAll('.mode-edit-input[data-field]').forEach(el => {
            attachFieldAutocomplete(el, el.dataset.field);
        });
        content.querySelectorAll('.mode-edit-input').forEach(input => {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveDetailEdit();
                }
            });
        });
        // Автодополнение НЕ вешаем на .work-edit-input: date/work_description/
        // isolation/inspection/signature не входят ни в ENGINE_COLUMNS, ни в
        // MODE_COLUMNS (см. app.py) — /api/search-suggestions для них всегда
        // вернёт пустой список, так что дропдаун был бы бесполезным шумом
        // (плюс лишние сетевые запросы на каждый фокус). Оставляем только
        // Enter-сохранение.
        content.querySelectorAll('.work-edit-input').forEach(input => {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveDetailEdit();
                }
            });
        });
    }
}


// ===== ДОБАВЛЕНИЕ СТРОКИ РАБОТЫ =====
// ===== ДОБАВЛЕНИЕ СТРОКИ РАБОТЫ =====
function addWorkRowInline() {
    if (!currentEngineData) return;
    // Сначала считываем то, что уже напечатано в DOM (включая другие,
    // ещё не сохранённые строки) — иначе renderDetailContent() ниже
    // перерисует таблицу из currentEngineData.works "как было до этого
    // клика", и всё введённое в предыдущих строках молча потеряется.
    currentEngineData.works = collectWorkRowsFromDom();
    // work_number больше не хранится/не считается вручную — "№ п/п"
    // это позиция строки в списке (см. renderDetailContent). Раньше
    // здесь был maxNum, который считался ТОЛЬКО по не-новым строкам и
    // поэтому давал одинаковый номер при добавлении нескольких строк
    // подряд без сохранения между ними — с позиционной нумерацией эта
    // категория бага исчезает сама по себе.
    // Дата новой записи — сегодняшним числом по умолчанию (в формате
    // YYYY-MM-DD, как и ожидает input[type="date"], и как parse_maintenance_works
    // в app.py уже приводит даты при импорте из Excel — форматы совпадают,
    // никакой отдельной конвертации не нужно).
    currentEngineData.works.push({
        date: new Date().toISOString().slice(0, 10),
        work_description: '', isolation: '', inspection: '', signature: ''
    });
    renderDetailContent();

    setTimeout(() => {
        const tbody = document.getElementById('worksDisplayBody');
        const lastRow = tbody && tbody.lastElementChild;
        if (lastRow) {
            lastRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            lastRow.classList.add('work-row-flash');
            setTimeout(() => lastRow.classList.remove('work-row-flash'), 2000);
        }
    }, 100);

    showToast('<span class="icon icon-add"></span> Добавлена строка. Заполните поля и нажмите "Сохранить" или Enter.', 'success');
}


// ===== УДАЛЕНИЕ СТРОКИ РАБОТЫ =====
function removeWorkRowInline(idx) {
    if (!currentEngineData) return;
    // Синхронизация с DOM по той же причине, что и в addWorkRowInline —
    // иначе правки в ДРУГИХ, ещё не сохранённых строках потерялись бы
    // при перерисовке ниже.
    currentEngineData.works = collectWorkRowsFromDom();
    const work = currentEngineData.works[idx];
    if (!work) return;
    // В отличие от режимов работы, тут confirm() оставлен для ЛЮБОЙ
    // строки (не только уже сохранённой) — записи в этой таблице носят
    // характер журнала обслуживания, случайная потеря записи весомее,
    // чем у технических параметров режима. Реально с сервера запись
    // удалится только после следующего клика "Сохранить" — ровно как и
    // добавление новой строки.
    if (!confirm(`Удалить запись №${idx + 1} (${work.date || 'без даты'})?`)) return;
    currentEngineData.works.splice(idx, 1);
    renderDetailContent();
    showToast('<span class="icon icon-delete"></span> Запись удалена из списка — не забудьте нажать "Сохранить"', 'info');
}


// ===== СОХРАНЕНИЕ РАБОТ =====
// ===== ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ / СОХРАНЕНИЕ =====
// Раньше здесь было три отдельные кнопки сохранения (характеристики /
// режимы / работы) и два параллельных состояния (detailMode для
// режимов-работ, detailEditMode для характеристик) — путаница и источник
// как минимум одного реального бага (saveWorksOnly стирала историю работ,
// см. комментарий у works ниже). Теперь один detailMode('view'|'edit') на
// всю карточку и одна кнопка "<span class="icon icon-save"></span> Сохранить" в шапке (см. renderDetailContent).

function enterEditMode() {
    detailMode = 'edit';
    renderDetailContent();
}

function cancelDetailEdit() {
    if (currentEngineId !== null && currentEngineId === pendingNewEngineId) {
        // Новая, ещё не подтверждённая карточка — "Отмена" здесь означает
        // отказ от создания, а не откат правок. closeDetail() сам увидит
        // pendingNewEngineId и удалит запись.
        closeDetail();
        return;
    }
    // Существующий двигатель — перечитываем карточку с сервера, отбрасывая
    // все локальные несохранённые правки. Это касается не только полей
    // характеристик, но и режимов/работ: добавление/удаление их строк
    // мутирует currentEngineData.modes/works сразу же (см. addModeRowInline
    // и др.), а не только в момент сохранения.
    showDetail(currentEngineId, false);
}

function collectModeRowsFromDom() {
    return Array.from(document.querySelectorAll('#modesDisplayBody tr'))
        .map(tr => {
            const inputs = tr.querySelectorAll('.mode-edit-input[data-field]');
            if (inputs.length === 0) return null; // строка-заглушка "Нет режимов работы"
            const row = {};
            inputs.forEach(inp => { row[inp.dataset.field] = inp.value.trim(); });
            return row;
        })
        .filter(Boolean);
}

function collectWorkRowsFromDom() {
    return Array.from(document.querySelectorAll('#worksDisplayBody tr'))
        .map((tr, idx) => {
            const inputs = tr.querySelectorAll('.work-edit-input[data-field]');
            if (inputs.length === 0) return null; // строка-заглушка "Не было произведено работ"
            const row = { work_number: String(idx + 1) };
            inputs.forEach(inp => { row[inp.dataset.field] = inp.value.trim(); });
            return row;
        })
        .filter(Boolean);
}

function saveDetailEdit() {
    if (!currentEngineId) return;

    const payload = {};
    document.querySelectorAll('#detailContent .detail-edit-input[data-field]').forEach(el => {
        payload[el.dataset.field] = el.value.trim();
    });
    // modes/works уходят в том же PUT — backend (routes/engines.py::
    // update_engine) делает по ним полную замену (DELETE+INSERT), как и
    // раньше делали отдельные /modes и /works, просто теперь одним запросом
    // вместе с характеристиками.
    payload.modes = collectModeRowsFromDom();
    payload.works = collectWorkRowsFromDom();

    apiFetch(`/api/engine/${currentEngineId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            showToast('<span class="icon icon-cancel"></span> ' + result.error, 'error');
            return;
        }
        const wasPendingNew = currentEngineId === pendingNewEngineId;
        if (wasPendingNew) pendingNewEngineId = null;
        loadEngines();
        loadLocationTree();
        updateStats();
        showToast(wasPendingNew ? '<span class="icon icon-check-circle"></span> Двигатель добавлен' : '<span class="icon icon-check-circle"></span> Изменения сохранены', 'success');
        // Перечитываем карточку с сервера — актуальные updated_at/created_at,
        // и переключаемся в режим просмотра только что сохранённых данных.
        showDetail(currentEngineId, false);
    })
    .catch(e => showToast('<span class="icon icon-cancel"></span> Ошибка: ' + e.message, 'error'));
}


// ===== ПЕЧАТЬ КАРТОЧКИ =====
// Открываем отдельную print-страницу в новой вкладке (не переиспользуем
// detailModal с @media print — там слишком много интерактивного "мусора":
// toolbar с переключателем режима, кнопки навигации, drag-состояния
// галереи и т.п., которые пришлось бы прятать хрупкими CSS-overrides).
// Сама печатная страница по загрузке предлагает нативный диалог печати
// браузера (window.print()) — это и есть предпросмотр, и выбор
// принтера/PDF там же, без отдельной PDF-библиотеки на сервере.
function printEngineCard() {
    if (!currentEngineId) return;
    window.open(`/print/${currentEngineId}`, '_blank');
}


// ===== УДАЛЕНИЕ КАРТОЧКИ =====
function deleteCurrentEngine() {
    if (!currentEngineId) {
        showToast('<span class="icon icon-warning"></span> Нет открытой карточки', 'warning');
        return;
    }
    if (!confirm(`Удалить двигатель ID=${currentEngineId}?`)) return;

    apiFetch(`/api/engine/${currentEngineId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast('<span class="icon icon-cancel"></span> ' + data.error, 'error');
                return;
            }
            showToast('<span class="icon icon-check-circle"></span> ' + data.message, 'success');
            closeDetail();
            loadEngines();
            updateStats();
        })
        .catch(e => showToast('<span class="icon icon-cancel"></span> Ошибка: ' + e.message, 'error'));
}


// ===== ЗАКРЫТИЕ КАРТОЧКИ =====
// Общий helper для 'modal-open' на <body>. Раньше каждая вложенная модалка
// (кроп, добавление фото, просмотр фото) при закрытии безусловно снимала
// этот класс — а вложенные модалки открываются ПОВЕРХ ещё открытой
// detailModal (карточки двигателя). Итог: закрыл кроп-модалку — и скролл
// каталога за карточкой разблокировался, хотя сама карточка ещё открыта
// (тот же класс бага, что уже чинили один раз для detailModal — см.
// HISTORY.md "Скролл 'пробивает' модалку", только теперь для вложенных
// модалок поверх неё). Снимаем modal-open только если совсем не осталось
// открытых модалок (.modal.active включает detailModal/photoAddModal/
// photoCropModal, .photo-modal.active — отдельный класс у photoModal).
function _syncModalOpenState() {
    const anyOpen = document.querySelector('.modal.active, .photo-modal.active');
    document.body.classList.toggle('modal-open', !!anyOpen);
}

function closeDetail() {
    // Карточка была создана через "+" в дереве (POST /api/engine сразу при
    // клике — см. locationTree.js::createAndOpenEngine), но пользователь
    // так и не нажал "Сохранить" — запись существует в БД только как
    // техническая деталь реализации ("как будто редактируем существующий
    // двигатель"), пользователь её сохранённой не считал. Удаляем молча.
    const idToDiscard = (currentEngineId !== null && currentEngineId === pendingNewEngineId)
        ? currentEngineId
        : null;

    const modalContent = document.querySelector('.modal-content');
    if (modalContent) {
        modalContent.classList.add('slide-out');
    }
    
    setTimeout(() => {
        const modal = document.getElementById('detailModal');
        if (modal) {
            modal.classList.remove('active');
        }
        _syncModalOpenState();
        currentEngineId = null;
        currentEngineData = null;
        detailMode = 'view';
        if (modalContent) {
            modalContent.classList.remove('slide-out');
        }

        if (idToDiscard !== null) {
            pendingNewEngineId = null;
            apiFetch(`/api/engine/${idToDiscard}`, { method: 'DELETE' }).catch(() => {});
        }
    }, 300);
}


// ===== ФОТО: ДОБАВЛЕНИЕ И УДАЛЕНИЕ =====
function openPhotoAddModal() {
    detailPhotoFiles = [];
    renderDetailPhotoPreview();
    document.getElementById('photoAddModal').classList.add('active');
    document.body.classList.add('modal-open');
}

function closePhotoAddModal() {
    document.getElementById('photoAddModal').classList.remove('active');
    _syncModalOpenState();
    detailPhotoFiles = [];
}

function renderDetailPhotoPreview() {
    const wrap = document.getElementById('detailPhotoPreview');
    if (!wrap) return;
    wrap.innerHTML = '';
    detailPhotoFiles.forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const box = document.createElement('div');
        box.className = 'photo-thumb is-pending';
        box.innerHTML = `<img src="${url}" alt="Новое фото"><button type="button" class="photo-thumb-crop" title="Обрезать" onclick="openCropModal('detail', ${idx})"><span class="icon icon-content-cut"></span></button><button type="button" class="photo-thumb-remove" onclick="removeDetailPendingPhoto(${idx})"><span class="icon icon-close"></span></button>`;
        wrap.appendChild(box);
    });
}

function removeDetailPendingPhoto(idx) {
    detailPhotoFiles.splice(idx, 1);
    renderDetailPhotoPreview();
}

function submitDetailPhotoAdd() {
    if (!currentEngineId) return;
    if (detailPhotoFiles.length === 0) {
        showToast('<span class="icon icon-warning"></span> Выберите хотя бы одно фото', 'warning');
        return;
    }
    const formData = new FormData();
    detailPhotoFiles.forEach(f => formData.append('photos', f));
    apiFetch(`/api/engine/${currentEngineId}/photos`, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast('<span class="icon icon-cancel"></span> ' + data.error, 'error');
                return null;
            }
            showToast(`<span class="icon icon-check-circle"></span> Загружено фото: ${data.uploaded}`, 'success');
            closePhotoAddModal();
            return apiFetch(`/api/engine/${currentEngineId}/photos`).then(r => r.json());
        })
        .then(photos => {
            if (!photos) return;
            currentPhotos = photos;
            photoCacheBust = Date.now();
            renderDetailContent();
            loadEngines();
            updateStats();
        })
        .catch(e => showToast('<span class="icon icon-cancel"></span> Ошибка: ' + e.message, 'error'));
}

function removeDetailPhoto(filename) {
    if (!currentEngineId) return;
    if (!confirm('Удалить это фото?')) return;
    apiFetch(`/api/engine/${currentEngineId}/photos/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showToast('<span class="icon icon-cancel"></span> ' + data.error, 'error');
                return;
            }
            currentPhotos = currentPhotos.filter(p => p.filename !== filename);
            photoCacheBust = Date.now();
            renderDetailContent();
            loadEngines();
            updateStats();
            showToast('<span class="icon icon-delete"></span> Фото удалено', 'success');
        })
        .catch(e => showToast('<span class="icon icon-cancel"></span> Ошибка: ' + e.message, 'error'));
}


// ===== ОБРЕЗКА ФОТО (photoCropModal) =====
// Работает с двумя независимыми списками ещё не загруженных File —
// detailPhotoFiles (модалка фото в карточке) и pendingPhotoFiles (форма
// добавления нового двигателя). Какой из них редактируется сейчас,
// хранится в cropState.list, чтобы не дублировать canvas-логику дважды.
const cropState = {
    list: null,        // 'detail' | 'pending' | 'existing'
    index: -1,          // индекс в detailPhotoFiles/pendingPhotoFiles (для 'detail'/'pending')
    filename: null,      // имя файла на диске (только для 'existing')
    objectUrl: null,     // ObjectURL для File-веток; для 'existing' не используется (грузим по серверному пути)
    image: null,        // Image в естественном разрешении
    displayScale: 1,     // во сколько раз натуральный размер больше отображаемого на canvas
    sel: { x: 0, y: 0, w: 0, h: 0 }, // рамка выделения в координатах ОТОБРАЖАЕМОГО canvas
    drag: null           // {mode: 'move'|'nw'|'ne'|'sw'|'se'|'new', startX, startY, startSel}
};

const CROP_MAX_W = 640;
const CROP_MAX_H = 440;
// Зона захвата угла увеличена через CSS (.crop-handle::before, style.css) —
// там же и обоснование, отдельной JS-константы для неё больше не нужно.

function _cropFilesArray() {
    return cropState.list === 'detail' ? detailPhotoFiles : pendingPhotoFiles;
}

// Расширение файла -> mime-тип, в котором canvas должен отдать обрезанный
// результат. Для форматов, которые canvas.toBlob не умеет кодировать
// (gif/bmp), перекодируем в jpeg — см. applyCropExisting, где при смене
// расширения файл на диске пересохраняется под новым именем.
function _cropMimeForExt(ext) {
    const map = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp' };
    return map[(ext || '').toLowerCase()] || 'image/jpeg';
}
function _cropExtForMime(mime) {
    const map = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp' };
    return map[mime] || '.jpg';
}

function _openCropStage(img) {
    cropState.image = img;

    const scale = Math.min(CROP_MAX_W / img.naturalWidth, CROP_MAX_H / img.naturalHeight, 1);
    const dispW = Math.round(img.naturalWidth * scale);
    const dispH = Math.round(img.naturalHeight * scale);
    cropState.displayScale = img.naturalWidth / dispW;

    const canvas = document.getElementById('cropCanvas');
    canvas.width = dispW;
    canvas.height = dispH;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, dispW, dispH);
    ctx.drawImage(img, 0, 0, dispW, dispH);

    const stage = document.getElementById('cropStage');
    stage.style.width = dispW + 'px';
    stage.style.height = dispH + 'px';

    // Рамка по умолчанию — центрированные 80% изображения.
    cropState.sel = { x: dispW * 0.1, y: dispH * 0.1, w: dispW * 0.8, h: dispH * 0.8 };
    _renderCropSelection();

    document.getElementById('photoCropModal').classList.add('active');
    document.body.classList.add('modal-open');

    // Add global pointer listeners for crop functionality
    document.addEventListener('pointermove', _cropPointerMove);
    document.addEventListener('pointerup', _cropPointerUp);
}

// openCropModal('detail'|'pending', idx) — обрезка ещё не загруженного File.
// openCropModal('existing', filename, path) — обрезка уже сохранённого на
// сервере фото (карточка, режим редактирования).
function openCropModal(list, a, b) {
    if (list === 'existing') {
        const filename = a, path = b;
        cropState.list = 'existing';
        cropState.index = -1;
        cropState.filename = filename;
        if (cropState.objectUrl) { URL.revokeObjectURL(cropState.objectUrl); cropState.objectUrl = null; }

        const img = new Image();
        img.onload = function() { _openCropStage(img); };
        img.onerror = function() { showToast('<span class="icon icon-cancel"></span> Не удалось загрузить фото для обрезки', 'error'); };
        // Тот же путь, что и в галерее (без cache-bust параметра) — грузим
        // актуальную версию с сервера, same-origin, canvas не будет "грязным".
        // authPhotoUrl добавляет токен в query (?token=), иначе <img>
        // получит 401 (маршрут /api/photos защищён авторизацией).
        img.src = authPhotoUrl(path);
        return;
    }

    const idx = a;
    const files = list === 'detail' ? detailPhotoFiles : pendingPhotoFiles;
    const file = files[idx];
    if (!file) return;

    cropState.list = list;
    cropState.index = idx;
    cropState.filename = null;
    if (cropState.objectUrl) URL.revokeObjectURL(cropState.objectUrl);
    cropState.objectUrl = URL.createObjectURL(file);

    const img = new Image();
    img.onload = function() { _openCropStage(img); };
    img.src = cropState.objectUrl;
}

function closeCropModal() {
    document.getElementById('photoCropModal').classList.remove('active');
    _syncModalOpenState();
    if (cropState.objectUrl) {
        URL.revokeObjectURL(cropState.objectUrl);
        cropState.objectUrl = null;
    }
    cropState.image = null;
    cropState.filename = null;
    cropState.drag = null;

    // Remove global pointer listeners for crop functionality
    document.removeEventListener('pointermove', _cropPointerMove);
    document.removeEventListener('pointerup', _cropPointerUp);
}

// Позиция/размер рамки выделения — управляемая геометрия, меняющаяся на
// каждый pointermove, а не статичное состояние. Прямая запись в
// .style. здесь — тот же обоснованный случай, что и .progress-fill
// (см. style.css), а не нарушение правила "никаких inline-стилей".
function _renderCropSelection() {
    const sel = document.getElementById('cropSelection');
    sel.style.left = cropState.sel.x + 'px';
    sel.style.top = cropState.sel.y + 'px';
    sel.style.width = cropState.sel.w + 'px';
    sel.style.height = cropState.sel.h + 'px';
}

function _cropClamp() {
    const canvas = document.getElementById('cropCanvas');
    const maxW = canvas.width;
    const maxH = canvas.height;
    let { x, y, w, h } = cropState.sel;
    w = Math.max(20, Math.min(w, maxW));
    h = Math.max(20, Math.min(h, maxH));
    x = Math.max(0, Math.min(x, maxW - w));
    y = Math.max(0, Math.min(y, maxH - h));
    cropState.sel = { x, y, w, h };
}

function _cropPointerDown(e, mode) {
    e.preventDefault();
    e.stopPropagation();
    const stage = document.getElementById('cropStage');
    const rect = stage.getBoundingClientRect();
    cropState.drag = {
        mode,
        startX: e.clientX - rect.left,
        startY: e.clientY - rect.top,
        startSel: Object.assign({}, cropState.sel)
    };
    if (e.target.setPointerCapture && e.pointerId !== undefined) {
        e.target.setPointerCapture(e.pointerId);
    }
}

function _cropPointerMove(e) {
    if (!cropState.drag) return;
    const stage = document.getElementById('cropStage');
    const rect = stage.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    const curY = e.clientY - rect.top;
    const dx = curX - cropState.drag.startX;
    const dy = curY - cropState.drag.startY;
    const start = cropState.drag.startSel;

    if (cropState.drag.mode === 'move') {
        cropState.sel = { x: start.x + dx, y: start.y + dy, w: start.w, h: start.h };
    } else if (cropState.drag.mode === 'new') {
        // Рисование рамки "с нуля" от точки клика — считаем прямоугольник
        // от startX/startY до текущей позиции курсора в любом направлении
        // (в отличие от ресайза за угол, тут нет фиксированной стартовой
        // рамки, поэтому move-style dx/dy не подходит).
        cropState.sel = {
            x: Math.min(cropState.drag.startX, curX),
            y: Math.min(cropState.drag.startY, curY),
            w: Math.abs(curX - cropState.drag.startX),
            h: Math.abs(curY - cropState.drag.startY)
        };
    } else if (cropState.drag.mode === 'se') {
        cropState.sel = { x: start.x, y: start.y, w: start.w + dx, h: start.h + dy };
    } else if (cropState.drag.mode === 'nw') {
        cropState.sel = { x: start.x + dx, y: start.y + dy, w: start.w - dx, h: start.h - dy };
    } else if (cropState.drag.mode === 'ne') {
        cropState.sel = { x: start.x, y: start.y + dy, w: start.w + dx, h: start.h - dy };
    } else if (cropState.drag.mode === 'sw') {
        cropState.sel = { x: start.x + dx, y: start.y, w: start.w - dx, h: start.h + dy };
    }
    _cropClamp();
    _renderCropSelection();
}

function _cropPointerUp() {
    cropState.drag = null;
}

function applyCrop() {
    if (!cropState.image) return;
    if (cropState.list === 'existing') {
        _applyCropExisting();
    } else {
        _applyCropFile();
    }
}

// Обрезка ещё не загруженного File (карточка/форма добавления) — как и
// раньше, просто подменяем элемент массива, ничего не шлём на сервер.
function _applyCropFile() {
    if (cropState.index < 0) return;
    const files = _cropFilesArray();
    const file = files[cropState.index];
    if (!file) { closeCropModal(); return; }

    const s = cropState.displayScale;
    const sx = Math.round(cropState.sel.x * s);
    const sy = Math.round(cropState.sel.y * s);
    const sw = Math.round(cropState.sel.w * s);
    const sh = Math.round(cropState.sel.h * s);

    const out = document.createElement('canvas');
    out.width = sw;
    out.height = sh;
    const ctx = out.getContext('2d');
    ctx.drawImage(cropState.image, sx, sy, sw, sh, 0, 0, sw, sh);

    const mimeType = ['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/bmp'].includes(file.type)
        ? file.type
        : 'image/jpeg';

    out.toBlob(function(blob) {
        if (!blob) {
            showToast('<span class="icon icon-cancel"></span> Не удалось обрезать фото', 'error');
            return;
        }
        const croppedFile = new File([blob], file.name, { type: mimeType });
        // Заменяем оригинал обрезанным вариантом — второй копии не остаётся.
        files[cropState.index] = croppedFile;
        closeCropModal();
        if (cropState.list === 'detail') {
            renderDetailPhotoPreview();
        } else {
            renderPhotosPreview();
        }
        showToast('<span class="icon icon-check-circle"></span> Фото обрезано', 'success');
    }, mimeType, 0.92);
}

// Обрезка уже сохранённого на сервере фото — вырезаем область, кодируем
// в mime-тип, соответствующий исходному расширению файла (см.
// _cropMimeForExt), и загружаем на PUT /api/engine/:id/photos/:filename,
// который перезаписывает файл на диске тем же именем (если расширение
// не поменялось) либо пересохраняет под тем же базовым именем с новым
// расширением (см. app.py). Второй копии на диске не остаётся —
// backend сам удаляет старый файл при смене расширения.
function _applyCropExisting() {
    if (!currentEngineId || !cropState.filename) { closeCropModal(); return; }

    const s = cropState.displayScale;
    const sx = Math.round(cropState.sel.x * s);
    const sy = Math.round(cropState.sel.y * s);
    const sw = Math.round(cropState.sel.w * s);
    const sh = Math.round(cropState.sel.h * s);

    const out = document.createElement('canvas');
    out.width = sw;
    out.height = sh;
    const ctx = out.getContext('2d');
    ctx.drawImage(cropState.image, sx, sy, sw, sh, 0, 0, sw, sh);

    const origExt = cropState.filename.slice(cropState.filename.lastIndexOf('.'));
    const mimeType = _cropMimeForExt(origExt);
    const outExt = _cropExtForMime(mimeType);
    const engineId = currentEngineId;
    const filename = cropState.filename;

    out.toBlob(function(blob) {
        if (!blob) {
            showToast('<span class="icon icon-cancel"></span> Не удалось обрезать фото', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('photo', blob, `cropped${outExt}`);
        apiFetch(`/api/engine/${engineId}/photos/${encodeURIComponent(filename)}`, { method: 'PUT', body: formData })
            .then(r => r.json())
            .then(result => {
                if (result.error) {
                    showToast('<span class="icon icon-cancel"></span> ' + result.error, 'error');
                    return;
                }
                closeCropModal();
                photoCacheBust = Date.now();
                return apiFetch(`/api/engine/${engineId}/photos`).then(r => r.json());
            })
            .then(photos => {
                if (!photos) return;
                currentPhotos = photos;
                renderDetailContent();
                showToast('<span class="icon icon-check-circle"></span> Фото обрезано', 'success');
            })
            .catch(e => showToast('<span class="icon icon-cancel"></span> Ошибка: ' + e.message, 'error'));
    }, mimeType, 0.92);
}

document.addEventListener('DOMContentLoaded', function() {
    const stage = document.getElementById('cropStage');
    const selection = document.getElementById('cropSelection');
    if (!stage || !selection) return;

    stage.addEventListener('pointerdown', function(e) {
        // Клик по canvas вне текущей рамки — начинаем рисовать новую рамку
        // с этой точки в любом направлении (см. режим 'new' в _cropPointerMove).
        if (e.target !== stage && e.target.id !== 'cropCanvas') return;
        _cropPointerDown(e, 'new');
    });
    selection.addEventListener('pointerdown', function(e) {
        const handle = e.target.dataset && e.target.dataset.handle;
        _cropPointerDown(e, handle || 'move');
    });
});


// ===== РЕЖИМЫ РАБОТЫ (инлайн-редактирование в карточке, без модалки) =====
function addModeRowInline() {
    if (!currentEngineData) return;
    // Сначала считываем то, что уже напечатано в DOM (включая другие,
    // ещё не сохранённые строки) — иначе renderDetailContent() ниже
    // перерисует таблицу из currentEngineData.modes "как было до этого
    // клика", и всё введённое в предыдущих строках молча потеряется.
    currentEngineData.modes = collectModeRowsFromDom();
    currentEngineData.modes.push({ frequency: '', power: '', voltage: '', connection_type: '', current: '', rpm: '' });
    renderDetailContent();

    setTimeout(() => {
        const tbody = document.getElementById('modesDisplayBody');
        const lastRow = tbody && tbody.lastElementChild;
        if (lastRow) {
            lastRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Переиспользуем ту же подсветку, что и у новой строки работ
            // (см. .work-row-flash в style.css) — визуально это одна и та
            // же "новая строка только что добавлена", просто в другой таблице.
            lastRow.classList.add('work-row-flash');
            setTimeout(() => lastRow.classList.remove('work-row-flash'), 2000);
        }
    }, 100);
}

function removeModeRowInline(idx) {
    if (!currentEngineData) return;
    // В отличие от "Произведённых работ" тут не нужен confirm() для уже
    // существующих строк: пока не нажата "Сохранить", ничего не
    // отправляется на сервер — удаление строки просто убирает её из
    // текущего (несохранённого) редактируемого списка. Синхронизация с
    // DOM здесь по той же причине, что и в addModeRowInline — иначе
    // правки в ДРУГИХ строках потерялись бы при перерисовке.
    currentEngineData.modes = collectModeRowsFromDom();
    if (!currentEngineData.modes[idx]) return;
    currentEngineData.modes.splice(idx, 1);
    renderDetailContent();
}

// ===== ФОТО МОДАЛКА =====
function openPhotoModalWithNav(src) {
    const index = currentPhotos.findIndex(p => p.path === src);
    if (index !== -1) {
        currentPhotoIndex = index;
    }
    openPhotoModal();
}

function openPhotoModal() {
    const modal = document.getElementById('photoModal');
    const img = document.getElementById('modalImage');
    
    if (currentPhotos.length > 0 && currentPhotoIndex < currentPhotos.length) {
        // ?v=photoCacheBust — тот же приём, что и у миниатюр в галерее
        // (см. renderDetailContent/.gallery-thumb). Раньше здесь был путь
        // без cache-bust — после обрезки миниатюра обновлялась (она ЕСТЬ
        // с ?v=...), а увеличенный просмотр по клику на неё мог получить
        // старую версию файла прямо из кэша браузера по тому же "голому"
        // URL (см. также Cache-Control в app.py:get_photo).
        img.src = `${authPhotoUrl(currentPhotos[currentPhotoIndex].path)}?v=${photoCacheBust}`;
    }
    updatePhotoNavButtons();
    
    modal.classList.add('active');
    document.body.classList.add('modal-open');
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.classList.remove('active');
        _syncModalOpenState();
    }
}

function updatePhotoNavButtons() {
    const counter = document.getElementById('photoCounter');
    const prevBtn = document.getElementById('photoPrevBtn');
    const nextBtn = document.getElementById('photoNextBtn');
    if (counter) {
        counter.textContent = `${currentPhotoIndex + 1} / ${currentPhotos.length}`;
    }
    if (prevBtn) {
        prevBtn.classList.toggle('hidden', currentPhotoIndex <= 0);
    }
    if (nextBtn) {
        nextBtn.classList.toggle('hidden', currentPhotoIndex >= currentPhotos.length - 1);
    }
}

function navigatePhotoModal(direction) {
    if (!currentPhotos || currentPhotos.length === 0) return;
    const newIndex = currentPhotoIndex + direction;
    if (newIndex < 0 || newIndex >= currentPhotos.length) {
        showToast('<span class="icon icon-warning"></span> Фото больше нет', 'warning');
        return;
    }
    currentPhotoIndex = newIndex;
    
    const img = document.getElementById('modalImage');
    if (img) {
        img.src = `${authPhotoUrl(currentPhotos[currentPhotoIndex].path)}?v=${photoCacheBust}`;
    }
    updatePhotoNavButtons();
}


// ===== ЗАКРЫТИЕ ПО КЛИКУ =====

// Клик "вне модалки" ниже проверяется по e.target события click — но при
// ресайзе за угол (#detailModal .modal-content { resize: both } —
// см. style.css) mousedown стартует на ручке внутри карточки, а mouseup
// в момент завершения перетаскивания может оказаться уже над затемнённым
// фоном за пределами карточки: click-событие получает target снаружи,
// и старая проверка (!modalContent.contains(e.target)) ошибочно считает
// это кликом вне модалки и закрывает карточку. Тот же баг сработал бы и
// при обычном выделении текста, если отпустить кнопку мыши за пределами
// карточки. Чиним, запоминая, где реально был mousedown: если жест начался
// внутри карточки — не закрываем её, независимо от того, где палец/курсор
// оказался в момент отпускания кнопки.
let detailMouseDownInside = false;
document.addEventListener('mousedown', function(e) {
    const detailModal = document.getElementById('detailModal');
    if (detailModal && detailModal.classList.contains('active')) {
        const modalContent = detailModal.querySelector('.modal-content');
        detailMouseDownInside = !!(modalContent && modalContent.contains(e.target));
    }
}, true);

document.addEventListener('DOMContentLoaded', function() {
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
        photoModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closePhotoModal();
                e.stopPropagation();
            }
        });
    }

    const ADD_FORM_AUTOCOMPLETE_FIELDS = {
        f_purpose: 'purpose', f_workshop: 'workshop', f_location: 'location',
        f_engine_type: 'engine_type', f_manufacturer: 'manufacturer', f_serial_number: 'serial_number',
        f_bearing_front: 'bearing_front', f_bearing_rear: 'bearing_rear', f_shaft_diameter: 'shaft_diameter',
        f_protection_class: 'protection_class', f_mounting_type: 'mounting_type',
        f_temp_sensor: 'temp_sensor', f_encoder: 'encoder', f_cooling: 'cooling'
    };
    Object.entries(ADD_FORM_AUTOCOMPLETE_FIELDS).forEach(([id, field]) => {
        attachFieldAutocomplete(document.getElementById(id), field);
    });
    
    updateExportButton();
});

document.addEventListener('click', function(e) {
    const photoModal = document.getElementById('photoModal');
    if (photoModal && photoModal.classList.contains('active')) {
        return;
    }
    for (const nestedId of ['photoAddModal', 'photoCropModal']) {
        const nested = document.getElementById(nestedId);
        if (nested && nested.classList.contains('active')) return;
    }
    
    const detailModal = document.getElementById('detailModal');
    if (detailModal && detailModal.classList.contains('active')) {
        const modalContent = detailModal.querySelector('.modal-content');
        if (modalContent && !modalContent.contains(e.target) && !detailMouseDownInside) {
            if (e.target.closest('.clickable-row')) return;
            if (e.target.closest('.equipment-card')) return;
            
            if (window.closeTimeout) {
                clearTimeout(window.closeTimeout);
            }
            window.closeTimeout = setTimeout(function() {
                closeDetail();
            }, 200);
        }
    }
}, true);


