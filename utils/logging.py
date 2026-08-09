"""Утилита логирования: log_message() с потокобезопасной записью в файл и консоль.

Вынесена из app.py. Используется маршрутами импорта и другими модулями,
которые нуждаются в простом логировании без настройки logging-хендлеров.
"""
import os
import threading
from datetime import datetime

from config.settings import LOG_FILE

log_lock = threading.Lock()


def log_message(message):
    """Записать сообщение в лог-файл и вывести в консоль.

    Потокобезопасно (использует log_lock). Обрабатывает UnicodeEncodeError
    для Windows-консоли (cp1251).
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    with log_lock:
        # print в консоль Windows может упасть на кириллице (cp1252) —
        # ловим ошибку кодировки, чтобы не ронять приложение при логировании.
        try:
            print(log_entry.strip())
        except UnicodeEncodeError:
            try:
                print(log_entry.strip().encode('cp1251', 'replace').decode('cp1251'))
            except Exception:
                pass
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
