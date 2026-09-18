"""Русские описания unit/route-тестов для живого вывода `pytest -v`.

Зачем: при прогоне `pytest -v` рядом с каждым тестом хочется видеть, что именно
он проверяет, а не только английское имя. Для e2e это уже сделано через
`@pytest.mark.scn(...)` и `docs/e2e_test_results.md`; здесь тот же принцип,
но результат выводится прямо в консоль (см. хуки в tests/conftest.py).

Откуда берётся описание (по убыванию приоритета):

1. `@pytest.mark.scn("текст")` — тот же маркер, что в e2e. Явное описание
   для любого теста, удобно для новых и нестандартных случаев.
2. Docstring: первая непустая строка docstring теста, иначе — docstring класса
   теста. Ничего не дублируется: текст docstring и есть описание.
3. Автогенерация из имени теста (`_describe_from_name`) — чтобы описание было
   у КАЖДОГО теста, без правки 600+ существующих тестов руками.
   Словарь терминов ниже — русификация токенов имени (`test_delete_not_found`
   -> «Удаление: не найдено»). Если формулировка не нравится — добавьте
   тесту docstring или маркер `scn`, они приоритетнее.

Модуль ничего не печатает сам: он только считает текст, печать — в conftest.
"""
import re

# Маркер описания — тот же, что используется в tests/e2e (pytest.mark.scn).
MARKER = "scn"

# Кэш автогенерированных описаний в пределах процесса (имён немного, но
# pytest_runtest_makereport вызывается на каждый отчёт setup/call/teardown).
_NAME_CACHE = {}

# ---------------------------------------------------------------------------
# Словари русификации имён тестов
# ---------------------------------------------------------------------------

