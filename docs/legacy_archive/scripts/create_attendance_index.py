import sqlite3
import os

DB = os.path.normpath(os.path.join(os.getcwd(), 'instance', 'nuzum_local.db'))
if not os.path.exists(DB):
    print('DB not found at', DB)
    raise SystemExit(2)

conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    print('Creating index ix_attendance_date_status if missing...')
    cur.execute("CREATE INDEX IF NOT EXISTS ix_attendance_date_status ON attendance(date, status);")
    conn.commit()
    print('Done.')
    cur.execute("PRAGMA index_list('attendance')")
    for r in cur.fetchall():
        print(r)
finally:
    conn.close()
