"""Repository для базы знаний (failure_mode, failure_cause, knowledge_article).

Содержит ТОЛЬКО SQL-запросы. Бизнес-логика — в routes/ (как и у engine_repo —
в проекте нет отдельного слоя services/ для CRUD-операций, валидация вынесена
в schemas/).
Все функции принимают sqlite3.Connection как первый аргумент.
"""
from datetime import datetime


def _row_to_dict(row):
    """Преобразует sqlite3.Row в dict."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------------
# failure_mode / failure_cause — простые справочники, без soft-delete.
# Удаление защищено проверкой использования (см. ниже) вместо ON DELETE
# CASCADE/RESTRICT — та же логика, что и решение engine_repo.py::delete()
# не полагаться на FK-каскад продакшен-БД, только с обратным знаком:
# там нельзя ОСИРОТИТЬ дочерние записи, здесь нельзя УДАЛИТЬ то, что
# используется.
# ---------------------------------------------------------------------

def list_failure_modes(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM failure_mode ORDER BY name')
    return [_row_to_dict(row) for row in cur.fetchall()]


def list_failure_causes(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM failure_cause ORDER BY name')
    return [_row_to_dict(row) for row in cur.fetchall()]


def create_failure_mode(conn, code: str, name: str, description: str = None) -> int:
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO failure_mode (code, name, description) VALUES (?, ?, ?)',
        (code, name, description)
    )
    conn.commit()
    return cur.lastrowid


def create_failure_cause(conn, code: str, name: str, description: str = None) -> int:
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO failure_cause (code, name, description) VALUES (?, ?, ?)',
        (code, name, description)
    )
    conn.commit()
    return cur.lastrowid


def failure_mode_in_use(conn, failure_mode_id: int) -> bool:
    """True, если режим отказа используется хотя бы в одной статье базы
    знаний. Проверка по maintenance_works пока не нужна — база знаний
    ещё не привязана к двигателям (см. комментарий в modules/db.py)."""
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM knowledge_article WHERE failure_mode_id = ? LIMIT 1', (failure_mode_id,))
    return cur.fetchone() is not None


def failure_cause_in_use(conn, failure_cause_id: int) -> bool:
    """True, если причина используется хотя бы в одной статье базы знаний
    (через M2M). Проверка по maintenance_works пока не нужна — см.
    failure_mode_in_use выше."""
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM knowledge_article_cause WHERE failure_cause_id = ? LIMIT 1', (failure_cause_id,))
    return cur.fetchone() is not None


def delete_failure_mode(conn, failure_mode_id: int) -> bool:
    """Удалить режим отказа. Вызывающая сторона (routes) обязана сначала
    проверить failure_mode_in_use — repository здесь только выполняет SQL,
    без повторной проверки (как и delete() в engine_repo.py не проверяет
    предусловия сам, это ответственность роута)."""
    cur = conn.cursor()
    cur.execute('DELETE FROM failure_mode WHERE id = ?', (failure_mode_id,))
    conn.commit()
    return cur.rowcount > 0


def delete_failure_cause(conn, failure_cause_id: int) -> bool:
    cur = conn.cursor()
    cur.execute('DELETE FROM failure_cause WHERE id = ?', (failure_cause_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------
# knowledge_article
# ---------------------------------------------------------------------

def get_article_by_id(conn, article_id: int):
    cur = conn.cursor()
    cur.execute('SELECT * FROM knowledge_article WHERE id = ?', (article_id,))
    article = _row_to_dict(cur.fetchone())
    if article is None:
        return None
    article['causes'] = get_causes_for_article(conn, article_id)
    return article


def get_causes_for_article(conn, article_id: int):
    cur = conn.cursor()
    cur.execute('''
        SELECT fc.* FROM failure_cause fc
        JOIN knowledge_article_cause kac ON kac.failure_cause_id = fc.id
        WHERE kac.knowledge_article_id = ?
        ORDER BY fc.name
    ''', (article_id,))
    return [_row_to_dict(row) for row in cur.fetchall()]


def list_articles(conn, symptom_query: str = ''):
    """Список статей с краткой информацией (без causes — для списка не нужно,
    подтягивается отдельно на странице статьи, как modes/works у engine)."""
    cur = conn.cursor()
    if symptom_query:
        cur.execute('''
            SELECT ka.*, fm.name AS failure_mode_name
            FROM knowledge_article ka
            LEFT JOIN failure_mode fm ON fm.id = ka.failure_mode_id
            WHERE ka.symptom LIKE ? OR ka.title LIKE ?
            ORDER BY ka.updated_at DESC
        ''', (f'%{symptom_query}%', f'%{symptom_query}%'))
    else:
        cur.execute('''
            SELECT ka.*, fm.name AS failure_mode_name
            FROM knowledge_article ka
            LEFT JOIN failure_mode fm ON fm.id = ka.failure_mode_id
            ORDER BY ka.updated_at DESC
        ''')
    return [_row_to_dict(row) for row in cur.fetchall()]


def create_article(conn, data: dict) -> int:
    """Создать статью. Возвращает ID.

    В отличие от engines (см. engine_repo.py::create — явный поиск
    свободного id), здесь используется обычный AUTOINCREMENT: статей
    на порядки меньше, чем двигателей, "дыры" в нумерации не создают
    практических проблем, а конкурентное создание статей — не тот
    сценарий, для которого стоило городить BEGIN IMMEDIATE.
    """
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO knowledge_article
            (title, symptom, failure_mode_id, diagnostic_steps,
             recommended_action, reference_note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('title'), data.get('symptom'), data.get('failure_mode_id'),
        data.get('diagnostic_steps'), data.get('recommended_action'),
        data.get('reference_note'), now, now,
    ))
    article_id = cur.lastrowid
    _replace_article_causes(cur, article_id, data.get('cause_ids', []))
    conn.commit()
    return article_id


def update_article(conn, article_id: int, data: dict) -> bool:
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute('''
        UPDATE knowledge_article
        SET title = ?, symptom = ?, failure_mode_id = ?, diagnostic_steps = ?,
            recommended_action = ?, reference_note = ?, updated_at = ?
        WHERE id = ?
    ''', (
        data.get('title'), data.get('symptom'), data.get('failure_mode_id'),
        data.get('diagnostic_steps'), data.get('recommended_action'),
        data.get('reference_note'), now, article_id,
    ))
    updated = cur.rowcount > 0
    if updated and 'cause_ids' in data:
        _replace_article_causes(cur, article_id, data['cause_ids'])
    conn.commit()
    return updated


def _replace_article_causes(cur, article_id: int, cause_ids: list) -> None:
    """DELETE+INSERT связей статьи с причинами — тот же паттерн полной
    замены списка, что replace_all в mode_repo/work_repo для modes/works."""
    cur.execute('DELETE FROM knowledge_article_cause WHERE knowledge_article_id = ?', (article_id,))
    if cause_ids:
        cur.executemany(
            'INSERT INTO knowledge_article_cause (knowledge_article_id, failure_cause_id) VALUES (?, ?)',
            [(article_id, cid) for cid in cause_ids]
        )


def delete_article(conn, article_id: int) -> bool:
    """Удалить статью. knowledge_article_cause удаляется каскадно по схеме
    (ON DELETE CASCADE) — таблица новая, создана этим же патчем, поэтому
    каскад гарантированно работает (в отличие от старых таблиц проекта,
    где CASCADE мог быть добавлен в схему уже после создания продакшен-БД —
    см. PROJECT_CORE.md п.7.3). Явную очистку M2M добавляем всё равно —
    дёшево и единообразно с остальными delete() в проекте.
    """
    cur = conn.cursor()
    cur.execute('DELETE FROM knowledge_article_cause WHERE knowledge_article_id = ?', (article_id,))
    cur.execute('DELETE FROM knowledge_article WHERE id = ?', (article_id,))
    conn.commit()
    return cur.rowcount > 0
