"""Сервисный слой: бизнес-логика.

Services оркестрируют repository + внешние модули (parser, photo_manager,
backup). Принимают sqlite3.Connection как аргумент (dependency injection),
что делает их тестируемыми с in-memory SQLite.
"""
