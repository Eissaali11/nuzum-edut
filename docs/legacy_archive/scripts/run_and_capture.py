#!/usr/bin/env python3
import runpy, sys, io
from pathlib import Path

OUT = Path('artifacts') / 'db_table_info.txt'
OUT.parent.mkdir(parents=True, exist_ok=True)

buf_out = io.StringIO()
buf_err = io.StringIO()
old_out, old_err = sys.stdout, sys.stderr
try:
    sys.stdout, sys.stderr = buf_out, buf_err
    runpy.run_path('scripts/write_db_info_simple.py', run_name='__main__')
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    sys.stdout, sys.stderr = old_out, old_err
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('--- STDOUT ---\n')
        f.write(buf_out.getvalue())
        f.write('\n--- STDERR ---\n')
        f.write(buf_err.getvalue())
    print('wrote', OUT)
