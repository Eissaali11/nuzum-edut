#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
تنظيم ملفات routes بطريقة احترافية
Organizing routes files professionally
"""

import os
import shutil
from pathlib import Path

# المسار الأساسي
routes_dir = Path(__file__).parent

# تعريف الملفات حسب التصنيفات
classification = {
    'core': {
        'desc': 'مسارات أساسية - Core Routes',
        'files': ['auth.py', 'users.py', 'dashboard.py', 'landing.py', 'landing_admin.py']
    },
    
    'hr': {
        'desc': 'الموارد البشرية - Human Resources',
        'files': ['employees.py', 'employees_helpers.py', 'departments.py', 'salaries.py']
    },
    
    'attendance': {
        'desc': 'الحضور والإجازات - Attendance & Leave',
        'files': ['leave_management.py', 'mass_attendance.py', 'attendance_admin.py', 
                 'attendance_api.py', 'attendance_controller.py', 'attendance_dashboard.py']
    },
    
    'assets': {
        'desc': 'الأصول الثابتة - Fixed Assets',
        'files': ['mobile_devices.py', 'device_assignment.py', 'device_management.py']
    },
    
    'analytics': {
        'desc': 'التحليلات والتقارير - Analytics & Reports',
        'files': ['reports.py', 'analytics.py', 'analytics_direct.py', 'analytics_real.py',
                 'analytics_simple.py', 'enhanced_reports.py', 'insights.py']
    },
    
    'documents': {
        'desc': 'الوثائق - Documents Management',
        'files': ['documents.py', 'documents_controller.py']
    },
    
    'requests': {
        'desc': 'الطلبات والشؤون الإدارية - Employee Requests',
        'files': ['employee_requests.py', 'employee_requests_controller.py', 'employee_requests_v2.py']
    },
    
    'accounting': {
        'desc': 'المحاسبة والفواتير - Accounting',
        'files': ['accounting.py', 'accounting_analytics.py', 'accounting_extended.py', 'e_invoicing.py', 'fees_costs.py']
    },
    
    'api': {
        'desc': 'واجهات API - API Endpoints',
        'files': ['api.py', 'api_accident_reports.py', 'api_attendance_v2.py', 
                 'api_documents_v2.py', 'api_employee_requests.py', 'api_employee_requests_v2.py',
                 'api_external.py', 'api_external_safety.py', 'api_external_safety_v2.py']
    },
    
    'communications': {
        'desc': 'الاتصالات - Communications',
        'files': ['notifications.py', 'email_queue.py']
    },
    
    'integrations': {
        'desc': 'التكاملات والخدمات الخارجية - Integrations',
        'files': ['voicehub.py', 'google_drive_settings.py', 'drive_browser.py', 'external_safety.py', 'geofences.py']
    },
    
    'admin': {
        'desc': 'لوحات التحكم الإدارية - Admin Dashboards',
        'files': ['admin_dashboard.py', 'payroll_admin.py', 'payroll_management.py']
    }
}

# الأنظمة الفرعية المنظمة
subpackages = {
    'operations': 'العمليات - Operations Management',
    'powerbi_dashboard': 'لوحة معلومات Power BI - Analytics Dashboard',
    'properties_mgmt': 'إدارة العقارات - Property Management',
    'reports_mgmt': 'إدارة التقارير - Reports Management',
    'salaries_mgmt': 'إدارة الرواتب - Payroll Management',
    'sim_mgmt': 'إدارة بطاقات SIM - SIM Cards Management'
}

# الملفات الأرشيفية
legacy_files = [
    'operations_old.py', 'properties_old.py', 'reports_old.py', 
    'salaries_old.py', 'sim_management_old.py', 'mobile_devices_old.py',
    'attendance.py.backup', 'attendance.py.broken', 'database_backup.py',
    '_attendance_main.py', 'simple_analytics.py', 'integrated_simple.py',
    'integrated_management.py', 'mobile.py', 'employee_portal.py',
    'api_accident_reports.py'
]

print("=" * 80)
print("📊 تقرير تنظيم ملفات Routes - Routes Organization Report")
print("=" * 80)

# عد الملفات
total_files = sum(len(cat['files']) for cat in classification.values())
total_subpackages = len(subpackages)
total_legacy = len(legacy_files)

print(f"\n📁 توزيع الملفات الرئيسية:")
print(f"   أقسام وتصنيفات: {len(classification)}")
print(f"   ملفات في الأقسام: {total_files}")
print(f"   أنظمة فرعية: {total_subpackages}")
print(f"   ملفات أرشيفية: {total_legacy}")

print(f"\n📂 تفصيل الأقسام:")
print("-" * 80)
for category, info in classification.items():
    print(f"✅ {category.upper():<20} - {info['desc']:<50} ({len(info['files'])} ملفات)")

print(f"\n📦 الأنظمة الفرعية المنظمة:")
print("-" * 80)
for package, desc in subpackages.items():
    print(f"✅ {package:<25} - {desc}")

print(f"\n🗂️  الملفات الأرشيفية (legacy/): {total_legacy} ملفات")

print(f"\n{'=' * 80}")
print("البنية الموصى بها / Recommended Structure:")
print("=" * 80)

structure = """
routes/
├── __init__.py (مركزي - Central)
├── core/                     ← مسارات أساسية
├── hr/                       ← الموارد البشرية + salaries_mgmt
├── attendance/               ← الحضور والإجازات  
├── assets/                   ← الأصول الثابتة والأجهزة
├── documents/                ← إدارة الوثائق
├── requests/                 ← الطلبات والشؤون الإدارية
├── accounting/               ← المحاسبة والفواتير
├── api/                      ← واجهات API
├── communications/           ← الاتصالات والإخطارات
├── integrations/             ← التكاملات الخارجية
├── admin/                    ← لوحات التحكم
├── operations/               ← العمليات (منظمة)
├── powerbi_dashboard/        ← لوحة المعلومات (منظمة)
├── properties_mgmt/          ← العقارات (منظمة)
├── reports_mgmt/             ← إدارة التقارير (منظمة)
├── salaries_mgmt/            ← إدارة الرواتب (منظمة)
├── sim_mgmt/                 ← بطاقات SIM (منظمة)
└── legacy/                   ← الملفات القديمة والنسخ الاحتياطية
"""

print(structure)

print("=" * 80)
print("✅ البنية احترافية وسهلة الصيانة والتوسع")
print("=" * 80)
