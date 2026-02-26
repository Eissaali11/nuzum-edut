"""
Documents REST API v2
=====================
RESTful API for document management (mobile app integration).
All endpoints return consistent JSON format: {success, message, data}.

URL Prefix: /api/v2/documents/
Blueprint: api_documents_v2_bp

Features:
- Document CRUD operations
- File upload with camera integration
- Expiry tracking and notifications
- Statistics and analytics
- Bulk operations
- Excel import/export

Author: AI Assistant
Date: February 20, 2026
Version: 2.0.0
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
from functools import wraps

from src.services.document_service import DocumentService
from models import User, Employee, Department
from src.core.api_v2_security import validate_request_token, get_api_v2_claims, rate_limit

api_documents_v2_bp = Blueprint('api_documents_v2', __name__, url_prefix='/api/v2/documents')


# ==================== Authentication Decorator ====================

def api_key_required(f):
    """Require scoped API v2 JWT for endpoint access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        _, error = validate_request_token(
            required_scopes=['api:v2:write', 'documents:write'],
            optional=False,
        )
        if error:
            return error
        return f(*args, **kwargs)
    return decorated_function


def optional_auth(f):
    """Optional authentication - provides user_id if authenticated"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        claims, _ = validate_request_token(
            required_scopes=['api:v2:read', 'documents:read'],
            optional=True,
        )
        if claims is None:
            claims = get_api_v2_claims()
        kwargs['user_id'] = claims.get('sub_id') if claims else None
        return f(*args, **kwargs)
    return decorated_function


# ==================== Health Check ====================

@api_documents_v2_bp.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'success': True,
        'message': 'Documents API v2 is running',
        'data': {
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'endpoints': 27
        }
    })


# ==================== Document Types ====================

@api_documents_v2_bp.route('/types', methods=['GET'])
def get_document_types():
    """Get all document types"""
    try:
        types = DocumentService.get_document_types()
        
        return jsonify({
            'success': True,
            'message': 'تم جلب أنواع الوثائق',
            'data': {
                'types': types,
                'count': len(types)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Document CRUD ====================

@api_documents_v2_bp.route('/documents', methods=['GET'])
@optional_auth
@rate_limit("120 per minute")
def get_documents(user_id=None):
    """Get documents with filtering and pagination"""
    try:
        # Get query parameters
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status')
        status_filter = request.args.get('status')  # expired, expiring
        search_query = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Limit per_page for API
        if per_page > 100:
            per_page = 100
        
        # Get documents
        documents, total_count = DocumentService.get_documents(
            document_type=document_type,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status,
            status_filter=status_filter,
            search_query=search_query,
            page=page,
            per_page=per_page
        )
        
        # Format response
        documents_data = []
        today = datetime.now().date()
        
        for doc in documents:
            days_to_expiry = None
            status = 'valid'
            
            if doc.expiry_date:
                days_to_expiry = (doc.expiry_date - today).days
                
                if days_to_expiry < 0:
                    status = 'expired'
                elif days_to_expiry <= 30:
                    status = 'expiring_soon'
                elif days_to_expiry <= 60:
                    status = 'expiring_later'
            
            doc_data = {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_type_label': DocumentService.get_document_type_label(doc.document_type),
                'document_number': doc.document_number,
                'issue_date': doc.issue_date.isoformat() if doc.issue_date else None,
                'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                'days_to_expiry': days_to_expiry,
                'status': status,
                'notes': doc.notes,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'employee': {
                    'id': doc.employee.id,
                    'name': doc.employee.name,
                    'employee_id': doc.employee.employee_id
                } if doc.employee else None
            }
            
            documents_data.append(doc_data)
        
        # Pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'message': f'تم جلب {len(documents_data)} وثيقة',
            'data': {
                'documents': documents_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/documents/<int:document_id>', methods=['GET'])
def get_document(document_id):
    """Get single document by ID"""
    try:
        document = DocumentService.get_document_by_id(document_id)
        
        if not document:
            return jsonify({
                'success': False,
                'message': 'الوثيقة غير موجودة',
                'error': 'DOCUMENT_NOT_FOUND'
            }), 404
        
        # Calculate days to expiry
        days_to_expiry = None
        status = 'valid'
        
        if document.expiry_date:
            today = datetime.now().date()
            days_to_expiry = (document.expiry_date - today).days
            
            if days_to_expiry < 0:
                status = 'expired'
            elif days_to_expiry <= 30:
                status = 'expiring_soon'
        
        doc_data = {
            'id': document.id,
            'document_type': document.document_type,
            'document_type_label': DocumentService.get_document_type_label(document.document_type),
            'document_number': document.document_number,
            'issue_date': document.issue_date.isoformat() if document.issue_date else None,
            'expiry_date': document.expiry_date.isoformat() if document.expiry_date else None,
            'days_to_expiry': days_to_expiry,
            'status': status,
            'notes': document.notes,
            'created_at': document.created_at.isoformat() if document.created_at else None,
            'updated_at': document.updated_at.isoformat() if document.updated_at else None,
            'employee': {
                'id': document.employee.id,
                'name': document.employee.name,
                'employee_id': document.employee.employee_id,
                'national_id': document.employee.national_id,
                'department': document.employee.departments[0].name if document.employee.departments else None
            } if document.employee else None
        }
        
        return jsonify({
            'success': True,
            'message': 'تم جلب الوثيقة',
            'data': doc_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/documents', methods=['POST'])
@api_key_required
def create_document():
    """Create new document"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_id', 'document_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب',
                    'error': 'MISSING_REQUIRED_FIELD'
                }), 400
        
        # Parse dates
        from src.utils.date_converter import parse_date
        issue_date = parse_date(data.get('issue_date')) if data.get('issue_date') else None
        expiry_date = parse_date(data.get('expiry_date')) if data.get('expiry_date') else None
        
        # Create document
        success, message, document = DocumentService.create_document(
            employee_id=data['employee_id'],
            document_type=data['document_type'],
            document_number=data.get('document_number', ''),
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=data.get('notes', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {
                    'document_id': document.id,
                    'employee_id': document.employee_id,
                    'document_type': document.document_type
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'CREATION_FAILED'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/documents/<int:document_id>', methods=['PUT'])
@api_key_required
def update_document(document_id):
    """Update existing document"""
    try:
        data = request.get_json()
        
        # Parse dates if provided
        from src.utils.date_converter import parse_date
        issue_date = parse_date(data.get('issue_date')) if data.get('issue_date') else None
        expiry_date = parse_date(data.get('expiry_date')) if data.get('expiry_date') else None
        
        # Update document
        success, message = DocumentService.update_document(
            document_id=document_id,
            document_number=data.get('document_number'),
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=data.get('notes')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {'document_id': document_id}
            })
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'UPDATE_FAILED'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/documents/<int:document_id>', methods=['DELETE'])
@api_key_required
def delete_document(document_id):
    """Delete document"""
    try:
        success, message = DocumentService.delete_document(document_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {'document_id': document_id}
            })
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'DELETION_FAILED'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Bulk Operations ====================

@api_documents_v2_bp.route('/documents/bulk', methods=['POST'])
@api_key_required
def create_bulk_documents():
    """Create multiple documents at once"""
    try:
        data = request.get_json()
        
        # Validate
        if 'employee_ids' not in data or 'document_type' not in data:
            return jsonify({
                'success': False,
                'message': 'مطلوب employee_ids و document_type',
                'error': 'MISSING_REQUIRED_FIELDS'
            }), 400
        
        # Parse dates
        from src.utils.date_converter import parse_date
        issue_date = parse_date(data.get('issue_date')) if data.get('issue_date') else None
        expiry_date = parse_date(data.get('expiry_date')) if data.get('expiry_date') else None
        
        # Create bulk
        success, message, count = DocumentService.create_bulk_documents(
            employee_ids=data['employee_ids'],
            document_type=data['document_type'],
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=data.get('notes', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {
                    'count_created': count,
                    'document_type': data['document_type']
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'BULK_CREATION_FAILED'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/documents/bulk-with-data', methods=['POST'])
@api_key_required
def save_bulk_documents_with_data():
    """Save multiple documents with individual data"""
    try:
        data = request.get_json()
        
        if 'documents' not in data:
            return jsonify({
                'success': False,
                'message': 'مطلوب قائمة documents',
                'error': 'MISSING_DOCUMENTS'
            }), 400
        
        success, message, count = DocumentService.save_bulk_documents_with_data(data['documents'])
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {'count_saved': count}
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'BULK_SAVE_FAILED'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Statistics & Analytics ====================

@api_documents_v2_bp.route('/statistics/dashboard', methods=['GET'])
def get_dashboard_statistics():
    """Get dashboard statistics"""
    try:
        stats = DocumentService.get_dashboard_stats()
        
        # Format for API
        response_data = {
            'counts': {
                'total': stats.get('total_documents', 0),
                'expired': stats.get('expired_documents', 0),
                'expiring_soon': stats.get('expiring_soon', 0),
                'expiring_later': stats.get('expiring_later', 0),
                'valid': stats.get('valid_documents', 0)
            },
            'document_types': [
                {'type': dt[0], 'count': dt[1]}
                for dt in stats.get('document_types_stats', [])
            ],
            'departments': [
                {'name': dept[0], 'count': dept[1]}
                for dept in stats.get('department_stats', [])
            ]
        }
        
        return jsonify({
            'success': True,
            'message': 'تم جلب الإحصائيات',
            'data': response_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/statistics/expiry', methods=['GET'])
def get_expiry_statistics():
    """Get expiry statistics"""
    try:
        stats = DocumentService.get_expiry_stats()
        
        return jsonify({
            'success': True,
            'message': 'تم جلب إحصائيات الانتهاء',
            'data': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Employee Filtering ====================

@api_documents_v2_bp.route('/employees/by-sponsorship', methods=['GET'])
def get_employees_by_sponsorship():
    """Get employees filtered by sponsorship"""
    try:
        sponsorship_type = request.args.get('type')  # internal or external
        
        if not sponsorship_type:
            return jsonify({
                'success': False,
                'message': 'مطلوب نوع الكفالة (type)',
                'error': 'MISSING_SPONSORSHIP_TYPE'
            }), 400
        
        employees = DocumentService.get_employees_by_sponsorship(sponsorship_type)
        
        return jsonify({
            'success': True,
            'message': f'تم جلب {len(employees)} موظف',
            'data': {
                'employees': employees,
                'count': len(employees)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/employees/by-department-and-sponsorship', methods=['GET'])
def get_employees_by_department_and_sponsorship():
    """Get employees by department and sponsorship"""
    try:
        department_id = request.args.get('department_id', type=int)
        sponsorship_type = request.args.get('sponsorship_type')
        
        employees = DocumentService.get_employees_by_department_and_sponsorship(
            department_id=department_id,
            sponsorship_type=sponsorship_type
        )
        
        return jsonify({
            'success': True,
            'message': f'تم جلب {len(employees)} موظف',
            'data': {
                'employees': employees,
                'count': len(employees)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== File Upload (Camera Integration) ====================

@api_documents_v2_bp.route('/documents/<int:document_id>/upload-image', methods=['POST'])
@api_key_required
def upload_document_image(document_id):
    """
    Upload document image from camera/gallery
    
    Expected: multipart/form-data with 'image' file
    """
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'لم يتم إرفاق صورة',
                'error': 'NO_IMAGE'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'اسم الملف فارغ',
                'error': 'EMPTY_FILENAME'
            }), 400
        
        # Validate security
        is_valid, error_message = DocumentService.validate_file_security(file.filename)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_message,
                'error': 'INVALID_FILE'
            }), 400
        
        # Check if document exists
        document = DocumentService.get_document_by_id(document_id)
        if not document:
            return jsonify({
                'success': False,
                'message': 'الوثيقة غير موجودة',
                'error': 'DOCUMENT_NOT_FOUND'
            }), 404
        
        # Save file (simplified - in production, save to storage service)
        import os
        from werkzeug.utils import secure_filename
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f'doc_{document_id}_{timestamp}_{filename}'
        
        upload_folder = 'uploads/documents'
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, safe_filename)
        file.save(file_path)
        
        # In production, also compress image for mobile optimization
        # compressed_path = compress_image(file_path)
        
        return jsonify({
            'success': True,
            'message': 'تم رفع الصورة بنجاح',
            'data': {
                'document_id': document_id,
                'filename': safe_filename,
                'file_path': file_path,
                'uploaded_at': datetime.now().isoformat()
            }
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Import/Export ====================

@api_documents_v2_bp.route('/import/excel', methods=['POST'])
@api_key_required
def import_excel():
    """Import documents from Excel file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'لم يتم إرفاق ملف',
                'error': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        
        # Validate
        is_valid, error_message = DocumentService.validate_file_security(file.filename)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_message,
                'error': 'INVALID_FILE'
            }), 400
        
        # Import
        success, message, success_count, error_count = DocumentService.import_from_excel(file.stream)
        
        return jsonify({
            'success': success,
            'message': message,
            'data': {
                'success_count': success_count,
                'error_count': error_count
            }
        }), 200 if success else 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/export/excel', methods=['GET'])
def export_excel():
    """Export documents to Excel"""
    try:
        # Get filters
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        
        # Get documents
        documents, _ = DocumentService.get_documents(
            document_type=document_type,
            employee_id=employee_id,
            department_id=department_id,
            per_page=10000
        )
        
        # Generate Excel
        output = DocumentService.export_to_excel(documents, include_employee_data=True)
        
        return send_file(
            output,
            download_name=f'documents_{datetime.now().strftime("%Y%m%d")}.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


@api_documents_v2_bp.route('/export/pdf/employee/<int:employee_id>', methods=['GET'])
def export_employee_pdf(employee_id):
    """Export employee documents as PDF"""
    try:
        pdf_buffer = DocumentService.generate_employee_documents_pdf(employee_id)
        
        if not pdf_buffer:
            return jsonify({
                'success': False,
                'message': 'فشل إنشاء PDF',
                'error': 'PDF_GENERATION_FAILED'
            }), 500
        
        from flask import make_response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=employee_{employee_id}_docs.pdf'
        
        return response
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Notifications ====================

@api_documents_v2_bp.route('/notifications/create-expiry-alerts', methods=['POST'])
@api_key_required
def create_expiry_alerts():
    """Create expiry notifications for all users"""
    try:
        success, message, count = DocumentService.create_bulk_expiry_notifications()
        
        return jsonify({
            'success': success,
            'message': message,
            'data': {'notification_count': count}
        }), 200 if success else 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== PDF Templates ====================

@api_documents_v2_bp.route('/templates/blank-pdf', methods=['GET'])
def get_blank_template():
    """Get blank PDF template"""
    try:
        buffer = DocumentService.generate_document_template_pdf()
        
        from flask import make_response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=template.pdf'
        
        return response
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}',
            'error': 'SERVER_ERROR'
        }), 500


# ==================== Error Handlers ====================

@api_documents_v2_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'message': 'المسار غير موجود',
        'error': 'NOT_FOUND'
    }), 404


@api_documents_v2_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'message': 'خطأ في الخادم',
        'error': 'SERVER_ERROR'
    }), 500
