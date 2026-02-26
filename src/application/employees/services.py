"""
خدمات طبقة التطبيق للموظفين — جلب، فلترة، إحصائيات.
يُستدعى من طبقة العرض فقط. لا يتجاوز 400 سطر.
"""
from typing import Optional, List, Set, Any
from sqlalchemy import func, or_

from src.core.extensions import db
from src.domain.employees.models import Employee, Department, employee_departments


def list_employees_page_data(
    department_filter: str = "",
    status_filter: str = "",
    multi_department_filter: str = "",
    no_department_filter: str = "",
    duplicate_names_filter: str = "",
    location_filter: str = "",
    assigned_department_id: Optional[int] = None,
) -> dict:
    """
    يجلب بيانات صفحة قائمة الموظفين: الموظفون المفلترون، الأقسام، والإحصائيات.
    assigned_department_id: إن وُجد، يُقيّد النتائج والأقسام بقسم المستخدم فقط.
    """
    query = Employee.query.options(
        db.joinedload(Employee.departments),
        db.joinedload(Employee.nationality_rel),
    )

    if assigned_department_id:
        query = query.join(employee_departments).join(Department).filter(
            Department.id == assigned_department_id
        )
    elif department_filter:
        query = query.join(employee_departments).join(Department).filter(
            Department.id == department_filter
        )

    if status_filter:
        query = query.filter(Employee.status == status_filter)

    if location_filter:
        query = query.filter(Employee.location == location_filter)

    if duplicate_names_filter == "yes":
        duplicate_subq = (
            db.session.query(Employee.name, func.count(Employee.name).label("name_count"))
            .group_by(Employee.name)
            .having(func.count(Employee.name) > 1)
            .subquery()
        )
        query = query.join(duplicate_subq, Employee.name == duplicate_subq.c.name)

    if no_department_filter == "yes":
        query = query.outerjoin(employee_departments).filter(
            employee_departments.c.employee_id.is_(None)
        )
    elif multi_department_filter == "yes":
        subq = (
            db.session.query(
                employee_departments.c.employee_id,
                func.count(employee_departments.c.department_id).label("dept_count"),
            )
            .group_by(employee_departments.c.employee_id)
            .having(func.count(employee_departments.c.department_id) > 1)
            .subquery()
        )
        query = query.join(subq, Employee.id == subq.c.employee_id)
    elif multi_department_filter == "no":
        subq = (
            db.session.query(
                employee_departments.c.employee_id,
                func.count(employee_departments.c.department_id).label("dept_count"),
            )
            .group_by(employee_departments.c.employee_id)
            .having(func.count(employee_departments.c.department_id) <= 1)
            .subquery()
        )
        query = query.outerjoin(subq, Employee.id == subq.c.employee_id).filter(
            or_(subq.c.employee_id.is_(None), subq.c.dept_count <= 1)
        )

    employees: List[Any] = query.all()

    if assigned_department_id:
        departments = Department.query.filter(Department.id == assigned_department_id).all()
    else:
        departments = Department.query.all()

    multi_dept_count = (
        db.session.query(Employee.id)
        .join(employee_departments)
        .group_by(Employee.id)
        .having(func.count(employee_departments.c.department_id) > 1)
        .count()
    )
    no_dept_count = (
        db.session.query(Employee.id)
        .outerjoin(employee_departments)
        .filter(employee_departments.c.employee_id.is_(None))
        .count()
    )
    duplicate_names_list = (
        db.session.query(Employee.name)
        .group_by(Employee.name)
        .having(func.count(Employee.name) > 1)
        .all()
    )
    duplicate_names_count = 0
    duplicate_names_set: Set[str] = set()
    for (name,) in duplicate_names_list:
        duplicate_names_count += db.session.query(Employee).filter(Employee.name == name).count()
        duplicate_names_set.add(name)
    total = db.session.query(Employee).count()
    single_dept_count = total - multi_dept_count - no_dept_count

    return {
        "employees": employees,
        "departments": departments,
        "current_department": department_filter,
        "current_status": status_filter,
        "current_location": location_filter,
        "current_multi_department": multi_department_filter,
        "current_no_department": no_department_filter,
        "current_duplicate_names": duplicate_names_filter,
        "multi_dept_count": multi_dept_count,
        "single_dept_count": single_dept_count,
        "no_dept_count": no_dept_count,
        "duplicate_names_count": duplicate_names_count,
        "duplicate_names_set": duplicate_names_set,
    }
