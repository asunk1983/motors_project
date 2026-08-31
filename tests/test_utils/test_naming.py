"""Тесты для utils/naming.py"""
from utils.naming import normalize_base_name


class TestNormalizeBaseName:
    def test_simple_filename(self):
        assert normalize_base_name('engine_123.png') == 'engine_123'

    def test_with_extension(self):
        assert normalize_base_name('motor.xlsx') == 'motor'

    def test_special_chars_replaced(self):
        result = normalize_base_name('file<name>:"/\\|?*.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result

    def test_empty_filename_with_engine_id(self):
        assert normalize_base_name('', engine_id=42) == 'engine_42'

    def test_none_filename_with_engine_id(self):
        assert normalize_base_name(None, engine_id=42) == 'engine_42'

    def test_no_extension(self):
        assert normalize_base_name('plainname') == 'plainname'

    def test_multiple_dots(self):
        assert normalize_base_name('file.name.with.dots.xlsx') == 'file.name.with.dots'
