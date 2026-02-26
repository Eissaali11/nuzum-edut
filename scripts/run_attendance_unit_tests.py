from datetime import datetime, time
import sys
from pathlib import Path

# Ensure repo root on path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from routes.attendance.v1.services.attendance_service import AttendanceService

cases = [
    (datetime(2026,1,1,8,0), datetime(2026,1,1,8,0), 15, 0, 'On Time'),
    (datetime(2026,1,1,8,14), datetime(2026,1,1,8,0), 15, 0, 'Inside Grace'),
    (datetime(2026,1,1,8,16), datetime(2026,1,1,8,0), 15, 16, 'Just Outside Grace'),
    (datetime(2026,1,1,10,30), datetime(2026,1,1,8,0), 15, 150, 'Very Late'),
    (datetime(2026,1,1,7,45), datetime(2026,1,1,8,0), 15, 0, 'Early Bird'),
]

failed = []
for chk, shift, grace, expected, name in cases:
    got = AttendanceService.calculate_late_minutes(chk, shift, grace_period=grace)
    if got != expected:
        failed.append((name, expected, got))

if failed:
    print('FAILURES:')
    for name, exp, got in failed:
        print(f'{name}: expected {exp}, got {got}')
    sys.exit(1)
else:
    print('All attendance unit tests passed (5/5)')
    sys.exit(0)
