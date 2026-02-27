#!/usr/bin/env python3
import sqlite3
from pathlib import Path
OUT = Path('artifacts') / 'db_table_info.txt'
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    for p in [Path('instance') / 'nuzum_local.db', Path('nuzum_local.db')]:
        f.write(f'--- DB: {p} exists={p.exists()} ---\n')
        if not p.exists():
            continue
        try:
            conn = sqlite3.connect(str(p))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_handover'")
            f.write('table_present: '+repr(cur.fetchall())+'\n')
            try:
                cur.execute("PRAGMA table_info('vehicle_handover')")
                rows = cur.fetchall()
                f.write('table_info rows:\n')
                for r in rows:
                    f.write(repr(r)+'\n')
                cols = [r[1] for r in rows]
                f.write('cols: '+repr(cols)+'\n')
                if 'is_approved' not in cols:
                    try:
                        cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER DEFAULT 0")
                        conn.commit()
                        f.write('ACTION: added is_approved\n')
                    except Exception as e:
                        f.write('ACTION FAILED: '+repr(e)+'\n')
            except Exception as e:
                f.write('PRAGMA ERROR: '+repr(e)+'\n')
        except Exception as e:
            f.write('DB OPEN ERROR: '+repr(e)+'\n')
        finally:
            try:
                conn.close()
            except:
                pass
print('wrote', OUT)
