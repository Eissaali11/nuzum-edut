# -*- coding: utf-8 -*-
"""
دوال مساعدة لمسارات الحضور
Helper functions for attendance routes

الوظائف:
- تحويل الأوقات إلى صيغة عربية 12 ساعة
"""


def format_time_12h_ar(dt):
    """تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة عربية (صباح/مساء)"""
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
    """تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة قصيرة (بدون ثوانٍ)"""
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
