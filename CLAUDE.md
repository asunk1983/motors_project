# Инструкции для проекта Motors

## 🚨 Главные правила разработки
- **Только Single HTML / Vanilla JS:** Весь интерфейс строится на стандартном ES6+ без веб-фреймворков (React/Vue).
- **Отображение данных:** Используй исключительно ТАБЛИЦЫ (`<table>`). Не предлагай карточки (cards) или сетки блоков — пользователь явно предпочитает компактный табличный вид.
- **Ограничения верстки:** Экран должен влезать в `100vh` без появления глобальной полосы прокрутки (no page scrollbar). Все внутренние списки оборачивай в `overflow-y: auto`.
- **Именование фото:** Каноническая схема файлов фото: `ID{engine_id}_{n}.{ext}`. Не меняй этот формат!
- **Генерация ID:** Для новых двигателей используется функция `_next_free_id()` (поиск дыр в последовательности), а не стандартный AUTOINCREMENT.
- **Пути:** Все пути к файлам и БД импортируются **строго из `config/settings.py`** (абсолютные пути от `BASE_DIR`). Запрещено использовать относительные текстовые строки типа `'photos/'` или `'engine_data.db'`.

## 🛠 Команды разработки и тестирования
- **Запуск тестов:** `c:\motors_project\.venv\Scripts\python.exe -m pytest`
- **Запуск только репозиториев:** `c:\motors_project\.venv\Scripts\python.exe -m pytest tests/test_repositories/`
- **Запуск E2E тестов:** `c:\motors_project\.venv\Scripts\python.exe -m pytest tests/e2e/`

## 📁 Структура проекта
- `app.py` — Точка входа Flask.
- `routes/` — Flask Blueprints (10 штук).
- `modules/` — Бизнес-логика (db, auth, backup_system, engine_parser, photo_manager).
- `repositories/` — Слои доступа к БД (`engine_repo.py`, `mode_repo.py`, `work_repo.py`).
- `static/js/` — Фронтенд-модули (`catalog.js`, `engineCard.js`, `locationTree.js`, `search.js` и др.).
- `config/settings.py` — Единый источник конфигурации.



## Обязательный протокол завершения ответа (CRITICAL RULE)
Перед тем как вывести ФИНАЛЬНЫЙ ответ пользователю и перейти в режим ожидания:
1. Выполни команду Bash: `curl -d "Claude завершил шаг!" ntfy.sh/motors_claude_3216`
2. В САМОЙ ПОСЛЕДНЕЙ строчке своего ответа ОБЯЗАТЕЛЬНО напиши текст:
   "📲 Уведомление отправлено в ntfy"
