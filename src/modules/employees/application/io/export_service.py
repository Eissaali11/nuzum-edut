"""Employee export service for Excel/CSV generation."""
from io import BytesIO
from datetime import datetime
from typing import Optional

from src.core.extensions import db
from models import Employee, SystemAudit


def export_employees_excel() -> BytesIO:
    """
    Export all employees to Excel file with basic information.
    Returns BytesIO object ready for download.
    """
    from src.utils.excel import generate_employee_excel
    
    employees = Employee.query.options(
        db.joinedload(Employee.departments),
        db.joinedload(Employee.nationality_rel)
    ).all()
    
    output = generate_employee_excel(employees)
    
    # Log the export
    audit = SystemAudit(
        action='export',
        entity_type='employee',
        entity_id=0,
        details=f'تم تصدير {len(employees)} موظف إلى ملف Excel'
    )
    db.session.add(audit)
    db.session.commit()
    
    return BytesIO(output.getvalue())


def export_employees_comprehensive() -> tuple[BytesIO, str]:
    """
    Export comprehensive employee data with all details.
    Returns tuple of (BytesIO object, filename).
    """
    from src.utils.basic_comprehensive_export import generate_comprehensive_employee_excel
    
    employees = Employee.query.options(
        db.joinedload(Employee.departments),
        db.joinedload(Employee.nationality_rel),
        db.joinedload(Employee.salaries),
        db.joinedload(Employee.attendances),
        db.joinedload(Employee.documents)
    ).all()
    
    output = generate_comprehensive_employee_excel(employees)
    
    # Log the export
    audit = SystemAudit(
        action='export_comprehensive',
        entity_type='employee',
        entity_id=0,
        details=f'تم التصدير الشامل لبيانات {len(employees)} موظف مع جميع التفاصيل'
    )
    db.session.add(audit)
    db.session.commit()
    
    # Generate filename with timestamp
    current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'تصدير_شامل_الموظفين_{current_date}.xlsx'
    
    return output, filename