# Фразы: проверяются до пословного перевода (ключ — срез токенов через "_").
PHRASES = {
    "not_found": "не найдено",
    "not_exists": "не существует",
    "by_id": "по id",
    "by_filename": "по имени файла",
    "by_entity_type": "по типу сущности",
    "by_entity_id": "по id сущности",
    "by_date_range": "по диапазону дат",
    "by_actor": "по автору",
    "by_equipment": "по оборудованию",
    "in_use": "используется",
    "in_old_row": "в старой строке",
    "old_row": "старая строка",
    "no_actor": "без автора",
    "no_log": "не пишется в журнал",
    "writes_nothing": "ничего не пишет",
    "written_nothing": "не пишется",
    "writes_null": "пишет NULL",
    "display_name": "ФИО",
    "gets_null": "получает NULL",
    "set_both": "заполняет оба",
    "sets_both": "заполняет оба",
    "updates_both": "обновляет оба",
    "on_delete": "при удалении",
    "on_create": "при создании",
    "on_update": "при обновлении",
    "takes_effect_for_tokens": "действует на выданные токены",
    "only_changed": "только изменённые",
    "same_values": "те же значения",
    "as_is": "как есть",
    "as_string": "как строку",
    "as_is_int": "как целое",
    "without_number": "без номера",
    "without_designation": "без обозначения",
    "without_actor": "без автора",
    "without_folder": "без папки",
    "with_actor": "с автором",
    "with_data": "с данными",
    "with_token": "с токеном",
    "with_details": "с деталями",
    "with_extension": "с расширением",
    "with_threads": "с потоками",
    "keys_iterable": "перебор ключей",
    "get_by_username": "получение по логину",
    "list_by_equipment": "список по оборудованию",
    "root_or_descendants": "корень или потомки",
    "delete_photos_from_disk": "удаление фото с диска",
    "delete_cascades_modes_and_works": "каскадно удаляет режимы и работы",
    "empty_cells_are_empty_strings": "пустые ячейки — пустые строки",
    "keeps_other_fields": "остальные поля сохраняются",
    "keeps_display_name": "сохраняет ФИО",
    "keeps_raw": "сохраняет исходное значение",
    "bumps_last_edit": "обновляет время последней правки",
    # составные сущности (порядок слов как в русском, а не в английском)
    "equipment_type": "тип оборудования",
    "equipment_types": "типы оборудования",
    "equipment_placement": "размещение оборудования",
    "equipment_placements": "размещения оборудования",
    "equipment_repo": "репозиторий оборудования",
    "type_attributes": "атрибуты типа",
    "last_edited_by": "автор последней правки",
    "last_edited_at": "время последней правки",
    "last_edited": "последняя правка",
    "not_owner": "чужое фото",
    "only_own": "только свои",
    "bad_ext": "недопустимое расширение",
    "sorts_and_filters": "сортировка и фильтры",
    "sorts_paths": "сортировка путей",
    "filters_by_engine_id": "фильтр по id двигателя",
    "empty_is_one": "пустая папка — индекс 1",
    "max_plus_one": "максимум + 1",
    "continues_index": "нумерация продолжается",
    "errors_do_not_stop": "ошибки не останавливают обработку",
    "non_admin": "не-админ",
    "forbidden_non_admin": "запрещено не-админу",
    "no_ids": "без ids",
    "too_many_ids": "слишком много ids",
    "too_many": "слишком много",
    "wrong_equipment": "чужое оборудование",
    "with_modes_works": "с режимами и работами",
    "small_photo": "маленькое фото",
    "not": "не",
    "relation": "связь",
    "relations": "связи",
    "empty_arr": "пустой массив",
    "empty_sheet": "пустой лист",
    "empty_cells": "пустые ячейки",
    "after_existing": "после существующих",
    "roundtrip": "запись и чтение",
    "empty_designation": "пустое обозначение",
    "changed_at": "changed_at",
    "iso_format": "в формате ISO",
    "min_stock_qty": "минимального остатка на складе",
    "empty_body": "пустое тело запроса",
    "password_short": "слишком короткий пароль",
    "blank_name": "пустое имя",
    "round_trip": "полный цикл",
    "runs_cleanly": "выполняется без ошибок",
    "executors_round_trip": "исполнители: полный цикл",
    "initiators_round_trip": "инициаторы: полный цикл",
    "set_executors_replaces_existing": "установка исполнителей заменяет существующих",
    "location_counts_returns_dict": "подсчёт по местам возвращает словарь",
    "children_root_only": "дочерние узлы только у корня",
    "list_sorted_roots_first": "список: сначала корневые узлы",
    "subtree_ids": "ids поддерева",
    "breadcrumb_text": "текст хлебных крошек",
    "move_to_other_branch_ok_and_audit": "перенос в другую ветку — успешно и с записью в журнал",
    "move_into_subtree_rejected": "перенос внутрь своего поддерева — отклонено",
    "delete_with_children_rejected": "удаление узла с потомками — отклонено",
    "delete_leaf_ok": "удаление листа — успешно",
    "replace_all_deletes_old_inserts_new": "старые строки удаляются, новые вставляются",
    "traversal_not_exposed": "защита от path traversal — файл недоступен",
    "me_success": "GET /me — данные пользователя получены",
    "me_not_authenticated_401": "GET /me без токена — 401",
    "search_returns_matches": "поиск возвращает совпадения",
    "create_position_and_workshop_optional": "создание: должность и цех необязательны",
    "create_blank_name_400": "создание с пустым именем — 400",
    "logout_invalid_token_still_works": "выход с невалидным токеном всё равно успешен",
    "login_empty_body_401": "вход с пустым телом запроса — 401",
    "change_password_short_400": "смена пароля: слишком короткий пароль — 400",
    "patch_min_stock_qty_success": "частичное обновление минимального остатка — успешно",
    "patch_missing_min_stock_qty_400": "частичное обновление без минимального остатка — 400",
    "patch_invalid_min_stock_qty_400": "частичное обновление с некорректным минимальным остатком — 400",
    "ensure_updated_at_column_runs_cleanly": "миграция колонки updated_at выполняется без ошибок",
    "ensure_no_users_fk_runs_cleanly": "миграция убирает внешний ключ на пользователей без ошибок",
    "create_defaults": "создание со значениями по умолчанию",
    "get_location_counts_returns_dict": "подсчёт по местам возвращает словарь",
    "parser_error_reported": "ошибка парсера возвращается клиенту",
    "parser_exception_reported": "исключение парсера возвращается клиенту",
    "clear_success": "очистка БД — успешно",
    "clear_db_error_500": "очистка БД: ошибка БД — 500",
    "create_ticket_service_error_400": "создание заявки: ошибка сервиса — 400",
    "exception_returns_empty_200": "исключение — пустой список, 200",
    "exception_500": "исключение — 500",
    "create_requires_problem": "создание требует описания проблемы",
    "create_with_executor": "создание с исполнителем",
    "update_empty_problem_rejected": "обновление с пустым описанием проблемы — отклонено",
    "standard_date": "стандартная дата 2024-01-15 -> 15.01.2024",
    "partial_date": "неполная дата возвращается как есть",
    "load_corrupted_file": "загрузка повреждённого файла",
    "save_creates_directory": "сохранение создаёт каталог",
    "save_ensure_ascii_false": "кириллица сохраняется без \\u-экранирования",
    "patch_negative_min_stock_qty_400": "частичное обновление: отрицательный остаток — 400",
    "set_type_attributes_not_a_list_400": "установка атрибутов типа: передан не список — 400",
    "get_show_in_list_attributes_success": "получение атрибутов с признаком показа в списке",
    "appends_lines": "добавляет строки в конец файла",
    "prints_to_stdout": "пишет в stdout",
    "simple_filename": "простое имя файла",
    "special_chars_replaced": "специальные символы заменяются",
    "multiple_dots": "несколько точек в имени",
    "subtree_ids": "id узлов поддерева",
    "verify_empty_hash_false": "Пустой хеш — проверка не проходит",
    "verify_none_hash_false": "Хеш None — проверка не проходит",
    "duplicate_username_raises": "Дубликат логина — IntegrityError",
    "get_unknown_none": "Несуществующий логин или id — None",
    "delete_unknown": "Удаление несуществующего — False",
    "fallback_to_username": "Без сотрудника берётся логин",
    "from_crew": "ФИО берётся из привязанного сотрудника",
    "resolve_display_name": "Вычисление ФИО по crew_id",
    # частые короткие имена
    "another_date": "другая дата",
    "empty_string": "пустая строка",
    "invalid_format": "некорректный формат",
    "empty_token_none": "пустой токен — None",
    "revoke_all": "отзыв всех сессий",
    "empty_folder": "пустая папка",
    "in_another_location": "в другом месте",
    "count_by_status": "подсчёт по статусу",
    "create_mode": "создание режима",
    "create_work": "создание работы",
    "success_import": "успешный импорт",
    "list_all_empty": "список пуст",
    "from_header": "из заголовка Authorization",
    "from_query": "из параметров запроса",
    "admin_empty": "админ: пустой журнал — 200 и пустой ответ",
    "admin_distinct_sorted_list": "админ: уникальные типы — 200 и отсортированный список",
    "location_node_id_resolved_to_breadcrumb": "location_node_id превращается в подпись из хлебных крошек",
    "unknown_location_keeps_raw": "неизвестный узел — исходное значение без подмены",
    "list_equipment_types_empty": "пустой список типов оборудования",
    "get_equipment_types_empty": "пустой список типов оборудования",
    "get_stock_summary_empty": "пустая сводка по складу",
    "old_row_none_writes_nothing": "при отсутствии старой строки запись не создаётся",
    "unchanged_fields_written_nothing": "неизменённые поля в журнал не пишутся",
    "none_to_value_written": "переход NULL в значение фиксируется",
    "value_to_none_written": "переход значения в NULL фиксируется",
    "multiple_fields_multiple_rows": "несколько изменённых полей — отдельная строка на каждое",
    "actor_display_name_written": "автор (ФИО) записывается",
    "actor_fallback_to_username": "без ФИО берётся логин",
    "all_entries_and_total": "все записи и общее количество",
    "create_ticket_requires_user_401": "создание заявки — требуется авторизация",
    "create_ticket_location_required_400": "создание заявки: место обязательно — 400",
    "update_ticket_validation_400": "обновление заявки: ошибка валидации — 400",
    "location_counts_success": "подсчёт по местам — успешно",
    "get_stock_summary_success": "сводка по складу — успешно",
    "empty_filename_with_engine_id": "пустое имя файла при заданном id двигателя",
    "none_filename_with_engine_id": "имя файла None при заданном id двигателя",
}

