"""Маршруты поиска: подсказки и расширенный поиск двигателей.

Вынесено из app.py.
"""
from flask import Blueprint, request, jsonify

from modules.db import db_connection, ENGINE_COLUMNS, MODE_COLUMNS, ENGINE_COLUMNS_ORDERED

search_bp = Blueprint('search', __name__, url_prefix='/api')


@search_bp.route('/search-suggestions', methods=['GET'])
def search_suggestions():
    try:
        field = request.args.get('field', '')
        query = request.args.get('query', '')

        if not field:
            return jsonify([])

        if field in ENGINE_COLUMNS:
            table = 'engines'
        elif field in MODE_COLUMNS:
            table = 'operating_modes'
        else:
            return jsonify([])

        with db_connection() as conn:
            cursor = conn.cursor()
            if query:
                cursor.execute(f'''
                    SELECT DISTINCT {field}
                    FROM {table}
                    WHERE {field} LIKE ? AND {field} != '' AND {field} IS NOT NULL
                    ORDER BY {field}
                    LIMIT 50
                ''', (f'%{query}%',))
            else:
                cursor.execute(f'''
                    SELECT DISTINCT {field}
                    FROM {table}
                    WHERE {field} != '' AND {field} IS NOT NULL
                    ORDER BY {field}
                    LIMIT 50
                ''')
            suggestions = [str(row[0]) for row in cursor.fetchall() if row[0]]

        return jsonify(suggestions)
    except Exception:
        return jsonify([])


# Whitelist-словари для безопасной сборки SQL в расширенном поиске
_SEARCH_ENGINE_COL_MAP = {c: f'e.{c}' for c in ENGINE_COLUMNS}
_SEARCH_MODE_COL_MAP = {c: f'm.{c}' for c in MODE_COLUMNS}

# Операторы, требующие числовое приведение значения
_NUMERIC_OPS = {'gt', 'lt', 'between'}

# Поля, в которых пользователь иногда пишет диапазон вместо одного числа
# (например "220-240" в напряжении вместо "230"). Новое поле ввода под это
# заводить не стали — значение остаётся обычным текстом в той же колонке,
# а числовые операторы поиска (>, <, между) сами распознают дефис как
# разделитель диапазона и сравнивают по его границам. Список ограничен
# только техническими параметрами режима/характеристик, где диапазон
# физически осмыслен — отрицательных значений у них не бывает, поэтому
# "-" однозначно читается как разделитель, а не как знак минуса.
_RANGE_CAPABLE_FIELDS = {'power', 'voltage', 'frequency', 'rpm', 'current', 'shaft_diameter'}


def _coerce_numeric(val):
    """
    Пытается привести значение к float.
    Возвращает (float_val, None) при успехе, или (None, error_msg) при неудаче.
    """
    try:
        return float(str(val).replace(',', '.')), None
    except (ValueError, TypeError):
        return None, f'Значение "{val}" должно быть числом'


def _range_bounds_sql(col):
    """
    Возвращает пару SQL-выражений (min_expr, max_expr) для колонки col.

    Если значение в колонке содержит дефис (например '220-240') — это
    диапазон, min/max берутся из его частей. Если дефиса нет (обычное
    '230') — min и max совпадают и равны самому числу, т.е. поведение
    для "обычных" значений не меняется по сравнению с прежним
    CAST(col AS REAL). REPLACE(...,',','.') — та же терпимость к
    десятичной запятой, что и в _coerce_numeric() для введённого значения.
    CAST нечисловой/пустой строки в SQLite тихо даёт 0.0 — так же, как
    вело себя старое поведение, отдельно не обрабатываем.
    """
    single = f"CAST(REPLACE({col}, ',', '.') AS REAL)"
    left = f"CAST(REPLACE(SUBSTR({col}, 1, INSTR({col}, '-') - 1), ',', '.') AS REAL)"
    right = f"CAST(REPLACE(SUBSTR({col}, INSTR({col}, '-') + 1), ',', '.') AS REAL)"
    min_expr = f"(CASE WHEN INSTR({col}, '-') > 0 THEN {left} ELSE {single} END)"
    max_expr = f"(CASE WHEN INSTR({col}, '-') > 0 THEN {right} ELSE {single} END)"
    return min_expr, max_expr


