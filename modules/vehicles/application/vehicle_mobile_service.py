"""
خدمة واجهة الموبايل للمركبات — استعلامات وعمليات خاصة بـ Mobile API.
تُستخدم من: presentation/api/mobile/vehicle_routes.py
المعاملات تُمرَّر من طبقة العرض؛ لا استخدام لـ request أو Flask globals.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from core.extensions import db
from modules.vehicles.domain.models import (
    Vehicle,
    VehicleHandover,
    VehicleProject,
    VehicleWorkshop,
)
from domain.employees.models import Department, Employee, employee_departments
from modules.vehicles.domain import (
    ExternalAuthorization,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehiclePeriodicInspection,
    VehicleSafetyCheck,
)


def get_vehicle_details_context(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على سياق كامل لتفاصيل مركبة من أجل Mobile API.
    
    Args:
        vehicle_id: معرف المركبة.
    
    Returns:
        Dict أو None: قاموس يحتوي على بيانات السيارة وجميع السجلات المرتبطة،
        أو None إذا لم تُعثر على المركبة.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    
    try:
        # جلب سجلات الصيانة
        maintenance_records = (
            VehicleMaintenance.query
            .filter_by(vehicle_id=vehicle_id)
            .order_by(VehicleMaintenance.date.desc())
            .all()
        )
        
        # جلب سجلات الورشة
        workshop_records = (
            VehicleWorkshop.query
            .filter_by(vehicle_id=vehicle_id)
            .order_by(VehicleWorkshop.entry_date.desc())
            .all()
        )
        
        # جلب تعيينات المشاريع
        project_assignments = (
            VehicleProject.query
            .filter_by(vehicle_id=vehicle_id)
            .order_by(VehicleProject.start_date.desc())
            .limit(5)
            .all()
        )
        
        # جلب سجلات التسليم والاستلام مع بيانات الموظف
        handover_records = (
            VehicleHandover.query
            .filter_by(vehicle_id=vehicle_id)
            .options(
                joinedload(VehicleHandover.driver_employee).joinedload(Employee.departments)
            )
            .order_by(VehicleHandover.handover_date.desc())
            .all()
        )
        
        # جلب التفويضات الخارجية
        external_authorizations = ExternalAuthorization.query.filter_by(
            vehicle_id=vehicle_id
        ).all()
        external_authorizations = sorted(
            external_authorizations,
            key=lambda x: x.created_at or datetime.min,
            reverse=True,
        )
        
        # جلب الأقسام والموظفين
        departments = Department.query.all()
        employees = Employee.query.all()
        
        # جلب سجلات الفحص الدوري
        periodic_inspections = (
            VehiclePeriodicInspection.query
            .filter_by(vehicle_id=vehicle_id)
            .order_by(VehiclePeriodicInspection.inspection_date.desc())
            .limit(3)
            .all()
        )
        
        # جلب سجلات فحص السلامة
        safety_checks = (
            VehicleSafetyCheck.query
            .filter_by(vehicle_id=vehicle_id)
            .order_by(VehicleSafetyCheck.check_date.desc())
            .limit(3)
            .all()
        )
        
        # حساب تكلفة الإصلاحات الإجمالية
        total_maintenance_cost = (
            db.session.query(func.sum(VehicleWorkshop.cost))
            .filter_by(vehicle_id=vehicle_id)
            .scalar() or 0
        )
        
        # حساب عدد الأيام في الورشة (للسنة الحالية)
        current_year = datetime.now().year
        days_in_workshop = 0
        for record in workshop_records:
            if record.entry_date.year == current_year:
                if record.exit_date:
                    days_in_workshop += (record.exit_date - record.entry_date).days
                else:
                    days_in_workshop += (datetime.now().date() - record.entry_date).days
        
        # ملاحظات تنبيهية عن انتهاء الفحص الدوري
        inspection_warnings = []
        for inspection in periodic_inspections:
            if hasattr(inspection, 'is_expired') and inspection.is_expired:
                days_expired = (datetime.now().date() - inspection.expiry_date).days
                inspection_warnings.append(
                    f"الفحص الدوري منتهي الصلاحية منذ {days_expired} يومًا"
                )
                break
            elif hasattr(inspection, 'is_expiring_soon') and inspection.is_expiring_soon:
                days_remaining = (inspection.expiry_date - datetime.now().date()).days
                inspection_warnings.append(
                    f"الفحص الدوري سينتهي خلال {days_remaining} يومًا"
                )
                break
        
        return {
            'vehicle': vehicle,
            'maintenance_records': maintenance_records,
            'workshop_records': workshop_records,
            'project_assignments': project_assignments,
            'handover_records': handover_records,
            'external_authorizations': external_authorizations,
            'departments': departments,
            'employees': employees,
            'periodic_inspections': periodic_inspections,
            'safety_checks': safety_checks,
            'documents': [],  # سيتم إضافة منطق لجلب الوثائق لاحقاً
            'fees': [],  # سيتم إضافة منطق لجلب الرسوم لاحقاً
            'total_maintenance_cost': total_maintenance_cost,
            'days_in_workshop': days_in_workshop,
            'inspection_warnings': inspection_warnings,
        }
    
    except Exception as e:
        print(f"خطأ في get_vehicle_details_context: {str(e)}")
        return None


def get_maintenance_details_context(maintenance_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على سياق تفاصيل سجل صيانة.
    
    Args:
        maintenance_id: معرف سجل الصيانة.
    
    Returns:
        Dict أو None: قاموس يحتوي على maintenance، vehicle، images، status_class.
    """
    maintenance = VehicleMaintenance.query.get(maintenance_id)
    if not maintenance:
        return None
    
    vehicle = Vehicle.query.get(maintenance.vehicle_id)
    
    # تحديد الفئة المناسبة لحالة الصيانة
    status_class = ""
    if maintenance.status == "قيد التنفيذ":
        status_class = "ongoing"
    elif maintenance.status == "منجزة":
        status_class = "completed"
    elif maintenance.status == "قيد الانتظار":
        if maintenance.date < datetime.now().date():
            status_class = "late"
        else:
            status_class = "scheduled"
    elif maintenance.status == "ملغية":
        status_class = "canceled"
    
    # جلب صور الصيانة
    images = VehicleMaintenanceImage.query.filter_by(maintenance_id=maintenance_id).all()
    
    return {
        'maintenance': maintenance,
        'vehicle': vehicle,
        'images': images,
        'status_class': status_class,
    }