# Описания, зависящие от класса теста (когда одинаковое имя теста значит разное).
CLASS_PHRASES = {
    ("TestIsValidIsoDate", "test_empty"): "Пустая строка — невалидная дата",
    ("TestDiskPaths", "test_empty"): "Пустой список путей",
    ("TestGetEnginePhotos", "test_empty"): "Пустой список фото",
    ("TestListByEquipment", "test_empty"): "Пустой список размещений",
    ("TestSearchCrew", "test_empty_query"): "Пустой поисковый запрос",
    ("TestListTickets", "test_empty"): "Пустой список заявок",
}

# Готовые описания для имён, которые автопереводом звучат криво.
# Ключ — остаток имени теста без префикса `test_`.
NAME_PHRASES = {
    "timestamps_filled": "Колонки created_at и last_edit заполняются",
    "resolve_direct": "resolve_display_name по crew_id и None",
    "missing_crew_record_fallback": "Нет записи сотрудника — берётся логин",
    "update_crew_id_unbind": "Отвязка crew_id (None)",
    "verify_correct": "Корректный пароль — проверка проходит",
    "hash_is_salted": "Хеш с солью: одинаковые пароли дают разные хеши",
    "hash_no_plaintext": "В хеше нет пароля в открытом виде",
    "deterministic": "Хеш токена детерминирован",
    "sha256_hex": "Хеш — 64 hex-символа SHA-256",
    "differs": "Разные токены дают разные хеши",
    "urlsafe": "Токен URL-safe: только A-Za-z0-9_-",
    "length_43": "Длина токена — 43 символа (32 байта base64url)",
    "unique": "Два сгенерированных токена не совпадают",
    "db_user_into_tokens": "Токен пользователя БД сохраняется в tokens.json",
    "with_expiration": "Токен со сроком действия",
    "expired_token_none": "Истёкший токен — None",
    "issue_and_validate_file_user": "Файловый пользователь: выдача и проверка токена",
    "workshop_without_number": "Цех без номера",
    "empty_cells_are_empty_strings": "Пустые ячейки — пустые строки",
    "stops_at_first_empty_frequency": "Разбор останавливается на первой пустой частоте",
    "empty_arr_returns_empty": "Пустой массив — пустой результат",
    "text_in_frequency_returned_as_is": "Текст в поле частоты возвращается как есть",
    "empty_sheet_returns_error": "Пустой лист — ошибка",
    "replace_changes_extension": "Замена меняет расширение файла",
    "saves_file": "Файл сохраняется",
    "retries_on_error": "Повтор при ошибке сохранения",
    "upload_after_existing_continues_index": "Загрузка после существующих продолжает нумерацию",
    "get_by_id_roundtrip": "Запись и чтение по id (round-trip)",
    "empty_designation_never_conflicts": "Пустое обозначение не конфликтует",
    "empty_designation_in_same_location": "Пустое обозначение в том же месте",
    "get_relations_empty": "Пустой список связей инцидент-оборудование",
    "add_relation": "Добавление связи инцидент-оборудование",
    "add_relation_duplicate_ignored": "Повторная связь игнорируется",
    "remove_relation": "Удаление связи",
    "admin_distinct_sorted": "Админ: уникальные типы отсортированы",
    "order_by_changed_at_desc": "Сортировка по changed_at по убыванию",
    "field_absent_in_old_row_skipped": "Поле, которого нет в старой строке, пропускается",
    "changed_at_is_iso_format": "changed_at пишется в ISO-формате",
    "does_not_commit_itself": "Функция не коммитит транзакцию",
    "does_not_leak_other_equipment": "Возвращаются только размещения своего оборудования",
    "compare_is_str_insensitive_to_types": "Сравнение: число и строка с тем же значением не считаются изменением",
    "verify_wrong": "Проверка неверного пароля — отказ",
    "valid_ok": "Валидный токен — доступ разрешён",
    "valid_db_token": "Валидный токен пользователя из БД",
    "valid_date": "Корректная ISO-дата",
    "non_date_string": "Не дата, а строка — возвращается как есть",
    "revoke_one_keeps_others": "Отзыв одной сессии не трогает остальные",
    "success_on_valid_xlsx": "Успешный разбор корректного xlsx",
    "upload_skips_bad_ext": "Загрузка пропускает файлы с недопустимым расширением",
    "removes_only_own": "Удаляются только свои файлы",
    "errors_do_not_stop": "Ошибки на одном файле не останавливают обработку остальных",
    "create_requires_at_least_one_initiator": "Создание требует хотя бы одного инициатора",
    "create_auto_adds_closed_at_on_rejected": "При отказе время закрытия проставляется автоматически",
    "create_resolved_keeps_explicit_closed_at": "Статус «решена» сохраняет явно заданное время закрытия",
    "update_status_to_resolved_fills_closed_at": "Переход в «решена» заполняет время закрытия",
    "update_back_to_in_progress_clears_closed_at": "Возврат в «в работе» очищает время закрытия",
    "update_explicit_closed_at_clear": "Явная очистка времени закрытия",
    "add_link_duplicate_ignored": "Повторное добавление связи игнорируется",
    "delete_placement_wrong_equipment_404": "Удаление размещения чужого оборудования — 404",
    "export_no_ids_400": "Экспорт без ids — 400",
    "export_too_many_ids_400": "Экспорт: слишком много ids — 400",
    "create_equipment_type_forbidden_non_admin": "Создание типа оборудования — запрещено не-админу",
    "delete_equipment_type_forbidden_non_admin": "Удаление типа оборудования — запрещено не-админу",
    "set_type_attributes_forbidden_non_admin": "Установка атрибутов типа — запрещено не-админу",
    "delete_ticket_forbidden_non_admin": "Удаление заявки — запрещено не-админу",
    "delete_equipment_forbidden_non_admin": "Удаление оборудования — запрещено не-админу",
    "list_tickets_filters_passed": "Список заявок с фильтрами",
    "empty_journal": "Пустой журнал",
    "ensure_last_edited_columns_no_race_with_8_threads": "Колонки последней правки: миграция без гонки при 8 потоках",
    "update_logs_only_changed_fields": "В журнал пишутся только реально изменившиеся поля",
    "update_same_values_no_log": "Обновление теми же значениями в журнал не пишется",
    "create_with_actor_sets_both": "Создание с автором заполняет обе колонки правки",
    "update_with_actor_updates_both": "Обновление с автором обновляет обе колонки правки",
    "create_without_actor_by_null_at_set": "Создание без автора: автор NULL, время заполнено",
    "update_without_actor_overwrites_null": "Обновление без автора перезаписывает автора на NULL",
}

