#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs' / 'legacy_archive' / 'backups'
DEST.mkdir(parents=True, exist_ok=True)
count = 0
for src in [ROOT / '_backups', ROOT / 'backups']:
    if not src.exists():
        continue
    for p in src.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.sql', '.db'):
            shutil.move(str(p), str(DEST / p.name))
            print('moved', p.name)
            count += 1
print('moved_count', count)