def get_vehicle_list_context(
    status_filter: str = "",
    make_filter: str = "",
    type_filter: str = "",
    department_filter: str = "",
    search_filter: str = "",
    page: int = 1,
    per_page: int = 50,
    assigned_department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    الحصول على سياق قائمة المركبات للموبايل مع التصفية والترقيم.
    
    Args:
        status_filter: تصفية حسب الحالة.
        make_filter: تصفية حسب الشركة المصنعة.
        type_filter: تصفية حسب النوع.
        department_filter: تصفية حسب القسم.
        search_filter: بحث في رقم اللوحة أو المودل.
        page: رقم الصفحة.
        per_page: عدد السيارات لكل صفحة.
        assigned_department_id: معرف القسم المخصص للمستخدم الحالي (للتصفية).
    
    Returns:
        Dict: قائمة المركبات، معلومات الترقيم، الفلاتر.
    """
    query = Vehicle.query
    
    # تصفية حسب الحالة
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    
    # تصفية حسب الشركة المصنعة
    if make_filter:
        query = query.filter(Vehicle.make == make_filter)
    
    # تصفية حسب النوع
    if type_filter:
        query = query.filter(Vehicle.type_of_car == type_filter)
    
    # تصفية حسب القسم (من خلال السائق الحالي)
    if department_filter:
        employees_in_dept = (
            db.session.query(Employee.name)
            .join(employee_departments, Employee.id == employee_departments.c.employee_id)
            .filter(employee_departments.c.department_id == department_filter)
            .all()
        )
        employee_names = [emp[0] for emp in employees_in_dept]
        
        if employee_names:
            query = query.filter(Vehicle.driver_name.in_(employee_names))
        else:
            query = query.filter(Vehicle.id == -1)  # لا توجد نتائج
    
    # البحث في رقم اللوحة أو المودل
    if search_filter:
        search_term = f"%{search_filter}%"
        query = query.filter(
            or_(
                Vehicle.plate_number.ilike(search_term),
                Vehicle.model.ilike(search_term),
                Vehicle.make.ilike(search_term),
            )
        )
    
    # الترقيم
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    vehicles = pagination.items
    
    # جلب الأقسام وجميع القيم المميزة للفلاتر
    departments = Department.query.all()
    statuses = db.session.query(Vehicle.status).distinct().all()
    makes = db.session.query(Vehicle.make).distinct().all()
    types = db.session.query(Vehicle.type_of_car).filter(
        Vehicle.type_of_car.isnot(None)
    ).distinct().all()
    
    return {
        'vehicles': vehicles,
        'pagination': pagination,
        'departments': departments,
        'statuses': [s[0] for s in statuses if s[0]],
        'makes': [m[0] for m in makes if m[0]],
        'types': [t[0] for t in types if t[0]],
        'current_filters': {
            'status': status_filter,
            'make': make_filter,
            'type': type_filter,
            'department': department_filter,
            'search': search_filter,
        },
        'page': page,
        'per_page': per_page,
    }


def get_vehicle_driver_info(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على معلومات السائق الحالي للمركبة.
    
    Args:
        vehicle_id: معرف المركبة.
    
    Returns:
        Dict أو None: معلومات السائق (driver_name، employee_id، department_name)
        أو None إذا لم تُعثر على المركبة.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    
    # البحث عن آخر تسليم
    latest_handover = (
        VehicleHandover.query
        .filter_by(vehicle_id=vehicle_id, handover_type='delivery')
        .order_by(VehicleHandover.handover_date.desc())
        .first()
    )
    
    driver_name = vehicle.driver_name
    employee_id = None
    department_name = None
    
    if latest_handover:
        if latest_handover.employee_id:
            employee_id = latest_handover.employee_id
            employee = Employee.query.get(employee_id)
            if employee:
                driver_name = employee.name
                if employee.departments:
                    department_name = employee.departments[0].name
        elif latest_handover.person_name:
            driver_name = latest_handover.person_name
    
    return {
        'vehicle_id': vehicle_id,
        'driver_name': driver_name,
        'employee_id': employee_id,
        'department_name': department_name,
        'plate_number': vehicle.plate_number,
    }
