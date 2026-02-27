#!/usr/bin/env python3
"""Scan all .db files, record PRAGMA table_info('vehicle_handover'),
and add column is_approved if missing. Write results to artifacts/db_table_info.txt
"""
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / 'artifacts' / 'db_table_info.txt'
OUT.parent.mkdir(parents=True, exist_ok=True)

def inspect_db(db_path: Path):
    OUT.write_text(OUT.read_text(encoding='utf-8') + f"\n--- DB: {db_path} checked at {datetime.utcnow().isoformat()}Z ---\n", encoding='utf-8') if OUT.exists() else None
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(f"DB: {db_path} exists={db_path.exists()}\n")
        if not db_path.exists():
            return
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            # does table exist?
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_handover'")
            tbl = cur.fetchall()
            f.write('vehicle_handover table present: ' + repr(tbl) + '\n')
            # table_info
            try:
                cur.execute("PRAGMA table_info('vehicle_handover')")
                rows = cur.fetchall()
                f.write('PRAGMA table_info rows:\n')
                for r in rows:
                    f.write(repr(r) + '\n')
                cols = [r[1] for r in rows]
                if 'is_approved' in cols:
                    f.write('STATUS: is_approved PRESENT\n')
                else:
                    f.write('STATUS: is_approved MISSING -- attempting to add\n')
                    try:
                        cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0")
                        conn.commit()
                        f.write('ACTION: Column added successfully\n')
                        # re-dump
                        cur.execute("PRAGMA table_info('vehicle_handover')")
                        for r in cur.fetchall():
                            f.write(repr(r) + '\n')
                    except Exception as e:
                        f.write('ACTION FAILED: ' + repr(e) + '\n')
            except Exception as e:
                f.write('PRAGMA error: ' + repr(e) + '\n')
            # index list for attendance (best-effort)
            try:
                cur.execute("PRAGMA index_list('attendance')")
                idxs = cur.fetchall()
                f.write('attendance indexes: ' + repr(idxs) + '\n')
            except Exception:
                f.write('attendance index check failed\n')
            conn.close()
        except Exception as e:
            f.write('DB open error: ' + repr(e) + '\n')

def main():
    # find all .db files in repo (skip node_modules/.venv etc)
    for p in ROOT.rglob('*.db'):
        # skip obvious system DBs in .git internals
        if '.git' in p.parts:
            continue
        inspect_db(p)
    print('Wrote', OUT)

if __name__ == '__main__':
    main()
