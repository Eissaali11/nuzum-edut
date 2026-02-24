import sqlite3
import runpy


g = runpy.run_path('app.py')
app = g['app']

conn = sqlite3.connect('nuzum_local.db')
cur = conn.cursor()
cur.execute('select id from user where is_active=1 limit 1')
uid = str((cur.fetchone() or [1])[0])
conn.close()

c = app.test_client()
with c.session_transaction() as s:
    s['_user_id'] = uid
    s['_fresh'] = True

r = c.get('/employees/')
h = r.data.decode('utf-8', 'ignore')

print('status', r.status_code)
print('html_len', len(h))
print('script_tags', h.count('<script'))
print('table_rows', h.count('<tr'))
print('title_hits', h.count('إدارة الموظفين'))
print('mutation_observer', 'MutationObserver' in h)
print('has_safe_mode_marker', 'Safe mode' in h)
