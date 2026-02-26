import os
import subprocess
import sys

def main():
    env = os.environ.copy()
    env['ATTENDANCE_USE_MODULAR'] = '1'
    # Force UTF-8 output to avoid console encoding errors on Windows
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'

    python = os.path.join('venv', 'Scripts', 'python')
    cmd = [python, '-c', 'from scripts.test_attendance_smoke import run; run()']

    print('Running flip test: ATTENDANCE_USE_MODULAR=1')
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    if proc.returncode == 0:
        print('Flip test completed: SUCCESS')
    else:
        print(f'Flip test failed (exit {proc.returncode})', file=sys.stderr)
    sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
