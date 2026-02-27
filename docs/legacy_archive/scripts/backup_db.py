#!/usr/bin/env python3
"""Simple DB backup script for NUZUM - copies instance/nuzum_local.db to backups with timestamp."""
import shutil
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[1]
DB = BASE / 'instance' / 'nuzum_local.db'
BACKUP_DIR = BASE / 'instance' / 'backups'

def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dest = BACKUP_DIR / f'nuzum_before_migration_fix_{ts}.db'
    if not DB.exists():
        print(f"ERROR: source DB not found: {DB}")
        return 2
    shutil.copy2(DB, dest)
    print(f"Backup created: {dest}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
