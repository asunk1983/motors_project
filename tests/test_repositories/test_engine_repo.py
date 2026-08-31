"""Тесты для repositories/engine_repo.py"""
import pytest
from repositories.engine_repo import (
    get_by_id, get_with_details, get_all, count_all,
    create, update, delete, update_photo_count, get_by_filename,
    get_modes_for_engine, get_works_for_engine
)


@pytest.fixture
def sample_engine_data():
    return {
        'location': 'Цех 1',
        'engine_type': 'АИР112М4У2',
        'serial_number': 'SN12345',
        'manufacturer': 'ЭДМ',
        'purpose': 'Вентиляция',
        'workshop': '1',
    }


class TestCreateAndGet:
    def test_create_and_get_by_id(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        assert engine_id > 0

        engine = get_by_id(db_conn, engine_id)
        assert engine['location'] == 'Цех 1'
        assert engine['engine_type'] == 'АИР112М4У2'
        assert engine['serial_number'] == 'SN12345'

    def test_get_by_id_not_found(self, db_conn):
        assert get_by_id(db_conn, 99999) is None

    def test_get_with_details(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        from repositories.mode_repo import replace_all as replace_modes
        from repositories.work_repo import replace_all as replace_works

        replace_modes(db_conn, engine_id, [
            {'frequency': '50', 'power': '1.5', 'voltage': '380',
             'connection_type': 'ЗВ', 'current': '2.5', 'rpm': '1420'}
        ])
        replace_works(db_conn, engine_id, [
            {'work_number': '1', 'date': '2024-01-15',
             'work_description': 'Проверка', 'isolation': '0.5',
             'inspection': 'ГУД', 'signature': 'Иванов'}
        ])

        engine = get_with_details(db_conn, engine_id)
        assert engine['modes'] is not None
        assert len(engine['modes']) == 1
        assert engine['modes'][0]['frequency'] == '50'
        assert engine['works'] is not None
        assert len(engine['works']) == 1
        assert engine['works'][0]['work_number'] == '1'


class TestUpdate:
    def test_update(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        result = update(db_conn, engine_id, {'location': 'Цех 2', 'note': 'Обновлено'})
        assert result is True

        engine = get_by_id(db_conn, engine_id)
        assert engine['location'] == 'Цех 2'
        assert engine['note'] == 'Обновлено'

    def test_update_not_found(self, db_conn):
        result = update(db_conn, 99999, {'location': 'Цех 2'})
        assert result is False

    def test_update_empty_data(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        result = update(db_conn, engine_id, {})
        assert result is True


class TestDelete:
    def test_delete(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        result = delete(db_conn, engine_id)
        assert result is True
        assert get_by_id(db_conn, engine_id) is None

    def test_delete_not_found(self, db_conn):
        result = delete(db_conn, 99999)
        assert result is False

    def test_delete_cascades_modes_and_works(self, db_conn, sample_engine_data):
        """Удаление двигателя должно каскадно удалять modes и works."""
        from repositories.mode_repo import replace_all as replace_modes
        from repositories.work_repo import replace_all as replace_works

        engine_id = create(db_conn, sample_engine_data)
        replace_modes(db_conn, engine_id, [
            {'frequency': '50', 'power': '1.5', 'voltage': '380',
             'connection_type': 'ЗВ', 'current': '2.5', 'rpm': '1420'}
        ])
        replace_works(db_conn, engine_id, [
            {'work_number': '1', 'date': '2024-01-15',
             'work_description': 'Проверка', 'isolation': '0.5',
             'inspection': 'ГУД', 'signature': 'Иванов'}
        ])

        # Проверяем, что режимы и работы существуют
        assert len(get_modes_for_engine(db_conn, engine_id)) == 1
        assert len(get_works_for_engine(db_conn, engine_id)) == 1

        # Удаляем двигатель — должно каскадно удалить и modes, и works
        result = delete(db_conn, engine_id)
        assert result is True

        # Двигатель удалён
        assert get_by_id(db_conn, engine_id) is None

        # Режимы и работы тоже удалены
        assert get_modes_for_engine(db_conn, engine_id) == []
        assert get_works_for_engine(db_conn, engine_id) == []


class TestGetAll:
    def test_get_all_empty(self, db_conn):
        engines = get_all(db_conn)
        assert engines == []

    def test_get_all_with_data(self, db_conn, sample_engine_data):
        create(db_conn, sample_engine_data)
        create(db_conn, {**sample_engine_data, 'location': 'Цех 2', 'serial_number': 'SN67890'})

        engines = get_all(db_conn, limit=30, offset=0)
        assert len(engines) == 2

    def test_get_all_pagination(self, db_conn, sample_engine_data):
        for i in range(5):
            create(db_conn, {**sample_engine_data, 'serial_number': f'SN{i}'})

        engines = get_all(db_conn, limit=2, offset=0)
        assert len(engines) == 2

        engines = get_all(db_conn, limit=2, offset=2)
        assert len(engines) == 2

    def test_count_all(self, db_conn, sample_engine_data):
        assert count_all(db_conn) == 0
        create(db_conn, sample_engine_data)
        create(db_conn, {**sample_engine_data, 'serial_number': 'SN67890'})
        assert count_all(db_conn) == 2

    def test_search(self, db_conn, sample_engine_data):
        create(db_conn, sample_engine_data)
        create(db_conn, {**sample_engine_data, 'serial_number': 'SN67890', 'location': 'Цех 2'})

        results = get_all(db_conn, search_field='all', search_query='Цех 2')
        assert len(results) == 1
        assert results[0]['location'] == 'Цех 2'


class TestPhotoCount:
    def test_update_photo_count(self, db_conn, sample_engine_data):
        engine_id = create(db_conn, sample_engine_data)
        update_photo_count(db_conn, engine_id, 5)
        engine = get_by_id(db_conn, engine_id)
        assert engine['photo_count'] == 5


class TestGetByFilename:
    def test_get_by_filename(self, db_conn, sample_engine_data):
        data = {**sample_engine_data, 'filename': 'test_file.xlsx'}
        engine_id = create(db_conn, data)
        engine = get_by_filename(db_conn, 'test_file.xlsx')
        assert engine is not None
        assert engine['id'] == engine_id

    def test_get_by_filename_not_found(self, db_conn):
        assert get_by_filename(db_conn, 'nonexistent.xlsx') is None
