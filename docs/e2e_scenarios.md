# E2E Сценарии тестирования — "Паспорта двигателей"

> Назначение: список пользовательских сценариев для e2e-тестирования. Каждый сценарий описывает действие человека → API-запрос → ожидаемый результат. Никаких тестов в файле нет — только список для сверки.

## Архитектура интерфейса

### Вкладки (sidebar nav, `templates/index.html`)

| Вкладка | `data-tab` | Видимость | JS-файл |
|--------|------------|-----------|---------|
| Каталог | `catalog` | всегда | `catalog.js` |
| Добавить | `add` | всегда | `exportManager.js` |
| Импорт | `import` | админ только | `importer.js` |
| Поиск | `search` | всегда | `search.js` |
| Настройки | `settings` | всегда | `backupManager.js` |
| Инфо | `info` | всегда | `backupManager.js` |
| Админ | `admin` | админ только | `auth.js` |

### Модальные окна (`templates/index.html`)

| Модаль | ID | JS-файл |
|--------|-----|---------|
| Детальная карточка | `detailModal` | `engineCard.js` |
| Добавить фото (в карточке) | `photoAddModal` | `engineCard.js` |
| Обрезка фото | `photoCropModal` | `engineCard.js` |
| Просмотр фото (фуллскрин) | `photoModal` | `engineCard.js` |
| Экран логина | `login-overlay` (динамически) | `auth.js` |

---

## Полный список роутов бэкенда

Все роуты зарегистрированы как blueprint-ы через `routes/__init__.py` → `app.py:28 register_blueprints(app)`.

| Blueprint | Метод | Путь | Тело / параметры |
|-----------|-------|------|------------------|
| auth_bp | POST | /api/auth/login | {username, password} |
| auth_bp | POST | /api/auth/logout | — |
| auth_bp | GET | /api/auth/me | — |
| auth_bp | GET | /api/admin/users | — |
| auth_bp | POST | /api/admin/users | {username, password, role} |
| auth_bp | DELETE | /api/admin/users/<user_id> | — |
| auth_bp | POST | /api/admin/users/<user_id>/password | {password} |
| auth_bp | POST | /api/admin/users/<user_id>/revoke | — |
| backup_bp | GET | /api/backup/list | — |
| backup_bp | POST | /api/backup/create | — |
| backup_bp | POST | /api/backup/inspect-upload | FormData(file) |
| backup_bp | POST | /api/backup/restore/<filename> | — |
| backup_bp | POST | /api/backup/confirm-restore | {filename} |
| backup_bp | GET | /api/backup/download/<filename> | — |
| backup_bp | POST | /api/backup/delete/<filename> | — |
| backup_bp | DELETE | /backup/<filename> | — (альтернативный, фронтенд не использует) |
| changelog_bp | GET | /api/changelog | — |
| changelog_bp | POST | /api/changelog | {text, date} |
| changelog_bp | DELETE | /api/changelog/<entry_id> | — |
| changelog_bp | GET | /api/wishlist | — |
| changelog_bp | POST | /api/wishlist | {text} |
| changelog_bp | PUT | /api/wishlist/<item_id> | {text} |
| changelog_bp | DELETE | /api/wishlist/<item_id> | — |
| engines_bp | GET | /api/engines | ?sort_by, ?sort_order, ?search_field, ?search, ?limit, ?offset |
| engines_bp | GET | /api/engine/<engine_id> | — |
| engines_bp | POST | /api/engine | {engine_data} |
| engines_bp | PUT | /api/engine/<engine_id> | {engine_data} |
| engines_bp | DELETE | /api/engine/<engine_id> | — |
| engines_bp | PUT | /api/engine/<engine_id>/modes | {modes} |
| engines_bp | PUT | /api/engine/<engine_id>/works | {works} |
| export_bp | POST | /api/engines/export | {ids} |
| import_bp | POST | /api/import-folder | — |
| import_bp | POST | /api/clear | — |
| pages_bp | GET | / | — (отдаёт index.html) |
| pages_bp | GET | /print/<engine_id> | — (отдаёт print.html) |
| pages_bp | GET | /static/<path:path> | — (статика) |
| pages_bp | GET | /test | — (служебный, фронтенд не вызывает) |
| photos_bp | GET | /api/engine/<engine_id>/photos | — |
| photos_bp | GET | /api/photos/<filename> | — |
| photos_bp | POST | /api/engine/<engine_id>/photos | FormData(photos) |
| photos_bp | DELETE | /api/engine/<engine_id>/photos/<filename> | — |
| photos_bp | PUT | /api/engine/<engine_id>/photos/<filename> | FormData(photo) |
| search_bp | GET | /api/search-suggestions | ?field, ?query |
| search_bp | POST | /api/engines/search | {conditions} |
| status_bp | GET | /api/status | — |

