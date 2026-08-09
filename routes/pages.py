"""Инфраструктурные маршруты: главная страница, печать, статика, тест.

Вынесено из app.py.
"""
from flask import Blueprint, send_from_directory

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@pages_bp.route('/print/<int:engine_id>')
def print_engine_page(engine_id):
    # engine_id в URL не используется на бэкенде — страница статическая,
    # id парсится в print.js из window.location.pathname и подставляется
    # в fetch('/api/engine/:id') на клиенте. Если такого двигателя нет,
    # печатная страница покажет свою собственную ошибку (см. print.js),
    # а не 404 здесь — так пользователь видит осмысленное сообщение
    # внутри уже открытой вкладки, а не пустой браузерный 404.
    return send_from_directory('templates', 'print.html')


@pages_bp.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@pages_bp.route('/test')
def test():
    return {'status': 'ok', 'message': 'Сервер работает!'}
