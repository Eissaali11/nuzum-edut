import os
import sys
import time
import sqlite3

ROOT = os.getcwd()
DB = os.path.normpath(os.path.join(ROOT, 'instance', 'nuzum_local.db'))

print('Project root:', ROOT)
print('DB path:', DB)
if not os.path.exists(DB):
    print('DB not found; aborting')
    raise SystemExit(2)

# ensure composite index exists
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("CREATE INDEX IF NOT EXISTS ix_attendance_date_status ON attendance(date,status)")
conn.commit()
cur.execute("PRAGMA index_list('attendance')")
print('Indexes:')
for r in cur.fetchall():
    print(' ', r)
cur.execute('SELECT COUNT(*) FROM attendance')
cnt = cur.fetchone()[0]
print('attendance row count:', cnt)
conn.close()

# import app and benchmark dashboard
sys.path.insert(0, ROOT)
os.environ['ATTENDANCE_USE_MODULAR'] = os.environ.get('ATTENDANCE_USE_MODULAR', '1')
try:
    from app import app
except Exception as e:
    print('Import app failed:', e)
    raise

client = app.test_client()
start = time.perf_counter()
resp = client.get('/attendance/dashboard')
elapsed_ms = (time.perf_counter() - start) * 1000.0
print('DASHBOARD_STATUS:', resp.status_code)
print('DASHBOARD_TIME_MS: %.2f' % elapsed_ms)
body = resp.data.decode('utf-8', 'ignore')
print('BODY_SNIPPET:', body[:800].replace('\n','\\n'))

# Prefer explicit header set by v1 handlers, fallback to body heuristics
handler_header = resp.headers.get('X-Attendance-Handler')
if handler_header:
    print('HANDLER:', handler_header)
elif 'dashboard_new' in body or 'daily_trend_chart_data' in body:
    print('HANDLER: MODULAR_v1')
else:
    print('HANDLER: LEGACY_OR_UNKNOWN')
