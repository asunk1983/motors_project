"""Маршруты changelog и wishlist (вкладка «Инфо»).

Вынесено из app.py.

История изменений (changelog) теперь хранится в data/changelog.json
(см. scripts/migrate_changelog_to_json.py). Запись/удаление через API больше
не поддерживаются — POST /api/changelog и DELETE /api/changelog/<id> удалены.
"""
import logging
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

from config.settings import BASE_DIR
from modules.db import db_connection

logger = logging.getLogger(__name__)

changelog_bp = Blueprint('changelog', __name__, url_prefix='/api')

CHANGELOG_JSON_PATH = Path(BASE_DIR) / 'data' / 'changelog.json'


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
        import json
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


@changelog_bp.route('/wishlist', methods=['GET'])
def get_wishlist():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM wishlist_items ORDER BY done ASC, id DESC')
            items = [dict(row) for row in cursor.fetchall()]
            for item in items:
                item['done'] = bool(item['done'])
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/wishlist', methods=['POST'])
def create_wishlist_item():
    try:
        data = request.json or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'Текст пожелания не может быть пустым'}), 400
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO wishlist_items (text, done, created_at) VALUES (?, 0, ?)',
                (text, datetime.now().isoformat())
            )
            conn.commit()
            item_id = cursor.lastrowid
        return jsonify({'success': True, 'id': item_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/wishlist/<int:item_id>', methods=['PUT'])
def update_wishlist_item(item_id):
    try:
        data = request.json or {}
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM wishlist_items WHERE id = ?', (item_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Пожелание не найдено'}), 404
            if 'done' in data:
                cursor.execute('UPDATE wishlist_items SET done = ? WHERE id = ?', (1 if data.get('done') else 0, item_id))
            if 'text' in data:
                text = (data.get('text') or '').strip()
                if not text:
                    return jsonify({'error': 'Текст пожелания не может быть пустым'}), 400
                cursor.execute('UPDATE wishlist_items SET text = ? WHERE id = ?', (text, item_id))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/wishlist/<int:item_id>', methods=['DELETE'])
def delete_wishlist_item(item_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM wishlist_items WHERE id = ?', (item_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Пожелание не найдено'}), 404
            cursor.execute('DELETE FROM wishlist_items WHERE id = ?', (item_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
