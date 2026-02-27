#!/usr/bin/env python3
"""Ensure vehicle_handover.is_approved exists; add column and index safely for SQLite."""
import sqlite3
from pathlib import Path
import sys

DB = Path('instance') / 'nuzum_local.db'

def main():
    if not DB.exists():
        print(f"ERROR: DB not found: {DB}")
        return 2
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info('vehicle_handover')")
        cols = [r[1] for r in cur.fetchall()]
        if 'is_approved' in cols:
            print('OK: is_approved already present')
        else:
            print('Adding column is_approved to vehicle_handover...')
            # Add column with default 0 (false) and NOT NULL
            try:
                cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                print('Column added.')
            except sqlite3.OperationalError as oe:
                print('OperationalError while adding column:', oe)
        # ensure index exists
        cur.execute("PRAGMA index_list('vehicle_handover')")
        idxs = [r[1] for r in cur.fetchall()]
        if 'ix_vehicle_handover_is_approved' in idxs:
            print('OK: ix_vehicle_handover_is_approved exists')
        else:
            print('Creating index ix_vehicle_handover_is_approved...')
            cur.execute("CREATE INDEX IF NOT EXISTS ix_vehicle_handover_is_approved ON vehicle_handover(is_approved)")
            conn.commit()
            print('Index created.')
        return 0
    except Exception as e:
        print('ERROR:', e)
        return 3
    finally:
        conn.close()

if __name__ == '__main__':
    sys.exit(main())
