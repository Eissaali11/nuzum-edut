#!/usr/bin/env python3
import sqlite3
from pathlib import Path
DB = Path('instance') / 'nuzum_local.db'
print('DB path:', DB, 'exists=', DB.exists())
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
try:
    cur.execute("PRAGMA table_info('vehicle_handover')")
    cols = [r[1] for r in cur.fetchall()]
    print('cols before:', cols)
    if 'is_approved' not in cols:
        try:
            cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            print('Column added successfully')
        except sqlite3.OperationalError as oe:
            print('OperationalError adding column:', oe)
    else:
        print('Column already exists')
    cur.execute("PRAGMA table_info('vehicle_handover')")
    print('cols after:', [r[1] for r in cur.fetchall()])
finally:
    conn.close()
