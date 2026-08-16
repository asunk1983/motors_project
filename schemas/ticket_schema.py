"""Валидация/санитизация payload для ticket/failure/equipment_work.

Контракт функций — как в остальных schemas/*.py:
  validate_..._payload(data) -> (is_valid: bool, error: str|None)
  sanitize_..._data(data) -> dict
"""

PRIORITIES = ('high', 'normal', 'low')
TICKET_STATUSES = ('new', 'in_progress', 'waiting', 'resolved', 'closed', 'rejected', 'cancelled')


def validate_ticket_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    title = (data.get('title') or '').strip()
    if not title:
        return False, 'Тема заявки обязательна'
    priority = data.get('priority', 'normal')
    if priority not in PRIORITIES:
        return False, f'priority должен быть одним из: {", ".join(PRIORITIES)}'
    equipment_id = data.get('equipment_id')
    if equipment_id is not None and equipment_id != '' and not isinstance(equipment_id, int):
        return False, 'equipment_id должен быть целым числом'
    return True, None


def sanitize_ticket_data(data: dict) -> dict:
    clean = {k: data[k] for k in ('equipment_id', 'priority', 'title', 'description') if k in data}
    if 'title' in clean:
        clean['title'] = clean['title'].strip()
    if clean.get('equipment_id') == '':
        clean['equipment_id'] = None
    return clean


def validate_status_payload(data: dict):
    status = data.get('status')
    if status not in TICKET_STATUSES:
        return False, f'status должен быть одним из: {", ".join(TICKET_STATUSES)}'
    if status == 'rejected' and not (data.get('rejection_reason') or '').strip():
        return False, 'При отклонении заявки нужно указать причину'
    return True, None


def validate_failure_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    if not data.get('ticket_id'):
        return False, 'ticket_id обязателен'
    if not data.get('equipment_id'):
        return False, 'equipment_id обязателен'
    return True, None


def sanitize_failure_data(data: dict) -> dict:
    fields = ('ticket_id', 'equipment_id', 'failure_mode_id', 'failure_cause_id',
              'knowledge_article_id', 'symptom', 'description', 'confirmed',
              'occurred_at', 'restored_at')
    return {k: data[k] for k in fields if k in data}


def validate_work_payload(data: dict):
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'
    if not data.get('failure_id'):
        return False, 'failure_id обязателен'
    return True, None


def sanitize_work_data(data: dict) -> dict:
    fields = ('failure_id', 'action_type_id', 'executor_user_id', 'description', 'result',
              'successful', 'version_from', 'version_to', 'parameter_changed', 'old_value', 'new_value')
    return {k: data[k] for k in fields if k in data}
