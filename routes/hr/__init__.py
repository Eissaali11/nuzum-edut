"""
قسم الموارد البشرية (HR) - الموظفين والرواتب
═══════════════════════════════════════════════════════════════════════════

يضم:
- إدارة بيانات الموظفين (Employee Management)
- إدارة الأقسام (Department Management)
- نظام الرواتب (Salary Management - متقدم)

═══════════════════════════════════════════════════════════════════════════
"""

hr_blueprints = []

try:
    from .employees import employees_bp
    hr_blueprints.append(employees_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد employees: {e}")

try:
    from .departments import departments_bp
    hr_blueprints.append(departments_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد departments: {e}")

try:
    from ..salaries_mgmt.salaries import salaries_bp
    hr_blueprints.append(salaries_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد salaries: {e}")

# نظام إدارة الرواتب المتقدم
try:
    from ..salaries_mgmt import salaries_bp as salaries_mgmt_bp
    hr_blueprints.append(salaries_mgmt_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد salaries_mgmt: {e}")

__all__ = [
    'employees_bp',
    'departments_bp',
    'salaries_bp',
    'hr_blueprints'
]
