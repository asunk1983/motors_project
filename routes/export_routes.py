"""Маршрут экспорта выбранных паспортов в Excel.

Вынесено из app.py. Делегирует логику в services/export_service.py.
Контракт синхронизирован с catalog.js: POST /api/engines/export,
param: ids (list[int]), ответ: xlsx blob.
"""
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

from modules.db import db_connection
from services.export_service import export_to_xlsx

export_bp = Blueprint('export', __name__, url_prefix='/api')


@export_bp.route('/engines/export', methods=['POST'])
def export_to_excel():
    try:
        data = request.json or {}
        ids = data.get('ids', [])
        if not isinstance(ids, list) or not ids:
            return jsonify({'error': 'Не выбраны двигатели для экспорта'}), 400
        ids = ids[:100]

        with db_connection() as conn:
            xlsx_bytes = export_to_xlsx(conn, ids)

        filename = f"passports_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(
            BytesIO(xlsx_bytes), as_attachment=True, download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
