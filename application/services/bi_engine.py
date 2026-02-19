"""
Business Intelligence Engine - Star Schema Data Preparation
==========================================================
محرك الذكاء التجاري لإعداد البيانات بنموذج Star Schema
يوفر Fact & Dimension Tables لتحليلات Power BI المتقدمة
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, case, and_, or_
from collections import defaultdict
import pandas as pd

from core.extensions import db
from models import (
    Employee, Vehicle, Salary, Department, Attendance, 
    VehicleWorkshop, VehicleAccident, Document, Project,
    VehicleProject, RentalProperty
)


class BIEngine:
    """محرك الذكاء التجاري - إعداد البيانات للتحليل"""
    
    # خريطة المناطق الجغرافية
    REGION_MAPPING = {
        'الرياض': 'Riyadh',
        'riyadh': 'Riyadh',
        'جدة': 'Jeddah',
        'jeddah': 'Jeddah',
        'الدمام': 'Dammam',
        'dammam': 'Dammam',
        'مكة': 'Makkah',
        'makkah': 'Makkah',
        'المدينة': 'Madinah',
        'madinah': 'Madinah',
        'القصيم': 'Qassim',
        'qassim': 'Qassim',
        'الخبر': 'Khobar',
        'khobar': 'Khobar',
        'الطائف': 'Taif',
        'taif': 'Taif',
        'تبوك': 'Tabuk',
        'tabuk': 'Tabuk',
        'حائل': 'Hail',
        'hail': 'Hail',
        'أبها': 'Abha',
        'abha': 'Abha',
        'جازان': 'Jazan',
        'jazan': 'Jazan',
    }
    
    def __init__(self):
        """تهيئة محرك الذكاء التجاري"""
        self.today = date.today()
        self.current_month = self.today.month
        self.current_year = self.today.year
    
    def standardize_region(self, location: str) -> str:
        """
        تحويل أسماء المواقع إلى أسماء مناطق موحدة
        متوافقة مع Power BI Map Visuals
        """
        if not location:
            return 'Unknown'
        
        location_lower = location.strip().lower()
        
        # البحث المباشر
        for key, value in self.REGION_MAPPING.items():
            if key in location_lower:
                return value
        
        # البحث في أجزاء النص
        for key, value in self.REGION_MAPPING.items():
            if key.split()[0] in location_lower:
                return value
        
        return 'Other'
    
    def get_dimension_employees(self) -> List[Dict[str, Any]]:
        """
        DIM_Employees: جدول بُعد الموظفين
        يحتوي على التفاصيل الكاملة للموظفين مع تنظيف الأسماء والمشاريع
        """
        employees = Employee.query.filter_by(status='active').all()
        
        dim_employees = []
        for emp in employees:
            # تنظيف اسم الموظف
            clean_name = emp.name.strip() if emp.name else 'غير محدد'
            
            # المشروع الحالي
            current_project = 'N/A'
            if emp.project:
                current_project = emp.project.strip()
            
            # القسم
            department_name = emp.department.name if emp.department else 'N/A'
            
            # المنطقة الجغرافية
            region = self.standardize_region(emp.location)
            
            # حساب الراتب الحالي
            current_salary = emp.basic_salary or 0
            
            # حالة العقد
            contract_status = emp.contract_status or 'active'
            
            # نوع الموظف
            employee_type = emp.employee_type or 'permanent'
            
            dim_employees.append({
                'employee_key': emp.id,
                'employee_id': emp.employee_id,
                'employee_name': clean_name,
                'national_id': emp.national_id,
                'department': department_name,
                'job_title': emp.job_title or 'N/A',
                'project': current_project,
                'location': emp.location or 'N/A',
                'region': region,
                'basic_salary': current_salary,
                'daily_wage': emp.daily_wage or 0,
                'attendance_bonus': emp.attendance_bonus or 0,
                'contract_type': emp.contract_type or 'N/A',
                'contract_status': contract_status,
                'employee_type': employee_type,
                'nationality': emp.nationality or 'Saudi',
                'mobile': emp.mobile or 'N/A',
                'join_date': emp.join_date.isoformat() if emp.join_date else None,
                'birth_date': emp.birth_date.isoformat() if emp.birth_date else None,
                'is_active': emp.status == 'active',
                'created_at': emp.created_at.isoformat() if emp.created_at else None
            })
        
        return dim_employees
    
    def get_dimension_vehicles(self) -> List[Dict[str, Any]]:
        """
        DIM_Vehicles: جدول بُعد المركبات
        يحتوي على معرفات اللوحات، حالة الصيانة، والتوزيع الإقليمي
        """
        vehicles = Vehicle.query.all()
        
        dim_vehicles = []
        for veh in vehicles:
            # حالة الصيانة
            maintenance_status = 'Good'
            workshops = VehicleWorkshop.query.filter_by(
                vehicle_id=veh.id
            ).order_by(VehicleWorkshop.entry_date.desc()).limit(3).all()
            
            if workshops:
                recent_cost = sum(w.cost or 0 for w in workshops)
                if recent_cost > 10000:
                    maintenance_status = 'High Maintenance'
                elif recent_cost > 5000:
                    maintenance_status = 'Medium Maintenance'
            
            # عدد الحوادث
            accidents_count = VehicleAccident.query.filter_by(
                vehicle_id=veh.id
            ).count()
            
            # المنطقة
            region = self.standardize_region(veh.region)
            
            # القسم
            department_name = veh.department.name if veh.department else 'N/A'
            
            # حالة المستندات
            docs_status = 'Valid'
            if veh.authorization_expiry_date and veh.authorization_expiry_date < self.today:
                docs_status = 'Expired'
            elif veh.registration_expiry_date and veh.registration_expiry_date < self.today:
                docs_status = 'Expired'
            elif veh.inspection_expiry_date and veh.inspection_expiry_date < self.today:
                docs_status = 'Expired'
            
            dim_vehicles.append({
                'vehicle_key': veh.id,
                'plate_number': veh.plate_number,
                'make': veh.make or 'N/A',
                'model': veh.model or 'N/A',
                'year': veh.year or 0,
                'color': veh.color or 'N/A',
                'type_of_car': veh.type_of_car or 'N/A',
                'status': veh.status or 'active',
                'department': department_name,
                'region': region,
                'location': veh.region or 'N/A',
                'project': veh.project or 'N/A',
                'driver_name': veh.driver_name or 'Unassigned',
                'owned_by': veh.owned_by or 'Company',
                'maintenance_status': maintenance_status,
                'accidents_count': accidents_count,
                'documents_status': docs_status,
                'authorization_expiry': veh.authorization_expiry_date.isoformat() if veh.authorization_expiry_date else None,
                'registration_expiry': veh.registration_expiry_date.isoformat() if veh.registration_expiry_date else None,
                'inspection_expiry': veh.inspection_expiry_date.isoformat() if veh.inspection_expiry_date else None,
                'created_at': veh.created_at.isoformat() if veh.created_at else None
            })
        
        return dim_vehicles
    
    def get_dimension_departments(self) -> List[Dict[str, Any]]:
        """
        DIM_Departments: جدول بُعد الأقسام
        """
        departments = Department.query.all()
        
        dim_departments = []
        for dept in departments:
            # عدد الموظفين النشطين
            employees_count = Employee.query.filter_by(
                department_id=dept.id,
                status='active'
            ).count()
            
            # عدد المركبات
            vehicles_count = Vehicle.query.filter_by(
                department_id=dept.id
            ).count()
            
            dim_departments.append({
                'department_key': dept.id,
                'department_name': dept.name,
                'description': dept.description or 'N/A',
                'employees_count': employees_count,
                'vehicles_count': vehicles_count,
                'is_active': True,
                'created_at': dept.created_at.isoformat() if dept.created_at else None
            })
        
        return dim_departments
    
    def get_dimension_time(self, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """
        DIM_Time: جدول بُعد الوقت (Time Dimension)
        """
        if not start_date:
            start_date = date(self.current_year - 2, 1, 1)
        if not end_date:
            end_date = date(self.current_year + 1, 12, 31)
        
        dim_time = []
        current = start_date
        
        while current <= end_date:
            dim_time.append({
                'date_key': int(current.strftime('%Y%m%d')),
                'full_date': current.isoformat(),
                'year': current.year,
                'quarter': (current.month - 1) // 3 + 1,
                'month': current.month,
                'month_name': current.strftime('%B'),
                'month_name_ar': self._get_arabic_month(current.month),
                'day': current.day,
                'day_of_week': current.weekday() + 1,
                'day_name': current.strftime('%A'),
                'is_weekend': current.weekday() >= 4,  # الجمعة والسبت
                'is_month_start': current.day == 1,
                'is_month_end': (current + timedelta(days=1)).day == 1
            })
            
            current += timedelta(days=1)
        
        return dim_time
    
    def _get_arabic_month(self, month: int) -> str:
        """الحصول على اسم الشهر بالعربية"""
        months = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        return months.get(month, 'Unknown')
    
    def get_fact_financials(self) -> List[Dict[str, Any]]:
        """
        FACT_Financials: جدول الحقائق المالية
        رواتب مجمعة، مكافآت، وتكاليف تشغيلية حسب الموقع/المشروع
        """
        # الحصول على جميع سجلات الرواتب
        salaries = Salary.query.all()
        
        # تجميع البيانات
        financial_facts = []
        
        for salary in salaries:
            employee = salary.employee
            if not employee:
                continue
            
            # المنطقة والمشروع
            region = self.standardize_region(employee.location)
            project = employee.project or 'N/A'
            department_name = employee.department.name if employee.department else 'N/A'
            
            # التاريخ
            date_key = int(f"{salary.year}{salary.month:02d}01")
            
            financial_facts.append({
                'date_key': date_key,
                'employee_key': employee.id,
                'department': department_name,
                'region': region,
                'project': project,
                'year': salary.year,
                'month': salary.month,
                'basic_salary': salary.basic_salary or 0,
                'attendance_bonus': salary.attendance_bonus or 0,
                'allowances': salary.allowances or 0,
                'deductions': salary.deductions or 0,
                'bonus': salary.bonus or 0,
                'overtime_hours': salary.overtime_hours or 0,
                'net_salary': salary.net_salary or 0,
                'attendance_deduction': salary.attendance_deduction or 0,
                'absent_days': salary.absent_days or 0,
                'present_days': salary.present_days or 0,
                'leave_days': salary.leave_days or 0,
                'sick_days': salary.sick_days or 0,
                'is_paid': salary.is_paid
            })
        
        return financial_facts
    
    def get_fact_maintenance(self) -> List[Dict[str, Any]]:
        """
        FACT_Maintenance: جدول حقائق الصيانة
        """
        workshops = VehicleWorkshop.query.all()
        
        maintenance_facts = []
        
        for workshop in workshops:
            vehicle = workshop.vehicle
            if not vehicle:
                continue
            
            region = self.standardize_region(vehicle.region)
            department_name = vehicle.department.name if vehicle.department else 'N/A'
            
            # حساب مدة الصيانة
            duration_days = 0
            if workshop.exit_date and workshop.entry_date:
                duration_days = (workshop.exit_date - workshop.entry_date).days
            
            date_key = int(workshop.entry_date.strftime('%Y%m%d')) if workshop.entry_date else 0
            
            maintenance_facts.append({
                'date_key': date_key,
                'vehicle_key': vehicle.id,
                'workshop_id': workshop.id,
                'department': department_name,
                'region': region,
                'maintenance_type': workshop.maintenance_type or 'General',
                'cost': workshop.cost or 0,
                'duration_days': duration_days,
                'entry_date': workshop.entry_date.isoformat() if workshop.entry_date else None,
                'exit_date': workshop.exit_date.isoformat() if workshop.exit_date else None,
                'is_completed': workshop.exit_date is not None
            })
        
        return maintenance_facts
    
    def get_fact_attendance(self, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """
        FACT_Attendance: جدول حقائق الحضور
        """
        if not start_date:
            start_date = date(self.current_year, 1, 1)
        if not end_date:
            end_date = self.today
        
        attendances = Attendance.query.filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        attendance_facts = []
        
        for att in attendances:
            employee = att.employee
            if not employee:
                continue
            
            region = self.standardize_region(employee.location)
            department_name = employee.department.name if employee.department else 'N/A'
            project = employee.project or 'N/A'
            
            date_key = int(att.date.strftime('%Y%m%d')) if att.date else 0
            
            # حالة الحضور
            is_present = att.status in ['present', 'on_time', 'late']
            is_late = att.status == 'late'
            is_absent = att.status == 'absent'
            is_leave = att.status in ['leave', 'annual_leave', 'sick_leave']
            
            attendance_facts.append({
                'date_key': date_key,
                'employee_key': employee.id,
                'department': department_name,
                'region': region,
                'project': project,
                'attendance_date': att.date.isoformat() if att.date else None,
                'status': att.status or 'absent',
                'is_present': is_present,
                'is_late': is_late,
                'is_absent': is_absent,
                'is_leave': is_leave,
                'check_in_time': att.check_in_time.isoformat() if att.check_in_time else None,
                'check_out_time': att.check_out_time.isoformat() if att.check_out_time else None,
                'notes': att.notes or ''
            })
        
        return attendance_facts
    
    def get_kpi_summary(self) -> Dict[str, Any]:
        """
        الحصول على ملخص KPIs الرئيسية
        """
        # إجمالي الالتزامات المالية
        total_salary_liability = db.session.query(
            func.sum(Employee.basic_salary)
        ).filter(Employee.status == 'active').scalar() or 0
        
        # نسبة الأسطول النشط
        total_vehicles = Vehicle.query.count()
        active_vehicles = Vehicle.query.filter_by(status='active').count()
        fleet_active_percentage = (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        
        # تغطية المشاريع
        total_employees = Employee.query.filter_by(status='active').count()
        employees_with_projects = Employee.query.filter(
            Employee.status == 'active',
            Employee.project != None,
            Employee.project != ''
        ).count()
        project_coverage = (employees_with_projects / total_employees * 100) if total_employees > 0 else 0
        
        # عدد الأقسام النشطة
        active_departments = Department.query.count()
        
        # تكاليف الصيانة الشهرية
        first_day = date(self.current_year, self.current_month, 1)
        if self.current_month == 12:
            last_day = date(self.current_year + 1, 1, 1)
        else:
            last_day = date(self.current_year, self.current_month + 1, 1)
        
        monthly_maintenance_cost = db.session.query(
            func.sum(VehicleWorkshop.cost)
        ).filter(
            VehicleWorkshop.entry_date >= first_day,
            VehicleWorkshop.entry_date < last_day
        ).scalar() or 0
        
        # معدل الحضور هذا الشهر
        total_attendance = Attendance.query.filter(
            Attendance.date >= first_day,
            Attendance.date < last_day
        ).count()
        
        present_attendance = Attendance.query.filter(
            Attendance.date >= first_day,
            Attendance.date < last_day,
            Attendance.status.in_(['present', 'on_time', 'late'])
        ).count()
        
        attendance_rate = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0
        
        return {
            'total_salary_liability': round(total_salary_liability, 2),
            'fleet_active_percentage': round(fleet_active_percentage, 2),
            'project_coverage_percentage': round(project_coverage, 2),
            'active_employees': total_employees,
            'active_vehicles': active_vehicles,
            'total_vehicles': total_vehicles,
            'active_departments': active_departments,
            'monthly_maintenance_cost': round(monthly_maintenance_cost, 2),
            'attendance_rate_this_month': round(attendance_rate, 2),
            'data_as_of': self.today.isoformat()
        }


# Instance للاستخدام السريع
bi_engine = BIEngine()
