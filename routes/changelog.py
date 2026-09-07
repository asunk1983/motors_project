"""Маршруты changelog и wishlist (вкладка «Инфо»).

Вынесено из app.py.

История изменений (changelog) хранится в data/changelog.json
(см. scripts/migrate_changelog_to_json.py). Запись/удаление через API не
поддерживаются — POST /api/changelog и DELETE /api/changelog/<id> удалены.

Пожелания (wishlist) хранятся в data/wishlist.json
(см. scripts/migrate_wishlist_to_json.py). В отличие от changelog, здесь
API продолжает поддерживать создание/изменение/удаление — пользователи
пополняют список сами через UI, поэтому CRUD сохранён, просто источником
данных стал JSON-файл вместо таблицы wishlist_items.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

from config.settings import BASE_DIR
from modules.db import db_connection
from modules.auth import auth as auth_module

logger = logging.getLogger(__name__)

changelog_bp = Blueprint('changelog', __name__, url_prefix='/api')

CHANGELOG_JSON_PATH = Path(BASE_DIR) / 'data' / 'changelog.json'
WISHLIST_JSON_PATH = Path(BASE_DIR) / 'data' / 'wishlist.json'


@changelog_bp.route('/changelog', methods=['GET'])
def get_changelog():
    """Отдаёт записи лога изменений из data/changelog.json.

    Файл уже отсортирован entry_date DESC, id DESC на этапе миграции —
    пересортировка здесь не нужна. Маппим ключи {"date": ..., "text": ...}
    на {"entry_date": ..., "text": ...}, чтобы фронт (backupManager.js
    использует e.entry_date при группировке по дате) продолжал работать
    без изменений.
    """
    if not CHANGELOG_JSON_PATH.exists():
        # Миграция ещё не запущена или файл удалён — это не ошибка для
        # пользователя, просто пустой лог.
        logger.warning(
            'Файл лога изменений не найден: %s. Вернён пустой массив.',
            CHANGELOG_JSON_PATH,
        )
        return jsonify([])

    try:
        with open(CHANGELOG_JSON_PATH, encoding='utf-8') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        logger.exception('Не удалось прочитать %s', CHANGELOG_JSON_PATH)
        return jsonify({'error': str(e)}), 500

    if not isinstance(raw, list):
        logger.error(
            'Неожиданный формат %s: ожидался JSON-массив, получен %s',
            CHANGELOG_JSON_PATH,
            type(raw).__name__,
        )
        return jsonify({'error': 'Некорректный формат файла лога изменений'}), 500

    # Маппинг ключей: фронт ожидает "entry_date" (см. backupManager.js).
    entries = [
        {'entry_date': item.get('date'), 'text': item.get('text')}
        for item in raw
        if isinstance(item, dict)
    ]
    return jsonify(entries)


def _load_wishlist():
    """Читает data/wishlist.json. Отсутствие файла — не ошибка, пустой список."""
    if not WISHLIST_JSON_PATH.exists():
        return []
    with open(WISHLIST_JSON_PATH, encoding='utf-8') as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(
            f'Некорректный формат {WISHLIST_JSON_PATH}: ожидался JSON-массив, '
            f'получен {type(raw).__name__}'
        )
    return raw


def _save_wishlist(items):
    """Пишет список пожеланий в data/wishlist.json."""
    WISHLIST_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WISHLIST_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
        f.write('\n')


def _sort_wishlist_key(item):
    # ORDER BY done ASC, id DESC — как было в SQL-варианте.
    return (bool(item.get('done')), -int(item.get('id', 0)))


@changelog_bp.route('/wishlist', methods=['GET'])
def get_wishlist():
    try:
        items = _load_wishlist()
    except (OSError, ValueError) as e:
        logger.exception('Не удалось прочитать %s', WISHLIST_JSON_PATH)
        return jsonify({'error': str(e)}), 500

    # Старые записи (созданные до добавления поля author) не содержат
    # информацию об авторе — показываем "неизвестно", а не пропускаем поле.
    for item in items:
        item.setdefault('author', 'неизвестно')

    # Резолвим display_name автора через auth_module.get_user_by_username
    # (после 6a1ba46 он всегда возвращает display_name через
    # modules/auth/db_users._attach_display_name, с fallback на username).
    # Если логин 'неизвестно' или пользователь удалён — оставляем сам
    # логин, чтобы не сломать совместимость со старыми записями.
    with db_connection() as conn:
        for item in items:
            author_username = item.get('author')
            if not author_username or author_username == 'неизвестно':
                item['author_display_name'] = 'неизвестно'
                continue
            user = auth_module.get_user_by_username(conn, author_username)
            if user and user.get('display_name'):
                item['author_display_name'] = user['display_name']
            else:
                # пользователь удалён, но логин в записи остался —
                # показываем сам логин, а не пустоту
                item['author_display_name'] = author_username

    items = sorted(items, key=_sort_wishlist_key)
    return jsonify(items)


@changelog_bp.route('/wishlist', methods=['POST'])
def create_wishlist_item():
    try:
        data = request.json or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'Текст пожелания не может быть пустым'}), 400

        current_user = getattr(request, 'current_user', None) or {}
        author = current_user.get('username') or 'неизвестно'

        items = _load_wishlist()
        new_id = max((item.get('id', 0) for item in items), default=0) + 1
        items.append({
            'id': new_id,
            'text': text,
            'done': False,
            'created_at': datetime.now().isoformat(),
            'author': author,
        })
        _save_wishlist(items)
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        logger.exception('Не удалось добавить пожелание')
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/wishlist/<int:item_id>', methods=['PUT'])
def update_wishlist_item(item_id):
    try:
        data = request.json or {}
        items = _load_wishlist()
        item = next((i for i in items if i.get('id') == item_id), None)
        if item is None:
            return jsonify({'error': 'Пожелание не найдено'}), 404

        if 'done' in data:
            item['done'] = bool(data.get('done'))
        if 'text' in data:
            text = (data.get('text') or '').strip()
            if not text:
                return jsonify({'error': 'Текст пожелания не может быть пустым'}), 400
            item['text'] = text

        _save_wishlist(items)
        return jsonify({'success': True})
    except Exception as e:
        logger.exception('Не удалось обновить пожелание %s', item_id)
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/wishlist/<int:item_id>', methods=['DELETE'])
def delete_wishlist_item(item_id):
    try:
        items = _load_wishlist()
        if not any(i.get('id') == item_id for i in items):
            return jsonify({'error': 'Пожелание не найдено'}), 404

        items = [i for i in items if i.get('id') != item_id]
        _save_wishlist(items)
        return jsonify({'success': True})
    except Exception as e:
        logger.exception('Не удалось удалить пожелание %s', item_id)
        return jsonify({'error': str(e)}), 500