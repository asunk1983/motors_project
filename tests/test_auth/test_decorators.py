"""Тесты декораторов авторизации (modules/auth/decorators.py).

Подменяем служебную get_current_user заглушкой — сама проверка токена
покрывается в test_tokens.py; здесь важен контракт декораторов (401/403).
"""
import pytest
from flask import Flask, jsonify, request

from modules.auth import decorators


@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route('/protected')
    @decorators.require_auth
    def protected():
        return jsonify({'ok': True, 'user': request.current_user.get('username')})

    @app.route('/echo-current')
    @decorators.require_auth
    def echo_current():
        return jsonify({'id': request.current_user['id']})

    @app.route('/admin-only')
    @decorators.require_admin
    def admin_only():
        return jsonify({'ok': True, 'user': request.current_user.get('username')})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _fake_user(**overrides):
    user = {'id': 1, 'username': 'petrov', 'role': 'user', 'display_name': 'Петров Пётр'}
    user.update(overrides)
    return user


class TestRequireAuth:
    def test_missing_token_401(self, client):
        assert client.get('/protected').status_code == 401

    def test_invalid_token_401(self, client, monkeypatch):
        monkeypatch.setattr(decorators, 'get_current_user', lambda: None)
        assert client.get('/protected', headers={'Authorization': 'Bearer bad'}).status_code == 401

    def test_valid_ok(self, client, monkeypatch):
        monkeypatch.setattr(decorators, 'get_current_user', lambda: _fake_user())
        r = client.get('/protected', headers={'Authorization': 'Bearer good'})
        assert r.status_code == 200 and r.get_json()['user'] == 'petrov'

    def test_current_user_set(self, client, monkeypatch):
        monkeypatch.setattr(decorators, 'get_current_user', lambda: _fake_user(id=42))
        r = client.get('/echo-current', headers={'Authorization': 'Bearer good'})
        assert r.get_json()['id'] == 42


class TestRequireAdmin:
    def test_missing_token_401(self, client):
        assert client.get('/admin-only').status_code == 401

    def test_non_admin_403(self, client, monkeypatch):
        monkeypatch.setattr(decorators, 'get_current_user', lambda: _fake_user(role='user'))
        assert client.get('/admin-only', headers={'Authorization': 'Bearer t'}).status_code == 403

    def test_admin_ok(self, client, monkeypatch):
        monkeypatch.setattr(decorators, 'get_current_user', lambda: _fake_user(role='admin'))
        assert client.get('/admin-only', headers={'Authorization': 'Bearer t'}).status_code == 200


class TestExtractBearerToken:
    def test_from_header(self, app):
        with app.test_request_context(headers={'Authorization': 'Bearer abc123'}):
            assert decorators._extract_bearer_token() == 'abc123'

    def test_from_query(self, app):
        with app.test_request_context('/x?token=abc123'):
            assert decorators._extract_bearer_token() == 'abc123'

    def test_none(self, app):
        with app.test_request_context('/x'):
            assert decorators._extract_bearer_token() is None

    def test_query_fallback_when_no_bearer(self, app):
        with app.test_request_context('/x?token=abc123', headers={'Authorization': 'Basic xyz'}):
            assert decorators._extract_bearer_token() == 'abc123'