# Глаголы и первые токены имени -> отглагольное существительное (тема теста).
ACTIONS = {
    "get": "Получение",
    "create": "Создание",
    "delete": "Удаление",
    "update": "Обновление",
    "list": "Список",
    "add": "Добавление",
    "edit": "Изменение",
    "change": "Смена",
    "set": "Установка",
    "replace": "Замена",
    "upload": "Загрузка",
    "move": "Перенос",
    "link": "Привязка",
    "unlink": "Отвязка",
    "remove": "Удаление",
    "export": "Экспорт",
    "import": "Импорт",
    "revoke": "Отзыв сессий",
    "verify": "Проверка",
    "validate": "Валидация",
    "parse": "Разбор",
    "restore": "Восстановление",
    "save": "Сохранение",
    "load": "Загрузка",
    "count": "Подсчёт",
    "search": "Поиск",
    "find": "Поиск",
    "filter": "Фильтр",
    "normalize": "Нормализация",
    "patch": "Частичное обновление",
    "get_me": "Текущий пользователь",
    "format": "Форматирование",
    "is": "Проверка",
    "are": "Проверка",
    "does": "Проверка",
    "has": "Проверка",
    "no": "Отсутствие",
    "without": "Без",
    "all": "Все",
    "empty": "Пустой",
    "none": "Пустое значение",
    "null": "Пустое значение",
    "invalid": "Некорректные данные",
    "missing": "Отсутствие данных",
    "nonexistent": "Несуществующий объект",
    "cannot": "Запрет",
}

