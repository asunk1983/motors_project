"""Маршруты changelog и wishlist (вкладка «Инфо»).

Вынесено из app.py.
"""
import re
from datetime import datetime
from flask import Blueprint, request, jsonify

from modules.db import db_connection

changelog_bp = Blueprint('changelog', __name__, url_prefix='/api')


@changelog_bp.route('/changelog', methods=['GET'])
def get_changelog():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM changelog_entries ORDER BY entry_date DESC, id DESC')
            entries = [dict(row) for row in cursor.fetchall()]
        return jsonify(entries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/changelog', methods=['POST'])
def create_changelog_entry():
    try:
        data = request.json or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'Текст записи не может быть пустым'}), 400
        entry_date = (data.get('date') or '').strip() or datetime.now().strftime('%Y-%m-%d')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', entry_date):
            return jsonify({'error': 'Дата должна быть в формате ГГГГ-ММ-ДД'}), 400
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO changelog_entries (entry_date, text, created_at) VALUES (?, ?, ?)',
                (entry_date, text, datetime.now().isoformat())
            )
            conn.commit()
            entry_id = cursor.lastrowid
        return jsonify({'success': True, 'id': entry_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@changelog_bp.route('/changelog/<int:entry_id>', methods=['DELETE'])
def delete_changelog_entry(entry_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM changelog_entries WHERE id = ?', (entry_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Запись не найдена'}), 404
            cursor.execute('DELETE FROM changelog_entries WHERE id = ?', (entry_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
