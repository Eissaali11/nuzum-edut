from pathlib import Path
import traceback
import runpy

try:
    runpy.run_path('scripts/clean_and_report.py', run_name='__main__')
except Exception:
    traceback.print_exc()
    # also show current working directory and listing of backups dirs
    import os
    print('CWD:', os.getcwd())
    for d in ['_backups', 'backups']:
        p = Path(d)
        print('DIR', d, 'exists', p.exists())
        if p.exists():
            for f in list(p.glob('*'))[:20]:
                print(' -', f)