---

## Сценарии

### 1. Аутентификация

1. **Вход в систему** — Пользователь видит экран логина (`login-overlay`, `auth.js:85`), вводит логин и пароль в форму (`auth.js:107`) → нажимает "Войти" → `fetch('/api/auth/login', POST, auth.js:114)` → токен сохраняется в `localStorage`, экран логина скрывается (`hideLoginScreen`), вызывается `onLoggedIn()` → загружаются двигатели, статистика, changelog, wishlist; для админа — список пользователей.

2. **Выход из системы** — Пользователь нажимает кнопку "Выйти" в `auth-user-badge` (создаётся в `auth.js:162`, клик в `auth.js:171`) → `POST /api/auth/logout` (`auth.js:177`) → токен удаляется из `localStorage` (`clearAuth`), показывается экран логина.

3. **Проверка токена при загрузке страницы** — При `DOMContentLoaded` (`auth.js:183`) → если токен есть в `localStorage`, вызывается `GET /api/auth/me` через `apiFetch` (`auth.js:186`) → если токен валиден (`data.username` есть), скрывается логин и вызывается `onLoggedIn()`; иначе — `clearAuth()` + `showLoginScreen()`.

4. **Автоматический редирект на логин при 401** — Любой запрос `apiFetch`, получивший 401 (`auth.js:57`) → `clearAuth()` + `showLoginScreen()` + выбрасывается ошибка.

5. **Отображение вкладки "Админ" и "Импорт" только для админа** — После входа `applyRoleUI` (`auth.js:153`) → `importTab.style.display = isAdmin ? '' : 'none'` (скрыта по умолчанию в `index.html:24`), `adminTab.style.display = isAdmin ? '' : 'none'` (скрыта по умолчанию в `index.html:36`).

6. **Просмотр списка пользователей** — Для админа при входе вызывается `GET /api/auth/admin/users` (`auth.js:215, loadAdminUsers`) → отображается таблица с колонками: ID, Логин, Роль, Активных сессий, Создан.

7. **Создание пользователя** — В вкладке "Админ" нажимается кнопка "➕ Добавить пользователя" (`index.html:351, showAddUserForm`) → появляется форма (`index.html:353`) → ввод логина, пароля, роли → "Создать" (`auth.js:276, adminCreateUser`) → `POST /api/auth/admin/users` → список обновляется.

8. **Смена пароля пользователя** — В таблице пользователей нажимается кнопка "🔐" (`auth.js:238`) → `prompt()` ввода нового пароля (мин. 6 симв.) → `POST /api/auth/admin/users/<user_id>/password` (`auth.js:261`) → toast "Пароль изменён".

9. **Сброс всех сессий пользователя** — В таблице нажимается кнопка "🔄" (`auth.js:237`) → `POST /api/auth/admin/users/<user_id>/revoke` (`auth.js:322`) → toast "Все сессии сброшены".

10. **Удаление пользователя** — В таблице (не для админа) нажимается "🗑" (`auth.js:239`) → `confirm()` → `DELETE /api/auth/admin/users/<user_id>` (`auth.js:307`) → список обновляется.

### 2. Каталог двигателей

11. **Просмотр каталога при входе** — При загрузке `auth.js:183` и переключении на вкладку "Каталог" (`catalog.js:57`) вызывается `GET /api/engines` с параметрами сортировки и поиска (`catalog.js:66-78`) → таблица или карточки отображаются в `tableBody` / `cardWrapper`.

