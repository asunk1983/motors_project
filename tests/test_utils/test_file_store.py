"""Тесты для utils/file_store.py"""
import json
import os
import tempfile

from utils.file_store import load_json, save_json


class TestLoadJson:
    def test_load_existing_file(self, tmp_path):
        path = str(tmp_path / 'test.json')
        data = [{'id': 1, 'name': 'test'}]
        with open(path, 'w') as f:
            json.dump(data, f)
        result = load_json(path)
        assert result == data

    def test_load_nonexistent_file(self, tmp_path):
        path = str(tmp_path / 'nonexistent.json')
        result = load_json(path)
        assert result == []

    def test_load_nonexistent_with_default(self, tmp_path):
        path = str(tmp_path / 'nonexistent.json')
        result = load_json(path, default={'key': 'val'})
        assert result == {'key': 'val'}

    def test_load_corrupted_file(self, tmp_path):
        path = str(tmp_path / 'corrupt.json')
        with open(path, 'w') as f:
            f.write('{invalid json')
        result = load_json(path)
        assert result == []


class TestSaveJson:
    def test_save_and_load_roundtrip(self, tmp_path):
        path = str(tmp_path / 'roundtrip.json')
        data = [{'id': 1, 'name': 'test'}, {'id': 2, 'name': 'test2'}]
        save_json(path, data)
        result = load_json(path)
        assert result == data

    def test_save_creates_directory(self, tmp_path):
        path = str(tmp_path / 'subdir' / 'nested.json')
        save_json(path, [{'id': 1}])
        assert os.path.exists(path)

    def test_save_ensure_ascii_false(self, tmp_path):
        path = str(tmp_path / 'unicode.json')
        save_json(path, [{'name': 'Тест'}])
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'Тест' in content
        assert '\\u' not in content