# Служебные/статусные токены.
TERMS = {
    "success": "успешно", "ok": "успешно", "passed": "пройдено",
    "fails": "падает", "failed": "падает", "raises": "ошибка", "raise": "ошибка",
    "rejected": "отклонено", "forbidden": "запрещено", "denied": "доступ запрещён",
    "accepted": "принимается", "allowed": "разрешено", "returns": "возвращает",
    "returned": "возвращено", "result": "результат", "true": "да", "false": "нет",
    "none": "пустое", "null": "NULL", "unknown": "неизвестный",
    "existing": "существующий", "duplicate": "дубликат", "duplicates": "дубликаты",
    "conflict": "конфликт", "insensitive": "без учёта регистра", "case": "регистр",
    "trim": "обрезка пробелов", "trimmed": "обрезано", "empty": "пустое",
    "whitespace": "пробелы", "changed": "изменено", "unchanged": "без изменений",
    "written": "записано", "writes": "пишет", "nothing": "ничего",
    "clears": "очищает", "cleared": "очищено", "sorted": "отсортировано",
    "sort": "сортировка", "order": "порядок", "counted": "посчитано",
    "counts": "считает", "skipped": "пропускается", "skips": "пропускает",
    "added": "добавлено", "removed": "удалено", "keeps": "сохраняет",
    "kept": "сохранено", "preserved": "сохранено", "incremented": "увеличено",
    "increments": "увеличивает", "bumps": "обновляет", "updates": "обновляет",
    "overwrites": "перезаписывает", "idempotent": "идемпотентно",
    "atomic": "атомарно", "isolated": "изолировано", "isolates": "изолирует",
    "isolate": "изоляция", "race": "гонка", "concurrent": "параллельные",
    "threads": "потоки", "delegates": "делегирует", "requires": "требует",
    "require": "требование", "prevents": "не допускает", "protects": "защищает",
    "ensure": "проверка", "ensures": "обеспечивает", "guards": "защита",
    "guard": "защита", "allows": "разрешает", "ignores": "игнорирует",
    "reports": "сообщает", "reported": "сообщено", "checks": "проверяет",
    "check": "проверка", "detects": "определяет", "detected": "определено",
    "resolves": "вычисляет", "resolved": "вычислено", "generates": "генерирует",
    "generated": "сгенерировано", "loads": "загружает", "loaded": "загружено",
    "parses": "разбирает", "parsed": "разобрано", "extracts": "извлекает",
    "extracted": "извлечено", "fills": "заполняет", "filled": "заполнено",
    "uses": "использует", "used": "используется", "applies": "применяет",
    "linked": "привязан", "unlinked": "отвязан", "referenced": "есть ссылки",
    "usable": "рабочий", "lost": "потеряно", "deep": "глубокий",
    "nested": "вложенный", "explicit": "явный", "implicit": "неявный",
    "direct": "напрямую", "raw": "исходное значение", "label": "подпись",
    "breadcrumb": "хлебные крошки", "definition": "определение",
    "definitions": "определения", "attributes": "атрибуты",
    "attribute": "атрибут", "inheritance": "наследование",
    "inherits": "наследует", "overrides": "перекрывает", "child": "потомок",
    "parent": "родитель", "own": "свой", "only": "только",
    "effective": "действующие", "assigned": "назначенные",
    "legacy": "устаревшие", "dropped": "удалены", "minimal": "минимальный",
    "unlimited": "без ограничений", "multiple": "несколько", "both": "оба",
    "same": "тот же", "other": "другой", "different": "другой",
    "another": "другой", "plus": "и", "limit": "лимит", "offset": "смещение",
    "range": "диапазон", "qty": "количество", "min": "минимум",
    "max": "максимум", "total": "итого", "next": "следующий",
    "last": "последний", "first": "первый", "old": "старое", "new": "новое",
    "value": "значение", "values": "значения", "data": "данные",
    "error": "ошибка", "errors": "ошибки", "fail": "сбой", "failure": "отказ",
    "folder": "папка", "path": "путь", "paths": "пути", "disk": "диск",
    "stored": "хранится", "storage": "хранилище", "rollback": "откат",
    "transaction": "транзакция", "commit": "коммит", "commits": "коммитит",
    "itself": "сам", "schema": "схема", "migrations": "миграции",
    "migration": "миграция", "columns": "столбцы", "column": "столбец",
    "index": "индекс", "indexes": "индексы", "query": "запрос", "sql": "SQL",
    "json": "JSON", "xlsx": "xlsx", "csv": "CSV", "api": "API", "http": "HTTP",
    "url": "URL", "version": "версия", "public": "публичный",
    "fallback": "запасной вариант", "default": "по умолчанию", "reset": "сброс",
    "cache": "кеш", "cached": "кешировано", "invalidates": "сбрасывает",
    "invalidate": "сброс", "config": "конфиг", "settings": "настройки",
    "log": "лог", "logs": "пишет в лог", "logging": "логирование",
    # сущности предметной области
    "audit": "журнал изменений", "entry": "запись", "entries": "записи",
    "row": "строка", "rows": "строки", "entity": "сущность",
    "entity_type": "тип сущности", "actor": "автор", "author": "автор",
    "stats": "статистика", "growth": "рост", "summary": "сводка",
    "details": "детали", "sections": "разделы", "pagination": "пагинация",
    "page": "страница", "pages": "страницы", "suggestions": "подсказки",
    "checksums": "контрольные суммы", "hash": "хеш", "token": "токен",
    "tokens": "токены", "session": "сессия", "sessions": "сессии",
    "password": "пароль", "username": "логин", "role": "роль", "roles": "роли",
    "superadmin": "суперадмин", "admin": "админ", "blocked": "заблокирован",
    "self": "себя", "own_role": "своя роль", "login": "вход", "logout": "выход",
    "engine": "двигатель", "engines": "двигатели", "engine_id": "id двигателя",
    "equipment": "оборудование", "equipment_id": "id оборудования",
    "placement": "размещение", "placements": "размещения",
    "designation": "обозначение", "designation_id": "id обозначения",
    "location": "место", "locations": "места", "location_id": "id места",
    "node": "узел", "node_id": "id узла", "tree": "дерево",
    "descendants": "потомки", "ancestors": "предки", "root": "корень",
    "move_and_delete": "перенос и удаление", "photo": "фото", "photos": "фото",
    "photo_count": "число фото", "photos_folder": "папка фото",
    "filename": "имя файла", "file": "файл", "files": "файлы",
    "extension": "расширение", "media": "медиа", "ticket": "заявка",
    "tickets": "заявки", "ticket_id": "id заявки", "incident": "инцидент",
    "incidents": "инциденты", "incident_id": "id инцидента",
    "incident_ticket": "заявка инцидента", "work": "работа", "works": "работы",
    "failure": "отказ", "failures": "отказы", "mode": "режим", "modes": "режимы",
    "frequency": "частота", "power": "мощность", "voltage": "напряжение",
    "current": "ток", "rpm": "обороты", "isolation": "изоляция",
    "inspection": "осмотр", "signature": "подпись", "crew": "сотрудник",
    "crew_id": "id сотрудника", "user": "пользователь", "users": "пользователи",
    "user_id": "id пользователя", "backup": "резервная копия",
    "backups": "резервные копии", "stock": "склад", "date": "дата",
    "dates": "даты", "name": "имя", "names": "имена", "type": "тип",
    "types": "типы", "type_id": "id типа", "field": "поле", "fields": "поля",
    "priority": "приоритет", "status": "статус", "statuses": "статусы",
    "changelog": "журнал изменений", "wishlist": "пожелания",
    "wish": "пожелание", "knowledge": "база знаний", "article": "статья",
    "articles": "статьи", "cause": "причина", "causes": "причины",
    "sensor": "датчик", "sensors": "датчики", "catalog": "каталог",
    "tab": "вкладка", "tabs": "вкладки", "overlay": "оверлей",
    "selector": "селектор", "header": "заголовок", "token_url": "URL с токеном",
    "chunk": "чанк", "batch": "пакет", "import": "импорт", "export": "экспорт",
    "archive": "архив", "zip": "zip", "mode_select": "выбор режима",
    # слова, которые чаще всего оставались латиницей
    "owner": "владелец", "least": "минимум", "ignored": "игнорируется",
    "one": "один", "two": "два", "three": "три", "zero": "ноль",
    "string": "строка", "str": "строка", "back": "обратно",
    "progress": "работа", "auto": "автоматически", "adds": "добавляет",
    "valid": "корректный", "wrong": "неверный", "bad": "неверный",
    "non": "не", "cyrillic": "кириллица", "registry": "справочник",
    "filters": "фильтры", "validation": "валидация", "closed": "закрыто",
    "the": "", "do": "", "of": "",
    # термины из имён тестов location/incident/crew
    "children": "потомки", "roots": "корневые узлы", "subtree": "поддерево",
    "leaf": "лист", "branch": "ветка", "text": "текст", "short": "короткий",
    "still": "всё равно", "optional": "необязательный", "position": "должность",
    "workshop": "цех", "matches": "совпадения", "dict": "словарь",
    "fk": "внешний ключ", "runs": "выполняется", "cleanly": "без ошибок",
    "updated": "обновлено", "exposed": "раскрыт", "saves": "сохраняет",
    "retries": "повторяет", "changes": "меняет", "stops": "останавливается",
    "sheet": "лист", "cells": "ячейки", "arr": "массив",
    "issue": "выдача", "expiration": "срок действия", "urlsafe": "URL-safe",
    "length": "длина", "unique": "уникальность", "hex": "hex",
    "correct": "корректный", "salted": "с солью", "plaintext": "открытый текст",
    "deterministic": "детерминированность", "distinct": "уникальные",
    "desc": "по убыванию", "record": "запись", "unbind": "отвязка",
    "absent": "отсутствует", "defaults": "значения по умолчанию",
    "executors": "исполнители", "initiators": "инициаторы",
    "replaces": "заменяет", "free": "свободный", "required": "обязательный",
    "negative": "отрицательный", "problem": "описание проблемы",
    "executor": "исполнитель", "service": "сервис", "exception": "исключение",
    "parser": "парсер", "clear": "очистка", "standard": "стандартный",
    "partial": "частичная", "corrupted": "повреждённый", "creates": "создаёт",
    "directory": "каталог", "ascii": "ASCII", "show": "признак показа",
    "a": "", "reported": "сообщается", "in_l": "",
    "header": "заголовок", "query": "запрос", "body": "тело запроса",
    "another": "другой", "dots": "точек",
}

