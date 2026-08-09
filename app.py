# app.py
"""Точка входа в приложение Motors.

Создаёт Flask-приложение, регистрирует blueprint-ы (через routes/__init__.py)
и инициализирует БД при запуске. Вся роут-логика вынесена в routes/.
"""
import os
import logging

from flask import Flask
from flask_cors import CORS

from modules.db import init_db
from routes import register_blueprints
from config.settings import PHOTOS_FOLDER, MOTORS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB на запрос

for folder in [PHOTOS_FOLDER, MOTORS_FOLDER, BACKUPS_FOLDER, BACKUP_STAGING_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

register_blueprints(app)


if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('templates'):
        os.makedirs('templates')

    init_db()
    app.run(debug=True, port=5000, host='0.0.0.0')
