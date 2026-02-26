#!/usr/bin/env python3
import sqlite3
from pathlib import Path

def inspect(db_path):
    p = Path(db_path)
    print('DB:', p, 'exists=', p.exists())
    if not p.exists():
        return
    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_handover'")
        print('table rows:', cur.fetchall())
        cur.execute("PRAGMA table_info('vehicle_handover')")
        cols = [r[1] for r in cur.fetchall()]
        print('cols:', cols)
    except Exception as e:
        print('ERR', e)
    finally:
        conn.close()

if __name__ == '__main__':
    inspect('instance/nuzum_local.db')
    inspect('nuzum_local.db')
