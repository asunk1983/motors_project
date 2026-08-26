"""Валидация/санитизация payload для номенклатуры оборудования.

Контракт функций — как в schemas/engine_schema.py и schemas/knowledge_schema.py:
  validate_..._payload(data) -> (is_valid: bool, error: str|None)
  sanitize_..._data(data) -> dict
"""

VALUE_TYPES = ('text', 'number', 'select', 'boolean', 'textarea')


def validate_equipment_type_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    code = (data.get('code') or '').strip()
    if not code:
        return False, 'Код типа обязателен'
    name = (data.get('name') or '').strip()
    if not name:
        return False, 'Название типа обязательно'
    return True, None


def sanitize_equipment_type_data(data: dict) -> dict:
    clean = {k: data[k] for k in ('code', 'name', 'parent_type_id', 'description') if k in data}
    if 'code' in clean:
        clean['code'] = clean['code'].strip().upper()
    if 'name' in clean:
        clean['name'] = clean['name'].strip()
    return clean


def validate_attribute_definition_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    key = (data.get('key') or '').strip()
    if not key:
        return False, 'Ключ атрибута обязателен'
    if not key.replace('_', '').isalnum() or key != key.lower():
        return False, 'Ключ должен быть в формате lower_snake_case (латиница/цифры/подчёркивание)'
    label = (data.get('label') or '').strip()
    if not label:
        return False, 'Подпись атрибута обязательна'
    value_type = data.get('value_type', 'text')
    if value_type not in VALUE_TYPES:
        return False, f'value_type должен быть одним из: {", ".join(VALUE_TYPES)}'
    if value_type == 'select' and not data.get('options'):
        return False, 'Для типа "список" нужно указать варианты (options)'
    return True, None


def sanitize_attribute_definition_data(data: dict) -> dict:
    clean = {k: data[k] for k in
             ('key', 'label', 'group_name', 'value_type', 'unit', 'options', 'default_value', 'weight')
             if k in data}
    if 'key' in clean:
        clean['key'] = clean['key'].strip().lower()
    if 'label' in clean:
        clean['label'] = clean['label'].strip()
    return clean


def validate_equipment_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    if not data.get('equipment_type_id'):
        return False, 'Тип оборудования обязателен'
    name = (data.get('name') or '').strip()
    if not name:
        return False, 'Наименование обязательно'
    criticality = data.get('criticality')
    if criticality is not None and criticality != '' and not (isinstance(criticality, int) and 1 <= criticality <= 5):
        return False, 'Критичность должна быть числом от 1 до 5'
    return True, None


def sanitize_equipment_data(data: dict) -> dict:
    fields = ('equipment_type_id', 'name', 'article', 'manufacturer', 'serial_number',
              'workshop', 'location', 'location_node_id', 'firmware_version', 'criticality', 'installed_at',
              'specs', 'note')
    clean = {k: data[k] for k in fields if k in data}
    if 'name' in clean:
        clean['name'] = clean['name'].strip()
    if clean.get('criticality') == '':
        clean['criticality'] = None
    if clean.get('location_node_id') == '':
        clean['location_node_id'] = None
    if 'specs' in clean and not isinstance(clean['specs'], dict):
        clean['specs'] = {}
    return clean
