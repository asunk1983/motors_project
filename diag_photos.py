import sqlite3, os, glob, re, sys
sys.stdout.reconfigure(encoding='utf-8')

from config.settings import PHOTOS_FOLDER, ALLOWED_PHOTO_EXT, DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('SELECT id, filename, photo_count FROM engines WHERE photo_count > 0 LIMIT 10')
rows = cur.fetchall()

def norm_base(filename, engine_id=None):
    base = os.path.splitext(filename or '')[0] or f'engine_{engine_id}'
    base = re.sub(r'[<>:"/\\|?*]', '_', base)
    return base

print("=== DB engines with photo_count>0 vs disk files ===")
for r in rows:
    eid, fname, count = r
    base = norm_base(fname, eid)
    matches = []
    for ext in ALLOWED_PHOTO_EXT:
        pattern = f"{base}_img_*_{eid}.{ext.lstrip('.')}"
        matches.extend(sorted(glob.glob(os.path.join(PHOTOS_FOLDER, pattern))))
    print(f"id={eid} count_db={count} file='{fname[:50]}' base='{base[:50]}' -> matches={len(matches)}")

print()
print("=== Actual photo files on disk (first 10) ===")
for f in sorted(os.listdir(PHOTOS_FOLDER))[:10]:
    print(f"  {f}")

print()
print("=== Total photo files on disk ===")
print(len([f for f in os.listdir(PHOTOS_FOLDER) if os.path.isfile(os.path.join(PHOTOS_FOLDER, f))]))