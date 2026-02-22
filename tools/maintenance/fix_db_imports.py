#!/usr/bin/env python
"""
سكريبت لاستبدال 'from core.extensions import db' بـ 'from core.extensions import db' في جميع الملفات
"""
import os
import re

files_to_fix = [
    "utils/audit_logger.py",
    "utils/chart_of_accounts.py",
    "utils/audit_helpers.py",
    "utils/arabic_handover_pdf.py",
    "utils/excel.py",
    "utils/request_notifications.py",
    "utils/vehicle_driver_utils.py",
    "services/ai_analyzer.py",
    "services/attendance_analytics.py",
    "services/employee_finance_service.py",
    "services/accounting_service.py",
    "services/ai_analytics.py",
    "routes/ai_services_simple.py",
    "routes/analytics_simple.py",
    "routes/api_employee_requests.py",
    "routes/dashboard.py",
    "routes/auth.py",
    "routes/documents.py",
    "routes/voicehub.py"
]

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        print(f"⏭️ ملف غير موجود: {file_path}")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # استبدال from core.extensions import db
    modified = content.replace('from core.extensions import db', 'from core.extensions import db')
    
    if modified != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified)
        print(f"✅ تم إصلاح: {file_path}")
    else:
        print(f"⏭️  لا حاجة لتعديل: {file_path}")

print("\n🎉 اكتمل الإصلاح!")