# Родительный падеж: после предлогов (по/без/из/для/с/от) и после действия
# («Удаление двигателя», «Создание типа оборудования»).
GENITIVE = {
    "id": "id", "entity": "сущности", "entity_type": "типа сущности",
    "filename": "имени файла", "file": "файла", "folder": "папки",
    "actor": "автора", "author": "автора", "date": "даты",
    "equipment": "оборудования", "equipment_type": "типа оборудования",
    "engine": "двигателя", "engine_id": "id двигателя",
    "user": "пользователя", "users": "пользователей", "username": "логина",
    "role": "роли", "token": "токена", "tokens": "токенов", "session": "сессии",
    "ticket": "заявки", "tickets": "заявок", "incident": "инцидента",
    "location": "места", "locations": "мест", "crew": "сотрудника",
    "photo": "фото", "photos": "фото", "type": "типа", "types": "типов",
    "name": "имени", "names": "имён", "extension": "расширения",
    "field": "поля", "fields": "полей", "value": "значения",
    "column": "столбца", "columns": "столбцов", "row": "строки",
    "rows": "строк", "entry": "записи", "entries": "записей",
    "values": "значений", "errors": "ошибок", "threads": "потоков",
    "range": "диапазона", "access": "доступа", "permission": "прав",
    "role_change": "смены роли", "designation": "обозначения",
    "placement": "размещения", "placements": "размещений",
    "mode": "режима", "modes": "режимов", "work": "работы", "works": "работ",
    "attribute": "атрибута", "attributes": "атрибутов", "data": "данных",
    "backup": "резервной копии", "backups": "резервных копий",
    "status": "статуса", "statuses": "статусов", "ids": "id",
    "definition": "определения", "definitions": "определений",
    "journal": "журнала", "link": "связи", "relation": "связи",
    "priority": "приоритета", "cache": "кеша", "index": "индекса",
    "password": "пароля", "crew_id": "id сотрудника", "username": "логина",
    "user_id": "id пользователя", "ticket_id": "id заявки",
    "incident_id": "id инцидента", "location_id": "id места",
    "asset": "объекта", "stock": "склада",
    "header": "заголовка", "query": "запроса", "body": "тела запроса",
}

