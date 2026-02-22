from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

from services.document_service import DocumentService


documents_api_v2_bp = Blueprint('documents_api_v2', __name__, url_prefix='/api/v2/documents')


def _require_api_key():
    api_key = request.headers.get('X-API-Key', '')
    if len(api_key) < 10:
        return False
    return True


@documents_api_v2_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'message': 'Documents API v2 OK', 'data': {'ts': datetime.utcnow().isoformat()}})


@documents_api_v2_bp.route('/documents/<int:document_id>/upload-image', methods=['POST'])
def upload_image(document_id):
    if not _require_api_key():
        return jsonify({'success': False, 'message': 'مفتاح API غير صالح', 'error': 'INVALID_API_KEY'}), 401

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'لم يتم إرفاق صورة', 'error': 'NO_IMAGE'}), 400

    success, message, data = DocumentService.upload_document_file(document_id, request.files['image'])
    if not success:
        return jsonify({'success': False, 'message': message, 'error': 'UPLOAD_FAILED'}), 400

    return jsonify({'success': True, 'message': message, 'data': data}), 201


@documents_api_v2_bp.route('/documents/<int:document_id>/upload-file', methods=['POST'])
def upload_file(document_id):
    if not _require_api_key():
        return jsonify({'success': False, 'message': 'مفتاح API غير صالح', 'error': 'INVALID_API_KEY'}), 401

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'لم يتم إرفاق ملف', 'error': 'NO_FILE'}), 400

    success, message, data = DocumentService.upload_document_file(document_id, request.files['file'])
    if not success:
        return jsonify({'success': False, 'message': message, 'error': 'UPLOAD_FAILED'}), 400

    return jsonify({'success': True, 'message': message, 'data': data}), 201


@documents_api_v2_bp.route('/documents/<int:document_id>/download', methods=['GET'])
def download_file(document_id):
    if not _require_api_key():
        return jsonify({'success': False, 'message': 'مفتاح API غير صالح', 'error': 'INVALID_API_KEY'}), 401

    success, message, data = DocumentService.get_document_download_info(document_id)
    if not success:
        return jsonify({'success': False, 'message': message, 'error': 'DOWNLOAD_FAILED'}), 404

    return send_file(data['file_path'], download_name=data['download_name'], as_attachment=True)


@documents_api_v2_bp.route('/documents', methods=['GET'])
def list_documents():
    document_type = request.args.get('document_type')
    employee_id = request.args.get('employee_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    documents, total = DocumentService.get_documents(
        document_type=document_type,
        employee_id=employee_id,
        page=page,
        per_page=per_page,
    )

    rows = []
    today = datetime.now().date()
    for doc in documents:
        rows.append({
            'id': doc.id,
            'employee_id': doc.employee_id,
            'document_type': doc.document_type,
            'document_type_label': DocumentService.get_document_type_label(doc.document_type),
            'document_number': doc.document_number,
            'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
            'days_to_expiry': (doc.expiry_date - today).days if doc.expiry_date else None,
            'has_file': bool(doc.file_path),
        })

    return jsonify({
        'success': True,
        'message': 'تم جلب الوثائق',
        'data': {
            'documents': rows,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page if per_page else 1,
            },
        },
    })
