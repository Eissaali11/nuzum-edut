"""
Strategic Payroll Processor Service
محرك حساب الرواتب الاستراتيجي
يتوافق مع قانون العمل السعودي
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func
from core.extensions import db
from models import Employee, Attendance
from modules.payroll.domain.models import PayrollRecord, PayrollConfiguration, PayrollHistory


class PayrollProcessor:
    """معالج الرواتب - الحسابات الأساسية"""
    
    def __init__(self, pay_period_year: int, pay_period_month: int):
        self.pay_period_year = pay_period_year
        self.pay_period_month = pay_period_month
        self.config = self._get_active_configuration()
        
    def _get_active_configuration(self) -> PayrollConfiguration:
        """الحصول على إعدادات الرواتب النشطة"""
        config = PayrollConfiguration.query.filter_by(is_active=True).order_by(
            PayrollConfiguration.effective_from.desc()
        ).first()
        
        if not config:
            # إنشاء إعدادات افتراضية
            config = PayrollConfiguration()
            db.session.add(config)
            db.session.commit()
        
        return config
    
    def _calculate_period_dates(self) -> tuple:
        """حساب تواريخ بداية ونهاية الفترة"""
        if self.pay_period_month == 2:
            # فبراير - 28 أو 29 يوم
            last_day = 29 if self.pay_period_year % 4 == 0 else 28
        elif self.pay_period_month in [4, 6, 9, 11]:
            last_day = 30
        else:
            last_day = 31
        
        start_date = date(self.pay_period_year, self.pay_period_month, 1)
        end_date = date(self.pay_period_year, self.pay_period_month, last_day)
        
        return start_date, end_date
    
    def calculate_daily_rate(self, basic_salary: Decimal) -> Decimal:
        """
        حساب الراتب اليومي
        Daily_Rate = Basic_Salary / 30
        """
        return Decimal(str(basic_salary)) / Decimal('30')
    
    def calculate_hourly_rate(self, basic_salary: Decimal) -> Decimal:
        """
        حساب الراتب بالساعة
        Hourly_Rate = Basic_Salary / (30 * 8)
        """
        return Decimal(str(basic_salary)) / (Decimal('30') * Decimal('8'))
    
    def calculate_attendance_data(self, employee_id: int, start_date: date, end_date: date) -> dict:
        """
        حساب بيانات الحضور والغياب
        """
        # جلب سجلات الحضور
        attendance_records = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        # تصنيف الأيام
        present_days = 0
        absent_days = 0
        leave_days = 0
        unpaid_leave_days = 0
        sick_leave_days = 0
        
        for record in attendance_records:
            if record.status == 'present':
                present_days += 1
            elif record.status == 'absent':
                absent_days += 1
            elif record.status == 'leave':
                leave_days += 1
            elif record.status == 'unpaid_leave':
                unpaid_leave_days += 1
            elif record.status == 'sick_leave':
                sick_leave_days += 1
        
        # حساب أيام العطل والعطل الرسمية
        # (هذا يمكن تحسينه لاحقاً برابط قاعدة البيانات للعطل)
        public_holiday_days = 0
        
        # إجمالي أيام العمل الفعلية
        working_days_required = self.config.working_days_per_month
        actual_working_days = (
            present_days + leave_days + 
            sick_leave_days + public_holiday_days
        )
        
        return {
            'present_days': present_days,
            'absent_days': absent_days,
            'leave_days': leave_days,
            'unpaid_leave_days': unpaid_leave_days,
            'sick_leave_days': sick_leave_days,
            'public_holiday_days': public_holiday_days,
            'actual_working_days': actual_working_days,
            'working_days_required': working_days_required,
        }
    
    def calculate_absence_deduction(self, daily_rate: Decimal, absent_days: int) -> Decimal:
        """
        حساب خصم الغياب
        Absence_Deduction = Absent_Days * Daily_Rate
        """
        return Decimal(str(absent_days)) * daily_rate
    
    def calculate_unpaid_leave_deduction(self, daily_rate: Decimal, unpaid_leave_days: int) -> Decimal:
        """
        حساب خصم الإجازة بدون راتب
        """
        return Decimal(str(unpaid_leave_days)) * daily_rate
    
    def calculate_gosi(self, employee_id: int, basic_salary: Decimal) -> dict:
        """
        حساب اشتراكات GOSI بناءً على جنسية الموظف
        """
        employee = Employee.query.get(employee_id)
        
        gosi_employee = Decimal('0')
        gosi_company = Decimal('0')
        
        # التحقق من الجنسية وتطبيق القوانين
        if employee.nationality == 'Saudi' or employee.nationality_id:
            if self.config.saudi_national_gosi_required:
                gosi_employee = (
                    Decimal(str(basic_salary)) * 
                    (self.config.gosi_employee_percentage / Decimal('100'))
                )
                gosi_company = (
                    Decimal(str(basic_salary)) * 
                    (self.config.gosi_company_percentage / Decimal('100'))
                )
        else:
            # موظف أجنبي
            if self.config.expat_gosi_required:
                gosi_employee = (
                    Decimal(str(basic_salary)) * 
                    (self.config.gosi_employee_percentage / Decimal('100'))
                )
                gosi_company = (
                    Decimal(str(basic_salary)) * 
                    (self.config.gosi_company_percentage / Decimal('100'))
                )
        
        return {
            'gosi_employee': gosi_employee,
            'gosi_company': gosi_company,
            'total_gosi': gosi_employee,  # الموظف يدفع فقط
        }
    
    def calculate_gross_salary(self, employee: Employee) -> dict:
        """
        حساب الراتب الإجمالي قبل الخصومات
        Gross_Salary = Basic + Allowances
        """
        basic = Decimal(str(employee.basic_salary or 0))
        
        allowances = {
            'housing': Decimal(str(getattr(employee, 'housing_allowance', 0) or 0)),
            'transportation': Decimal(str(getattr(employee, 'transportation', 0) or 0)),
            'meal': Decimal(str(getattr(employee, 'meal_allowance', 0) or 0)),
            'other': Decimal('0'),
        }
        
        total_allowances = sum(allowances.values())
        gross = basic + total_allowances
        
        return {
            'basic': basic,
            'allowances': allowances,
            'total_allowances': total_allowances,
            'gross': gross,
        }

    def _to_decimal(self, value) -> Decimal:
        return Decimal(str(value if value is not None else 0))
    
    def process_employee_payroll(self, employee_id: int) -> PayrollRecord:
        """
        معالجة الراتب الكامل للموظف
        """
        employee = Employee.query.get(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # الحصول على تواريخ الفترة
        start_date, end_date = self._calculate_period_dates()
        
        # التحقق من وجود سجل راتب سابق
        existing_payroll = PayrollRecord.query.filter_by(
            employee_id=employee_id,
            pay_period_year=self.pay_period_year,
            pay_period_month=self.pay_period_month
        ).first()
        
        if existing_payroll:
            payroll = existing_payroll
        else:
            payroll = PayrollRecord(
                employee_id=employee_id,
                pay_period_year=self.pay_period_year,
                pay_period_month=self.pay_period_month,
                pay_period_start=start_date,
                pay_period_end=end_date,
            )
        
        # 1. الراتب الأساسي
        gross_data = self.calculate_gross_salary(employee)
        payroll.basic_salary = gross_data['basic']
        payroll.daily_rate = self.calculate_daily_rate(gross_data['basic'])
        payroll.hourly_rate = self.calculate_hourly_rate(gross_data['basic'])
        
        # المزايا
        payroll.housing_allowance = gross_data['allowances']['housing']
        payroll.transportation = gross_data['allowances']['transportation']
        payroll.meal_allowance = gross_data['allowances']['meal']
        
        # 2. بيانات الحضور
        attendance = self.calculate_attendance_data(employee_id, start_date, end_date)
        payroll.present_days = attendance['present_days']
        payroll.absent_days = attendance['absent_days']
        payroll.leave_days = attendance['leave_days']
        payroll.unpaid_leave_days = attendance['unpaid_leave_days']
        payroll.sick_leave_days = attendance['sick_leave_days']
        payroll.actual_working_days = attendance['actual_working_days']
        payroll.working_days_required = attendance['working_days_required']
        
        # 3. الخصومات
        # خصم الغياب
        payroll.absence_deduction = self.calculate_absence_deduction(
            payroll.daily_rate,
            attendance['absent_days']
        )
        
        # خصم الإجازة بدون راتب
        unpaid_deduction = self.calculate_unpaid_leave_deduction(
            payroll.daily_rate,
            attendance['unpaid_leave_days']
        )
        
        # GOSI
        gosi_data = self.calculate_gosi(employee_id, gross_data['basic'])
        payroll.gosi_employee = gosi_data['gosi_employee']
        payroll.gosi_company = gosi_data['gosi_company']
        
        # 4. حساب الراتب الإجمالي والنهائي
        payroll.gross_salary = gross_data['gross']
        
        total_deductions = (
            self._to_decimal(payroll.absence_deduction) +
            self._to_decimal(unpaid_deduction) +
            self._to_decimal(payroll.gosi_employee) +
            self._to_decimal(payroll.late_deduction) +
            self._to_decimal(payroll.early_leave_deduction) +
            self._to_decimal(payroll.loan_deduction) +
            self._to_decimal(payroll.insurance_deduction) +
            self._to_decimal(payroll.other_deductions)
        )
        
        payroll.total_deductions = total_deductions
        payroll.net_payable = payroll.gross_salary - total_deductions
        
        # التأكد من عدم سلبية الراتب
        if payroll.net_payable < Decimal('0'):
            payroll.net_payable = Decimal('0')
        
        payroll.calculated_at = datetime.utcnow()
        payroll.payment_status = 'pending'
        
        return payroll
    
    def process_all_employees(self) -> list:
        """
        معالجة رواتب جميع الموظفين النشطين
        """
        # جلب جميع الموظفين النشطين
        employees = Employee.query.filter_by(status='active').all()
        
        processed_payrolls = []
        
        for employee in employees:
            try:
                payroll = self.process_employee_payroll(employee.id)
                db.session.add(payroll)
                processed_payrolls.append(payroll)
            except Exception as e:
                print(f"Error processing payroll for employee {employee.id}: {str(e)}")
                continue
        
        db.session.commit()
        return processed_payrolls
    
    def approve_payroll(self, payroll_id: int, approved_by_user_id: int, notes: str = None) -> PayrollRecord:
        """
        الموافقة على الراتب
        """
        payroll = PayrollRecord.query.get(payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")
        
        payroll.payment_status = 'approved'
        payroll.approved_by = approved_by_user_id
        payroll.approved_at = datetime.utcnow()
        
        if notes:
            payroll.admin_notes = notes
        
        db.session.commit()
        return payroll
    
    def reject_payroll(self, payroll_id: int, reason: str) -> PayrollRecord:
        """
        رفض الراتب
        """
        payroll = PayrollRecord.query.get(payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")
        
        payroll.payment_status = 'rejected'
        payroll.admin_notes = f"مرفوض: {reason}"
        
        db.session.commit()
        return payroll
    
    def mark_as_paid(self, payroll_id: int, payment_date: datetime = None) -> PayrollRecord:
        """
        تحديث حالة الراتب إلى مدفوع
        """
        payroll = PayrollRecord.query.get(payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")
        
        payroll.payment_status = 'paid'
        payroll.payment_date = payment_date or datetime.utcnow()
        payroll.is_exported = True
        
        db.session.commit()
        return payroll