# Маркеры «случая»: по первому из них имя делится на «действие: случай».
CASE_MARKERS = {
    "not", "invalid", "empty", "none", "null", "missing", "nonexistent",
    "forbidden", "rejected", "success", "ok", "unknown", "duplicate",
    "conflict", "raises", "fail", "failed", "fails", "true", "false",
    "cannot", "no", "without", "wrong", "expired", "revoked", "corrupted",
    "extra", "too", "already", "closed", "only", "same", "other", "different",
    "deep", "nested", "explicit", "unlimited", "minimal", "twice", "again",
    "first", "second", "third", "default", "fallback", "partial", "full",
    "zero", "one", "two", "three", "many", "multiple", "all", "both",
}

PREPOSITIONS = {"по", "без", "из", "для", "с", "от", "у", "к", "на", "в"}

# Союзы/предлоги внутри имени теста (сшивают части описания).
CONNECTORS = {
    "by": "по", "without": "без", "with": "с", "and": "и", "to": "в",
    "in": "в", "on": "в", "at": "в", "for": "для", "from": "из", "of": "из",
    "into": "в", "or": "или", "when": "когда", "as": "как",
}

# Предлоги, после которых слово идёт в родительном/дательном падеже.
_GENITIVE_AFTER = {"по", "без", "для", "из", "от", "с"}