11. **(фрагмент)** **Просмотр каталога при входе (продолжение)** — Статистика в сайдбаре (`#totalEngines`, `#totalPhotos`, `#totalFiles`) заполняется из `GET /api/status` (вызывается в `catalog.js:6 updateStats` при загрузке `DOMContentLoaded` и при переключении на вкладку "Каталог"/"Импорт"/"Настройки").

12. **Быстрый поиск в каталоге** — Пользователь вводит текст в `#searchInput` (`index.html:63`) с debounce 350мс (`catalog.js:427`) → при вводе `loadEngines()` → `GET /api/engines?search_field=...&search=...&sort_by=...&sort_order=...` → таблица обновляется (без перезагрузки страницы).

13. **Выбор поля поиска** — Пользователь меняет `#searchFieldSelect` (`index.html:64`) → `loadEngines()` → `GET /api/engines?search_field=<value>` → результаты фильтруются по выбранному полю.

14. **Сортировка** — Пользователь меняет `#sortSelect` (`index.html:73`) или кликает на заголовок столбца (`catalog.js:99-103, onclick="sortTable('location')"`) → `loadEngines()` с новыми параметрами `?sort_by=...&sort_order=...` → таблица перерисовывается.

15. **Переключение вида (таблица / карточки)** — Клик на кнопку "📋 Таблица" / "📇 Карточки" (`index.html:83-84, onclick="toggleView('table'|'cards')"`) → `toggleView()` (`catalog.js:181`) → таблица или карточки показываются/скрываются (`.hidden`).

16. **Пагинация** — Кнопки "◀"/"▶" (`index.html:118-120`) → `prevPage()`/`nextPage()` (`catalog.js:212-218`) → локальная пагинация по `pageSize` (20); `#pageInfo` и `#pageNumber` обновляются.

17. **Выбор движителей для экспорта** — Чекбоксы в строках/карточках (`catalog.js:113-114, 142`) → `toggleEngineSelection()` (`catalog.js:237`) → кнопка "📊 Экспорт в Excel" (`index.html:88`) активируется (`updateExportButton`, `catalog.js:315`).

18. **Выбор всех** — Чекбокс "selectAll" (`index.html:97`) → `toggleSelectAll()` (`catalog.js:247`) → выбрать/снять все видимые.

19. **Снятие выбора** — Кнопка "✕ снять" (`index.html:87`) → `clearSelection()` (`catalog.js:283`) → чекбоксы сбрасываются, кнопка экспорта деактивируется.

20. **Экспорт выбранных в Excel** — Кнопка "📊 Экспорт в Excel" (`index.html:88, onclick="exportSelected()"`) → `POST /api/engines/export` (`catalog.js:344`) с `{ids: [...]}` → браузер скачивает `.xlsx` файл.

21. **Обновление каталога** — Кнопка "🔄 Обновить" (`index.html:89, onclick="refreshTable()"`) → `currentPage = 1`, `loadEngines()` → `GET /api/engines`.

### 3. Добавление двигателя (вкладка "Добавить")

22. **Открытие вкладки "Добавить"** — Клик на `tab-btn[data-tab="add"]` (`index.html:21-23`) → `switchTab('add')` (`catalog.js:48`) → отображается `#tab-add` (`index.html:126`).

23. **Заполнение формы двигателя** — Поля формы `#engineForm` (`index.html:129`): `f_location`, `f_engine_type`, `f_serial_number`, `f_manufacturer`, `f_purpose`, `f_workshop`, `f_protection_class`, `f_mounting_type`, `f_shaft_diameter`, `f_bearing_front`, `f_bearing_rear`, `f_temp_sensor`, `f_encoder`, `f_cooling`, `f_note`.

24. **Добавление режима работы** — Кнопка "➕ Добавить режим" (`index.html:197, onclick="addModeRow()"`) → в `#modesBody` (`index.html:202`) добавляется строка с полями: Частота, Мощность, Напряжение, Тип подключения, Ток, Обороты.

