import datetime
from routes.attendance.v1.services.attendance_service import AttendanceService


def test_on_time():
    shift = datetime.time(8, 0)
    check_in = datetime.time(8, 0)
    assert AttendanceService.calculate_late_minutes(check_in, shift) == 0


def test_inside_grace_period():
    shift = datetime.time(8, 0)
    check_in = datetime.time(8, 14)
    assert AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15) == 0


def test_just_outside_grace():
    shift = datetime.time(8, 0)
    check_in = datetime.time(8, 16)
    # Expected: total minutes late = 16
    assert AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15) == 16


def test_very_late():
    shift = datetime.time(8, 0)
    check_in = datetime.time(10, 30)
    # 2.5 hours = 150 minutes
    assert AttendanceService.calculate_late_minutes(check_in, shift) == 150


def test_early_bird():
    shift = datetime.time(8, 0)
    check_in = datetime.time(7, 45)
    assert AttendanceService.calculate_late_minutes(check_in, shift) == 0
