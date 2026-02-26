import pytest
from routes.attendance.v1.services.attendance_service import AttendanceService
from datetime import datetime, time


def test_calculate_late_minutes_with_datetime():
    shift = datetime(2026, 2, 26, 9, 0)
    check_in = datetime(2026, 2, 26, 9, 20)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15)
    assert minutes == 20


def test_calculate_late_minutes_with_time_objects():
    shift = time(9, 0)
    check_in = time(9, 10)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15)
    assert minutes == 0


def test_calculate_late_minutes_with_strings():
    shift = '2026-02-26T09:00:00'
    check_in = '2026-02-26T09:30:00'
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=10)
    assert minutes == 30


def test_cross_day_shift():
    # Shift starts on previous day at 22:00, check-in after midnight
    shift = datetime(2026, 2, 25, 22, 0)
    check_in = datetime(2026, 2, 26, 0, 10)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=15)
    assert minutes == 130


def test_small_seconds_delay():
    # Delay of seconds only should floor to 0 minutes
    shift = datetime(2026, 2, 26, 9, 0, 0)
    check_in = datetime(2026, 2, 26, 9, 0, 30)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=0)
    assert minutes == 0


def test_no_delay_exact_time():
    shift = datetime(2026, 2, 26, 9, 0)
    check_in = datetime(2026, 2, 26, 9, 0)
    minutes = AttendanceService.calculate_late_minutes(check_in, shift, grace_period=5)
    assert minutes == 0


def test_malformed_inputs_and_none():
    assert AttendanceService.calculate_late_minutes(None, None) == 0
    assert AttendanceService.calculate_late_minutes('not-a-date', 'also-bad') == 0
    assert AttendanceService.calculate_late_minutes(None, datetime(2026,2,26,9,0)) == 0


def test_multiple_records_counting():
    # Simulate two check-ins for same employee: one within grace, one late
    shift = datetime(2026, 2, 26, 9, 0)
    check_ins = [datetime(2026, 2, 26, 9, 5), datetime(2026, 2, 26, 9, 30)]
    late_count = 0
    for ch in check_ins:
        if AttendanceService.calculate_late_minutes(ch, shift, grace_period=10) > 0:
            late_count += 1
    assert late_count == 1