def describe_from_name(name):
    """Собирает русское описание из имени теста.

    `test_get_by_id_not_found` -> «Получение по id — не найдено».
    Первый токен берётся из ACTIONS (действие/тема), остальные — из TERMS,
    после предлогов — из GENITIVE. Незнакомые токены остаются как есть.
    """
    cached = _NAME_CACHE.get(name)
    if cached is not None:
        return cached

    tokens = [t for t in name.split("_") if t]
    if tokens[:1] == ["test"]:  # сам префикс test_ — не часть описания
        tokens.pop(0)
    # ведущая нумерация сценария (test_01_login, test_03b_x) — тоже не часть
    while tokens and re.fullmatch(r"\d+[a-z]?", tokens[0]):
        tokens.pop(0)

    full = "_".join(tokens)
    preset = NAME_PHRASES.get(full) or PHRASES.get(full)
    if preset:  # готовое описание целиком
        _NAME_CACHE[name] = preset[0].upper() + preset[1:]
        return _NAME_CACHE[name]

    split = next((k for k, t in enumerate(tokens) if t in CASE_MARKERS), None)
    if split:  # «действие — случай»
        action = " ".join(_translate(tokens[:split], actions=True))
        case = " ".join(_translate(tokens[split:]))
        if action and case:
            sep = " " if case.split(" ")[0] in PREPOSITIONS else " — "
            text = action + sep + case
        else:
            text = action or case
    else:
        text = " ".join(_translate(tokens, actions=True))

    text = re.sub(r"\s+", " ", text).strip(" .")
    if text:
        text = text[0].upper() + text[1:]
    _NAME_CACHE[name] = text
    return text


def _translate(tokens, actions=False):
    """Русифицирует срез токенов имени, подставляя слова из словарей."""
    words = []
    expect_genitive = False
    i = 0
    while i < len(tokens):
        phrase = None
        for size in (4, 3, 2):  # сначала фразы подлиннее
            key = "_".join(tokens[i:i + size])
            if key in PHRASES:
                phrase = PHRASES[key]
                i += size
                break
        if phrase is not None:
            words.append(phrase)
            expect_genitive = False
            continue

        tok = tokens[i]
        i += 1

        if re.fullmatch(r"\d{3}", tok):  # HTTP-коды 400/401/403/404/500
            words.append("HTTP " + tok)
        elif actions and not words and tok in ACTIONS:
            words.append(ACTIONS[tok])
            expect_genitive = True  # «Удаление двигателя»
            continue
        elif tok in CONNECTORS:
            word = CONNECTORS[tok]
            words.append(word)
            expect_genitive = word in _GENITIVE_AFTER
            continue
        else:
            word = None
            if expect_genitive:
                word = GENITIVE.get(tok)
            if word is None:
                word = TERMS.get(tok)
            if word is None and tok in ACTIONS:
                word = ACTIONS[tok].lower()
            if word is None:
                word = tok
            if actions and not words:
                word = word[0].upper() + word[1:]
            words.append(word)
        expect_genitive = False
    return words


def _first_line(doc):
    """Первая непустая строка docstring — по соглашению краткое описание."""
    if not doc:
        return ""
    for line in doc.strip().splitlines():
        line = " ".join(line.split())
        if line:
            return line.rstrip(".")
    return ""


def describe(item):
    """Описание теста по приоритету: класс+имя -> маркер scn -> docstring -> имя."""
    name = item.name.split("[")[0]
    cls = getattr(item, "cls", None)
    if cls is not None:
        preset = CLASS_PHRASES.get((cls.__name__, name))
        if preset:
            return preset
    text = _from_marker(item)
    if not text:
        func = getattr(item, "function", None)
        text = _russian_docstring(func.__doc__ if func is not None else "")
    if not text:
        text = _russian_docstring(cls.__doc__ if cls is not None else "")
    if not text:
        text = describe_from_name(name)
    return text


def _russian_docstring(doc):
    """Первая строка docstring, если она на русском.

    Английский docstring описанием не считаем (нужно русское описание) —
    тогда сработает автогенерация из имени теста.
    """
    text = _first_line(doc)
    if text and not re.search(r"[А-Яа-яЁё]", text):
        return ""
    return text


def _from_marker(item):
    """Текст из @pytest.mark.scn(...), если он задан (как в e2e)."""
    marker = item.get_closest_marker(MARKER)
    if marker is not None and marker.args:
        return str(marker.args[0]).strip()
    return ""

