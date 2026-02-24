import importlib.util
import traceback
import sqlite3

spec = importlib.util.spec_from_file_location('app_main', 'app.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app
app.testing = True

conn = sqlite3.connect('nuzum_local.db')
cur = conn.cursor()
cur.execute("select id from user where is_active=1 and lower(role)='admin' order by id limit 1")
row = cur.fetchone()
if not row:
    cur.execute('select id from user where is_active=1 order by id limit 1')
    row = cur.fetchone()
conn.close()
uid = str((row or [1])[0])

client = app.test_client()
with client.session_transaction() as s:
    s['_user_id'] = uid
    s['_fresh'] = True

try:
    response = client.get('/operations/1')
    print('status', response.status_code)
    body = response.data.decode('utf-8', 'ignore')
    print('body_prefix', body[:500].replace('\\n', ' '))
except Exception:
    traceback.print_exc()
