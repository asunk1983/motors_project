# routes/incident_photo_routes.py — отдача файлов фото заявок Инцидентов.
# Отдельный blueprint (не под /api/incident-tickets), потому что путь к
# файлу не содержит ticket_id — та же схема, что у /api/photos/<filename>
# для двигателей (routes/photos.py): имя файла само по себе однозначно
# (ID{ticket_id}_{n}.ext), доступ read-only.

from flask import Blueprint

from modules.photo_manager import incident_manager

incident_photo_bp = Blueprint('incident_photo_bp', __name__, url_prefix='/api/incident-photos')


@incident_photo_bp.route('/<path:filename>', methods=['GET'])
def get_incident_photo_route(filename):
    return incident_manager.get_photo(filename)
