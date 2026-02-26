import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'nuzum_local.db')
DB_PATH = os.path.normpath(DB_PATH)

if not os.path.exists(DB_PATH):
    print('DB not found at', DB_PATH)
    raise SystemExit(2)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print('Using DB:', DB_PATH)
cur.execute("PRAGMA index_list('attendance')")
indexes = cur.fetchall()
if not indexes:
    print('No indexes found for table attendance')
else:
    print('Indexes for attendance:')
    for idx in indexes:
        # idx -> (seq, name, unique, origin, partial)
        print(' -', idx)
        name = idx[1]
        cur.execute("PRAGMA index_info('%s')" % name)
        cols = cur.fetchall()
        print('    columns:', cols)

conn.close()
