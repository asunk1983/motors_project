"""Валидация и санитизация payload для статей базы знаний.

Контракт функций — как в schemas/engine_schema.py:
  validate_article_payload(data) -> (is_valid: bool, error: str|None)
  sanitize_article_data(data) -> dict (только разрешённые поля)
"""

ARTICLE_FIELDS = (
    'title', 'symptom', 'failure_mode_id', 'diagnostic_steps',
    'recommended_action', 'reference_note', 'cause_ids',
)


def validate_article_payload(data: dict):
    """Проверяет payload статьи. title и symptom обязательны — без них
    статья не имеет смысла ни для поиска, ни для отображения в списке."""
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'

    title = (data.get('title') or '').strip()
    if not title:
        return False, 'Заголовок статьи обязателен'
    if len(title) > 300:
        return False, 'Заголовок слишком длинный (макс. 300 символов)'

    symptom = (data.get('symptom') or '').strip()
    if not symptom:
        return False, 'Симптом обязателен'

    failure_mode_id = data.get('failure_mode_id')
    if failure_mode_id is not None and not isinstance(failure_mode_id, int):
        return False, 'failure_mode_id должен быть целым числом'

    cause_ids = data.get('cause_ids')
    if cause_ids is not None:
        if not isinstance(cause_ids, list) or not all(isinstance(c, int) for c in cause_ids):
            return False, 'cause_ids должен быть списком целых чисел'

    return True, None


def sanitize_article_data(data: dict) -> dict:
    """Оставляет только разрешённые поля, отсекая всё остальное —
    та же защита от лишних/чужих ключей в payload, что и
    sanitize_engine_data для engines."""
    clean = {k: data[k] for k in ARTICLE_FIELDS if k in data}
    if 'title' in clean:
        clean['title'] = clean['title'].strip()
    if 'symptom' in clean:
        clean['symptom'] = clean['symptom'].strip()
    return clean


def validate_dictionary_payload(data: dict):
    """Валидация для failure_mode/failure_cause — оба справочника имеют
    одинаковую форму (code, name, description), общая проверка."""
    if not isinstance(data, dict):
        return False, 'Некорректный формат данных'

    code = (data.get('code') or '').strip()
    if not code:
        return False, 'Код обязателен'
    if not code.replace('_', '').isalnum() or not code.isupper():
        return False, 'Код должен быть в формате UPPER_SNAKE_CASE'

    name = (data.get('name') or '').strip()
    if not name:
        return False, 'Название обязательно'

    return True, None


def sanitize_dictionary_data(data: dict) -> dict:
    clean = {k: data[k] for k in ('code', 'name', 'description') if k in data}
    if 'code' in clean:
        clean['code'] = clean['code'].strip().upper()
    if 'name' in clean:
        clean['name'] = clean['name'].strip()
    return clean
