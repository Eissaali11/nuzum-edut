from decimal import Decimal
from datetime import date
import calendar
import logging

from core.extensions import db
from sqlalchemy import func
from models import Employee, Department, Attendance, employee_departments
from modules.payroll.domain.models import PayrollRecord
from modules.vehicles.domain.models import Vehicle
from modules.vehicles.domain.handover_models import VehicleHandover
from modules.accounting.domain.profitability_models import ProjectContract, ContractResource

logger = logging.getLogger(__name__)

ZERO = Decimal('0')

IQAMA_ANNUAL_COST = Decimal('650')
INSURANCE_ANNUAL_COST = Decimal('1800')
IQAMA_MONTHLY = IQAMA_ANNUAL_COST / Decimal('12')
INSURANCE_MONTHLY = INSURANCE_ANNUAL_COST / Decimal('12')


def _get_employee_vehicle_cost(employee_id, month, year):
    last_handover = (
        VehicleHandover.query
        .filter(
            VehicleHandover.employee_id == employee_id,
            VehicleHandover.handover_type == 'delivery',
            VehicleHandover.handover_date <= date(year, month, calendar.monthrange(year, month)[1])
        )
        .order_by(VehicleHandover.handover_date.desc())
        .first()
    )
    if not last_handover:
        return ZERO

    vehicle = Vehicle.query.get(last_handover.vehicle_id)
    if not vehicle:
        return ZERO

    return Decimal(str(vehicle.monthly_fixed_cost or 0))


def calculate_project_profitability(department_id, month, year):
    department = Department.query.get(department_id)
    if not department:
        return None

    contract = (
        ProjectContract.query
        .filter_by(department_id=department_id, status='active')
        .first()
    )

    active_employees = (
        Employee.query
        .join(employee_departments)
        .filter(
            employee_departments.c.department_id == department_id,
            Employee.status == 'active'
        )
        .all()
    )

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    employees_data = []
    totals = {
        'revenue': ZERO,
        'salary_cost': ZERO,
        'gosi_cost': ZERO,
        'vehicle_cost': ZERO,
        'overhead': ZERO,
        'iqama_insurance': ZERO,
        'total_cost': ZERO,
        'profit': ZERO,
    }

    for emp in active_employees:
        resource = None
        if contract:
            resource = (
                ContractResource.query
                .filter_by(contract_id=contract.id, employee_id=emp.id, is_active=True)
                .first()
            )

        if resource and resource.start_date and resource.start_date > end_date:
            resource = None
        if resource and resource.end_date and resource.end_date < start_date:
            resource = None

        billing_rate = Decimal(str(resource.billing_rate)) if resource else ZERO
        billing_type = resource.billing_type if resource else 'monthly'
        overhead = Decimal(str(resource.overhead_monthly)) if resource else ZERO
        housing = Decimal(str(resource.housing_allowance)) if resource else ZERO

        payroll = (
            PayrollRecord.query
            .filter_by(employee_id=emp.id, pay_period_month=month, pay_period_year=year)
            .first()
        )

        if payroll:
            salary_cost = Decimal(str(payroll.gross_salary or 0))
            gosi_company = Decimal(str(payroll.gosi_company or 0))
            present_days = payroll.present_days or 0
        else:
            salary_cost = Decimal(str(emp.basic_salary or 0))
            gosi_company = salary_cost * Decimal('0.13')
            present_count = (
                db.session.query(func.count(Attendance.id))
                .filter(
                    Attendance.employee_id == emp.id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date,
                    Attendance.status == 'present'
                )
                .scalar() or 0
            )
            present_days = present_count

        vehicle_cost = _get_employee_vehicle_cost(emp.id, month, year)

        iqama_cost = IQAMA_MONTHLY
        insurance_cost = INSURANCE_MONTHLY

        if billing_type == 'daily':
            revenue = billing_rate * Decimal(str(present_days))
        else:
            revenue = billing_rate

        total_cost = salary_cost + gosi_company + vehicle_cost + overhead + housing + iqama_cost + insurance_cost
        net_profit = revenue - total_cost
        margin_pct = (net_profit / revenue * 100) if revenue > 0 else ZERO

        emp_data = {
            'employee_id': emp.id,
            'employee_name': emp.name,
            'employee_code': emp.employee_id,
            'job_title': emp.job_title,
            'billing_rate': float(billing_rate),
            'billing_type': billing_type,
            'present_days': present_days,
            'revenue': float(revenue),
            'salary_cost': float(salary_cost),
            'gosi_cost': float(gosi_company),
            'vehicle_cost': float(vehicle_cost),
            'overhead': float(overhead),
            'housing': float(housing),
            'iqama_cost': float(iqama_cost),
            'insurance_cost': float(insurance_cost),
            'total_cost': float(total_cost),
            'net_profit': float(net_profit),
            'margin_pct': float(margin_pct),
        }
        employees_data.append(emp_data)

        totals['revenue'] += revenue
        totals['salary_cost'] += salary_cost
        totals['gosi_cost'] += gosi_company
        totals['vehicle_cost'] += vehicle_cost
        totals['overhead'] += overhead + housing
        totals['iqama_insurance'] = totals.get('iqama_insurance', ZERO) + iqama_cost + insurance_cost
        totals['total_cost'] += total_cost
        totals['profit'] += net_profit

    overall_margin = (totals['profit'] / totals['revenue'] * 100) if totals['revenue'] > 0 else ZERO

    return {
        'department': {
            'id': department.id,
            'name': department.name,
        },
        'contract': {
            'id': contract.id if contract else None,
            'client_name': contract.client_name if contract else 'غير محدد',
            'contract_type': contract.contract_type if contract else None,
            'contract_type_ar': contract.contract_type_ar if contract else 'غير محدد',
        },
        'period': {
            'month': month,
            'year': year,
            'month_name': _get_month_name_ar(month),
        },
        'employees': employees_data,
        'totals': {k: float(v) for k, v in totals.items()},
        'overall_margin': float(overall_margin),
        'employee_count': len(active_employees),
        'configured_count': sum(1 for e in employees_data if e['billing_rate'] > 0),
    }


