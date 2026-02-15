from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from models import Module, Permission
from utils.user_helpers import require_module_access
from modules.employees.application.core import (create_employee, update_employee, delete_employee, 
    update_employee_status, prepare_employee_form_context, get_employee_view_context, update_employee_iban,
    delete_employee_iban_image, delete_employee_housing_image, list_employees_page_data)
from modules.employees.application.tracking import (get_tracking_page_data, get_tracking_dashboard_data, 
    get_track_history_page_data)
from modules.employees.application.io import (process_employee_import, generate_sample_import_template,
    generate_empty_import_template, export_employees_excel, export_employees_comprehensive,
    upload_employee_image, delete_housing_image)
from modules.employees.application.report_service import (export_basic_report_pdf, export_comprehensive_report_pdf,
    export_comprehensive_report_excel, export_attendance_excel as build_attendance_excel,
    export_track_history_pdf as build_track_history_pdf, export_track_history_excel as build_track_history_excel)
from modules.employees.application.messages import translate_service_message
from routes.employees_helpers import (handle_unlink_flash, extract_department_id_from_url,
    send_file_or_error, handle_form_submission, send_report_file, send_report_file_track)

employees_bp = Blueprint('employees', __name__)

@employees_bp.route('/')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def index():
    from flask_login import current_user
    data = list_employees_page_data(
        department_filter=request.args.get('department', ''),
        status_filter=request.args.get('status', ''),
        multi_department_filter=request.args.get('multi_department', ''),
        no_department_filter=request.args.get('no_department', ''),
        duplicate_names_filter=request.args.get('duplicate_names', ''),
        assigned_department_id=getattr(current_user, 'assigned_department_id', None),
    )
    return render_template('employees/index.html', **data)

@employees_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.CREATE)
def create():
    return handle_form_submission(
        create_employee, 'create', prepare_employee_form_context,
        url_for('employees.index'), translate_service_message,
    )

@employees_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def edit(id):
    if request.method == 'POST':
        result = update_employee(id, request.form, request.files)
        if result.success:
            handle_unlink_flash(result)
            flash(translate_service_message(result), result.category)
            dept_id = extract_department_id_from_url(request.form.get('return_url') or request.referrer)
            if dept_id:
                return redirect(url_for('departments.view', id=dept_id))
            return redirect(url_for('employees.index'))
        flash(translate_service_message(result), result.category)
    context = prepare_employee_form_context(employee_id=id)
    if not context.get('employee'):
        flash('الموظف غير موجود', 'danger')
        return redirect(url_for('employees.index'))
    return render_template('employees/edit.html', **context)

@employees_bp.route('/<int:id>/view')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def view(id):
    context = get_employee_view_context(id)
    if not context:
        flash('الموظف غير موجود', 'danger')
        return redirect(url_for('employees.index'))
    return render_template('employees/view.html', **context)

