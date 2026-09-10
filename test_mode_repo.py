"""Тесты для ModeRepo."""

import pytest
from unittest.mock import Mock, patch

from your_module import ModeRepo  # ЗАМЕНИ на реальный путь


class TestModeRepo:
    """Набор тестов для ModeRepo."""

    def test_init_default(self):
        """Проверка инициализации."""
        repo = ModeRepo()
        assert repo is not None

    def test_get_mode(self):
        """Проверка получения режима."""
        repo = ModeRepo()
        assert repo.get_mode() == "default"

    def test_set_mode(self):
        """Проверка установки режима."""
        repo = ModeRepo()
        repo.set_mode("test")
        assert repo.get_mode() == "test"

    def test_validate_mode(self):
        """Проверка валидации режима."""
        repo = ModeRepo()
        assert repo.validate_mode("default") is True
        with pytest.raises(ValueError):
            repo.validate_mode("invalid")
