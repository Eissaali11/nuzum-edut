#!/usr/bin/env python3
"""Run repo scan, archive DB dumps, and run final health check; write reports to artifacts/"""
import io
import sys
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
#!/usr/bin/env python3
"""Run repo scan, archive DB dumps, and run final health check; write reports to artifacts/"""
import io
import sys
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
LEGACY_BACKUPS = ROOT / 'docs' / 'legacy_archive' / 'backups'

def ensure_dirs():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    LEGACY_BACKUPS.mkdir(parents=True, exist_ok=True)

def run_scan():
    # import and capture output from scripts.scan_repo
    try:
        from scripts import scan_repo
    except Exception:
        # fallback: execute as script
        import subprocess
        p = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'scan_repo.py')], capture_output=True, text=True)
        return p.stdout
    buf = io.StringIO()
    sys_stdout = sys.stdout
    try:
        sys.stdout = buf
        scan_repo.main()
    finally:
        sys.stdout = sys_stdout
    return buf.getvalue()

def move_backups():
    moved = []
    for src_dir in [ROOT / '_backups', ROOT / 'backups']:
        if not src_dir.exists():
            continue
        for p in src_dir.rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.sql', '.db'):
                dest = LEGACY_BACKUPS / p.name
                shutil.move(str(p), str(dest))
                moved.append(str(dest.relative_to(ROOT)))
    return moved

def run_health_check():
    # Run the health_check script by importing
    try:
        from tools.diagnostics.health_check import SystemHealthCheck
        checker = SystemHealthCheck()
        # capture prints
        import io, sys
        buf = io.StringIO()
        old = sys.stdout
        try:
            sys.stdout = buf
            rc = checker.run_all_checks()
        finally:
            sys.stdout = old
        return buf.getvalue(), rc
    except Exception:
        import subprocess
        p = subprocess.run([sys.executable, str(ROOT / 'tools' / 'diagnostics' / 'health_check.py')], capture_output=True, text=True)
        return p.stdout + p.stderr, p.returncode

def main():
    ensure_dirs()
    scan_out = run_scan()
    (ARTIFACTS / 'scan_report.txt').write_text(scan_out, encoding='utf-8')
    moved = move_backups()
    health_out, rc = run_health_check()
    (ARTIFACTS / 'health_final.txt').write_text(health_out, encoding='utf-8')
    summary = []
    summary.append('scan_report: ' + str(ARTIFACTS / 'scan_report.txt'))
    summary.append('health_report: ' + str(ARTIFACTS / 'health_final.txt'))
    summary.append('moved_files_count: ' + str(len(moved)))
    if moved:
        summary.append('moved_files_sample:')
        summary.extend(moved[:20])
    (ARTIFACTS / 'clean_summary.txt').write_text('\n'.join(summary), encoding='utf-8')
    print('\n'.join(summary))

if __name__ == '__main__':
    main()
