import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from src.core.extensions import db
from models import (
    EmployeeRequest, AdvancePaymentRequest, InvoiceRequest,
    RequestType, RequestStatus, RequestNotification
)
from src.modules.employees.presentation.api.v1.auth_routes import token_required
from src.services.employee_finance_service import EmployeeFinanceService

logger = logging.getLogger(__name__)

financial_api_v1 = Blueprint('financial_api_v1', __name__, url_prefix='/api/v1')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'pdf'}
    if not filename or not isinstance(filename, str):
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@financial_api_v1.route('/employee/liabilities', methods=['GET'])
@token_required
def get_employee_liabilities(current_employee):
    """
    جلب الالتزامات المالية للموظف (سلف، ديون، تلفيات)
    """
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type')

    try:
        liabilities_data = EmployeeFinanceService.get_employee_liabilities(
            current_employee.id,
            status_filter=status_filter,
            liability_type_filter=type_filter
        )

        return jsonify({
            'success': True,
            'data': liabilities_data
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error fetching liabilities for employee {current_employee.id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء جلب الالتزامات المالية',
            'error': str(e)
        }), 500

@financial_api_v1.route('/employee/financial-summary', methods=['GET'])
@token_required
def get_employee_financial_summary(current_employee):
    """
    جلب الملخص المالي الشامل للموظف
    """
    try:
        summary = EmployeeFinanceService.get_financial_summary(current_employee.id)
        if not summary:
            return jsonify({
                'success': False,
                'message': 'الموظف غير موجود'
            }), 404

        return jsonify({
            'success': True,
            'data': summary
        }), 200

    except Exception as e:
        logger.error(f"Error fetching financial summary for employee {current_employee.id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء جلب الملخص المالي',
            'error': str(e)
        }), 500

