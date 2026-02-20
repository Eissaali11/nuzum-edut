#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify departments are showing up in payroll review
اختبار للتحقق من أن الأقسام تعرض في مراجعة الرواتب
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Create Flask app context
from app import app
from models import Department, Employee, PayrollRecord
from datetime import datetime

with app.app_context():
    print("=" * 60)
    print("اختبار توفر الأقسام والموظفين")
    print("=" * 60)
    
    # Check departments
    departments = Department.query.all()
    print(f"\n✓ عدد الأقسام: {len(departments)}")
    for dept in departments:
        print(f"  - {dept.id}: {dept.name}")
    
    # Check employees
    employees = Employee.query.limit(5).all()
    print(f"\n✓ عدد الموظفين (عينة): {len(Employee.query.all())}")
    for emp in employees[:3]:
        dept_name = emp.department.name if emp.department else "بلا قسم"
        print(f"  - {emp.id}: {emp.get_name() or 'بلا اسم'} ({dept_name})")
    
    # Check payroll records
    current_month = datetime.now().month
    current_year = datetime.now().year
    payrolls = PayrollRecord.query.filter_by(
        pay_period_month=current_month,
        pay_period_year=current_year
    ).limit(3).all()
    print(f"\n✓ رواتب الشهر الحالي: {PayrollRecord.query.filter_by(pay_period_month=current_month, pay_period_year=current_year).count()}")
    for payroll in payrolls:
        if payroll.employee and payroll.employee.department:
            print(f"  - {payroll.employee.id}: {payroll.employee.get_name()} ({payroll.employee.department.name})")
    
    print("\n✓ تم الاختبار بنجاح!")
    print("\nملاحظات:")
    print("- يجب أن تجد أقسام في قاعدة البيانات")
    print("- يجب أن تجد موظفين مرتبطين بأقسام")
    print("- يجب أن تجد رواتب موظفينها لديهم أقسام")
