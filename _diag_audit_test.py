import sqlite3
import sys
import importlib.util
from datetime import datetime

DB_PATH = r'C:\motors_project\engine_data.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Actor с именем для записи в аудит
ACTOR = {'id': 1, 'username': 'Cline', 'display_name': 'Cline (тест)'}

print('=' * 70)
print('ПРИЛОЖЕНИЕ АУДИТА ИЗМЕНЕНИЙ (audit_log)')
print('=' * 70)
print()

# Сначала сбросим audit_log для чистого теста
cur.execute('DELETE FROM audit_log')
conn.commit()
print('✓ audit_log очищен для теста')

print('\n--- Данные до изменений ---')

# engines
engines_before = cur.execute('SELECT id, workshop, purpose FROM engines WHERE id = 1').fetchone()
print(f'engine id=1: workshop={engines_before["workshop"]}, purpose={engines_before["purpose"]}')

# equipment
equipment_before = cur.execute('SELECT id, name, workshop, criticality FROM equipment WHERE id = 1').fetchone()
print(f'equipment id=1: name={equipment_before["name"]}, workshop={equipment_before["workshop"]}, criticality={equipment_before["criticality"]}')

# incident_ticket
incident_before = cur.execute('SELECT id, problem, priority FROM incident_ticket WHERE id = 1').fetchone()
print(f'incident_ticket id=1: problem={incident_before["problem"][:30]}..., priority={incident_before["priority"]}')

print('\n--- audit_log (до изменений) ---')
cur.execute('SELECT COUNT(*) AS cnt FROM audit_log')
print('Всего записей:', cur.fetchone()[0])

# ------------------------------------------------------------------------
# 1. Изменить двигатель: workshop, purpose
print('\n' + '=' * 70)
print('ШАГ 1: edit engine #1 (изменяем workshop и purpose)')
print('=' * 70)

spec = importlib.util.spec_from_file_location('engine_repo', r'C:\motors_project\repositories\engine_repo.py')
engine_repo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine_repo)

engine_id = 1
ok = engine_repo.update(conn, engine_id, {'workshop': '3507', 'purpose': 'извлечения'}, actor=ACTOR)
print(f'Результат: {ok}')

print('\n--- audit_log после изменения двигателя ---')
cur.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 10')
for row in cur.fetchall():
    print(f'  field: {row["field_name"]}, old: "{row["old_value"]}", new: "{row["new_value"]}", by: {row["changed_by_display_name"]}')

# ------------------------------------------------------------------------
# 2. Изменить оборудование: name, criticality
print('\n' + '=' * 70)
print('ШАГ 2: edit equipment #1 (изменяем name и criticality)')
print('=' * 70)

spec2 = importlib.util.spec_from_file_location('equipment_repo', r'C:\motors_project\repositories\equipment_repo.py')
equipment_repo = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(equipment_repo)

equipment_id = 1
ok2 = equipment_repo.update_equipment(conn, equipment_id, {
    'equipment_type_id': 1,
    'name': 'Автоматический выключатель MCCB',
    'workshop': equipment_before['workshop'],  # не меняем
    'criticality': 3,  # целое число от 1 до 5 (grade - средний)
}, actor=ACTOR)
print(f'Результат: {ok2}')

print('\n--- audit_log после изменения оборудования ---')
cur.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 10')
for row in cur.fetchall():
    print(f'  field: {row["field_name"]}, old: "{row["old_value"]}", new: "{row["new_value"]}", by: {row["changed_by_display_name"]}')

# ------------------------------------------------------------------------
# 3. Изменить заявку инцидента: priority
print('\n' + '=' * 70)
print('ШАГ 3: edit incident_ticket #1 (изменяем priority)')
print('=' * 70)

spec3 = importlib.util.spec_from_file_location('incident_ticket_repo', r'C:\motors_project\repositories\incident_ticket_repo.py')
incident_ticket_repo = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(incident_ticket_repo)

incident_id = 1
ok3 = incident_ticket_repo.update(conn, incident_id, actor=ACTOR, priority='high', problem='Нужно укоротить длину кабеля двигателя ножа после установки (обновлено)')
print(f'Результат: {ok3}')

print('\n--- audit_log после изменения заявки ---')
cur.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 10')
for row in cur.fetchall():
    print(f'  field: {row["field_name"]}, old: "{row["old_value"]}", new: "{row["new_value"]}", by: {row["changed_by_display_name"]}')

# ------------------------------------------------------------------------
# 4. Ложные изменения (ничего не меняем)
print('\n' + '=' * 70)
print('ШАГ 4: LОЖНЫЕ ИЗМЕНЕНИЯ (сохраняем без изменений)')
print('=' * 70)

# Получаем текущие значения
engine_curr = cur.execute('SELECT workshop, purpose FROM engines WHERE id = 1').fetchone()
equipment_curr = cur.execute('SELECT equipment_type_id, name, workshop, criticality FROM equipment WHERE id = 1').fetchone()

print(f'engine: workshop={engine_curr["workshop"]}, purpose={engine_curr["purpose"]} (ничего не меняем)')
print(f'equipment: criticality={equipment_curr["criticality"]} (ничего не меняем)')
print(f'incident: priority=high (ничего не меняем)')

count_before = cur.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0]

# Пытаемся сохранить без изменений
engine_repo.update(conn, engine_id, {'workshop': engine_curr['workshop'], 'purpose': engine_curr['purpose']}, actor=ACTOR)
equipment_repo.update_equipment(conn, equipment_id, {
    'equipment_type_id': equipment_curr['equipment_type_id'],
    'name': equipment_curr['name'],
    'workshop': equipment_curr['workshop'],
    'criticality': equipment_curr['criticality'],
}, actor=ACTOR)
incident_ticket_repo.update(conn, incident_id, actor=ACTOR, priority='high')

count_after = cur.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0]

print(f'\nЗаписей в audit_log ДО: {count_before}, ПОСЛЕ: {count_after}')
if count_after == count_before:
    print('✓ Успешно: без реальных изменений записи аудита не добавлены!')
else:
    print(f'✗ Ошибка: добавлено {count_after - count_before} новых записей!')

conn.close()
print('\n' + '=' * 70)
print('ТЕСТ ЗАВЕРШЁН')
print('=' * 70)