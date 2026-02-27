import os
import sqlite3
import subprocess
import sys
import time

OUT = os.path.join(os.path.dirname(__file__), 'output_attendance_audit.txt')
DB = os.path.normpath(os.path.join(os.getcwd(), 'instance', 'nuzum_local.db'))

def writeline(s=''):
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(s + '\n')
    print(s)

if os.path.exists(OUT):
    os.remove(OUT)

writeline('DB path: ' + DB)
if not os.path.exists(DB):
    writeline('DB_NOT_FOUND')
    sys.exit(2)

try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    writeline('PRAGMA index_list:')
    cur.execute("PRAGMA index_list('attendance')")
    for r in cur.fetchall():
        writeline(str(r))
    cur.execute('select count(*) from attendance')
    cnt = cur.fetchone()[0]
    writeline('ROW_COUNT: %s' % cnt)
finally:
    conn.close()

# Try to run alembic/Flask migration
writeline('\nRunning flask db upgrade...')
env = os.environ.copy()
env['FLASK_APP'] = 'app.py'
env['PYTHONIOENCODING'] = 'utf-8'
env['PYTHONUTF8'] = '1'
try:
    res = subprocess.run([os.path.join('venv','Scripts','python.exe'), '-m', 'flask', 'db', 'upgrade'], env=env, capture_output=True, text=True, timeout=300)
    writeline('RET_CODE: %s' % res.returncode)
    writeline('STDOUT:\n' + res.stdout)
    writeline('STDERR:\n' + res.stderr)
except Exception as e:
    writeline('MIGRATION_ERROR: %s' % e)

# Run modular smoke + benchmark
writeline('\nRunning modular benchmark (test_client)')
env = os.environ.copy()
env['ATTENDANCE_USE_MODULAR'] = '1'
env['PYTHONIOENCODING'] = 'utf-8'
env['PYTHONUTF8'] = '1'
os.environ.update(env)

try:
    from app import app
    client = app.test_client()
    t0 = time.perf_counter()
    res = client.get('/attendance/dashboard')
    t1 = time.perf_counter()
    elapsed_ms = (t1 - t0) * 1000.0
    writeline('DASHBOARD_STATUS: %s' % res.status_code)
    writeline('DASHBOARD_TIME_MS: %.2f' % elapsed_ms)
    body = res.data.decode('utf-8', 'ignore')
    writeline('DASHBOARD_BODY_START:')
    writeline(body[:800].replace('\n','\\n'))
    # simple heuristic for legacy proxy
    if 'Legacy Proxy' in body or 'proxy' in body.lower():
        writeline('MODALITY: LEGACY_FALLBACK_DETECTED')
    else:
        writeline('MODALITY: MODULAR_ACTIVE_POSSIBLE')
except Exception as e:
    writeline('DASHBOARD_ERROR: %s' % e)

writeline('\nAudit complete')