25. **Добавление записи о работе** — Кнопка "➕ Добавить запись" (`index.html:210, onclick="addWorkRow()"`) → в `#worksBody` (`index.html:215`) добавляется строка с полями: №, Дата, Вид работ, Сопротивление изоляции, Осмотр, ФИО.

26. **Выбор фото** — Кнопка "➕ Выбрать фото" (файловый ввод `f_photos`, `index.html:223-226`) → выбранные файлы отображаются в `#photosPreview` (`exportManager.js:43, renderPhotosPreview`).

27. **Обрезка фото перед загрузкой** — Кнопка "✂️" на превью фото (`exportManager.js:16, onclick="openCropModal('pending', ${idx})"`) → модаль `photoCropModal` → "✂️ Обрезать и применить" (`engineCard.js:818, applyCrop`) → локальная замена File в `pendingPhotoFiles` (без запроса на сервер).

28. **Удаление фото из списка перед загрузкой** — Кнопка "✕" на превью (`exportManager.js:17, onclick="removePendingPhoto(${idx})"`) → файл удаляется из `pendingPhotoFiles`.

29. **Очистка формы** — Кнопка "Очистить" (`index.html:233, onclick="resetForm()"`) → форма сбрасывается, фото очищаются, добавляются пустые строки режима и работы (`exportManager.js:57, resetForm`).

30. **Применить (сохранить как черновик)** — Кнопка "✅ Применить" (`index.html:234, onclick="saveEngine()"`) → `POST /api/engine` (`exportManager.js:123`) → после создания: загрузка pending-фото `POST /api/engine/<id>/photos` (`uploadPendingPhotos`, `exportManager.js:32`), сброс формы, загрузка каталога, переключение на вкладку "Каталог".

31. **Сохранить (через submit формы)** — Нажатие Enter в форме или кнопка "💾 Сохранить" (`index.html:235, type="submit"`) → `engineForm submit` (`exportManager.js:67`) → `saveEngine()` → `POST /api/engine` (см. пункт 30).

### 4. Детальная карточка двигателя (модал `detailModal`)

32. **Открытие карточки** — Клик на строку таблицы (`catalog.js:112, onclick="showDetail(${e.id})"`) или карточку (`catalog.js:141, onclick="showDetail(${e.id})"`) → `GET /api/engine/<id>` + `GET /api/engine/<id>/photos` параллельно (`engineCard.js:35-37`) → модал `detailModal` (`index.html:396`) отображается с данными двигателя.

33. **Просмотр характеристик** — В режиме "Просмотр" (`detailMode = 'view'`) отображаются характеристики двигателя в read-only виде (`engineCard.js:142, DETAIL_CHAR_FIELDS`).

34. **Редактирование характеристик** — Кнопка "✏️" в toolbar карточки (`engineCard.js:83, onclick="toggleDetailMode('edit')"`) → форма с инпутами появляется → ввод значений → "💾 Сохранить" (`engineCard.js:122, onclick="saveDetailEdit()"`) → `PUT /api/engine/<id>` (`engineCard.js:441`) → toast "Изменения сохранены", карточка и каталог обновляются.

35. **Отмена редактирования** — Кнопка "✕ Отмена" (`engineCard.js:123, onclick="cancelDetailEdit()"`) → `detailEditMode = false`, `renderDetailContent()` — изменения не сохраняются.

36. **Переключение режима просмотра/редактирования** — Кнопки "👁 Просмотр" / "✏️ Редактирование" (`engineCard.js:82-83, onclick="toggleDetailMode('view'|'edit')"`).

37. **Добавление/удаление режимов работы (в редактировании)** — "➕ Добавить режим" (`engineCard.js:155`) → строка в таблице режимов → "💾 Сохранить режимы" (`engineCard.js:178, onclick="saveModesInline()"`) → `PUT /api/engine/<id>/modes` (`engineCard.js:979`) → toast "Режимы работы сохранены".

38. **Добавление/удаление работ (в редактировании)** — "➕ Добавить" (`engineCard.js:204`) → строка в таблице работ → "💾 Сохранить работы" (`engineCard.js:228, onclick="saveWorksOnly()"`) → `PUT /api/engine/<id>/works` (`engineCard.js:385`) → toast "Работы сохранены", каталог и статистика обновляются.

