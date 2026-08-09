"""Сервис экспорта в Excel.

Раньше вся логика экспорта (~200 строк) была в app.py:export_engines().
Теперь сервис оркестрирует: repository → build_workbook → bytes.
"""
import io
import logging

from repositories.engine_repo import get_with_details

logger = logging.getLogger(__name__)


def export_to_xlsx(conn, engine_ids: list[int]) -> bytes:
    """Экспортировать двигатели в Excel-файл.

    Возвращает bytes xlsx-файла (для отправки клиенту через Flask).
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    from PIL import Image as PILImage

    from utils.date import format_ru_date

    engines = []
    for eid in engine_ids:
        engine = get_with_details(conn, eid)
        if engine:
            engines.append(engine)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Паспорта двигателей'

    # --- Стили ---
    FONT = 'Calibri'
    BORDER = Border(
        left=Side(style='thin', color='D0D5DD'),
        right=Side(style='thin', color='D0D5DD'),
        top=Side(style='thin', color='D0D5DD'),
        bottom=Side(style='thin', color='D0D5DD'),
    )
    ALIGN_CENTER = Alignment(horizontal='center', vertical='center')
    ALIGN_LEFT = Alignment(vertical='center')
    FILL_PRIMARY = PatternFill(start_color='1B365D', end_color='1B365D', fill_type='solid')
    FILL_SECONDARY = PatternFill(start_color='EDF2F7', end_color='EDF2F7', fill_type='solid')
    FILL_ACCENT = PatternFill(start_color='E3F2FD', end_color='E3F2FD', fill_type='solid')

    # --- Ширина колонок ---
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 22
    ws.column_dimensions['C'].width = 22
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 18

    row = 1

    for engine in engines:
        # --- Шапка ---
        ws.cell(row=row, column=1, value='Паспорт двигателя')
        ws.cell(row=row, column=1).font = Font(name=FONT, size=14, bold=True, color='FFFFFF')
        ws.cell(row=row, column=1).fill = FILL_PRIMARY
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        row += 1

        # --- Характеристики ---
        ws.cell(row=row, column=1, value='Характеристика')
        ws.cell(row=row, column=1).font = Font(name=FONT, size=10, bold=True)
        ws.cell(row=row, column=2, value='Значение')
        ws.cell(row=row, column=2).font = Font(name=FONT, size=10, bold=True)
        row += 1

        char_fields = [
            ('Место установки', engine.get('location')),
            ('Тип двигателя', engine.get('engine_type')),
            ('Зав. номер', engine.get('serial_number')),
            ('Производитель', engine.get('manufacturer')),
            ('Назначение', engine.get('purpose')),
            ('Цех', engine.get('workshop')),
            ('Степень защиты', engine.get('protection_class')),
            ('Тип крепления', engine.get('mounting_type')),
            ('Диаметр вала (мм)', engine.get('shaft_diameter')),
            ('Подшипник передний', engine.get('bearing_front')),
            ('Подшипник задний', engine.get('bearing_rear')),
            ('Датчик температуры', engine.get('temp_sensor')),
            ('Энкодер', engine.get('encoder')),
            ('Охлаждение', engine.get('cooling')),
            ('Примечание', engine.get('note')),
        ]

        for label, value in char_fields:
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=1).font = Font(name=FONT, size=9)
            ws.cell(row=row, column=1).border = BORDER
            ws.cell(row=row, column=2, value=value or '—')
            ws.cell(row=row, column=2).font = Font(name=FONT, size=9)
            ws.cell(row=row, column=2).border = BORDER
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            row += 1

        row += 1  # отступ

        # --- Режимы работы ---
        ws.cell(row=row, column=1, value='⚡ Режимы работы')
        ws.cell(row=row, column=1).font = Font(name=FONT, size=11, bold=True, color='0F766E')
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        row += 1

        modes = engine.get('modes', [])
        if modes:
            headers = ['Частота, Гц', 'Мощность, кВт', 'Напряжение, В', 'Тип подкл.', 'Ток, А', 'Обороты, об/мин']
            for col, h in enumerate(headers, start=1):
                ws.cell(row=row, column=col, value=h)
                ws.cell(row=row, column=col).font = Font(name=FONT, size=9, bold=True)
                ws.cell(row=row, column=col).fill = FILL_SECONDARY
                ws.cell(row=row, column=col).border = BORDER
                ws.cell(row=row, column=col).alignment = ALIGN_CENTER
            row += 1

            for m in modes:
                for col, key in enumerate(['frequency', 'power', 'voltage', 'connection_type', 'current', 'rpm'], start=1):
                    ws.cell(row=row, column=col, value=m.get(key) or '—')
                    ws.cell(row=row, column=col).font = Font(name=FONT, size=9)
                    ws.cell(row=row, column=col).border = BORDER
                    ws.cell(row=row, column=col).alignment = ALIGN_CENTER
                row += 1
        else:
            ws.cell(row=row, column=1, value='Нет данных')
            ws.cell(row=row, column=1).font = Font(name=FONT, size=9, italic=True, color='9CA3AF')
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

        row += 1  # отступ

        # --- Произведённые работы ---
        ws.cell(row=row, column=1, value='🔧 Произведенные работы')
        ws.cell(row=row, column=1).font = Font(name=FONT, size=11, bold=True, color='4338CA')
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        row += 1

        works = engine.get('works', [])
        if works:
            headers = ['№ п/п', 'Дата', 'Вид производимых работ', 'Сопротивление изоляции', 'Внешний осмотр и проверка работы', 'ФИО исполнителя']
            for col, h in enumerate(headers, start=1):
                ws.cell(row=row, column=col, value=h)
                ws.cell(row=row, column=col).font = Font(name=FONT, size=9, bold=True)
                ws.cell(row=row, column=col).fill = FILL_SECONDARY
                ws.cell(row=row, column=col).border = BORDER
                ws.cell(row=row, column=col).alignment = ALIGN_CENTER
            row += 1

            for w in works:
                for col, key in enumerate(['work_number', 'date', 'work_description', 'isolation', 'inspection', 'signature'], start=1):
                    raw = w.get(key)
                    cell_value = format_ru_date(raw) if key == 'date' else raw
                    ws.cell(row=row, column=col, value=cell_value or '—')
                    ws.cell(row=row, column=col).font = Font(name=FONT, size=9)
                    ws.cell(row=row, column=col).border = BORDER
                    ws.cell(row=row, column=col).alignment = Alignment(vertical='center', wrap_text=(key == 'work_description'))
                row += 1
        else:
            ws.cell(row=row, column=1, value='Нет данных')
            ws.cell(row=row, column=1).font = Font(name=FONT, size=9, italic=True, color='9CA3AF')
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

        row += 1  # отступ перед фото

        # --- Фото ---
        photo_paths = _get_photo_paths(engine['id'])
        if photo_paths:
            ws.cell(row=row, column=1, value=f'📸 Фото ({len(photo_paths)})')
            ws.cell(row=row, column=1).font = Font(name=FONT, size=11, bold=True, color='1B365D')
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

            PHOTOS_PER_ROW = 3
            PHOTO_CELL_COLS = 2
            col_cursor = 1
            photo_row = row
            for i, p in enumerate(photo_paths):
                if i > 0 and i % PHOTOS_PER_ROW == 0:
                    photo_row = row + 1
                    row = photo_row
                    col_cursor = 1
                try:
                    img = XLImage(p)
                    img.width = 250
                    img.height = 190
                    ws.add_image(img, f'{_col_letter(col_cursor)}{row}')
                except Exception:
                    pass
                col_cursor += PHOTO_CELL_COLS
            row = photo_row + 1

        row += 2  # отступ между двигателями

    # --- Page setup ---
    ws.print_area = f'A1:F{row}'
    ws.print_options.fit_to_width = 1

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _get_photo_paths(engine_id: int) -> list[str]:
    """Получить пути к фото двигателя.

    ИСПРАВЛЕНО: раньше здесь была собственная реализация со старой схемой
    имён (`engine_{id}_...`), из-за чего экспорт молча не находил фото для
    любого двигателя, загруженного после перехода на актуальную схему
    (`ID{id}_...`). Теперь используется каноническая функция photo_manager —
    единственный источник истины для схемы именования и путей, вместо
    третьей независимой копии той же логики.
    """
    from modules.photo_manager.manager import engine_photo_disk_paths

    return engine_photo_disk_paths(engine_id)


def _col_letter(col: int) -> str:
    """Преобразует номер колонки в букву (1 -> 'A', 27 -> 'AA')."""
    result = ''
    while col > 0:
        col, rem = divmod(col - 1, 26)
        result = chr(65 + rem) + result
    return result
