"""
خدمة قائمة المركبات — استخراج منطق البيانات لصفحة القائمة (index).
تُستخدم من: vehicle_routes.index (ويب) و vehicle_api (API v1).
لا تعتمد على Flask (request/g/session)؛ تُمرَّر المعاملات صراحة لضمان إمكانية الاستدعاء من أي طبقة.
"""
from typing import Any, Dict, Optional

from modules.vehicles.application.vehicle_service import get_index_context


def get_vehicle_list_payload(
    request_args: Any,
    assigned_department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    يجمع سياق صفحة قائمة المركبات (index) بناءً على معاملات الطلب.

    يعالج نفس التصفيات الحالية: status, make, search_plate, project، وفلتر الفرع (assigned_department_id).
    لا يستخدم pagination حالياً (مطابق للتنفيذ الحالي في get_index_context).

    Args:
        request_args: كائن يشبه request.args (يدعم .get)، أو dict.
        assigned_department_id: معرف القسم المعيَّن للمستخدم (للتصفية حسب الفرع).

    Returns:
        قاموس بنفس المفاتيح التي تُمرَّر لقالب vehicles/index.html:
        vehicles, stats, status_filter, make_filter, search_plate, project_filter,
        makes, projects, statuses, expiring_documents, expired_authorization_vehicles,
        expired_inspection_vehicles, now, timedelta, today.
    """
    status_filter = (request_args.get("status") or "").strip()
    make_filter = (request_args.get("make") or "").strip()
    search_plate = (request_args.get("search_plate") or "").strip()
    project_filter = (request_args.get("project") or "").strip()

    return get_index_context(
        status_filter=status_filter,
        make_filter=make_filter,
        search_plate=search_plate,
        project_filter=project_filter,
        assigned_department_id=assigned_department_id,
    )
