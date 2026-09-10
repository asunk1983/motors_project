"""Тесты хэширования паролей и токенов (modules/auth/hashing.py)."""
import re

from modules.auth.hashing import hash_password, verify_password, hash_token, generate_token


class TestPasswordHashing:
    def test_verify_correct(self):
        assert verify_password('secret123', hash_password('secret123')) is True

    def test_verify_wrong(self):
        assert verify_password('wrong', hash_password('secret123')) is False

    def test_verify_empty_hash_false(self):
        assert verify_password('secret123', '') is False

    def test_verify_none_hash_false(self):
        assert verify_password('secret123', None) is False

    def test_hash_is_salted(self):
        assert hash_password('secret123') != hash_password('secret123')

    def test_hash_no_plaintext(self):
        assert 'secret123' not in hash_password('secret123')


class TestTokenHashing:
    def test_deterministic(self):
        assert hash_token('mytoken') == hash_token('mytoken')

    def test_sha256_hex(self):
        assert re.fullmatch(r'[0-9a-f]{64}', hash_token('mytoken'))

    def test_differs(self):
        assert hash_token('a') != hash_token('b')


class TestGenerateToken:
    def test_urlsafe(self):
        assert re.fullmatch(r'[A-Za-z0-9_-]+', generate_token())

    def test_length_43(self):
        assert len(generate_token()) == 43   # 32 байта base64url без паддинга

    def test_unique(self):
        assert len({generate_token() for _ in range(100)}) == 100