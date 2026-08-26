# routes/equipment_photo_routes.py — отдача файлов фото оборудования.
# Отдельный blueprint (не под /api/equipment), потому что путь к файлу не
# содержит equipment_id — та же схема, что у /api/incident-photos/<filename>
# для заявок Инцидентов и /api/photos/<filename> для двигателей: имя
# файла само по себе однозначно (ID{equipment_id}_{n}.ext), доступ
# read-only.

from flask import Blueprint

from modules.photo_manager import equipment_manager

equipment_photo_bp = Blueprint('equipment_photo_bp', __name__, url_prefix='/api/equipment-photos')


@equipment_photo_bp.route('/<path:filename>', methods=['GET'])
def get_equipment_photo_route(filename):
    return equipment_manager.get_photo(filename)
