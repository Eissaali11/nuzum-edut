"""
خدمات طبقة التطبيق للعمليات — تحديد السجلات الرسمية مقابل المعلقة.
يُستخدم من خدمة المركبات (تسليم/استلام) دون ربط مباشر بمنطق العمليات القديم.
لا يتجاوز 400 سطر.
"""
from typing import List, Dict


def get_handover_approval_state(vehicle_id: int) -> Dict[str, List[int]]:
    """
    يُرجع معرفات سجلات التسليم/الاستلام المُعتمدة وجميع طلبات التسليم للسيارة.
    السجل «رسمي» إن كان مُعتمداً أو غير مرتبط بأي طلب موافقة.
    """
    from core.extensions import db
    try:
        from models import OperationRequest
    except ImportError:
        return {"approved_ids": [], "all_request_record_ids": []}
    approved = (
        db.session.query(OperationRequest.related_record_id)
        .filter_by(
            operation_type="handover",
            status="approved",
            vehicle_id=vehicle_id,
        )
        .all()
    )
    all_request = (
        db.session.query(OperationRequest.related_record_id)
        .filter_by(operation_type="handover", vehicle_id=vehicle_id)
        .all()
    )
    return {
        "approved_ids": [r[0] for r in approved],
        "all_request_record_ids": [r[0] for r in all_request],
    }
