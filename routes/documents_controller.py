"""
Documents Controller (Refactored)
==================================
Slim web controller for document management interface.
Delegates all business logic to DocumentService.

URL Prefix: /documents-new/
Blueprint: documents_refactored_bp

Author: AI Assistant
Date: February 20, 2026
Version: 2.0.0
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import current_user, login_required
from datetime import datetime
from werkzeug.utils import secure_filename

from services.document_service import DocumentService
from models import Employee, Department

documents_refactored_bp = Blueprint('documents_refactored', __name__, url_prefix='/documents-new')


# ==================== Dashboard & Statistics ====================

@documents_refactored_bp.route('/dashboard')
@login_required
def dashboard():
    """Document dashboard with statistics"""
    try:
        stats = DocumentService.get_dashboard_stats()
        current_date = datetime.now().date()
        
        return render_template('documents/dashboard.html',
                             total_documents=stats.get('total_documents', 0),
                             expired_documents=stats.get('expired_documents', 0),
                             expiring_soon=stats.get('expiring_soon', 0),
                             expiring_later=stats.get('expiring_later', 0),
                             valid_documents=stats.get('valid_documents', 0),
                             expired_docs=stats.get('expired_docs', []),
                             expiring_docs=stats.get('expiring_docs', []),
                             document_types_stats=stats.get('document_types_stats', []),
                             department_stats=stats.get('department_stats', []),
                             current_date=current_date)
    except Exception as e:
        flash(f'حدث خطأ في تحميل الإحصائيات: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.index'))


@documents_refactored_bp.route('/expiry-stats')
@login_required
def expiry_stats():
    """Get document expiry statistics (JSON)"""
    try:
        stats = DocumentService.get_expiry_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Document Listing & Filtering ====================

@documents_refactored_bp.route('/')
@login_required
def index():
    """List documents with filtering"""
    try:
        # Get filter parameters
        document_type = request.args.get('document_type', '')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status', '')
        status_filter = request.args.get('expiring', '')
        search_query = request.args.get('search_query', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Get documents
        documents, total_count = DocumentService.get_documents(
            document_type=document_type if document_type else None,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status if sponsorship_status else None,
            status_filter=status_filter if status_filter else None,
            search_query=search_query if search_query else None,
            page=page,
            per_page=per_page
        )
        
        # Calculate days to expiry
        today = datetime.now().date()
        for doc in documents:
            if doc.expiry_date:
                doc.days_to_expiry = (doc.expiry_date - today).days
            else:
                doc.days_to_expiry = None
        
        # Get filter data
        document_types = DocumentService.get_document_types()
        employees = Employee.query.all()
        departments = Department.query.all()
        
        # Pagination
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('documents/index.html',
                             documents=documents,
                             document_types=document_types,
                             employees=employees,
                             departments=departments,
                             selected_type=document_type,
                             selected_employee=employee_id,
                             selected_department=department_id,
                             selected_sponsorship=sponsorship_status,
                             status_filter=status_filter,
                             search_query=search_query,
                             page=page,
                             per_page=per_page,
                             total_count=total_count,
                             total_pages=total_pages)
    except Exception as e:
        flash(f'حدث خطأ في تحميل الوثائق: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.dashboard'))


@documents_refactored_bp.route('/expiring')
@login_required
def expiring():
    """Show expiring or expired documents"""
    try:
        # Get filter parameters
        days = int(request.args.get('days', '30'))
        document_type = request.args.get('document_type', '')
        status = request.args.get('status', 'expiring')  # 'expiring' or 'expired'
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status', '')
        
        # Build status filter
        if status == 'expired':
            status_filter = 'expired'
        else:
            status_filter = 'expiring'
        
        # Get documents
        documents, _ = DocumentService.get_documents(
            document_type=document_type if document_type else None,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status if sponsorship_status else None,
            status_filter=status_filter,
            per_page=1000  # Get all for expiring view
        )
        
        # Calculate days to expiry
        today = datetime.now().date()
        for doc in documents:
            if doc.expiry_date:
                doc.days_to_expiry = (doc.expiry_date - today).days
            else:
                doc.days_to_expiry = None
        
        # Get filter data
        document_types = DocumentService.get_document_types()
        employees = Employee.query.all()
        departments = Department.query.all()
        
        return render_template('documents/expiring.html',
                             documents=documents,
                             days=days,
                             document_types=document_types,
                             employees=employees,
                             departments=departments,
                             selected_type=document_type,
                             selected_employee=employee_id,
                             selected_department=department_id,
                             selected_sponsorship=sponsorship_status,
                             status=status)
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.dashboard'))


# ==================== Document CRUD Operations ====================

@documents_refactored_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new document"""
    if request.method == 'POST':
        try:
            # Get form data
            add_type = request.form.get('add_type', 'single')
            employee_id = request.form.get('employee_id', type=int)
            document_type = request.form.get('document_type')
            document_number = request.form.get('document_number', '')
            issue_date_str = request.form.get('issue_date')
            expiry_date_str = request.form.get('expiry_date')
            notes = request.form.get('notes', '')
            
            # Parse dates
            from utils.date_converter import parse_date
            issue_date = parse_date(issue_date_str) if issue_date_str else None
            expiry_date = parse_date(expiry_date_str) if expiry_date_str else None
            
            if add_type == 'single':
                # Single document
                success, message, document = DocumentService.create_document(
                    employee_id=employee_id,
                    document_type=document_type,
                    document_number=document_number,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    notes=notes,
                    user_id=current_user.id
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('documents_refactored.index'))
                else:
                    flash(message, 'danger')
            
            elif add_type == 'department_bulk':
                # Bulk create for department
                department_id = request.form.get('department_id', type=int)
                department = Department.query.get(department_id)
                
                if not department:
                    flash('القسم غير موجود', 'danger')
                    return redirect(url_for('documents_refactored.create'))
                
                employee_ids = [emp.id for emp in department.employees]
                
                success, message, count = DocumentService.create_bulk_documents(
                    employee_ids=employee_ids,
                    document_type=document_type,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    notes=notes
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('documents_refactored.index'))
                else:
                    flash(message, 'danger')
            
            else:
                flash('نوع الإضافة غير صحيح', 'danger')
        
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    # GET request - show form
    employees = Employee.query.all()
    departments = Department.query.all()
    document_types = DocumentService.get_document_types()
    
    return render_template('documents/create.html',
                         employees=employees,
                         departments=departments,
                         document_types=document_types)


