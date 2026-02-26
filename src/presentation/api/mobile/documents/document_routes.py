"""Mobile document routes extracted from vehicle_routes.py."""

from __future__ import annotations

import os
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from src.utils.status_validator import StatusValidator
from src.core.extensions import db
from src.modules.vehicles.application.document_service import DocumentService
from src.utils.audit_logger import log_activity


document_bp = Blueprint("documents", __name__)


def _json_response(success: bool, message: str, data: Dict[str, Any] | None = None, status_code: int = 200):
    return jsonify({
        "status": "success" if success else "error",
        "message": message,
        "data": data or {},
    }), status_code


@document_bp.route('/vehicles/<int:vehicle_id>/upload-document', methods=['POST'])
@login_required
def upload_vehicle_document(vehicle_id: int):
    """Upload vehicle document with date validation."""
    valid, message, _ = StatusValidator.validate_transition(vehicle_id, "document_update")
    if not valid:
        return _json_response(False, message, status_code=400)

    document_type = request.form.get('document_type')
    form_data = {
        "issue_date": request.form.get("issue_date"),
        "expiry_date": request.form.get("expiry_date"),
    }
    file = request.files.get('file')

    upload_root = None
    if current_app.static_folder:
        upload_root = os.path.join(current_app.static_folder, "uploads")

    service = DocumentService(upload_root=upload_root)
    success, msg, data = service.upload_document(vehicle_id, document_type, file, form_data)

    if success:
        try:
            db.session.commit()
            log_activity(
                action='upload',
                entity_type='Vehicle',
                entity_id=vehicle_id,
                details=f'رفع وثيقة {document_type} للسيارة {vehicle_id}',
            )
        except Exception as exc:
            db.session.rollback()
            return _json_response(False, f'خطأ في حفظ الوثيقة: {str(exc)}', status_code=500)

    return _json_response(success, msg, data, status_code=200 if success else 400)


@document_bp.route('/vehicles/<int:vehicle_id>/delete-document', methods=['POST'])
@login_required
def delete_vehicle_document(vehicle_id: int):
    """Delete vehicle document reference."""
    valid, message, _ = StatusValidator.validate_transition(vehicle_id, "document_update")
    if not valid:
        return _json_response(False, message, status_code=400)

    document_type = request.form.get('document_type')

    upload_root = None
    if current_app.static_folder:
        upload_root = os.path.join(current_app.static_folder, "uploads")

    service = DocumentService(upload_root=upload_root)
    success, msg, data = service.delete_document(vehicle_id, document_type)

    if success:
        try:
            db.session.commit()
            log_activity(
                action='delete',
                entity_type='Vehicle',
                entity_id=vehicle_id,
                details=f'حذف وثيقة {document_type} للسيارة {vehicle_id}',
            )
        except Exception as exc:
            db.session.rollback()
            return _json_response(False, f'خطأ في حذف الوثيقة: {str(exc)}', status_code=500)

    return _json_response(success, msg, data, status_code=200 if success else 400)


@document_bp.route('/vehicles/documents', methods=['GET'])
@login_required
def vehicle_documents():
    """Return vehicle documents overview."""
    service = DocumentService()
    data = service.list_documents()
    return _json_response(True, "تم تحميل الوثائق", data)


def register_document_routes(bp):
    """Register document routes on the given blueprint."""
    bp.register_blueprint(document_bp)
