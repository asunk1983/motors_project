"""Тесты для knowledge_repo.py."""

import pytest


class TestFailureModeRepo:
    def test_list_empty(self, db_conn):
        from repositories.knowledge_repo import list_failure_modes
        rows = list_failure_modes(db_conn)
        assert rows == []

    def test_create_and_list(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, list_failure_modes
        create_failure_mode(db_conn, code="FM01", name="Перегрев", description="Тест")
        rows = list_failure_modes(db_conn)
        assert len(rows) == 1
        assert rows[0]["code"] == "FM01"
        assert rows[0]["name"] == "Перегрев"

    def test_in_use_false(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, failure_mode_in_use
        mid = create_failure_mode(db_conn, code="FM02", name="Тест")
        assert failure_mode_in_use(db_conn, mid) is False

    def test_in_use_true(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, create_article, failure_mode_in_use
        mid = create_failure_mode(db_conn, code="FM03", name="Тест")
        create_article(db_conn, {"title": "Статья", "failure_mode_id": mid})
        assert failure_mode_in_use(db_conn, mid) is True

    def test_delete(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, delete_failure_mode
        mid = create_failure_mode(db_conn, code="FM04", name="Удалить")
        result = delete_failure_mode(db_conn, mid)
        assert result is True


class TestFailureCauseRepo:
    def test_list_empty(self, db_conn):
        from repositories.knowledge_repo import list_failure_causes
        rows = list_failure_causes(db_conn)
        assert rows == []

    def test_create_and_list(self, db_conn):
        from repositories.knowledge_repo import create_failure_cause, list_failure_causes
        create_failure_cause(db_conn, code="CC01", name="Износ")
        rows = list_failure_causes(db_conn)
        assert len(rows) == 1
        assert rows[0]["code"] == "CC01"

    def test_in_use_false(self, db_conn):
        from repositories.knowledge_repo import create_failure_cause, failure_cause_in_use
        cid = create_failure_cause(db_conn, code="CC02", name="Тест")
        assert failure_cause_in_use(db_conn, cid) is False

    def test_in_use_true(self, db_conn):
        from repositories.knowledge_repo import create_failure_cause, create_article, failure_cause_in_use
        cid = create_failure_cause(db_conn, code="CC03", name="Тест")
        create_article(db_conn, {"title": "Статья", "cause_ids": [cid]})
        assert failure_cause_in_use(db_conn, cid) is True

    def test_delete(self, db_conn):
        from repositories.knowledge_repo import create_failure_cause, delete_failure_cause
        cid = create_failure_cause(db_conn, code="CC04", name="Удалить")
        result = delete_failure_cause(db_conn, cid)
        assert result is True
class TestKnowledgeArticleRepo:
    def test_get_by_id_nonexistent(self, db_conn):
        from repositories.knowledge_repo import get_article_by_id
        assert get_article_by_id(db_conn, 99999) is None

    def test_create_article(self, db_conn):
        from repositories.knowledge_repo import create_article
        aid = create_article(db_conn, {"title": "Перегрев подшипника", "symptom": "Температура 80°C"})
        assert aid > 0

    def test_get_by_id_returns_created(self, db_conn):
        from repositories.knowledge_repo import create_article, get_article_by_id
        aid = create_article(db_conn, {"title": "Вибрация", "symptom": "Уровень 10 мм/с"})
        row = get_article_by_id(db_conn, aid)
        assert row is not None
        assert row["title"] == "Вибрация"
        assert row["symptom"] == "Уровень 10 мм/с"

    def test_list_articles_empty(self, db_conn):
        from repositories.knowledge_repo import list_articles
        rows = list_articles(db_conn)
        assert rows == []

    def test_list_articles_returns_all(self, db_conn):
        from repositories.knowledge_repo import create_article, list_articles
        create_article(db_conn, {"title": "Статья 1"})
        create_article(db_conn, {"title": "Статья 2"})
        rows = list_articles(db_conn)
        assert len(rows) == 2

    def test_list_articles_filter_by_failure_mode(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, create_article, list_articles
        mid1 = create_failure_mode(db_conn, code="FM10", name="Режим 1")
        mid2 = create_failure_mode(db_conn, code="FM11", name="Режим 2")
        create_article(db_conn, {"title": "А1", "failure_mode_id": mid1})
        create_article(db_conn, {"title": "А2", "failure_mode_id": mid2})
        rows = list_articles(db_conn, failure_mode_id=mid1)
        assert len(rows) == 1
        assert rows[0]["title"] == "А1"

    def test_update_article(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, create_failure_cause, create_article, update_article, get_article_by_id
        mode_id = create_failure_mode(db_conn, code="FM300", name="Mode")
        cause1_id = create_failure_cause(db_conn, code="FC301", name="Cause1")
        cause2_id = create_failure_cause(db_conn, code="FC302", name="Cause2")
        article_id = create_article(db_conn, {"title": "Статья", "symptom": "Symptom", "failure_mode_id": mode_id, "cause_ids": [cause1_id]})
        updated = update_article(db_conn, article_id, {"title": "Updated Article", "symptom": "NewSymptom", "cause_ids": [cause2_id]}, actor={"id": 1, "username": "admin"})
        assert updated is True
        article = get_article_by_id(db_conn, article_id)
        assert article["title"] == "Updated Article"
        assert article["symptom"] == "NewSymptom"
        cur = db_conn.cursor()
        cur.execute("SELECT failure_cause_id FROM knowledge_article_cause WHERE knowledge_article_id = ?", (article_id,))
        cause_rows = [r[0] for r in cur.fetchall()]
        assert cause2_id in cause_rows
        assert cause1_id not in cause_rows

    def test_update_article_nonexistent(self, db_conn):
        from repositories.knowledge_repo import update_article
        updated = update_article(db_conn, 99999, {"title": "Test"}, actor=None)
        assert updated is False

    def test_delete_article(self, db_conn):
        from repositories.knowledge_repo import create_failure_mode, create_failure_cause, create_article, delete_article, get_article_by_id
        mode_id = create_failure_mode(db_conn, code="FM400", name="Mode")
        cause_id = create_failure_cause(db_conn, code="FC400", name="Cause")
        article_id = create_article(db_conn, {"title": "Статья для удаления", "symptom": "Symptom", "failure_mode_id": mode_id, "cause_ids": [cause_id]})
        ok = delete_article(db_conn, article_id)
        assert ok is True
        assert get_article_by_id(db_conn, article_id) is None
        cur = db_conn.cursor()
        cur.execute("SELECT 1 FROM knowledge_article_cause WHERE knowledge_article_id = ?", (article_id,))
        assert cur.fetchone() is None

    def test_delete_article_nonexistent(self, db_conn):
        from repositories.knowledge_repo import delete_article
        ok = delete_article(db_conn, 99999)
        assert ok is False