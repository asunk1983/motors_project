"""Тесты HTTP-слоя номенклатуры оборудования (routes/equipment_routes.py).

Покрывает эндпоинты:
  - конструктор: equipment-types (GET/POST/DELETE/PATCH), attribute-definitions
    (GET/POST/DELETE), назначение атрибутов типу (GET/PUT);
  - оборудование: список, location-counts, CRUD записей, placements, фото, экспорт.

Паттерн — как в существующих route-тестах проекта (test_engines.py,
test_crew_routes.py): db_connection и repo-функции
мокаются на уровне модуля роута; admin-гейты через мок _require_admin.

ВАЖНО: никакие файловые операции (фото, экспорт) реально не выполняются —
equipment_manager и export_service мокаются, на диск ничего не пишется.
"""

from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from routes.equipment_routes import equipment_bp


def _conn_mock():
    """Контекст-менеджер-мок для db_connection (паттерн test_auth_routes)."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=MagicMock())
    m.__exit__ = MagicMock(return_value=False)
    return m


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(equipment_bp)  # у bp уже есть url_prefix='/api'
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------
# Типы оборудования (GET/POST/DELETE/PATCH)
# ---------------------------------------------------------------------
class TestEquipmentTypes:
    @patch('routes.equipment_routes.list_equipment_types')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_types_empty(self, m_db, m_list, client):
        m_list.return_value = []
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types')
        assert r.status_code == 200
        assert r.get_json() == []

    @patch('routes.equipment_routes.list_equipment_types')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_types_with_data(self, m_db, m_list, client):
        m_list.return_value = [{'id': 1, 'code': 'PUMP', 'name': 'Насос'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]['code'] == 'PUMP'

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.create_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_create_equipment_type_success(self, m_db, m_create, m_require, client):
        m_require.return_value = None  # admin
        m_create.return_value = 42
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment-types', json={'code': 'pump', 'name': 'Насос'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 42
        assert 'создан' in data['message'].lower()

    @patch('routes.equipment_routes._require_admin')
    def test_create_equipment_type_forbidden_non_admin(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль admin)'}, 403)
        r = client.post('/api/equipment-types', json={'code': 'pump', 'name': 'Насос'})
        assert r.status_code == 403

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.validate_equipment_type_payload')
    def test_create_equipment_type_validation_400(self, m_validate, m_require, client):
        m_require.return_value = None
        m_validate.return_value = (False, 'Код типа обязателен')
        r = client.post('/api/equipment-types', json={})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'Код типа обязателен'

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.equipment_type_in_use')
    @patch('routes.equipment_routes.delete_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_type_success(self, m_db, m_delete, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = False
        m_delete.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment-types/1')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.equipment_type_in_use')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_type_in_use_400(self, m_db, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment-types/1')
        assert r.status_code == 400
        assert 'используется' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.equipment_type_in_use')
    @patch('routes.equipment_routes.delete_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_type_not_found_404(self, m_db, m_delete, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = False
        m_delete.return_value = False
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment-types/999')
        assert r.status_code == 404
        assert 'не найден' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes._require_admin')
    def test_delete_equipment_type_forbidden_non_admin(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль admin)'}, 403)
        r = client.delete('/api/equipment-types/1')
        assert r.status_code == 403

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.update_equipment_type_min_stock_qty')
    @patch('routes.equipment_routes.db_connection')
    def test_patch_min_stock_qty_success(self, m_db, m_update, m_get_type, client):
        m_get_type.return_value = {'id': 1, 'code': 'PUMP'}
        m_update.return_value = True
        m_db.return_value = _conn_mock()
        r = client.patch('/api/equipment-types/1', json={'min_stock_qty': 5})
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        args, kwargs = m_update.call_args
        assert args[2] == 5

    @patch('routes.equipment_routes.db_connection')
    def test_patch_missing_min_stock_qty_400(self, m_db, client):
        m_db.return_value = _conn_mock()
        r = client.patch('/api/equipment-types/1', json={})
        assert r.status_code == 400
        assert 'min_stock_qty' in r.get_json()['error']

    @patch('routes.equipment_routes.db_connection')
    def test_patch_invalid_min_stock_qty_400(self, m_db, client):
        m_db.return_value = _conn_mock()
        r = client.patch('/api/equipment-types/1', json={'min_stock_qty': 'not-int'})
        assert r.status_code == 400
        assert 'числом' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes.db_connection')
    def test_patch_negative_min_stock_qty_400(self, m_db, client):
        m_db.return_value = _conn_mock()
        r = client.patch('/api/equipment-types/1', json={'min_stock_qty': -1})
        assert r.status_code == 400
        assert 'отрицательн' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_patch_type_not_found_404(self, m_db, m_get_type, client):
        m_get_type.return_value = None
        m_db.return_value = _conn_mock()
        r = client.patch('/api/equipment-types/1', json={'min_stock_qty': 5})
        assert r.status_code == 404
# ---------------------------------------------------------------------
# Сводка ЗИП + пул атрибутов
# ---------------------------------------------------------------------
class TestStockSummary:
    @patch('routes.equipment_routes.get_stock_summary')
    @patch('routes.equipment_routes.db_connection')
    def test_get_stock_summary_success(self, m_db, m_summary, client):
        m_summary.return_value = [{'code': 'PUMP', 'min_stock_qty': 3}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/stock-summary')
        assert r.status_code == 200
        assert r.get_json()[0]['code'] == 'PUMP'


class TestAttributeDefinitionRoutes:
    @patch('routes.equipment_routes.list_attribute_definitions')
    @patch('routes.equipment_routes.db_connection')
    def test_get_attribute_definitions_success(self, m_db, m_list, client):
        m_list.return_value = [{'id': 1, 'key': 'power', 'label': 'Мощность'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/attribute-definitions')
        assert r.status_code == 200
        assert r.get_json()[0]['key'] == 'power'

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.create_attribute_definition')
    @patch('routes.equipment_routes.db_connection')
    def test_create_attribute_definition_success(self, m_db, m_create, m_require, client):
        m_require.return_value = None
        m_create.return_value = 7
        m_db.return_value = _conn_mock()
        r = client.post('/api/attribute-definitions', json={
            'key': 'power', 'label': 'Мощность', 'value_type': 'number',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 7

    @patch('routes.equipment_routes._require_admin')
    def test_create_attribute_definition_forbidden(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль admin)'}, 403)
        r = client.post('/api/attribute-definitions', json={
            'key': 'power', 'label': 'Мощность',
        })
        assert r.status_code == 403

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.validate_attribute_definition_payload')
    def test_create_attribute_definition_validation_400(self, m_validate, m_require, client):
        m_require.return_value = None
        m_validate.return_value = (False, 'Ключ атрибута обязателен')
        r = client.post('/api/attribute-definitions', json={})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'Ключ атрибута обязателен'

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.attribute_definition_in_use')
    @patch('routes.equipment_routes.delete_attribute_definition')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_attribute_definition_success(self, m_db, m_delete, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = False
        m_delete.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/attribute-definitions/1')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.attribute_definition_in_use')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_attribute_definition_in_use_400(self, m_db, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/attribute-definitions/1')
        assert r.status_code == 400
        assert 'назначен' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.attribute_definition_in_use')
    @patch('routes.equipment_routes.delete_attribute_definition')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_attribute_definition_not_found_404(self, m_db, m_delete, m_in_use, m_require, client):
        m_require.return_value = None
        m_in_use.return_value = False
        m_delete.return_value = False
        m_db.return_value = _conn_mock()
        r = client.delete('/api/attribute-definitions/999')
        assert r.status_code == 404
        assert 'не найден' in r.get_json()['error'].lower()
# ---------------------------------------------------------------------
# Атрибуты типа (effective / own / set)
# ---------------------------------------------------------------------
class TestTypeAttributes:
    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.get_effective_attributes')
    @patch('routes.equipment_routes.db_connection')
    def test_get_type_attributes_success(self, m_db, m_attrs, m_get_type, client):
        m_get_type.return_value = {'id': 1}
        m_attrs.return_value = [{'key': 'power', 'label': 'Мощность'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types/1/attributes')
        assert r.status_code == 200
        assert r.get_json()[0]['key'] == 'power'

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_get_type_attributes_type_not_found_404(self, m_db, m_get_type, client):
        m_get_type.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types/999/attributes')
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.get_assigned_attributes')
    @patch('routes.equipment_routes.db_connection')
    def test_get_own_attributes_success(self, m_db, m_attrs, m_get_type, client):
        m_get_type.return_value = {'id': 1}
        m_attrs.return_value = [{'key': 'power', 'label': 'Мощность'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types/1/own-attributes')
        assert r.status_code == 200
        assert r.get_json()[0]['key'] == 'power'

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_get_own_attributes_type_not_found_404(self, m_db, m_get_type, client):
        m_get_type.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types/999/own-attributes')
        assert r.status_code == 404

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.set_type_attributes')
    @patch('routes.equipment_routes.db_connection')
    def test_set_type_attributes_success(self, m_db, m_set, m_get_type, m_require, client):
        m_require.return_value = None
        m_get_type.return_value = {'id': 1}
        m_set.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment-types/1/attributes', json={
            'assignments': [{'attribute_definition_id': 1, 'is_required': True}],
        })
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        m_set.assert_called_once()

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.db_connection')
    def test_set_type_attributes_not_a_list_400(self, m_db, m_require, client):
        m_require.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment-types/1/attributes', json={'assignments': 'oops'})
        assert r.status_code == 400
        assert 'списком' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes._require_admin')
    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_set_type_attributes_type_not_found_404(self, m_db, m_get_type, m_require, client):
        m_require.return_value = None
        m_get_type.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment-types/999/attributes', json={'assignments': []})
        assert r.status_code == 404

    @patch('routes.equipment_routes._require_admin')
    def test_set_type_attributes_forbidden_non_admin(self, m_require, client):
        m_require.return_value = ({'error': 'Доступ запрещён (нужна роль admin)'}, 403)
        r = client.put('/api/equipment-types/1/attributes', json={'assignments': []})
        assert r.status_code == 403

    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.get_show_in_list_attributes')
    @patch('routes.equipment_routes.db_connection')
    def test_get_show_in_list_attributes_success(self, m_db, m_attrs, m_get_type, client):
        m_get_type.return_value = {'id': 1}
        m_attrs.return_value = [{'key': 'power', 'label': 'Мощность', 'unit': 'кВт'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment-types/1/show-in-list-attributes')
        assert r.status_code == 200
        assert r.get_json()[0]['key'] == 'power'


# ---------------------------------------------------------------------
# Оборудование — CRUD
# ---------------------------------------------------------------------
class TestEquipmentCRUD:
    @patch('routes.equipment_routes.list_equipment')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_list_success(self, m_db, m_list, client):
        m_list.return_value = [{'id': 1, 'name': 'Насос Н1'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment')
        assert r.status_code == 200
        assert len(r.get_json()) == 1

    @patch('routes.equipment_routes.get_equipment_location_counts')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_location_counts_success(self, m_db, m_counts, client):
        m_counts.return_value = {1: 3, 2: 1}
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/location-counts')
        assert r.status_code == 200
        # jsonify возвращает строковые ключи (JSON-формат)
        assert r.get_json() == {'1': 3, '2': 1}

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_by_id_success(self, m_db, m_get, client):
        m_get.return_value = {'id': 1, 'name': 'Насос Н1'}
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/1')
        assert r.status_code == 200
        assert r.get_json()['id'] == 1

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_get_equipment_by_id_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/999')
        assert r.status_code == 404
        assert 'не найдено' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes.validate_equipment_payload')
    @patch('routes.equipment_routes.sanitize_equipment_data')
    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.create_equipment')
    @patch('routes.equipment_routes.db_connection')
    def test_create_equipment_success(self, m_db, m_create, m_get_type, m_sanitize, m_validate, client):
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'equipment_type_id': 1, 'name': 'Насос Н1'}
        m_get_type.return_value = {'id': 1}
        m_create.return_value = 10
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment', json={'equipment_type_id': 1, 'name': 'Насос Н1'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['id'] == 10

    @patch('routes.equipment_routes.validate_equipment_payload')
    def test_create_equipment_validation_400(self, m_validate, client):
        m_validate.return_value = (False, 'Наименование обязательно')
        r = client.post('/api/equipment', json={})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'Наименование обязательно'

    @patch('routes.equipment_routes.validate_equipment_payload')
    @patch('routes.equipment_routes.sanitize_equipment_data')
    @patch('routes.equipment_routes.get_equipment_type')
    @patch('routes.equipment_routes.db_connection')
    def test_create_equipment_type_not_found_400(self, m_db, m_get_type, m_sanitize, m_validate, client):
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'equipment_type_id': 999, 'name': 'X'}
        m_get_type.return_value = None
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment', json={'equipment_type_id': 999, 'name': 'X'})
        assert r.status_code == 400
        assert 'тип' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes.validate_equipment_payload')
    @patch('routes.equipment_routes.sanitize_equipment_data')
    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.update_equipment')
    @patch('routes.equipment_routes.db_connection')
    def test_update_equipment_success(self, m_db, m_update, m_get, m_sanitize, m_validate, client):
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'equipment_type_id': 1, 'name': 'Н2'}
        m_get.return_value = {'id': 1}
        m_update.return_value = True
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment/1', json={'equipment_type_id': 1, 'name': 'Н2'})
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.equipment_routes.validate_equipment_payload')
    @patch('routes.equipment_routes.sanitize_equipment_data')
    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_update_equipment_not_found_404(self, m_db, m_get, m_sanitize, m_validate, client):
        m_validate.return_value = (True, None)
        m_sanitize.return_value = {'equipment_type_id': 1, 'name': 'X'}
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment/999', json={'equipment_type_id': 1, 'name': 'X'})
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_referenced_by_incidents')
    @patch('routes.equipment_routes.equipment_manager')
    @patch('routes.equipment_routes.delete_equipment')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_success(self, m_db, m_delete, m_manager, m_ref, m_get, client):
        m_get.return_value = {'id': 1}
        m_ref.return_value = False
        m_delete.return_value = True
        # фото удаляются «на диске» только через мок — реального доступа к диску нет
        m_manager.delete_equipment_photos_from_disk.return_value = (0, [])
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/1')
        assert r.status_code == 200
        assert r.get_json()['success'] is True
        m_manager.delete_equipment_photos_from_disk.assert_called_once_with(1)

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/999')
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_referenced_by_incidents')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_equipment_referenced_by_incident_400(self, m_db, m_ref, m_get, client):
        m_get.return_value = {'id': 1}
        m_ref.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/1')
        assert r.status_code == 400
        assert 'заявк' in r.get_json()['error'].lower()
# ---------------------------------------------------------------------
# Места оборудования (placements)
# ---------------------------------------------------------------------
class TestEquipmentPlacements:
    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_get_placements_success(self, m_db, m_repo, m_get, client):
        m_get.return_value = {'id': 1}
        m_repo.list_by_equipment.return_value = [{'id': 1, 'designation': 'КМ1'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/1/placements')
        assert r.status_code == 200
        assert r.get_json()[0]['designation'] == 'КМ1'

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_get_placements_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/999/placements')
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.location_repo')
    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_create_placements_success(self, m_db, m_repo, m_loc, m_get, client):
        m_get.return_value = {'id': 1}
        m_loc.get_by_id.return_value = {'id': 5}
        m_repo.designation_exists_in_location.return_value = False
        m_repo.create.side_effect = [11, 12]
        m_repo.list_by_equipment.return_value = []
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/1/placements', json={
            'location_node_id': 5, 'designations': 'КМ1, КМ2',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['created'] == [11, 12]
        assert data['errors'] == []
        assert m_repo.create.call_count == 2

    @patch('routes.equipment_routes.db_connection')
    def test_create_placements_location_required_400(self, m_db, client):
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/1/placements', json={})
        assert r.status_code == 400
        assert 'Место обязательно' == r.get_json()['error']

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_create_placements_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/999/placements', json={'location_node_id': 5, 'designations': 'КМ1'})
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.location_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_create_placements_location_not_found_400(self, m_db, m_loc, m_get, client):
        m_get.return_value = {'id': 1}
        m_loc.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/1/placements', json={'location_node_id': 999, 'designations': 'КМ1'})
        assert r.status_code == 400
        assert 'место' in r.get_json()['error'].lower()

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.location_repo')
    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_create_placements_duplicate_designation_errors(self, m_db, m_repo, m_loc, m_get, client):
        m_get.return_value = {'id': 1}
        m_loc.get_by_id.return_value = {'id': 5}
        # 'КМ1' занят, 'КМ2' свободен
        m_repo.designation_exists_in_location.side_effect = lambda conn, loc, des: des == 'КМ1'
        m_repo.create.return_value = 11
        m_repo.list_by_equipment.return_value = []
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/1/placements', json={
            'location_node_id': 5, 'designations': 'КМ1, КМ2',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['created'] == [11]
        assert len(data['errors']) == 1
        assert 'занято' in data['errors'][0].lower()

    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_placement_success(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = {'id': 3, 'equipment_id': 1}
        m_repo.delete.return_value = True
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/1/placements/3')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_placement_not_found_404(self, m_db, m_repo, client):
        m_repo.get_by_id.return_value = None
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/1/placements/999')
        assert r.status_code == 404

    @patch('routes.equipment_routes.equipment_placement_repo')
    @patch('routes.equipment_routes.db_connection')
    def test_delete_placement_wrong_equipment_404(self, m_db, m_repo, client):
        # placement принадлежит другому оборудованию
        m_repo.get_by_id.return_value = {'id': 3, 'equipment_id': 999}
        m_db.return_value = _conn_mock()
        r = client.delete('/api/equipment/1/placements/3')
        assert r.status_code == 404
# ---------------------------------------------------------------------
# Фото оборудования — только моки, диск не трогается
# ---------------------------------------------------------------------
class TestEquipmentPhotos:
    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_manager')
    @patch('routes.equipment_routes.db_connection')
    def test_get_photos_success(self, m_db, m_manager, m_get, client):
        m_get.return_value = {'id': 1}
        m_manager.get_equipment_photos.return_value = [{'filename': 'ID1_1.jpg'}]
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/1/photos')
        assert r.status_code == 200
        assert r.get_json()[0]['filename'] == 'ID1_1.jpg'

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_get_photos_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.get('/api/equipment/999/photos')
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_manager')
    @patch('routes.equipment_routes.db_connection')
    def test_upload_photos_success(self, m_db, m_manager, m_get, client):
        m_get.return_value = {'id': 1}
        m_manager.upload_equipment_photos.return_value = (
            {'success': True, 'uploaded': 1, 'skipped': 0}, 200,
        )
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/1/photos',
                        data={'photos': (b'abc', 'x.jpg')},
                        content_type='multipart/form-data')
        assert r.status_code == 200
        assert r.get_json()['uploaded'] == 1

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_upload_photos_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/999/photos',
                        data={'photos': (b'abc', 'x.jpg')},
                        content_type='multipart/form-data')
        assert r.status_code == 404

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.equipment_manager')
    @patch('routes.equipment_routes.db_connection')
    def test_replace_photo_success(self, m_db, m_manager, m_get, client):
        m_get.return_value = {'id': 1}
        m_manager.replace_equipment_photo.return_value = (
            {'success': True, 'message': 'Фото заменено'}, 200,
        )
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment/1/photos/ID1_1.jpg',
                       data={'photo': (b'abc', 'y.jpg')},
                       content_type='multipart/form-data')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    @patch('routes.equipment_routes.get_equipment_by_id')
    @patch('routes.equipment_routes.db_connection')
    def test_replace_photo_equipment_not_found_404(self, m_db, m_get, client):
        m_get.return_value = None
        m_db.return_value = _conn_mock()
        r = client.put('/api/equipment/999/photos/ID1_1.jpg',
                       data={'photo': (b'abc', 'y.jpg')},
                       content_type='multipart/form-data')
        assert r.status_code == 404

    @patch('routes.equipment_routes.equipment_manager')
    def test_delete_photo_success(self, m_manager, client):
        m_manager.delete_equipment_photo.return_value = (
            {'success': True, 'message': 'Фото удалено'}, 200,
        )
        r = client.delete('/api/equipment/1/photos/ID1_1.jpg')
        assert r.status_code == 200
        assert r.get_json()['success'] is True


# ---------------------------------------------------------------------
# Экспорт оборудования — только моки, файл не создаётся на диске
# ---------------------------------------------------------------------
class TestEquipmentExport:
    def test_export_no_ids_400(self, client):
        r = client.post('/api/equipment/export', json={})
        assert r.status_code == 400
        assert 'Не выбрано' in r.get_json()['error']

    def test_export_too_many_ids_400(self, client):
        r = client.post('/api/equipment/export', json={'ids': list(range(101))})
        assert r.status_code == 400
        assert 'Слишком много' in r.get_json()['error']

    @patch('routes.equipment_routes.export_service')
    @patch('routes.equipment_routes.db_connection')
    def test_export_success(self, m_db, m_export, client):
        m_export.export_equipment_to_xlsx.return_value = b'PK\x03\x04fake-xlsx'
        m_db.return_value = _conn_mock()
        r = client.post('/api/equipment/export', json={'ids': [1, 2]})
        assert r.status_code == 200
        assert r.data == b'PK\x03\x04fake-xlsx'
        assert 'spreadsheetml' in r.headers.get('Content-Type', '')