# E2E test results

Браузер: Google Chrome (channel="chrome"), headless=False. Данные тестовые (создаются и удаляются каждым тестом).

| Группа | Сценарий | Статус | Детали при провале |
| --- | --- | --- | --- |
| test_01_auth | 1. Вход в систему | PASSED | Console errors/warnings: [error] Failed to load resource: the server responded with a status of 404 (NOT FOUND) |
| test_01_auth | 2. Выход (logout) | PASSED |  |
| test_01_auth | 3. Проверка токена при загрузке (валидный) | PASSED | Page errors: Unexpected token '>>>' |
| test_01_auth | 3. Проверка токена при загрузке (невалидный) | PASSED | Console errors/warnings: [error] Failed to load resource: the server responded with a status of 401 (UNAUTHORIZED) Network >=400: GET http://localhost:5000/api/auth/me -> 401 Page errors: Unexpected token '>>>' |
| test_01_auth | 4. Редирект на вход при 401 от apiFetch | PASSED | Console errors/warnings: [error] Failed to load resource: the server responded with a status of 401 (UNAUTHORIZED) Network >=400: GET http://localhost:5000/api/auth/me -> 401 |
| test_01_auth | 5. Вкладки Импорт/Админ видны для админа | PASSED |  |
| test_01_auth | 5. Вкладки Импорт/Админ скрыты для пользователя | PASSED |  |
| test_01_auth | 6. Список пользователей | PASSED |  |
| test_01_auth | 7. Создание пользователя | PASSED |  |
| test_01_auth | 8. Смена пароля | PASSED |  |
| test_01_auth | 9. Сброс всех сессий пользователя | PASSED |  |
| test_01_auth | 10. Удаление пользователя | PASSED |  |
| test_02_catalog | 11. Просмотр каталога при входе | PASSED |  |
| test_02_catalog | 12. Быстрый поиск | PASSED |  |
| test_02_catalog | 13. Выбор поля поиска | PASSED |  |
| test_02_catalog | 14. Сортировка через выпадающий список | PASSED |  |
| test_02_catalog | 14b. Сортировка по клику на заголовке колонки | PASSED |  |
| test_02_catalog | 15. Переключение вида (таблица/карточки) | PASSED |  |
| test_02_catalog | 16. Пагинация | PASSED |  |
| test_02_catalog | 17. Выбор двигателей для экспорта | PASSED |  |
| test_02_catalog | 18. Выбор всех | PASSED |  |
| test_02_catalog | 19. Очистка выбора | PASSED |  |
| test_02_catalog | 21. Обновление каталога (кнопка Refresh) | PASSED |  |
| test_03_add_engine | 22. Открытие вкладки «Добавить» | PASSED |  |
| test_03_add_engine | 23. Заполнение формы | PASSED |  |
| test_03_add_engine | 24. Добавление ряда режима работы | PASSED |  |
| test_03_add_engine | 25. Добавление записи о работе | PASSED |  |
| test_03_add_engine | 26. Выбор фото | PASSED |  |
| test_03_add_engine | 28. Удаление непривязанного фото | PASSED |  |
| test_03_add_engine | 29. Очистка формы | PASSED |  |
| test_03_add_engine | 30. Кнопка «Применить» (создание двигателя) | PASSED |  |
| test_03_add_engine | 31. Сохранение через кнопку формы (submit) | PASSED |  |
| test_04_detail | 32. Открытие детальной карточки | PASSED |  |
| test_04_detail | 33. Просмотр характеристик | PASSED |  |
| test_04_detail | 34. Редактирование и сохранение характеристик | PASSED |  |
| test_04_detail | 35. Отмена редактирования | PASSED |  |
| test_04_detail | 36. Переключение режимов просмотра/редактирования | PASSED |  |
| test_04_detail | 37. Добавление и сохранение режима работы | PASSED |  |
| test_04_detail | 38. Добавление и сохранение работы | PASSED |  |
| test_04_detail | 40. Навигация между двигателями | PASSED |  |
| test_04_detail | 41. Печать карточки | PASSED |  |
| test_04_detail | 42. Закрытие карточки | PASSED |  |
| test_05_photos | 43. Добавление фото в карточку | FAILED | page = <Page url='http://localhost:5000/'> test_engine = {'location': 'Тестовое место E2E_TESTS', 'engine_type': 'Электродвигатель', 'serial_number': 'E2E-2136e4a3', 'manufacturer': 'ТестПроизв', ...} tmp_path = WindowsPath('C:/Users/KIPIA/AppData/Local/Temp/pytest-of-KIPIA/pytes |
| test_05_photos | 44. Удаление фото | FAILED | page = <Page url='http://localhost:5000/'> test_engine = {'location': 'Тестовое место E2E_TESTS', 'engine_type': 'Электродвигатель', 'serial_number': 'E2E-130e7cdf', 'manufacturer': 'ТестПроизв', ...} tmp_path = WindowsPath('C:/Users/KIPIA/AppData/Local/Temp/pytest-of-KIPIA/pytes |
| test_05_photos | 46. Просмотр фото в модальном окне | FAILED | page = <Page url='http://localhost:5000/'> test_engine = {'location': 'Тестовое место E2E_TESTS', 'engine_type': 'Электродвигатель', 'serial_number': 'E2E-67cca3c3', 'manufacturer': 'ТестПроизв', ...} tmp_path = WindowsPath('C:/Users/KIPIA/AppData/Local/Temp/pytest-of-KIPIA/pytes |
| test_05_photos | 47. Навигация между фото в модальном окне | FAILED | page = <Page url='http://localhost:5000/'> test_engine = {'location': 'Тестовое место E2E_TESTS', 'engine_type': 'Электродвигатель', 'serial_number': 'E2E-d536d0d3', 'manufacturer': 'ТестПроизв', ...} tmp_path = WindowsPath('C:/Users/KIPIA/AppData/Local/Temp/pytest-of-KIPIA/pytes |
| test_05_photos | 48. Закрытие модального окна фото (Escape) | FAILED | page = <Page url='http://localhost:5000/'> test_engine = {'location': 'Тестовое место E2E_TESTS', 'engine_type': 'Электродвигатель', 'serial_number': 'E2E-099d49a6', 'manufacturer': 'ТестПроизв', ...} tmp_path = WindowsPath('C:/Users/KIPIA/AppData/Local/Temp/pytest-of-KIPIA/pytes |
| test_05_photos | 49. Автодополнение полей в редактировании | PASSED |  |
| test_06_import | 50. Переключение на вкладку «Импорт» | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("50. Переключение на вкладку «Импорт»")     def test_50_switch_import_tab(page):         """Вкладка импорта доступна и отображает информацию о файлах."""         switch_tab(page, "import")         expect(page.locato |
| test_06_import | 51. Импорт из Excel | FAILED | page = <Page url='http://localhost:5000/'> admin_api = <playwright._impl._fetch.APIRequestContext object at 0x000002033A65C8C0>      @pytest.mark.scn("51. Импорт из Excel")     def test_51_import_excel(page, admin_api):         """Импорт из Excel-файла создаёт двигатели в БД."""  |
| test_06_import | 52. Очистка БД | FAILED | page = <Page url='http://localhost:5000/'> admin_api = <playwright._impl._fetch.APIRequestContext object at 0x000002033C76CAA0>      @pytest.mark.scn("52. Очистка БД")     def test_52_clear_db(page, admin_api):         """Очистка БД удаляет все двигатели."""         # Create a te |
| test_07_search | 53. Переключение на вкладку «Поиск» | PASSED |  |
| test_07_search | 54. Добавление условия поиска | PASSED |  |
| test_07_search | 55. Выбор поля и оператора | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("55. Выбор поля и оператора")     def test_55_select_field_operator(page):         """Выбор поля меняет доступные операторы."""         switch_tab(page, "search")         # Default: first row has a text field with t |
| test_07_search | 56. Автодополнение (autocomplete) | PASSED |  |
| test_07_search | 57. Выполнение поиска | PASSED |  |
| test_07_search | 58. Очистка всех условий | PASSED |  |
| test_08_settings | 59. Переключение на вкладку «Настройки» | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("59. Переключение на вкладку «Настройки»")     def test_59_switch_settings_tab(page):         """Вкладка настроек отображается со статистикой."""         switch_tab(page, "settings")         expect(page.locator("#ta |
| test_08_settings | 60. Просмотр статистики БД | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("60. Просмотр статистики БД")     def test_60_view_db_stats(page):         """На вкладке настроек отображается количество двигателей."""         switch_tab(page, "settings")         page.wait_for_load_state("network |
| test_08_settings | 61. Просмотр статистики фото | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("61. Просмотр статистики фото")     def test_61_view_photo_stats(page):         """На вкладке настроек отображается количество фото."""         switch_tab(page, "settings")         page.wait_for_load_state("networki |
| test_08_settings | 63. Создание резервной копии | FAILED | page = <Page url='http://localhost:5000/'>      @pytest.mark.scn("63. Создание резервной копии")     def test_63_create_backup(page):         """Кнопка создания бэкапа создаёт резервную копию на сервере."""         switch_tab(page, "settings")         page.wait_for_load_state("ne |
| test_08_settings | 64. Просмотр списка резервных копий | PASSED |  |
| test_08_settings | 66. Инфо-подсказка в настройках | PASSED |  |
| test_09_backups | 67. Просмотр списка резервных копий | PASSED |  |
| test_09_backups | 68. Создание резервной копии | SKIPPED |  |
| test_09_backups | 69. Скачивание резервной копии | PASSED |  |
| test_09_backups | 71. Удаление резервной копии | PASSED |  |
| test_10_info | 72. Переключение на вкладку «Инфо» | PASSED |  |
| test_10_info | 73. Переключение подвкладок | PASSED |  |
| test_10_info | 74. Просмотр changelog | PASSED |  |
| test_10_info | 75. Добавление записи в changelog | PASSED |  |
| test_10_info | 76. Удаление записи из changelog | PASSED |  |
| test_10_info | 77. Просмотр wishlist | PASSED |  |
| test_10_info | 78. Добавление элемента в wishlist | PASSED |  |
| test_10_info | 79. Редактирование элемента wishlist (toggle done) | FAILED | page = <Page url='http://localhost:5000/'> admin_api = <playwright._impl._fetch.APIRequestContext object at 0x000002033C3619A0>      @pytest.mark.scn("79. Редактирование элемента wishlist (toggle done)")     def test_79_edit_wishlist(page, admin_api):         """Переключение чекб |
| test_10_info | 80. Удаление элемента из wishlist | PASSED |  |
| test_11_misc | 81. API статус | PASSED |  |
| test_11_misc | 82. Подсказки поискового поля (search-suggestions) | PASSED |  |
| test_11_misc | 83. URL фото с токеном | PASSED |  |
| test_11_misc | 84. Страница /test | PASSED |  |
| test_11_misc | 84b. Статус сервера после создания двигателя | PASSED |  |

**Итого:** 66 passed, 14 failed, 1 skipped
