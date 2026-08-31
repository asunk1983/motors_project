"""Тесты для utils/date.py"""
from utils.date import format_ru_date, is_valid_iso_date


class TestFormatRuDate:
    def test_standard_date(self):
        assert format_ru_date('2024-01-15') == '15.01.2024'

    def test_another_date(self):
        assert format_ru_date('2023-12-31') == '31.12.2023'

    def test_empty_string(self):
        assert format_ru_date('') == ''

    def test_none(self):
        assert format_ru_date(None) == ''

    def test_non_date_string(self):
        assert format_ru_date('not-a-date') == 'not-a-date'

    def test_partial_date(self):
        assert format_ru_date('2024-01') == '2024-01'


class TestIsValidIsoDate:
    def test_valid_date(self):
        assert is_valid_iso_date('2024-01-15') is True

    def test_invalid_format(self):
        assert is_valid_iso_date('15.01.2024') is False

    def test_empty(self):
        assert is_valid_iso_date('') is False

    def test_none(self):
        assert is_valid_iso_date(None) is False
