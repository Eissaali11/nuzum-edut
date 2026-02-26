from routes.attendance.v1.services.attendance_service import AttendanceService
from datetime import datetime, time
from pathlib import Path

ART = Path('artifacts')
ART.mkdir(exist_ok=True)
out = ART / 'manual_test_attendance_late.txt'

results = []

def assert_eq(a, b, msg=''):
    if a != b:
        raise AssertionError(f'{a!r} != {b!r} {msg}')

try:
    # test 1
    shift = datetime(2026, 2, 26, 9, 0)
    check_in = datetime(2026, 2, 26, 9, 20)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15)
    assert_eq(minutes, 20, 'test1')
    results.append('test1: PASS')
except Exception as e:
    results.append('test1: FAIL - ' + str(e))

try:
    shift = time(9, 0)
    check_in = time(9, 10)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15)
    assert_eq(minutes, 0, 'test2')
    results.append('test2: PASS')
except Exception as e:
    results.append('test2: FAIL - ' + str(e))

try:
    shift = '2026-02-26T09:00:00'
    check_in = '2026-02-26T09:30:00'
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=10)
    assert_eq(minutes, 30, 'test3')
    results.append('test3: PASS')
except Exception as e:
    results.append('test3: FAIL - ' + str(e))

with out.open('w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print('WROTE:', out)