39. **Удаление двигателя из карточки** — Кнопка "🗑 Удалить" в toolbar (`engineCard.js:88, onclick="deleteCurrentEngine()"`) → `confirm()` → `DELETE /api/engine/<id>` (`engineCard.js:485`) → `closeDetail()`, `loadEngines()`, `updateStats()`, toast "Двигатель удалён".

40. **Навигация между двумя двигателями** — Кнопки "◀ Предыдущий" / "Следующий ▶" (`engineCard.js:85-86, onclick="navigateEngine(-1|1)"`) → анимация slide-out → загрузка следующего/предыдущего двигателя через `showDetail()` (`catalog.js:373, navigateEngine`). Также через клавиши ← → на клавиатуре (`engines.js:140-170`), когда открыта `detailModal`.

41. **Печать карточки** — Кнопка "🖨 Печать" (`engineCard.js:87, onclick="printEngineCard()"`) → `window.open('/print/<id>', '_blank')` (`engineCard.js:473`) → новая вкладка с `templates/print.html` → браузерский диалог печати.

41. **(фрагмент)** **Печать карточки (продолжение)** — Страница печати (`routes/pages.py:15, GET /print/<engine_id>`) загружает `print.js`, который запрашивает данные двигателя через API (`print.js:145`).

42. **Закрытие карточки** — Кнопка "×" в header (`index.html:400, onclick="closeDetail()"`) или клавиша Escape (`engines.js:177`) → анимация slide-out → модал скрывается.

### 5. Фотографии

43. **Добавление фото в карточку двигателя** — В режиме редактирования кнопка "➕ Добавить" в секции "Фото" (`engineCard.js:95, onclick="openPhotoAddModal()"`) → модал `photoAddModal` (`index.html:409`) → выбор файлов через `detailPhotoInput` (`index.html:418`) → "💾 Загрузить" (`index.html:423, onclick="submitDetailPhotoAdd()"`) → `POST /api/engine/<id>/photos` (`engineCard.js:580`) → toast с кол-вом загруженных, карточка обновляется.

44. **Удаление фото** — Кнопка "−" на миниатюре фото в карточке (`engineCard.js:109, onclick="removeDetailPhoto(filename)"`) → `confirm()` → `DELETE /api/engine/<id>/photos/<filename>` (`engineCard.js:605`) → фото исчезает из галереи.

45. **Обрезка существующего фото** — Кнопка "✂️" на миниатюре (`engineCard.js:108, onclick="openCropModal('existing', filename, path)"`) → модал `photoCropModal` с canvas → "✂️ Обрезать и применить" (`engineCard.js:904, _applyCropExisting`) → `PUT /api/engine/<id>/photos/<filename>` (FormData) → фото обновляется на сервере.

46. **Просмотр фото в модальном окне** — Клик на миниатуру фото (`engineCard.js:107, onclick="openPhotoModalWithNav(path)"`) → модал `photoModal` (`index.html:459`) с `<img>` → навигация ← → через кнопки или клавиши (`engines.js:144-155, navigatePhotoModal`).

47. **Навигация по фото в модальном окне** — Кнопки "◀"/"▶" (`index.html:462-464, onclick="navigatePhotoModal(-1|1)"`) или клавиши ← →.

48. **Закрытие модального окна фото** — Кнопка "×" (`index.html:460, onclick="closePhotoModal()"`) или Escape (`engines.js:173`).

49. **Автозаполнение полей при редактировании** — При входе в режим редактирования (`engineCard.js:273, detailEditMode = true`) → `attachFieldAutocomplete()` на все инпуты характеристик (`engineCard.js:273`) → по фокусу/вводу `GET /api/search-suggestions?field=<field>&query=<query>` с debounce 200мс (`engines.js:77-89`).

### 6. Импорт (вкладка "Импорт")

50. **Переход на вкладку "Импорт"** — Клик на `tab-btn[data-tab="import"]` (`index.html:24-26`) → `switchTab('import')` → `updateStats()` → отображается `#tab-import` (`index.html:242`).

