#!/usr/bin/env python3
import sqlite3
from pathlib import Path

OUT = Path('artifacts') / 'db_table_info.txt'
OUT.parent.mkdir(parents=True, exist_ok=True)

def process(p):
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(f"--- DB: {p} exists={p.exists()} ---\n")
        if not p.exists():
            return
        try:
            conn = sqlite3.connect(str(p))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_handover'")
            f.write('table_present: ' + repr(cur.fetchall()) + '\n')
            cur.execute("PRAGMA table_info('vehicle_handover')")
            rows = cur.fetchall()
            f.write('table_info rows:\n')
            for r in rows:
                f.write(repr(r) + '\n')
            cols = [r[1] for r in rows]
            f.write('cols: ' + repr(cols) + '\n')
            if 'is_approved' not in cols:
                try:
                    cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                    f.write('ACTION: added is_approved\n')
                except Exception as e:
                    f.write('ACTION FAILED: ' + repr(e) + '\n')
            conn.close()
        except Exception as e:
            f.write('DB ERROR: ' + repr(e) + '\n')

def main():
    # check instance and root DB
    for p in [Path('instance') / 'nuzum_local.db', Path('nuzum_local.db')]:
        process(p)
    print('wrote', OUT)

if __name__ == '__main__':
    main()