@documents_refactored_bp.route('/<int:id>/update-expiry', methods=['GET', 'POST'])
@login_required
def update_expiry(id):
    """Update document expiry date"""
    document = DocumentService.get_document_by_id(id)
    if not document:
        flash('الوثيقة غير موجودة', 'danger')
        return redirect(url_for('documents_refactored.index'))
    
    if request.method == 'POST':
        try:
            expiry_date_str = request.form.get('expiry_date')
            
            from utils.date_converter import parse_date
            expiry_date = parse_date(expiry_date_str) if expiry_date_str else None
            
            if not expiry_date:
                flash('يجب إدخال تاريخ الانتهاء', 'danger')
                return redirect(request.referrer or url_for('documents_refactored.expiring'))
            
            success, message = DocumentService.update_document(
                document_id=id,
                expiry_date=expiry_date
            )
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            
            return redirect(request.referrer or url_for('documents_refactored.expiring'))
        
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(request.referrer or url_for('documents_refactored.expiring'))
    
    # GET request - show form
    return render_template('documents/update_expiry.html', document=document)


@documents_refactored_bp.route('/update-expiry-date/<int:document_id>', methods=['POST'])
@login_required
def update_expiry_date(document_id):
    """Quick update of expiry date (AJAX)"""
    try:
        new_expiry_date = request.form.get('new_expiry_date')
        
        if not new_expiry_date:
            return jsonify({'success': False, 'message': 'يجب إدخال تاريخ الانتهاء'}), 400
        
        from utils.date_converter import parse_date
        expiry_date = parse_date(new_expiry_date)
        
        if not expiry_date:
            return jsonify({'success': False, 'message': 'تنسيق التاريخ غير صحيح'}), 400
        
        success, message = DocumentService.update_document(
            document_id=document_id,
            expiry_date=expiry_date
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 500


@documents_refactored_bp.route('/<int:id>/confirm-delete')
@login_required
def confirm_delete(id):
    """Show delete confirmation page"""
    document = DocumentService.get_document_by_id(id)
    if not document:
        flash('الوثيقة غير موجودة', 'danger')
        return redirect(url_for('documents_refactored.index'))
    
    return render_template('documents/confirm_delete.html', document=document)


@documents_refactored_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete document"""
    try:
        success, message = DocumentService.delete_document(id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('documents_refactored.index'))
    
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.index'))


@documents_refactored_bp.route('/delete/<int:document_id>', methods=['GET', 'POST'])
@login_required
def delete_document(document_id):
    """Alternative delete route (for backwards compatibility)"""
    return delete(document_id)


# ==================== Bulk Operations ====================

@documents_refactored_bp.route('/save-individual-document', methods=['POST'])
@login_required
def save_individual_document():
    """Save individual document (AJAX)"""
    try:
        data = request.get_json()
        
        from utils.date_converter import parse_date
        success, message, document = DocumentService.create_document(
            employee_id=data['employee_id'],
            document_type=data['document_type'],
            document_number=data['document_number'],
            issue_date=parse_date(data['issue_date']) if data.get('issue_date') else None,
            expiry_date=parse_date(data['expiry_date']) if data.get('expiry_date') else None,
            notes=data.get('notes', ''),
            user_id=current_user.id
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 500


@documents_refactored_bp.route('/save-bulk-documents', methods=['POST'])
@login_required
def save_bulk_documents():
    """Save multiple documents (AJAX)"""
    try:
        data = request.get_json()
        documents_data = data.get('documents', [])
        
        success, message, count = DocumentService.save_bulk_documents_with_data(documents_data)
        
        if success:
            return jsonify({'success': True, 'message': message, 'saved_count': count})
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 500


@documents_refactored_bp.route('/department-bulk-create', methods=['GET', 'POST'])
@login_required
def department_bulk_create():
    """Bulk create documents for department"""
    if request.method == 'POST':
        try:
            department_id = request.form.get('department_id', type=int)
            document_type = request.form.get('document_type')
            
            from utils.date_converter import parse_date
            issue_date = parse_date(request.form.get('issue_date'))
            expiry_date = parse_date(request.form.get('expiry_date'))
            notes = request.form.get('notes', '')
            
            department = Department.query.get(department_id)
            if not department:
                flash('القسم غير موجود', 'danger')
                return redirect(url_for('documents_refactored.department_bulk_create'))
            
            employee_ids = [emp.id for emp in department.employees]
            
            success, message, count = DocumentService.create_bulk_documents(
                employee_ids=employee_ids,
                document_type=document_type,
                issue_date=issue_date,
                expiry_date=expiry_date,
                notes=notes
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('documents_refactored.index'))
            else:
                flash(message, 'danger')
        
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    # GET request
    departments = Department.query.all()
    document_types = DocumentService.get_document_types()
    
    return render_template('documents/department_bulk_create.html',
                         departments=departments,
                         document_types=document_types)


# ==================== Employee Filtering (AJAX) ====================

@documents_refactored_bp.route('/get-sponsorship-employees', methods=['POST'])
@login_required
def get_sponsorship_employees():
    """Get employees filtered by sponsorship (AJAX)"""
    try:
        data = request.get_json()
        sponsorship_type = data.get('sponsorship_type')
        
        employees = DocumentService.get_employees_by_sponsorship(sponsorship_type)
        
        return jsonify({
            'success': True,
            'employees': employees
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@documents_refactored_bp.route('/get-employees-by-sponsorship', methods=['POST'])
@login_required
def get_employees_by_sponsorship():
    """Alternative route for sponsorship filtering"""
    return get_sponsorship_employees()


@documents_refactored_bp.route('/get-employees-by-department-and-sponsorship', methods=['POST'])
@login_required
def get_employees_by_department_and_sponsorship():
    """Get employees by department and sponsorship (AJAX)"""
    try:
        data = request.get_json()
        department_id = data.get('department_id', type=int)
        sponsorship_type = data.get('sponsorship_type')
        
        employees = DocumentService.get_employees_by_department_and_sponsorship(
            department_id=department_id,
            sponsorship_type=sponsorship_type
        )
        
        return jsonify({
            'success': True,
            'employees': employees
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== Import/Export ====================

@documents_refactored_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_excel():
    """Import documents from Excel"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('documents_refactored.import_excel'))
            
            file = request.files['file']
            
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('documents_refactored.import_excel'))
            
            # Validate file
            is_valid, error_message = DocumentService.validate_file_security(file.filename)
            if not is_valid:
                flash(error_message, 'danger')
                return redirect(url_for('documents_refactored.import_excel'))
            
            # Import
            success, message, success_count, error_count = DocumentService.import_from_excel(file.stream)
            
            if error_count > 0:
                flash(f'{message} ({error_count} فشل)', 'warning')
            else:
                flash(message, 'success')
            
            return redirect(url_for('documents_refactored.index'))
        
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('documents_refactored.import_excel'))
    
    # GET request
    return render_template('documents/import.html')