@financial_api_v1.route('/requests/create-advance-payment', methods=['POST'])
@token_required
def create_advance_payment_request(current_employee):
    """
    إنشاء طلب سلفة جديد يدعم JSON و multipart/form-data
    """
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
        requested_amount_str = data.get('requested_amount')
        installments_str = data.get('installments')
        reason = data.get('reason', '')
    else:
        requested_amount_str = request.form.get('requested_amount')
        installments_str = request.form.get('installments')
        reason = request.form.get('reason', '')

    if not requested_amount_str:
        return jsonify({
            'success': False,
            'message': 'المبلغ المطلوب مطلوب'
        }), 400

    try:
        requested_amount = float(requested_amount_str)
        if requested_amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'المبلغ غير صحيح: {str(e)}'
        }), 400

    installments = int(installments_str) if installments_str else None
    has_image = 'image' in request.files

    if not has_image and installments:
        is_valid, message = EmployeeFinanceService.validate_advance_payment_request(
            current_employee.id,
            requested_amount,
            installments
        )

        if not is_valid:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    try:
        new_request = EmployeeRequest()
        new_request.employee_id = current_employee.id
        new_request.request_type = RequestType.ADVANCE_PAYMENT
        new_request.title = f"طلب سلفة - {requested_amount} ريال"
        new_request.status = RequestStatus.PENDING
        new_request.amount = requested_amount
        new_request.description = reason

        db.session.add(new_request)
        db.session.flush()

        monthly_installment = requested_amount / installments if installments else None
        advance_payment = AdvancePaymentRequest()
        advance_payment.request_id = new_request.id
        advance_payment.employee_name = current_employee.name
        advance_payment.employee_number = current_employee.employee_id
        advance_payment.national_id = current_employee.national_id
        advance_payment.job_title = current_employee.job_title or ''
        advance_payment.department_name = current_employee.departments[0].name if current_employee.departments else 'غير محدد'
        advance_payment.requested_amount = requested_amount
        advance_payment.installments = installments
        advance_payment.installment_amount = monthly_installment
        advance_payment.reason = reason
        advance_payment.remaining_amount = requested_amount

        db.session.add(advance_payment)
        db.session.flush()

        image_path = None
        if has_image:
            image_file = request.files['image']

            if image_file and image_file.filename and allowed_file(image_file.filename):
                file_extension = image_file.filename.rsplit('.', 1)[1].lower()
                filename = f"request_{new_request.id}_image.{file_extension}"

                upload_dir = os.path.join('static', 'uploads', 'advance_payments')
                os.makedirs(upload_dir, exist_ok=True)

                file_path = os.path.join(upload_dir, filename)
                image_file.save(file_path)

                image_path = file_path
                logger.info(f"✅ تم حفظ صورة السلفة: {file_path}")

                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"فشل حفظ الملف: {file_path}")

        db.session.commit()

        logger.info(f"✅ تم إنشاء طلب سلفة #{new_request.id} بواسطة {current_employee.name} - المبلغ: {requested_amount}")

        return jsonify({
            'success': True,
            'message': 'تم إنشاء طلب السلفة بنجاح',
            'data': {
                'request_id': new_request.id,
                'type': 'advance_payment',
                'status': 'pending',
                'requested_amount': requested_amount,
                'installments': installments,
                'monthly_installment': round(monthly_installment, 2) if monthly_installment else None,
                'has_image': image_path is not None,
                'image_path': f"/{image_path}" if image_path else None
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating advance payment request for employee {current_employee.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إنشاء الطلب',
            'error': str(e)
        }), 500

@financial_api_v1.route('/requests/create-invoice', methods=['POST'])
@token_required
def create_invoice_request(current_employee):
    """
    رفع فاتورة مع صورة
    """
    logger.info(f"📤 Create invoice request - Files: {list(request.files.keys())}, Form: {list(request.form.keys())}")
    if not request.files or 'invoice_image' not in request.files:
        logger.warning(f"❌ Invoice image missing - Available files: {list(request.files.keys())}")
        return jsonify({
            'success': False,
            'message': 'صورة الفاتورة مطلوبة',
            'debug': {
                'received_files': list(request.files.keys()),
                'expected': 'invoice_image'
            }
        }), 400

    vendor_name = request.form.get('vendor_name')
    amount = request.form.get('amount')

    if not vendor_name or not amount:
        logger.warning(f"❌ Missing fields - vendor_name: {vendor_name}, amount: {amount}")
        return jsonify({
            'success': False,
            'message': 'اسم المورد والمبلغ مطلوبان',
            'debug': {
                'vendor_name': vendor_name,
                'amount': amount,
                'received_form_fields': list(request.form.keys())
            }
        }), 400

    invoice_image = request.files['invoice_image']

    if not allowed_file(invoice_image.filename):
        return jsonify({
            'success': False,
            'message': 'نوع الملف غير مدعوم. استخدم: PNG, JPG, JPEG, PDF'
        }), 400

    try:
        new_request = EmployeeRequest()
        new_request.employee_id = current_employee.id
        new_request.request_type = RequestType.INVOICE
        new_request.title = f"فاتورة - {vendor_name}"
        new_request.status = RequestStatus.PENDING
        new_request.amount = float(amount)

        db.session.add(new_request)
        db.session.flush()

        invoice_request = InvoiceRequest()
        invoice_request.request_id = new_request.id
        invoice_request.vendor_name = vendor_name

        db.session.add(invoice_request)
        db.session.flush()

        if not invoice_image.filename:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'اسم الملف غير صالح'
            }), 400

        filename = secure_filename(invoice_image.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{new_request.id}_{timestamp}_{filename}"

        upload_folder = os.path.join('static', 'uploads', 'invoices')
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        logger.info(f"💾 حفظ الملف: {file_path}")

        invoice_image.save(file_path)

        if not os.path.exists(file_path):
            logger.error(f"❌ الملف لم يُحفظ على القرص: {file_path}")
            db.session.rollback()
            raise RuntimeError(f"Failed to save file to disk: {file_path}")

        file_size = os.path.getsize(file_path)
        logger.info(f"✅ الملف تم حفظه بنجاح - الحجم: {file_size} bytes")

        relative_path = os.path.join('uploads', 'invoices', unique_filename)
        invoice_request.local_image_path = relative_path

        logger.info(f"✅ Image saved locally: {file_path}")
        logger.info(f"✅ Relative path saved to DB: {relative_path}")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم رفع الفاتورة بنجاح',
            'data': {
                'request_id': new_request.id,
                'type': 'invoice',
                'status': 'pending',
                'vendor_name': vendor_name,
                'amount': float(amount),
                'image_saved': True,
                'local_path': relative_path
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating invoice request for employee {current_employee.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إنشاء طلب الفاتورة',
            'error': str(e)
        }), 500