@search_bp.route('/engines/search', methods=['POST'])
def search_engines_advanced():
    try:
        data = request.json
        conditions = data.get('conditions', [])

        if not conditions:
            return jsonify({'error': 'Не указаны параметры поиска'}), 400

        engine_where, mode_where = [], []
        engine_params, mode_params = [], []
        has_mode_condition = False

        for cond in conditions:
            field = cond.get('field', '')
            op = cond.get('operator', 'contains')
            value = cond.get('value', '')
            value2 = cond.get('value2', '')

            if not field or not value:
                continue

            # Безопасный lookup колонки через whitelist-словарь (никакой конкатенации пользовательского ввода)
            if field in ENGINE_COLUMNS:
                target, tparams, col = engine_where, engine_params, _SEARCH_ENGINE_COL_MAP[field]
            elif field in MODE_COLUMNS:
                target, tparams, col = mode_where, mode_params, _SEARCH_MODE_COL_MAP[field]
                has_mode_condition = True
            else:
                continue

            if op == 'contains':
                target.append(f'{col} LIKE ?'); tparams.append(f'%{value}%')
            elif op == 'equals':
                target.append(f'{col} = ?'); tparams.append(value)
            elif op == 'starts':
                target.append(f'{col} LIKE ?'); tparams.append(f'{value}%')
            elif op == 'ends':
                target.append(f'{col} LIKE ?'); tparams.append(f'%{value}')
            elif op in _NUMERIC_OPS:
                # Для числовых операторов — валидируем и приводим к float ПЕРЕД подстановкой
                # _coerce_numeric возвращает (float_val, None) при успехе или (None, error_msg) при ошибке
                num_val, err = _coerce_numeric(value)
                if err:
                    return jsonify({'error': f'{err} для оператора \'{op}\' по полю \'{field}\''}), 400

                if field in _RANGE_CAPABLE_FIELDS:
                    min_expr, max_expr = _range_bounds_sql(col)
                else:
                    min_expr = max_expr = f'CAST({col} AS REAL)'

                if op == 'gt':
                    # "Больше X" — диапазон подходит, если его верхняя граница выше X
                    target.append(f'{max_expr} > ?'); tparams.append(num_val)
                elif op == 'lt':
                    # "Меньше X" — диапазон подходит, если его нижняя граница ниже X
                    target.append(f'{min_expr} < ?'); tparams.append(num_val)
                elif op == 'between' and value2:
                    num_val2, err2 = _coerce_numeric(value2)
                    if err2:
                        return jsonify({'error': f'{err2} для второго значения оператора \'{op}\' по полю \'{field}\''}), 400
                    if num_val > num_val2:
                        return jsonify({'error': f'Для оператора \'between\' по полю \'{field}\' первое значение ({num_val}) должно быть <= второму ({num_val2})'}), 400
                    # Пересечение искомого диапазона [num_val, num_val2] с диапазоном
                    # значения в БД [min_expr, max_expr] — а не строгое вхождение:
                    # если ищут "между 225 и 235", запись "220-240" тоже должна найтись
                    # (её диапазон захватывает часть искомого), не только записи
                    # с одиночным числом внутри интервала.
                    target.append(f'{min_expr} <= ? AND {max_expr} >= ?'); tparams.extend([num_val2, num_val])

        all_where = engine_where + mode_where
        if not all_where:
            return jsonify([])

        # Раньше здесь был фиксированный подмножество из 6-9 колонок — этого
        # хватало для старой таблицы результатов с жёстко заданными
        # столбцами, но не позволяло показать значение поля, если искали,
        # скажем, по 'shaft_diameter' или 'protection_class' (их просто не
        # было в SELECT). Теперь отдаём ВСЕ характеристики двигателя —
        # фронт (search.js) сам решает, какие колонки показать первыми
        # (искомые), а какие — как остальные.
        base_cols = [f'e.{c}' for c in ENGINE_COLUMNS_ORDERED]
        mode_cols = [
            'm.frequency AS mode_frequency', 'm.power AS mode_power', 'm.voltage AS mode_voltage',
            'm.connection_type AS mode_connection_type', 'm.current AS mode_current', 'm.rpm AS mode_rpm'
        ]
        params = engine_params + mode_params

        if has_mode_condition:
            # У двигателя может быть несколько режимов, подходящих под условия
            # поиска (например, две разные строки operating_modes с power=75).
            # Раньше здесь был SELECT DISTINCT по всем колонкам, включая
            # mode_*, из-за чего такой двигатель выводился в выдаче несколько
            # раз — по разу на каждый совпавший режим. ROW_NUMBER() оставляет
            # только один (первый по id) совпавший режим на двигатель, так что
            # каждый двигатель встречается в результате ровно один раз.
            query = f'''
                WITH matched AS (
                    SELECT {", ".join(base_cols)}, {", ".join(mode_cols)},
                           ROW_NUMBER() OVER (PARTITION BY e.id ORDER BY m.id) AS rn
                    FROM engines e
                    JOIN operating_modes m ON m.engine_id = e.id
                    WHERE {" AND ".join(all_where)}
                )
                SELECT * FROM matched WHERE rn = 1
                ORDER BY id DESC
            '''
        else:
            query = f'''
                SELECT DISTINCT {", ".join(base_cols)}
                FROM engines e
                WHERE {" AND ".join(all_where)}
                ORDER BY e.id DESC
            '''

        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            engines = [dict(row) for row in cursor.fetchall()]
            # rn — служебная колонка ROW_NUMBER(), фронту не нужна.
            for e in engines:
                e.pop('rn', None)

        return jsonify(engines)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
