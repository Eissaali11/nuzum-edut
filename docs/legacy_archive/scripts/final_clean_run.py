from pathlib import Path
import shutil,sys,io,traceback
ROOT = Path.cwd()
ART = ROOT / 'artifacts'
ART.mkdir(parents=True, exist_ok=True)
LEG = ROOT / 'docs' / 'legacy_archive' / 'backups'
LEG.mkdir(parents=True, exist_ok=True)

# Scan
from collections import defaultdict

def human(n):
    for unit in ['B','KB','MB','GB']:
        if n < 1024.0:
            return f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n:.2f}TB"

files = []
for p in ROOT.rglob('*'):
    if p.is_file():
        try:
            files.append((p, p.stat().st_size))
        except Exception:
            pass
files.sort(key=lambda x: x[1], reverse=True)
top = files[:40]
scan_lines = []
scan_lines.append('REPO_SCAN_ROOT: ' + str(ROOT))
scan_lines.append('\nTop large files:')
for p,s in top:
    scan_lines.append(f" - {human(s):8}  {p.relative_to(ROOT)}")

# detect blueprint collisions
reg = ROOT / 'routes' / 'blueprint_registry.py'
collisions = []
if reg.exists():
    import re
    txt = reg.read_text(encoding='utf-8')
    pattern = re.compile(r"app\.register_blueprint\(([^,\)]+)(?:,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"])?")
    mapping = defaultdict(list)
    for m in pattern.finditer(txt):
        bp = m.group(1).strip()
        prefix = m.group(2) or ''
        mapping[prefix].append(bp)
    collisions = [(p,bps) for p,bps in mapping.items() if p and len(bps)>1]

scan_lines.append('\nBlueprint prefix collisions:')
if collisions:
    for prefix,bps in collisions:
        scan_lines.append(f" - COLLISION prefix='{prefix}' blueprints={bps}")
else:
    scan_lines.append(' - None found')

scan_text = '\n'.join(scan_lines)
(ART / 'scan_report.txt').write_text(scan_text, encoding='utf-8')

# Move backups
moved = []
for src_dir in [ROOT / '_backups', ROOT / 'backups']:
    if not src_dir.exists():
        continue
    for p in src_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.sql', '.db'):
            try:
                dest = LEG / p.name
                shutil.move(str(p), str(dest))
                moved.append(str(dest.relative_to(ROOT)))
            except Exception:
                moved.append('FAILED:' + str(p))

# Run health check
health_out = ''
rc = 0
try:
    from tools.diagnostics.health_check import SystemHealthCheck
    checker = SystemHealthCheck()
    buf = io.StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        rc = checker.run_all_checks()
    finally:
        sys.stdout = old
    health_out = buf.getvalue()
except Exception:
    try:
        import subprocess
        p = subprocess.run([sys.executable, str(ROOT / 'tools' / 'diagnostics' / 'health_check.py')], capture_output=True, text=True)
        health_out = p.stdout + '\n' + p.stderr
        rc = p.returncode
    except Exception:
        health_out = traceback.format_exc()
        rc = 2

(ART / 'health_final.txt').write_text(health_out, encoding='utf-8')

# Summary
summary = []
summary.append('scan_report: ' + str(ART / 'scan_report.txt'))
summary.append('health_report: ' + str(ART / 'health_final.txt'))
summary.append('moved_files_count: ' + str(len(moved)))
if moved:
    summary.append('moved_files_sample:')
    summary.extend(moved[:20])
(ART / 'clean_summary.txt').write_text('\n'.join(summary), encoding='utf-8')

print('\n'.join(summary))