@employees_bp.route('/<int:id>/upload_iban', methods=['POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def upload_iban(id):
    result = update_employee_iban(id, request.form.get('bank_iban', '').strip(), request.files.get('iban_image'))
    flash(translate_service_message(result), result.category)
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/<int:id>/delete_iban_image', methods=['POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def delete_iban_image(id):
    result = delete_employee_iban_image(id)
    flash(translate_service_message(result), result.category)
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/<int:id>/delete_housing_image', methods=['POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def delete_housing_image_route(id):
    result = delete_housing_image(id, request.form.get('image_path', '').strip())
    flash(result.message, result.category)
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/<int:id>/confirm_delete')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.DELETE)
def confirm_delete(id):
    result = get_employee_view_context(id)
    if not result.success:
        flash('الموظف غير موجود', 'danger')
        return redirect(url_for('employees.index'))
    return render_template('employees/confirm_delete.html', employee=result.data['employee'],
                          return_url=request.referrer or url_for('employees.index'))

@employees_bp.route('/<int:id>/delete', methods=['GET', 'POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.DELETE)
def delete(id):
    if request.method == 'GET':
        return redirect(url_for('employees.confirm_delete', id=id))
    if request.form.get('confirmed') != 'yes':
        flash('لم يتم تأكيد عملية الحذف', 'warning')
        return redirect(url_for('employees.view', id=id))
    result = delete_employee(id)
    flash(translate_service_message(result), result.category)
    if not result.success:
        return redirect(url_for('employees.view', id=id))
    dept_id = extract_department_id_from_url(request.form.get('return_url'))
    return redirect(url_for('departments.view', id=dept_id)) if dept_id else redirect(url_for('employees.index'))

@employees_bp.route('/import', methods=['GET', 'POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.CREATE)
def import_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('الملف يجب أن يكون بصيغة Excel (.xlsx, .xls)', 'danger')
            return redirect(request.url)
        result = process_employee_import(file)
        flash(result.message, result.category)
        return redirect(url_for('employees.index'))
    return render_template('employees/import.html')

@employees_bp.route('/import/template')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def import_template():
    return send_file_or_error(generate_sample_import_template, 'قالب_استيراد_الموظفين_شامل.xlsx',
                              'employees.import_excel', 'حدث خطأ في إنشاء القالب')

@employees_bp.route('/import/empty_template')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def empty_import_template():
    return send_file_or_error(generate_empty_import_template, 'نموذج_استيراد_الموظفين_فارغ.xlsx',
                              'employees.import_excel', 'حدث خطأ في إنشاء النموذج الفارغ')

@employees_bp.route('/<int:id>/update_status', methods=['POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def update_status(id):
    result = update_employee_status(id, request.form.get('status'), request.form.get('note', ''))
    if result.success:
        handle_unlink_flash(result)
        dept_id = extract_department_id_from_url(request.referrer)
        if dept_id:
            flash(translate_service_message(result), result.category)
            return redirect(url_for('departments.view', id=dept_id))
    flash(translate_service_message(result), result.category)
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/export')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def export_excel():
    return send_file_or_error(export_employees_excel, 'employees.xlsx', 'employees.index',
                              'حدث خطأ أثناء تصدير البيانات')

@employees_bp.route('/export_comprehensive')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def export_comprehensive():
    return send_file_or_error(export_employees_comprehensive, None, 'employees.index',
                              'حدث خطأ أثناء التصدير الشامل')

@employees_bp.route('/<int:id>/export_attendance_excel')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def export_attendance_excel(id):
    result = build_attendance_excel(id, request.args.get('month'), request.args.get('year'))
    if not result.success:
        flash(result.message, result.category)
        return redirect(url_for('employees.view', id=id))
    for w in result.data.get("warnings", []):
        flash(w, 'warning')
    return send_file(result.output, as_attachment=True, download_name=result.filename, mimetype=result.mimetype)

@employees_bp.route('/<int:id>/upload_image', methods=['POST'])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def upload_image(id):
    result = upload_employee_image(id, request.files.get('image'), request.form.get('image_type'))
    flash(result.message, result.category)
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/<int:id>/basic_report')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def basic_report(id):
    return send_report_file(export_basic_report_pdf, id)

@employees_bp.route('/<int:id>/comprehensive_report')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def comprehensive_report(id):
    return send_report_file(export_comprehensive_report_pdf, id)

@employees_bp.route('/<int:id>/comprehensive_report_excel')
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def comprehensive_report_excel(id):
    return send_report_file(export_comprehensive_report_excel, id)

@employees_bp.route('/tracking')
@login_required
def tracking():
    return render_template('employees/tracking.html',
        **get_tracking_page_data(request.args.get('department', ''), request.args.get('search', '')))

@employees_bp.route('/tracking-dashboard')
@login_required
def tracking_dashboard():
    return render_template('employees/tracking_dashboard.html', **get_tracking_dashboard_data())

@employees_bp.route('/<int:id>/track-history')
@login_required
def track_history(id):
    return render_template('employees/track_history.html', **get_track_history_page_data(id))

@employees_bp.route('/<int:employee_id>/track-history/export-pdf')
@login_required
def export_track_history_pdf(employee_id):
    return send_report_file_track(build_track_history_pdf, employee_id)

@employees_bp.route('/<int:employee_id>/track-history/export-excel')
@login_required
def export_track_history_excel(employee_id):
    return send_report_file_track(build_track_history_excel, employee_id)
