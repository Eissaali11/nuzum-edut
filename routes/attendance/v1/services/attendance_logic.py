from datetime import datetime, date


def calculate_late_minutes(check_in_time, shift_start_time, grace_period=15):
    """Calculate minutes late. Accepts datetimes, time objects, or ISO strings.

    Returns 0 if within grace_period or if inputs are invalid.
    """
    try:
        if check_in_time is None or shift_start_time is None:
            return 0

        # Parse ISO strings
        if isinstance(check_in_time, str):
            check_in_time = datetime.fromisoformat(check_in_time)
        if isinstance(shift_start_time, str):
            shift_start_time = datetime.fromisoformat(shift_start_time)

        # Validate attributes
        if not hasattr(check_in_time, 'hour') or not hasattr(shift_start_time, 'hour'):
            return 0

        # Attach today's date if only time objects given
        if getattr(check_in_time, 'year', None) is None:
            check_in_time = datetime.combine(date.today(), check_in_time)
        if getattr(shift_start_time, 'year', None) is None:
            shift_start_time = datetime.combine(date.today(), shift_start_time)

        delta = check_in_time - shift_start_time
        minutes = int(delta.total_seconds() // 60)
        if minutes <= grace_period:
            return 0
        return max(0, minutes)
    except Exception:
        return 0
