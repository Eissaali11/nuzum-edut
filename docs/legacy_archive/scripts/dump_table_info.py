#!/usr/bin/env python3
import sqlite3
from pathlib import Path

OUT = Path('artifacts') / 'db_table_info.txt'
OUT.parent.mkdir(parents=True, exist_ok=True)

def dump(db_path):
    p = Path(db_path)
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(f"\nDB: {p} exists={p.exists()}\n")
        if not p.exists():
            return
        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_handover'")
            f.write('table rows:' + repr(cur.fetchall()) + '\n')
            cur.execute("PRAGMA table_info('vehicle_handover')")
            rows = cur.fetchall()
            f.write('table_info rows:\n')
            for r in rows:
                f.write(repr(r) + '\n')
        except Exception as e:
            f.write('ERR ' + repr(e) + '\n')
        finally:
            conn.close()

if __name__ == '__main__':
    if Path('instance') .joinpath('nuzum_local.db').exists():
        dump('instance/nuzum_local.db')
    if Path('nuzum_local.db').exists():
        dump('nuzum_local.db')
