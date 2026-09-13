"""Тесты парсера Excel-паспортов двигателей (modules/engine_parser/parser.py).

Покрывают parse_engine_data, parse_operating_modes, parse_maintenance_works,
parse_file_fast и extract_images_from_excel на фиктивных xlsx-файлах,
создаваемых на лету через openpyxl во временной директории (tmp_path);
бинарники в репозиторий не кладутся.
"""
import zipfile

import numpy as np
import pytest
from openpyxl import Workbook


def _build_arr(values: dict, rows=40, cols=70):
    """Строит numpy-массив (строка, колонка) -> значение для парсера."""
    arr = np.empty((rows, cols), dtype=object)
    for (r, c), v in values.items():
        arr[r, c] = v
    return arr


def _make_xlsx(tmp_path, values: dict, sheet='Лист1') -> str:
    """Создаёт xlsx с данными в указанных координатах (строка, колонка)."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for (r, c), v in values.items():
        ws.cell(row=r + 1, column=c + 1, value=v)
    path = str(tmp_path / 'engine.xlsx')
    wb.save(path)
    return path


ENGINE_VALUES = {
    (9, 41): 'Назначение: насос',
    (10, 41): '№3 Линия A',
    (13, 50): 'АИР112М4У2',
    (14, 50): 'ЭДМ',
    (15, 50): 'SN12345',
    (22, 50): '2030',
    (23, 50): '1',
    (24, 50): '28',
    (25, 50): 'IP54',
    (26, 50): 'М1',
    (27, 50): 'DS18B20',
    (28, 50): '4096',
    (29, 50): 'IC1',
    (30, 50): 'заметка',
}


class TestParseEngineData:
    def test_parses_all_fields(self):
        from modules.engine_parser.parser import parse_engine_data
        data = parse_engine_data(_build_arr(ENGINE_VALUES), 'test.xlsx')
        assert data['filename'] == 'test.xlsx'
        assert data['purpose'] == 'Назначение: насос'
        assert data['workshop'] == '3'
        assert data['location'] == 'Линия A'
        assert data['engine_type'] == 'АИР112М4У2'
        assert data['manufacturer'] == 'ЭДМ'
        assert data['serial_number'] == 'SN12345'
        assert data['bearing_front'] == '2030'
        assert data['shaft_diameter'] == '28'
        assert data['protection_class'] == 'IP54'
        assert data['mounting_type'] == 'М1'
        assert data['temp_sensor'] == 'DS18B20'
        assert data['encoder'] == '4096'
        assert data['cooling'] == 'IC1'
        assert data['note'] == 'заметка'

    def test_workshop_without_number(self):
        from modules.engine_parser.parser import parse_engine_data
        values = dict(ENGINE_VALUES)
        values[(10, 41)] = 'Просто текст без номера'
        data = parse_engine_data(_build_arr(values), 'x.xlsx')
        assert data['workshop'] == ''
        assert data['location'] == ''

    def test_empty_cells_are_empty_strings(self):
        from modules.engine_parser.parser import parse_engine_data
        data = parse_engine_data(_build_arr({}), 'x.xlsx')
        assert data['purpose'] == ''
        assert data['engine_type'] == ''
        assert data['serial_number'] == ''
MODES_VALUES = {
    (16, 50): '50', (17, 50): '1.5', (18, 50): '380',
    (19, 50): 'ЗВ', (20, 50): '2.5', (21, 50): '1420',
    (16, 51): '60', (17, 51): '2.2', (18, 51): '220',
    (19, 51): 'Y', (20, 51): '5', (21, 51): '1750',
}


class TestParseOperatingModes:
    def test_parses_two_modes(self):
        from modules.engine_parser.parser import parse_operating_modes
        modes = parse_operating_modes(_build_arr(MODES_VALUES))
        assert len(modes) == 2
        assert modes[0]['frequency'] == '50'
        assert modes[0]['power'] == '1.5'
        assert modes[0]['voltage'] == '380'
        assert modes[0]['connection_type'] == 'ЗВ'
        assert modes[0]['current'] == '2.5'
        assert modes[0]['rpm'] == '1420'
        assert modes[1]['frequency'] == '60'

    def test_stops_at_first_empty_frequency(self):
        from modules.engine_parser.parser import parse_operating_modes
        values = dict(MODES_VALUES)
        del values[(16, 51)]  # вторая колонка без frequency — стоп
        modes = parse_operating_modes(_build_arr(values))
        assert len(modes) == 1

    def test_empty_arr_returns_empty(self):
        from modules.engine_parser.parser import parse_operating_modes
        assert parse_operating_modes(_build_arr({})) == []

    def test_text_in_frequency_returned_as_is(self):
        from modules.engine_parser.parser import parse_operating_modes
        values = {(16, 50): 'N/A', (17, 50): '?', (18, 50): 'x'}
        modes = parse_operating_modes(_build_arr(values))
        assert len(modes) == 1
        assert modes[0]['frequency'] == 'N/A'


WORKS_VALUES = {
    (39, 13): '1', (39, 15): '15.01.24', (39, 19): 'Замена масла',
    (39, 41): '0,5 МОм', (39, 45): 'ГУД', (39, 56): 'Иванов',
    (40, 13): '2', (40, 15): '01/02/2025', (40, 19): 'Замена подшипника',
    (40, 41): '1.2', (40, 45): 'ПВК', (40, 56): 'Петров',
}


class TestParseMaintenanceWorks:
    def test_parses_two_works_dates_and_isolation(self):
        from modules.engine_parser.parser import parse_maintenance_works
        works = parse_maintenance_works(_build_arr(WORKS_VALUES, rows=500))
        assert len(works) == 2
        w1 = works[0]
        assert w1['work_number'] == '1'
        assert w1['date'] == '2024-01-15'   # DD.MM.YY -> YYYY-MM-DD
        assert w1['work_description'] == 'Замена масла'
        assert w1['isolation'] == '0.5'      # "0,5 МОм" -> float -> "0.5"
        assert w1['inspection'] == 'ГУД'
        assert w1['signature'] == 'Иванов'
        w2 = works[1]
        assert w2['date'] == '2025-02-01'   # DD/MM/YYYY
        assert w2['isolation'] == '1.2'

    def test_empty_arr_returns_empty(self):
        from modules.engine_parser.parser import parse_maintenance_works
        assert parse_maintenance_works(_build_arr({}, rows=500)) == []
def _full_pasport_values():
    values = dict(ENGINE_VALUES)
    values.update(MODES_VALUES)
    values.update(WORKS_VALUES)
    return values


class TestParseFileFast:
    def test_success_on_valid_xlsx(self, tmp_path):
        from modules.engine_parser.parser import parse_file_fast
        path = _make_xlsx(tmp_path, _full_pasport_values())
        res = parse_file_fast(path)
        assert res['success'] is True
        assert res['filename'] == 'engine.xlsx'
        assert res['engine_tuple'] is not None
        # engine_tuple: (filename, purpose, workshop, location, engine_type, ...)
        assert res['engine_tuple'][0] == 'engine.xlsx'
        assert res['engine_tuple'][1] == 'Назначение: насос'
        assert len(res['modes']) == 2
        assert len(res['works']) == 2

    def test_missing_file_returns_error(self, tmp_path):
        from modules.engine_parser.parser import parse_file_fast
        res = parse_file_fast(str(tmp_path / 'nope.xlsx'))
        assert res['success'] is False
        assert 'не найден' in res['error']

    def test_empty_sheet_returns_error(self, tmp_path):
        from modules.engine_parser.parser import parse_file_fast
        path = _make_xlsx(tmp_path, {})
        res = parse_file_fast(path)
        assert res['success'] is False


class TestExtractImagesFromExcel:
    def test_extracts_media_from_xlsx_zip(self, tmp_path, monkeypatch):
        """XLSX — это ZIP; картинки лежат в xl/media/. Проверяем, что медиа
        извлекаются в PHOTOS_FOLDER. Собираем минимальный xlsx через openpyxl
        и доупаковываем в него файл картинки (как это делает Excel)."""
        from modules.engine_parser import parser
        monkeypatch.setattr(parser, 'PHOTOS_FOLDER', str(tmp_path))

        path = _make_xlsx(tmp_path, {(0, 0): 'x'}, sheet='Лист1')
        # Добавляем медиафайл в архив xlsx (как Excel: xl/media/image1.png)
        with zipfile.ZipFile(path, 'a') as zf:
            zf.writestr('xl/media/image1.png', b'fake-png-bytes')

        count = parser.extract_images_from_excel(
            path, filename='engine.xlsx', engine_id=7,
        )
        assert count == 1
        assert (tmp_path / 'ID7_1.png').read_bytes() == b'fake-png-bytes'