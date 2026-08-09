"""Фасад для обратной совместимости.

Раньше вся логика auth была в этом файле (411 строк). Теперь она разбита
на модули:
  - hashing.py     — hash_password, verify_password, hash_token, generate_token
  - db_users.py    — create_user, get_user_by_username, get_user_by_id,
                     list_users, delete_user, update_user_password, count_users
  - file_users.py  — create_file_user, delete_file_user, update_file_user_password,
                     _load_file_users, _save_file_users, _load_file_tokens,
                     _save_file_tokens, _next_file_user_id, _migrate_negative_file_user_ids,
                     FILE_USER_ID_OFFSET, FILE_USERS, FILE_TOKENS
  - tokens.py      — issue_token, get_user_from_token, revoke_token, revoke_all_for_user
  - decorators.py  — require_auth, require_admin, get_current_user, _extract_bearer_token

Этот файл переэкспортирует всё наружу, чтобы routes/auth.py и app.py
продолжали работать без изменений: `from modules.auth import auth as auth_module`.
"""
# Хэширование
from modules.auth.hashing import (
    hash_password,
    verify_password,
    hash_token,
    generate_token,
)

# DB-пользователи
from modules.auth.db_users import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    list_users,
    delete_user,
    update_user_password,
    update_last_login,
    count_users,
)

# Файловые пользователи и токены
from modules.auth.file_users import (
    create_file_user,
    delete_file_user,
    update_file_user_password,
    update_file_user_last_login,
    _load_file_users,
    _save_file_users,
    _load_file_tokens,
    _save_file_tokens,
    _next_file_user_id,
    _migrate_negative_file_user_ids,
    FILE_USER_ID_OFFSET,
    FILE_USERS,
    FILE_TOKENS,
    CONFIG_DIR,
)

# Токены
from modules.auth.tokens import (
    issue_token,
    get_user_from_token,
    revoke_token,
    revoke_all_for_user,
)

# Декораторы
from modules.auth.decorators import (
    require_auth,
    require_admin,
    get_current_user,
    _extract_bearer_token,
)

__all__ = [
    # hashing
    'hash_password', 'verify_password', 'hash_token', 'generate_token',
    # db_users
    'create_user', 'get_user_by_username', 'get_user_by_id', 'list_users',
    'delete_user', 'update_user_password', 'update_last_login', 'count_users',
    # file_users
    'create_file_user', 'delete_file_user', 'update_file_user_password',
    'update_file_user_last_login',
    '_load_file_users', '_save_file_users', '_load_file_tokens', '_save_file_tokens',
    '_next_file_user_id', '_migrate_negative_file_user_ids',
    'FILE_USER_ID_OFFSET', 'FILE_USERS', 'FILE_TOKENS', 'CONFIG_DIR',
    # tokens
    'issue_token', 'get_user_from_token', 'revoke_token', 'revoke_all_for_user',
    # decorators
    'require_auth', 'require_admin', 'get_current_user', '_extract_bearer_token',
]