51. **Импорт из Excel** — Кнопка "📥 Импортировать все файлы" (`index.html:262, onclick="importFiles()"`) → `apiFetch('/api/import-folder', POST)` (`importer.js:18`) → прогресс-бар (`importProgress`), лог (`progressLog`) → после завершения toast с `data.message`, обновление каталога и статистики.

52. **Очистка БД** — Кнопка "🗑 Очистить БД" (`index.html:263, onclick="clearAll()"`) → `apiFetch('/api/clear', POST)` (`importer.js:48`) → toast "База данных и фото очищены", каталог и статистика обновляются.

### 7. Поиск (вкладка "Поиск")

53. **Переход на вкладку "Поиск"** — Клик на `tab-btn[data-tab="search"]` (`index.html:27-29`).

54. **Добавление строки поиска** — Кнопка "➕ Добавить условие" (`index.html:284, id="addSearchBtn"`) → `addSearchRow()` (`search.js:103`) → новая строка с: полем (select), оператором (select), значением (input) + второе значение для "между".

55. **Выбор поля и оператора** — В строке поиска `select.search-field-select` (`search.js:114-116`) → при смене поля `applyFieldType()` (`search.js:160`) → `input` переходит в `type="number"` для числовых полей, операторы меняются (text: содержит/равно/начинается/заканчивается; number: +больше/меньше/между).

56. **Автодополнение значений полей поиска** — `attachSuggestDropdown(valueInput, () => fieldSelect.value)` (`search.js:210`) → `GET /api/search-suggestions` с debounce 200мс.

57. **Выполнение поиска** — Кнопка "🔍 Найти" (`index.html:286, id="searchBtn"`) или Enter внутри `.search-container` (`search.js:95-99`) → `executeSearch()` (`search.js:225`) → `POST /api/engines/search` с `{conditions: [...]}` → результаты в `#searchResults` (`index.html:292`) в виде таблицы с колонками по найденным полям.

58. **Очистка всех условий поиска** — Кнопка "🗑 Очистить всё" (`index.html:285, id="clearSearchBtn"`) → `clearAllSearch()` (`search.js:214`) → все строки удаляются, добавляется одна пустая, результаты очищаются.

### 8. Настройки (вкладка "Настройки")

59. **Переход на вкладку "Настройки"** — Клик на `tab-btn[data-tab="settings"]` (`index.html:30-31`) → `switchTab('settings')` → `loadSettings()` (`catalog.js:21`) → `updateStats()` + `loadBackupsList()`.

60. **Просмотр статистики БД** — Секция "База данных" (`index.html:303-308`): количество записей (`#settingsRecords`), размер БД (`#settingsDbSize`) — из `GET /api/status` (`catalog.js:6`).

61. **Просмотр статистики фото** — Секция "Фото" (`index.html:310-313`): `#settingsPhotos`, папка `photos/`.

62. **Очистка БД из настроек** — Кнопка "🗑 Очистить БД" (`index.html:307, onclick="clearAll()"`) → `POST /api/clear` (`importer.js:48`).

63. **Создание резервной копии** — Кнопка "📦 Создать резервную копию" (`index.html:320, onclick="createBackup()"`) → `POST /api/backup/create` (`backupManager.js:74`) → toast с результатом.

64. **Просмотр списка бэкапов** — `#backupsList` (`index.html:322`) заполняется из `GET /api/backup/list` (`backupManager.js:26, loadBackupsList`).

65. **Восстановление из загруженного файла** — Файловый ввод `#backupUploadInput` (`index.html:328, accept=".zip"`) → выбор файла → нажатие кнопки "📤 Выбрать файл резервной копии" → `POST /api/backup/inspect-upload` (`backupManager.js:149`) → проверка manifest + чексумм → модаль подтверждения восстановления.

66. **Сведения о резервных копиях** — Текст в `settings-hint` (`index.html:318`): "Только вручную — автоматических бэкапов нет."

### 9. Резервные копии (в секции "Настройки" и отдельные модалы)