@documents_refactored_bp.route('/export-excel')
@login_required
def export_excel():
    """Export documents to Excel"""
    try:
        # Get filters
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status')
        status_filter = request.args.get('expiring')
        
        # Get documents
        documents, _ = DocumentService.get_documents(
            document_type=document_type if document_type else None,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status if sponsorship_status else None,
            status_filter=status_filter if status_filter else None,
            per_page=10000  # Get all for export
        )
        
        # Generate Excel
        output = DocumentService.export_to_excel(documents, include_employee_data=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f'تقرير_الوثائق_{timestamp}.xlsx'
        
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'حدث خطأ في التصدير: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.index'))


@documents_refactored_bp.route('/employee/<int:employee_id>/export-pdf')
@login_required
def export_employee_documents_pdf(employee_id):
    """Export employee documents to PDF"""
    try:
        pdf_buffer = DocumentService.generate_employee_documents_pdf(employee_id)
        
        if not pdf_buffer:
            flash('حدث خطأ في إنشاء PDF', 'danger')
            return redirect(url_for('documents_refactored.index'))
        
        employee = Employee.query.get(employee_id)
        filename = f'وثائق_{employee.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
    
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.index'))


@documents_refactored_bp.route('/employee/<int:employee_id>/export-excel')
@login_required
def export_employee_documents_excel(employee_id):
    """Export employee documents to Excel"""
    try:
        # Get employee documents
        documents, _ = DocumentService.get_documents(
            employee_id=employee_id,
            per_page=1000
        )
        
        # Generate Excel
        output = DocumentService.export_to_excel(documents, include_employee_data=False)
        
        employee = Employee.query.get(employee_id)
        filename = f'وثائق_{employee.name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.index'))


