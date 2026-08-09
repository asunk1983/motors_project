"""Repository-слой: SQL-доступ к SQLite.

Каждый репозиторий принимает sqlite3.Connection (или использует
db_connection()) и содержит ТОЛЬКО SQL-запросы — никакой бизнес-логики.
Бизнес-логика живёт в services/.
"""