67. **Просмотр списка бэкапов** — `GET /api/backup/list` (`backupManager.js:26`) → таблица бэкапов с: имя файла, размер, дата создания, количество двигателей, количество фото.

68. **Создание бэкапа** — Кнопка "📦 Создать резервную копию" (`index.html:320`) → `POST /api/backup/create` (`backupManager.js:74`) → бэкап появляется в списке.

69. **Скачивание бэкапа** — Кнопка скачивания в списке бэкапов → `window.open('/api/backup/download/<filename>', '_blank')` (`api.js:166, downloadBackup`) → браузер скачивает zip.

70. **Восстановление из списка бэкапов** — Кнопка "Восстановить" в списке → `POST /api/backup/restore/<filename>` (`backupManager.js:123, restoreBackup`) → модаль "Подтверждение восстановления" → "Подтвердить" → `POST /api/backup/confirm-restore` (`backupManager.js:171`).

71. **Удаление бэкапа** — Кнопка "🗑" в списке → `POST /api/backup/delete/<filename>` (`backupManager.js:108`) → бэкап удаляется из списка.

### 10. Инфо: лог изменений и пожелания (вкладка "Инфо")

72. **Переключение на вкладку "Инфо"** — Клик на `tab-btn[data-tab="info"]` (`index.html:33-34`) → `switchTab('info')` → `loadInfoTab()` (`catalog.js:60`).

73. **Переключение субвкладок** — Кнопки "📋 Лог изменений" / "💡 Пожелания" (`index.html:372-374, onclick="switchInfoSubtab('changelog'|'wishlist')"`).

74. **Просмотр лога изменений** — `GET /api/changelog` (`backupManager.js:216, apiFetch('/api/changelog')`) → список записей в `#changelogList` (`index.html:382`).

75. **Добавление записи в лог** — Поля: дата (`#changelogDateInput`, `index.html:378`), текст (`#changelogTextInput`, `index.html:379`) → кнопка "➕ Добавить запись" (`index.html:380, onclick="addChangelogEntry()"`) → `POST /api/changelog` (`backupManager.js:278`) → запись появляется в списке.

76. **Удаление записи из лога** — Кнопка "🗑" в записи changelog → `DELETE /api/changelog/<id>` (`backupManager.js:298`) → запись удаляется.

77. **Просмотр пожеланий** — `GET /api/wishlist` (`backupManager.js:312`) → список в `#wishlistList` (`index.html:390`).

78. **Добавление пожелания** — Поле ввода (`#wishlistTextInput`, `index.html:387`) → кнопка "➕ Добавить" (`index.html:388, onclick="addWishlistItem()"`) → `POST /api/wishlist` (`backupManager.js:344`) → пожелание появляется в списке.

78. **(фрагмент)** **Добавление пожелания (продолжение)** — `PUT /api/wishlist/<id>` (`backupManager.js:362`) при редактировании, `DELETE /api/wishlist/<id>` (`backupManager.js:383`) при удалении.

79. **Редактирование пожелания** — (inline-редактирование в списке) → `PUT /api/wishlist/<id>` (`backupManager.js:362`).

80. **Удаление пожелания** — Кнопка удаления в списке → `DELETE /api/wishlist/<id>` (`backupManager.js:383`).

### 11. Специальные / вспомогательные

81. **Статус сервера** — `GET /api/status` (`status.py:14`) — возвращает `engine_count`, `photos_count`, `files_in_folder`, `db_size_label`. Вызывается при загрузке (`catalog.js:6, updateStats`), при переключении на "Каталог"/"Импорт"/"Настройки".

82. **Подсказки поисковых полей** — `GET /api/search-suggestions?field=<field>&query=<query>` (`search.py:12`) — используется в `engines.js:81` (автодополнение в форме добавления и карточке двигателя) и `search.js:81` (автодополнение в расширенном поиске).

83. **Получение фото (прямой URL)** — `GET /api/photos/<filename>` (`photos.py:51`) — используется в `<img src="/api/photos/...">` для отображения миниатюр и фото в модальном окне.

84. **Служебная страница /test** — `GET /test` (`pages.py:31`) — не вызывается фронтендом, служебный роут.
