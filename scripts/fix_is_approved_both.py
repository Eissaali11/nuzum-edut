#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DBS = [Path('instance') / 'nuzum_local.db', Path('nuzum_local.db')]

for DB in DBS:
    print('Checking DB:', DB, 'exists=', DB.exists())
    if not DB.exists():
        continue
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info('vehicle_handover')")
        cols = [r[1] for r in cur.fetchall()]
        print(' cols:', cols)
        if 'is_approved' not in cols:
            try:
                cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                print(' added is_approved to', DB)
            except Exception as e:
                print(' failed to add on', DB, e)
        else:
            print(' already present on', DB)
    finally:
        conn.close()
