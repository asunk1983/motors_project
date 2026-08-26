"""Фабрика blueprint-ов для Flask.

Централизует регистрацию всех blueprint-ов в одном месте.
app.py вызывает register_blueprints(app) вместо множества app.register_blueprint().
"""
from flask import Blueprint


def create_blueprints():
    """Создаёт и возвращает все blueprint-ы приложения.

    Порядок важен: auth_bp регистрируется первым (before_app_request
    для загрузки текущего пользователя).
    """
    from routes.auth import auth_bp
    from routes.engines import engines_bp
    from routes.knowledge_routes import knowledge_bp
    from routes.equipment_routes import equipment_bp
    from routes.equipment_photo_routes import equipment_photo_bp
    from routes.ticket_routes import ticket_bp
    from routes.location_routes import location_bp
    from routes.crew_routes import crew_bp
    from routes.incident_ticket_routes import incident_ticket_bp
    from routes.incident_photo_routes import incident_photo_bp
    from routes.photos import photos_bp
    from routes.import_routes import import_bp
    from routes.export_routes import export_bp
    from routes.backup_routes import backup_bp
    from routes.changelog import changelog_bp
    from routes.status import status_bp
    from routes.search import search_bp
    from routes.pages import pages_bp

    return [
        auth_bp,
        engines_bp,
        knowledge_bp,
        equipment_bp,
        equipment_photo_bp,
        ticket_bp,
        location_bp,
        crew_bp,
        incident_ticket_bp,
        incident_photo_bp,
        photos_bp,
        import_bp,
        export_bp,
        backup_bp,
        changelog_bp,
        status_bp,
        search_bp,
        pages_bp,
    ]


def register_blueprints(app):
    """Регистрирует все blueprint-ы в Flask-приложении."""
    for bp in create_blueprints():
        app.register_blueprint(bp)
