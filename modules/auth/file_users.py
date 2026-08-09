"""Файловые пользователи (config/users.json) и токены (config/tokens.json).

Вынесено из auth.py. Используется db_users.py (fallback) и tokens.py.
"""
import os
import json
from datetime import datetime

from modules.auth.hashing import hash_password
from config.settings import CONFIG_DIR, FILE_USERS, FILE_TOKENS

FILE_USER_ID_OFFSET = 1000000000


def _ensure_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


def _migrate_negative_file_user_ids(users):
    """ПРАВИЛО: id файлового пользователя не может быть отрицательным.

    Актуальная схема (_next_file_user_id) всегда выдаёт id >= FILE_USER_ID_OFFSET
    (положительное число), чтобы не пересекаться с id из БД (автоинкремент,
    начиная с 1) и проходить через Flask-маршруты <int:user_id> — конвертер
    <int:> матчит только \\d+ и НЕ матчит отрицательные числа.

    Отрицательные id могли остаться в users.json от более старой версии кода.
    Эта функция вызывается при каждой загрузке файла и один раз молча чинит
    такие записи — переприсваивает им следующий свободный id по офсетной схеме.
    Токены не теряются: tokens.json ссылается на пользователя по username.
    """
    negative = [u for u in users if isinstance(u.get('id'), int) and u['id'] < 0]
    if not negative:
        return users
    positive_ids = [u['id'] for u in users if isinstance(u.get('id'), int) and u['id'] >= 0]
    next_id = max(positive_ids + [FILE_USER_ID_OFFSET - 1]) + 1
    if next_id < FILE_USER_ID_OFFSET:
        next_id = FILE_USER_ID_OFFSET
    for u in negative:
        u['id'] = next_id
        next_id += 1
    _save_file_users(users)
    return users


def _load_file_users():
    _ensure_config()
    if not os.path.exists(FILE_USERS):
        return []
    try:
        with open(FILE_USERS, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except Exception:
        return []
    return _migrate_negative_file_user_ids(users)


def _save_file_users(users):
    _ensure_config()
    with open(FILE_USERS, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _load_file_tokens():
    _ensure_config()
    if not os.path.exists(FILE_TOKENS):
        return []
    try:
        with open(FILE_TOKENS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_file_tokens(tokens):
    _ensure_config()
    with open(FILE_TOKENS, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def _next_file_user_id():
    users = _load_file_users()
    if not users:
        return FILE_USER_ID_OFFSET
    ids = [u.get('id', 0) for u in users if isinstance(u.get('id', 0), int)]
    if not ids:
        return FILE_USER_ID_OFFSET
    return max(ids) + 1


def create_file_user(username, password, role='user'):
    """Создать файлового пользователя. Возвращает id."""
    username = (username or '').strip()
    if not username or not password:
        raise ValueError('Логин и пароль обязательны')
    users = _load_file_users()
    if any(u['username'] == username for u in users):
        raise ValueError('Пользователь с таким логином уже существует')
    uid = _next_file_user_id()
    # Защита от регресса: id не должен быть отрицательным
    if uid < 0:
        raise RuntimeError(f'Некорректный сгенерированный id пользователя: {uid} (ожидался id >= 0)')
    now = datetime.now().isoformat()
    users.append({
        'id': uid,
        'username': username,
        'password_hash': hash_password(password),
        'role': role,
        'created_at': now,
        'last_edit': now
    })
    _save_file_users(users)
    return uid


def delete_file_user(user_id):
    """Удалить файлового пользователя. Возвращает True если удалён."""
    users = _load_file_users()
    new = [u for u in users if u.get('id') != user_id]
    changed = len(new) != len(users)
    if changed:
        _save_file_users(new)
    return changed


def update_file_user_password(user_id, new_password):
    """Обновить пароль файлового пользователя. Возвращает True если изменён."""
    users = _load_file_users()
    changed = False
    for u in users:
        if u.get('id') == user_id:
            u['password_hash'] = hash_password(new_password)
            u['last_edit'] = datetime.now().isoformat()
            changed = True
            break
    if changed:
        _save_file_users(users)
    return changed


def update_file_user_last_login(user_id):
    """Обновить время последнего входа файлового пользователя. Возвращает True если изменён."""
    users = _load_file_users()
    changed = False
    for u in users:
        if u.get('id') == user_id:
            u['last_login'] = datetime.now().isoformat()
            changed = True
            break
    if changed:
        _save_file_users(users)
    return changed