def get_all_projects_summary(month, year):
    departments = Department.query.order_by(Department.name).all()
    projects = []

    for dept in departments:
        emp_count = (
            db.session.query(func.count(employee_departments.c.employee_id))
            .filter(employee_departments.c.department_id == dept.id)
            .join(Employee, Employee.id == employee_departments.c.employee_id)
            .filter(Employee.status == 'active')
            .scalar() or 0
        )
        if emp_count == 0:
            continue

        result = calculate_project_profitability(dept.id, month, year)
        if not result:
            continue

        projects.append({
            'department_id': dept.id,
            'department_name': dept.name,
            'client_name': result['contract']['client_name'],
            'employee_count': result['employee_count'],
            'configured_count': result['configured_count'],
            'revenue': result['totals']['revenue'],
            'total_cost': result['totals']['total_cost'],
            'profit': result['totals']['profit'],
            'margin': result['overall_margin'],
        })

    grand_totals = {
        'revenue': sum(p['revenue'] for p in projects),
        'total_cost': sum(p['total_cost'] for p in projects),
        'profit': sum(p['profit'] for p in projects),
        'employees': sum(p['employee_count'] for p in projects),
    }
    grand_totals['margin'] = (
        (grand_totals['profit'] / grand_totals['revenue'] * 100)
        if grand_totals['revenue'] > 0 else 0
    )

    return {
        'projects': projects,
        'totals': grand_totals,
        'period': {
            'month': month,
            'year': year,
            'month_name': _get_month_name_ar(month),
        }
    }


def _get_month_name_ar(month):
    names = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    return names.get(month, '')
