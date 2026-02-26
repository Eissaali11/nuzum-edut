import os
import sqlite3
import time

DB = os.path.normpath(os.path.join(os.getcwd(), 'instance', 'nuzum_local.db'))
print('DB:', DB)
if not os.path.exists(DB):
    print('DB_NOT_FOUND')
    raise SystemExit(2)

conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    print('Creating index ix_attendance_date_status if missing...')
    cur.execute("CREATE INDEX IF NOT EXISTS ix_attendance_date_status ON attendance(date, status)")
    print('Creating index ix_attendance_employee_date if missing...')
    cur.execute("CREATE INDEX IF NOT EXISTS ix_attendance_employee_date ON attendance(employee_id, date)")
    conn.commit()
    print('Indexes created/ensured.')
    cur.execute("PRAGMA index_list('attendance')")
    for r in cur.fetchall():
        print('INDEX:', r)
    cur.execute('SELECT COUNT(*) FROM attendance')
    cnt = cur.fetchone()[0]
    print('ROW_COUNT:', cnt)
except Exception as e:
    print('ERROR:', e)
    raise
finally:
    conn.close()
