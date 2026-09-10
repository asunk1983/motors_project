"""Тесты утилиты логирования (utils/logging.py::log_message)."""
import os

from utils import logging as logging_util


def test_writes_to_file(tmp_path, monkeypatch):
    log_file = str(tmp_path / 'app.log')
    monkeypatch.setattr(logging_util, 'LOG_FILE', log_file)

    logging_util.log_message('Тестовое сообщение')

    assert os.path.exists(log_file)
    with open(log_file, encoding='utf-8') as f:
        content = f.read()
    assert content.startswith('[')
    assert '] Тестовое сообщение' in content


def test_appends_lines(tmp_path, monkeypatch):
    log_file = str(tmp_path / 'app.log')
    monkeypatch.setattr(logging_util, 'LOG_FILE', log_file)
    logging_util.log_message('Первое')
    logging_util.log_message('Второе')
    with open(log_file, encoding='utf-8') as f:
        assert len(f.read().strip().split('\n')) == 2


def test_prints_to_stdout(tmp_path, monkeypatch, capsys):
    log_file = str(tmp_path / 'app.log')
    monkeypatch.setattr(logging_util, 'LOG_FILE', log_file)
    logging_util.log_message('В консоль')
    assert 'В консоль' in capsys.readouterr().out