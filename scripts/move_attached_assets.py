#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'backups' / 'attached_assets.zip'
DST = ROOT / 'docs' / 'legacy_archive' / 'backups' / 'attached_assets.zip'

if SRC.exists():
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(SRC), str(DST))
    print('moved', SRC, '->', DST)
else:
    print('not found', SRC)