# ==================== PDF Templates ====================

@documents_refactored_bp.route('/template/pdf')
@login_required
def document_template_pdf():
    """Generate blank PDF template"""
    try:
        buffer = DocumentService.generate_document_template_pdf()
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=document_template.pdf'
        
        return response
    
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents_refactored.dashboard'))


# ==================== Notifications ====================

@documents_refactored_bp.route('/test-notifications', methods=['GET', 'POST'])
@login_required
def test_expiry_notifications():
    """Test creating expiry notifications"""
    try:
        success, message, count = DocumentService.create_bulk_expiry_notifications()
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'notification_count': count
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== Excel Dashboard (Analytics) ====================

@documents_refactored_bp.route('/excel-dashboard', methods=['GET', 'POST'])
@login_required
def excel_dashboard():
    """Excel data analysis dashboard"""
    if request.method == 'POST':
        try:
            if 'excel_file' not in request.files:
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(request.url)
            
            file = request.files['excel_file']
            
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(request.url)
            
            if not file.filename.endswith(('.xlsx', '.xls')):
                flash('يرجى رفع ملف Excel فقط', 'danger')
                return redirect(request.url)
            
            # Note: This feature requires additional implementation
            # For now, redirect to import
            flash('هذه الميزة قيد التطوير. استخدم صفحة الاستيراد', 'info')
            return redirect(url_for('documents_refactored.import_excel'))
        
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('documents/excel_dashboard.html', uploaded=False)
