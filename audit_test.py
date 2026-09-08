import sqlite3
import importlib.util

DB = r"C:\motors_project\engine_data.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

ACTOR = {"id": 1, "username": "Cline", "display_name": "Cline (test)"}

print("=" * 70)
print("AUDIT LOG VERIFICATION")
print("=" * 70)

# Clear audit log
cur.execute("DELETE FROM audit_log")
conn.commit()
print("audit_log cleared")

# Get current values
e = cur.execute("SELECT workshop, purpose FROM engines WHERE id = 1").fetchone()
eq = cur.execute("SELECT name, criticality, equipment_type_id FROM equipment WHERE id = 1").fetchone()
i = cur.execute("SELECT priority, problem FROM incident_ticket WHERE id = 1").fetchone()
print(f"Engine before: workshop={e['workshop']}, purpose={e['purpose']}")
print(f"Equipment before: name={eq['name']}, criticality={eq['criticality']}")
print(f"Incident before: priority={i['priority']}")

# Step 1: Update engine
spec = importlib.util.spec_from_file_location("engine_repo", r"C:\motors_project\repositories\engine_repo.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)
ok = er.update(conn, 1, {"workshop": "3508", "purpose": "machining_pump"}, actor=ACTOR)
print(f"Engine updated: {ok}")

print("audit_log after engine update:")
for r in cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 10"):
    print(f"  {r['field_name']}: {r['old_value']} -> {r['new_value']} by {r['changed_by_display_name']}")

# Step 2: Update equipment
spec2 = importlib.util.spec_from_file_location("eq_repo", r"C:\motors_project\repositories\equipment_repo.py")
er2 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(er2)
ok2 = er2.update_equipment(conn, 1, {"equipment_type_id": eq["equipment_type_id"], "name": "Circuit Breaker MCCB PRO", "criticality": 4}, actor=ACTOR)
print(f"Equipment updated: {ok2}")

print("audit_log after equipment update:")
for r in cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 10"):
    print(f"  {r['field_name']}: {r['old_value']} -> {r['new_value']} by {r['changed_by_display_name']}")

# Step 3: Update incident
spec3 = importlib.util.spec_from_file_location("inc_repo", r"C:\motors_project\repositories\incident_ticket_repo.py")
ir = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(ir)
ok3 = ir.update(conn, 1, actor=ACTOR, priority="high", problem="Need to shorten cable (updated)")
print(f"Incident updated: {ok3}")

print("audit_log after incident update:")
for r in cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 10"):
    print(f"  {r['field_name']}: {r['old_value']} -> {r['new_value']} by {r['changed_by_display_name']}")

# Step 4: Fake changes (no actual changes)
enew = cur.execute("SELECT workshop, purpose FROM engines WHERE id = 1").fetchone()
eqnew = cur.execute("SELECT name, criticality FROM equipment WHERE id = 1").fetchone()
inew = cur.execute("SELECT priority, problem FROM incident_ticket WHERE id = 1").fetchone()

print(f"Fake changes: engine={enew['workshop']}/{enew['purpose']}, eq={eqnew['name']}/{eqnew['criticality']}, inc={inew['priority']}")

cnt_before = cur.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
er.update(conn, 1, {"workshop": enew["workshop"], "purpose": enew["purpose"]}, actor=ACTOR)
er2.update_equipment(conn, 1, {"equipment_type_id": 1, "name": eqnew["name"], "criticality": eqnew["criticality"]}, actor=ACTOR)
ir.update(conn, 1, actor=ACTOR, priority=inew["priority"], problem=inew["problem"])
cnt_after = cur.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

print(f"audit_log: {cnt_before} -> {cnt_after}")
if cnt_after == cnt_before:
    print("PASS: No new audit entries for fake changes!")
else:
    print(f"FAIL: {cnt_after - cnt_before} new entries added!")

conn.close()
print("=" * 70)
print("DONE")
print("=" * 70)