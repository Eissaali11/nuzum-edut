# -*- coding: utf-8 -*-
"""
مسارات الحضور والإجازات - النسخة المحسنة
Attendance Routes Module

استراتيجية المرحلة الانتقالية:
- الملف الأصلي attendance.py يحتفظ بجميع الوظائف الحالية
- هذا ال__init__.py يعيد تصدير Blueprint بشكل نظيف
- سيتم التقسيم التدريجي في المرحلة القادمة
"""

import sys
import os
from pathlib import Path

# Get the parent routes directory
parent_dir = Path(__file__).parent.parent

# Import the original attendance module
sys.path.insert(0, str(parent_dir))

# Import the original attendance blueprint 
import importlib.util
spec = importlib.util.spec_from_file_location("attendance_original", str(parent_dir / "attendance.py"))
attendance_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attendance_module)

# Get the blueprint from the original module
attendance_bp = attendance_module.attendance_bp

# Export for use in app
__all__ = ['attendance_bp']


