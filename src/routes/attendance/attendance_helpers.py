"""
Helper Functions for Attendance Module
=======================================
Extracted from _attendance_main.py (3,370 lines) as part of modularization.
Contains utility functions for time formatting and data conversion.
"""

from datetime import datetime


def format_time_12h_ar(dt):
    """تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة عربية (صباح/مساء)
    
    Args:
        dt: datetime object or None
        
    Returns:
        str: Formatted time string in Arabic 12-hour format, or '-' if None
        
    Examples:
        >>> format_time_12h_ar(datetime(2024, 1, 1, 14, 30, 0))
        '2:30:00 م'
        >>> format_time_12h_ar(datetime(2024, 1, 1, 8, 15, 30))
        '8:15:30 ص'
    """
    if not dt:
        return '-'
    
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    
    # تحديد صباح أو مساء
    period = 'ص' if hour < 12 else 'م'
    
    # تحويل الساعة
    if hour > 12:
        hour = hour - 12
    elif hour == 0:
        hour = 12
    
    return f'{hour}:{minute:02d}:{second:02d} {period}'


def format_time_12h_ar_short(dt):
    """تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة قصيرة (بدون ثوانٍ)
    
    Args:
        dt: datetime object or None
        
    Returns:
        str: Formatted time string in Arabic 12-hour format (no seconds), or '-' if None
        
    Examples:
        >>> format_time_12h_ar_short(datetime(2024, 1, 1, 14, 30))
        '2:30 م'
        >>> format_time_12h_ar_short(datetime(2024, 1, 1, 8, 15))
        '8:15 ص'
    """
    if not dt:
        return '-'
    
    hour = dt.hour
    minute = dt.minute
    
    # تحديد صباح أو مساء
    period = 'ص' if hour < 12 else 'م'
    
    # تحويل الساعة
    if hour > 12:
        hour = hour - 12
    elif hour == 0:
        hour = 12
    
    return f'{hour}:{minute:02d} {period}'
