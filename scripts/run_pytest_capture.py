import subprocess
import sys
from pathlib import Path

ART = Path('artifacts')
ART.mkdir(exist_ok=True)
out_file = ART / 'test_attendance_late.txt'

cmd = ['pytest', '-q', 'tests/test_attendance_late.py']
proc = subprocess.run(cmd, capture_output=True, text=True)

with out_file.open('w', encoding='utf-8') as f:
    f.write('RETURN CODE: %s\n\n' % proc.returncode)
    f.write(proc.stdout)
    f.write(proc.stderr)

print(f'WROTE: {out_file} (rc={proc.returncode})')
sys.exit(proc.returncode)
