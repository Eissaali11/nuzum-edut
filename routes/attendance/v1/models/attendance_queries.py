from datetime import date as _date
from core.extensions import db
from sqlalchemy import func

class AttendanceQuery:
    @staticmethod
    def build_employee_subquery(project_name=None):
        # Return a subquery selecting employee IDs for a project, or None
        try:
            from modules.employees.domain.models import Employee
            q = db.session.query(Employee.id)
            if project_name:
                if hasattr(Employee, 'project_name'):
                    q = q.filter(Employee.project_name == project_name)
            return q.subquery()
        except Exception:
            return None

    @staticmethod
    def get_aggregate_rows(start_date, end_date, employee_subq=None):
        try:
            from modules.employees.domain.models import Attendance
            q = db.session.query(Attendance.date.label('att_date'), Attendance.status.label('att_status'), func.count(Attendance.id).label('cnt'))
            q = q.filter(Attendance.date >= start_date, Attendance.date <= end_date)
            if employee_subq is not None:
                q = q.filter(Attendance.employee_id.in_(employee_subq))
            q = q.group_by(Attendance.date, Attendance.status)
            return q.all()
        except Exception:
            return []

    @staticmethod
    def range_stats(start_date, end_date, employee_subq=None):
        try:
            from modules.employees.domain.models import Attendance
            q = db.session.query(Attendance.status, func.count(Attendance.id))
            q = q.filter(Attendance.date >= start_date, Attendance.date <= end_date)
            if employee_subq is not None:
                q = q.filter(Attendance.employee_id.in_(employee_subq))
            q = q.group_by(Attendance.status)
            return q.all()
        except Exception:
            return []

    @staticmethod
    def get_attendance_rows_for_date(att_date, employee_subq=None):
        try:
            from modules.employees.domain.models import Attendance
            q = db.session.query(Attendance)
            q = q.filter(Attendance.date == att_date)
            if employee_subq is not None:
                q = q.filter(Attendance.employee_id.in_(employee_subq))
            return q.all()
        except Exception:
            return []

    @staticmethod
    def get_active_projects():
        try:
            from modules.employees.domain.models import Employee
            q = db.session.query(func.distinct(Employee.project_name)).filter(Employee.project_name != None)
            return [r[0] for r in q.all()]
        except Exception:
            return []

    @staticmethod
    def active_employees_count(employee_subq=None):
        try:
            from modules.employees.domain.models import Employee
            q = db.session.query(func.count(Employee.id))
            if employee_subq is not None:
                q = q.filter(Employee.id.in_(employee_subq))
            return q.scalar() or 0
        except Exception:
            return 0
from core.extensions import db
from sqlalchemy import func


class AttendanceQuery:
    """Data access helpers for attendance dashboard queries."""

    @staticmethod
    def build_employee_subquery(project_name):
        if not project_name:
            return None
        try:
            from modules.employees.domain.models import Employee
            return db.session.query(Employee.id).filter(
                Employee.project == project_name,
                ~Employee.status.in_(['terminated', 'inactive'])
            ).subquery()
        except Exception:
            return None

    @staticmethod
    def get_aggregate_rows(start_date, end_date, employee_subq=None):
        from modules.employees.domain.models import Attendance
        q = db.session.query(
            Attendance.date.label('att_date'),
            Attendance.status.label('att_status'),
            func.count(Attendance.id).label('cnt')
        ).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        if employee_subq is not None:
            q = q.filter(Attendance.employee_id.in_(employee_subq))
        q = q.group_by(Attendance.date, Attendance.status)
        return q.all()

    @staticmethod
    def get_attendance_rows_for_date(att_date, employee_subq=None):
        """Return Attendance rows for a specific date (used for late calculations)."""
        try:
            from modules.employees.domain.models import Attendance
            q = db.session.query(Attendance).filter(Attendance.date == att_date)
            if employee_subq is not None:
                q = q.filter(Attendance.employee_id.in_(employee_subq))
            return q.all()
        except Exception:
            return []

    @staticmethod
    def range_stats(start_date, end_date, employee_subq=None):
        from modules.employees.domain.models import Attendance
        q = db.session.query(
            Attendance.status,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        if employee_subq is not None:
            q = q.filter(Attendance.employee_id.in_(employee_subq))
        return q.group_by(Attendance.status).all()

    @staticmethod
    def get_active_projects():
        try:
            from modules.employees.domain.models import Employee
            rows = db.session.query(Employee.project).filter(
                ~Employee.status.in_(['terminated', 'inactive']),
                Employee.project.isnot(None)
            ).distinct().all()
            return [p[0] for p in rows if p[0]]
        except Exception:
            return []

    @staticmethod
    def active_employees_count(employee_subq=None):
        from sqlalchemy import func
        try:
            if employee_subq is not None:
                return db.session.query(func.count()).select_from(employee_subq).scalar() or 0
            from modules.employees.domain.models import employee_departments, Employee as _Emp
            return db.session.query(func.count(func.distinct(_Emp.id))).join(
                employee_departments, _Emp.id == employee_departments.c.employee_id
            ).filter(~_Emp.status.in_(['terminated', 'inactive'])).scalar() or 0
        except Exception:
            return 0
