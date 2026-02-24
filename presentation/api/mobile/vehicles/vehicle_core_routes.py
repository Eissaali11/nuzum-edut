"""Auto-split from vehicle_routes.py: mobile vehicle domain routes."""

"""
مسارات المركبات (السيارات، الورشة، التسليم/الاستلام، التصريحات الخارجية) للجوال.
مستخرجة من routes/mobile.py. تُسجّل على mobile_bp عبر register_vehicle_routes(mobile_bp).
"""
import base64
import io
import os
import uuid
from datetime import datetime, timedelta, date

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from models import (
    Department,
    Employee,
    ExternalAuthorization,
    GeofenceSession,
    OperationNotification,
    OperationRequest,
    Vehicle,
    VehicleAccident,
    VehicleChecklist,
    VehicleChecklistImage,
    VehicleChecklistItem,
    VehicleDamageMarker,
    VehicleFuelConsumption,
    VehicleHandover,
    VehicleHandoverImage,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehiclePeriodicInspection,
    VehicleProject,
    VehicleRental,
    VehicleSafetyCheck,
    VehicleWorkshop,
    VehicleWorkshopImage,
    employee_departments,
)
from core.extensions import db
from routes.operations import create_operation_request
from modules.vehicles.application.vehicle_service import update_vehicle_driver
from utils.audit_logger import log_activity
from utils.decorators import module_access_required, permission_required
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state

def register_vehicle_core_routes(bp):
    @bp.route('/vehicles')
    @login_required
    def vehicles():
        """صفحة السيارات للنسخة المحمولة"""
        # استخدام نفس البيانات الموجودة في قاعدة البيانات
        status_filter = request.args.get('status', '')
        make_filter = request.args.get('make', '')
        type_filter = request.args.get('type', '')
        department_filter = request.args.get('department', '')
        search_filter = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 50  # عدد السيارات في الصفحة الواحدة
    
        # قاعدة الاستعلام الأساسية
        query = Vehicle.query
    
        # إضافة التصفية حسب الحالة إذا تم تحديدها
        if status_filter:
            query = query.filter(Vehicle.status == status_filter)
    
        # إضافة التصفية حسب الشركة المصنعة إذا تم تحديدها
        if make_filter:
            query = query.filter(Vehicle.make == make_filter)
        
        # إضافة التصفية حسب النوع إذا تم تحديده
        if type_filter:
            query = query.filter(Vehicle.type_of_car == type_filter)
        
        # إضافة التصفية حسب القسم (من خلال السائق الحالي)
        if department_filter:
            # الحصول على معرفات الموظفين في القسم المحدد
            employees_in_dept = db.session.query(Employee.name).join(
                employee_departments, Employee.id == employee_departments.c.employee_id
            ).filter(employee_departments.c.department_id == department_filter).all()
            employee_names = [emp[0] for emp in employees_in_dept]
            
            if employee_names:
                query = query.filter(Vehicle.driver_name.in_(employee_names))
            else:
                # إذا لم يكن هناك موظفين في القسم، لا تعرض أي نتائج
                query = query.filter(Vehicle.id == -1)
    
        # إضافة التصفية حسب البحث
        if search_filter:
            search_pattern = f"%{search_filter}%"
            query = query.filter(
                (Vehicle.plate_number.like(search_pattern)) |
                (Vehicle.make.like(search_pattern)) |
                (Vehicle.model.like(search_pattern))
            )
    
        # الحصول على قائمة الشركات المصنعة المتوفرة
        makes = db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
        makes = [make[0] for make in makes if make[0]]  # استخراج أسماء الشركات وتجاهل القيم الفارغة
        
        # الحصول على قائمة الأقسام
        from models import Department
        departments = Department.query.order_by(Department.name).all()
    
        # تنفيذ الاستعلام مع الترقيم
        pagination = query.order_by(Vehicle.status, Vehicle.plate_number).paginate(page=page, per_page=per_page, error_out=False)
        vehicles = pagination.items
    
        # إحصائيات تفصيلية حسب الحالات
        stats = {
            'total': Vehicle.query.count(),
            'available': Vehicle.query.filter_by(status='available').count(),
            'active_with_driver': Vehicle.query.filter_by(status='active_with_driver').count(),
            'in_workshop_maintenance': Vehicle.query.filter_by(status='in_workshop_maintenance').count(),
            'in_workshop_accident': Vehicle.query.filter_by(status='in_workshop_accident').count(),
            'out_of_service': Vehicle.query.filter_by(status='out_of_service').count(),
            'out_of_region_management': Vehicle.query.filter_by(status='out_of_region_management').count(),
            'in_project': Vehicle.query.filter_by(status='in_project').count(),
            'in_workshop': Vehicle.query.filter_by(status='in_workshop').count()
        }
    
        return render_template('mobile/vehicles.html', 
                              vehicles=vehicles, 
                              stats=stats,
                              makes=makes,
                              departments=departments,
                              pagination=pagination)
    
    # تفاصيل السيارة - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>')
    @login_required
    def vehicle_details(vehicle_id):
        """تفاصيل السيارة للنسخة المحمولة"""
    
        # الحصول على سجلات مختلفة للسيارة
        try:
                # الحصول على بيانات السيارة من قاعدة البيانات
            vehicle = Vehicle.query.get_or_404(vehicle_id)
    
            maintenance_records = VehicleMaintenance.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleMaintenance.date.desc()).all()
    
                # الحصول على سجلات الورشة - جميع السجلات بدون حد
            workshop_records = VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleWorkshop.entry_date.desc()).all()
            print(f"DEBUG: عدد سجلات الورشة للسيارة {vehicle_id}: {len(workshop_records)}")
    
                # الحصول على تعيينات المشاريع
            project_assignments = VehicleProject.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleProject.start_date.desc()).limit(5).all()
    
                # الحصول على سجلات التسليم والاستلام مع بيانات الموظف والأقسام
            handover_records = VehicleHandover.query.filter_by(vehicle_id=vehicle_id)\
                .options(joinedload(VehicleHandover.driver_employee).joinedload(Employee.departments))\
                .order_by(VehicleHandover.handover_date.desc()).all()
    
            # الحصول على التفويضات الخارجية مع معالجة القيم الفارغة
            external_authorizations = ExternalAuthorization.query.filter_by(vehicle_id=vehicle_id).all()
            # ترتيب آمن للتفويضات (القيم الفارغة في النهاية)
            external_authorizations = sorted(external_authorizations, 
                                           key=lambda x: x.created_at or datetime.min, 
                                           reverse=True)
    
            # الحصول على الأقسام والموظفين للنموذج
            departments = Department.query.all()
            employees = Employee.query.all()
    
            # الحصول على سجل الصيانة الخاص بالسيارة
    
            # handover_records = VehicleHandover.query.filter_by(vehicle_id=id).order_by(VehicleHandover.handover_date.desc()).all()
    
    
            # الحصول على سجلات الفحص الدوري
            periodic_inspections = VehiclePeriodicInspection.query.filter_by(vehicle_id=vehicle_id).order_by(VehiclePeriodicInspection.inspection_date.desc()).limit(3).all()
    
            # الحصول على سجلات فحص السلامة
            safety_checks = VehicleSafetyCheck.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleSafetyCheck.check_date.desc()).limit(3).all()
    
            # حساب تكلفة الإصلاحات الإجمالية
            total_maintenance_cost = db.session.query(func.sum(VehicleWorkshop.cost)).filter_by(vehicle_id=vehicle_id).scalar() or 0
    
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
                    inspection_warnings.append(f"الفحص الدوري منتهي الصلاحية منذ {(datetime.now().date() - inspection.expiry_date).days} يومًا")
                    break
                elif hasattr(inspection, 'is_expiring_soon') and inspection.is_expiring_soon:
                    days_remaining = (inspection.expiry_date - datetime.now().date()).days
                    inspection_warnings.append(f"الفحص الدوري سينتهي خلال {days_remaining} يومًا")
                    break
    
        except Exception as e:
            print(f"خطأ في جلب بيانات السيارة: {str(e)}")
            maintenance_records = []
            workshop_records = []
            project_assignments = []
            handover_records = []
            external_authorizations = []
            departments = []
            employees = []
            periodic_inspections = []
            safety_checks = []
            total_maintenance_cost = 0
            days_in_workshop = 0
            inspection_warnings = []
    
        # الحصول على وثائق السيارة
        documents = []
        # سيتم إضافة منطق لجلب الوثائق لاحقًا
    
        # الحصول على رسوم السيارة
        fees = []
        # سيتم إضافة منطق لجلب الرسوم لاحقًا
    
        return render_template('mobile/vehicle_details_new.html',
                             vehicle=vehicle,
                             maintenance_records=maintenance_records,
                             workshop_records=workshop_records,
                             project_assignments=project_assignments,
                             handover_records=handover_records,
                             external_authorizations=external_authorizations,
                             departments=departments,
                             employees=employees,
                             periodic_inspections=periodic_inspections,
                             safety_checks=safety_checks,
                             documents=documents,
                             fees=fees,
                             total_maintenance_cost=total_maintenance_cost,
                             days_in_workshop=days_in_workshop,
                             inspection_warnings=inspection_warnings)
    
    # تعديل السيارة - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_vehicle(vehicle_id):
        """تعديل بيانات السيارة - واجهة الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        if request.method == 'POST':
            try:
                # تحديث البيانات الأساسية
                vehicle.plate_number = request.form.get('plate_number', '').strip()
                vehicle.make = request.form.get('make', '').strip()
                vehicle.model = request.form.get('model', '').strip()
                vehicle.year = request.form.get('year', '').strip()
                vehicle.color = request.form.get('color', '').strip()
                vehicle.chassis_number = request.form.get('chassis_number', '').strip()
                vehicle.engine_number = request.form.get('engine_number', '').strip()
                vehicle.fuel_type = request.form.get('fuel_type', '').strip()
                vehicle.status = request.form.get('status', '').strip()
                vehicle.notes = request.form.get('notes', '').strip()
                
                # تحديث القسم
                department_id = request.form.get('department_id')
                if department_id:
                    vehicle.department_id = int(department_id) if department_id != '' else None
                else:
                    vehicle.department_id = None
    
                # تحديث تواريخ انتهاء الوثائق
                registration_expiry = request.form.get('registration_expiry_date')
                if registration_expiry:
                    vehicle.registration_expiry_date = datetime.strptime(registration_expiry, '%Y-%m-%d').date()
    
                authorization_expiry = request.form.get('authorization_expiry_date')
                if authorization_expiry:
                    vehicle.authorization_expiry_date = datetime.strptime(authorization_expiry, '%Y-%m-%d').date()
    
                inspection_expiry = request.form.get('inspection_expiry_date')
                if inspection_expiry:
                    vehicle.inspection_expiry_date = datetime.strptime(inspection_expiry, '%Y-%m-%d').date()
    
                # تحديث تاريخ التعديل
                vehicle.updated_at = datetime.utcnow()
    
                db.session.commit()
    
                # تسجيل العملية في سجل النشاط
                log_activity(
                    action="update",
                    entity_type="vehicle",
                    entity_id=vehicle.id,
                    details=f"تم تحديث بيانات السيارة {vehicle.plate_number}"
                )
    
                flash('تم تحديث بيانات السيارة بنجاح', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث السيارة: {str(e)}', 'error')
    
        # الحصول على قائمة الأقسام
        departments = Department.query.order_by(Department.name).all()
        
        return render_template('mobile/edit_vehicle.html', vehicle=vehicle, departments=departments)
    
    # حذف السيارة - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
    @login_required
    def delete_vehicle(vehicle_id):
        """حذف السيارة - واجهة الموبايل"""
        # الحصول على معلومات السيارة أولاً ثم إغلاق session
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        plate_number = vehicle.plate_number
        
        # إغلاق session لتجنب مشاكل ORM
        db.session.expunge(vehicle)
        db.session.close()
    
        try:
            # استخدام اتصال قاعدة بيانات جديد للحذف
            with db.engine.begin() as connection:
                # حذف البيانات المرتبطة أولاً
                connection.execute(
                    db.text("DELETE FROM operation_requests WHERE vehicle_id = :vehicle_id"),
                    {"vehicle_id": vehicle_id}
                )
                
                connection.execute(
                    db.text("DELETE FROM external_authorization WHERE vehicle_id = :vehicle_id"), 
                    {"vehicle_id": vehicle_id}
                )
                
                connection.execute(
                    db.text("DELETE FROM vehicle_handover WHERE vehicle_id = :vehicle_id"),
                    {"vehicle_id": vehicle_id}
                )
                
                connection.execute(
                    db.text("DELETE FROM vehicle_workshop WHERE vehicle_id = :vehicle_id"),
                    {"vehicle_id": vehicle_id}
                )
                
                # حذف المعاملات المرتبطة بالسيارة
                connection.execute(
                    db.text("DELETE FROM transactions WHERE vehicle_id = :vehicle_id"),
                    {"vehicle_id": vehicle_id}
                )
                
                # حذف السيارة نفسها
                connection.execute(
                    db.text("DELETE FROM vehicle WHERE id = :vehicle_id"),
                    {"vehicle_id": vehicle_id}
                )
    
            # تسجيل العملية في سجل النشاط مع session جديد
            log_activity(
                action="vehicle_deleted",
                entity_type="vehicle",
                entity_id=vehicle_id,
                details=f"تم حذف السيارة {plate_number}"
            )
    
            flash(f'تم حذف السيارة {plate_number} بنجاح', 'success')
            return redirect(url_for('mobile.vehicles'))
    
        except Exception as e:
            flash(f'حدث خطأ أثناء حذف السيارة: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicles'))
    
    # رفع وثائق السيارة - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/upload-document', methods=['POST'])
    @login_required
    def upload_vehicle_document(vehicle_id):
        """رفع الوثائق (استمارة، لوحة، تأمين) - واجهة الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        document_type = request.form.get('document_type')
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
        
        # التحقق من نوع الملف
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        
        if file and allowed_file(file.filename):
            from werkzeug.utils import secure_filename
            
            # إنشاء اسم ملف فريد
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # إنشاء المسار المناسب حسب نوع الوثيقة
            if document_type == 'registration_form':
                upload_folder = 'static/uploads/vehicles/registration_forms'
                field_name = 'registration_form_image'
            elif document_type == 'plate':
                upload_folder = 'static/uploads/vehicles/plates'
                field_name = 'plate_image'
            elif document_type == 'insurance':
                upload_folder = 'static/uploads/vehicles/insurance'
                field_name = 'insurance_file'
            else:
                flash('نوع الوثيقة غير صحيح', 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
            
            # إنشاء المجلد إذا لم يكن موجوداً
            os.makedirs(upload_folder, exist_ok=True)
            
            # حفظ الملف
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            # تحديث قاعدة البيانات
            setattr(vehicle, field_name, file_path)
            
            try:
                db.session.commit()
                flash('تم رفع الوثيقة بنجاح', 'success')
                
                # تسجيل النشاط
                log_activity(
                    action='upload',
                    entity_type='Vehicle',
                    entity_id=vehicle.id,
                    details=f'رفع وثيقة {document_type} للسيارة {vehicle.plate_number}'
                )
                
            except Exception as e:
                db.session.rollback()
                # 💾 لا نحذف الملف حتى لو فشل الحفظ في DB - للفحص اليدوي
                print(f"💾 الملف محفوظ رغم فشل DB: {file_path}")
                flash(f'خطأ في حفظ الوثيقة: {str(e)}', 'error')
        else:
            flash('نوع الملف غير مسموح. يرجى رفع صورة أو ملف PDF', 'error')
        
        return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    # حذف وثائق السيارة - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/delete-document', methods=['POST'])
    @login_required
    def delete_vehicle_document(vehicle_id):
        """حذف الوثائق - واجهة الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        document_type = request.form.get('document_type')
        
        if document_type == 'registration_form':
            field_name = 'registration_form_image'
        elif document_type == 'plate':
            field_name = 'plate_image'
        elif document_type == 'insurance':
            field_name = 'insurance_file'
        else:
            flash('نوع الوثيقة غير صحيح', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
        
        # الحصول على مسار الملف الحالي
        file_path = getattr(vehicle, field_name)
        
        if file_path:
            # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
            # لا حذف للملفات الفعلية
            # حذف المسار من قاعدة البيانات
            setattr(vehicle, field_name, None)
            
            try:
                db.session.commit()
                flash('تم حذف الوثيقة بنجاح', 'success')
                
                # تسجيل النشاط
                log_activity(
                    action='delete',
                    entity_type='Vehicle',
                    entity_id=vehicle.id,
                    details=f'حذف وثيقة {document_type} للسيارة {vehicle.plate_number}'
                )
            except Exception as e:
                db.session.rollback()
                flash(f'خطأ في حذف الوثيقة من قاعدة البيانات: {str(e)}', 'error')
        else:
            flash('لا توجد وثيقة لحذفها', 'warning')
        
        return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    # إضافة سيارة جديدة - النسخة المحمولة
    @bp.route('/vehicles/add', methods=['GET', 'POST'])
    @login_required
    def add_vehicle():
        """إضافة سيارة جديدة للنسخة المحمولة"""
        if request.method == "POST":
            try:
                # استخراج البيانات من النموذج
                plate_number = request.form.get("plate_number")
                make = request.form.get("make")
                model = request.form.get("model")
                type_of_car = request.form.get("type_of_car")
                year = request.form.get("year")
                color = request.form.get("color")
                driver_name = request.form.get("driver_name")
                status = request.form.get("status")
                project = request.form.get("project")
                notes = request.form.get("notes")
    
                # التحقق من صحة البيانات المطلوبة
                if not all([plate_number, make, model, type_of_car, year, color, status]):
                    flash("جميع الحقول المطلوبة يجب ملؤها", "error")
                    return render_template("mobile/add_vehicle.html", departments=Department.query.all())
    
                # التحقق من عدم تكرار رقم اللوحة
                existing_vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
                if existing_vehicle:
                    flash("رقم اللوحة موجود مسبقاً في النظام", "error")
                    return render_template("mobile/add_vehicle.html", departments=Department.query.all())
    
                # إنشاء سيارة جديدة
                new_vehicle = Vehicle()
                new_vehicle.plate_number = plate_number
                new_vehicle.make = make
                new_vehicle.model = model
                new_vehicle.type_of_car = type_of_car
                new_vehicle.year = int(year)
                new_vehicle.color = color
                new_vehicle.driver_name = driver_name if driver_name else None
                new_vehicle.status = status
                new_vehicle.project = project if project else None
                new_vehicle.notes = notes if notes else None
                new_vehicle.created_at = datetime.utcnow()
    
                # حفظ السيارة في قاعدة البيانات
                db.session.add(new_vehicle)
                db.session.commit()
    
                # تسجيل العملية في سجل النشاط
                log_activity(
                    action="vehicle_added",
                    entity_type="vehicle",
                    entity_id=new_vehicle.id,
                    details=f"تم إضافة السيارة {plate_number} - {make} {model}"
                )
    
                flash(f"تم إضافة السيارة {plate_number} بنجاح", "success")
                return redirect(url_for("mobile.vehicles"))
    
            except ValueError as e:
                flash("يرجى التأكد من صحة البيانات المدخلة", "error")
            except Exception as e:
                db.session.rollback()
                flash(f"حدث خطأ أثناء إضافة السيارة: {str(e)}", "error")
    
        # جلب قائمة الأقسام للمشاريع
        departments = Department.query.all()
        return render_template("mobile/add_vehicle.html", departments=departments)
    
    # سجل صيانة السيارات - النسخة المحمولة
    
    
    # إضافة صيانة جديدة - النسخة المحمولة
    def maintenance_details(maintenance_id):
        """تفاصيل الصيانة للنسخة المحمولة"""
        # جلب سجل الصيانة من قاعدة البيانات
        maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    
        print(f"DEBUG: Maintenance ID: {maintenance.id}, Type: {type(maintenance)}")
    
        # جلب بيانات السيارة
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
    
        # جلب صور الصيانة إن وجدت
        images = VehicleMaintenanceImage.query.filter_by(maintenance_id=maintenance_id).all()
    
        # تعيين حالة الصيانة لاستخدامها في العرض
        maintenance.status_class = status_class
        # إضافة الصور إلى كائن الصيانة
        maintenance.images = images
    
        return render_template('mobile/maintenance_details.html',
                               maintenance=maintenance,
                               vehicle=vehicle)
    
    
    # تعديل سجل صيانة - النسخة المحمولة
    @bp.route('/vehicles/maintenance/edit/<int:maintenance_id>', methods=['GET', 'POST'])
    @login_required
    def edit_maintenance(maintenance_id):
        """تعديل سجل صيانة للنسخة المحمولة"""
        # جلب سجل الصيانة
        maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    
        # الحصول على قائمة السيارات
        vehicles = Vehicle.query.all()
    
        if request.method == 'POST':
            try:
                # استخراج البيانات من النموذج
                vehicle_id = request.form.get('vehicle_id')
                maintenance_type = request.form.get('maintenance_type')
                description = request.form.get('description')
                cost = request.form.get('cost', 0.0, type=float)
                date_str = request.form.get('date')
                status = request.form.get('status')
                technician = request.form.get('technician')
                notes = request.form.get('notes', '')
                parts_replaced = request.form.get('parts_replaced', '')
                actions_taken = request.form.get('actions_taken', '')
    
                # التحقق من تعبئة الحقول المطلوبة
                if not vehicle_id or not maintenance_type or not description or not date_str or not status or not technician:
                    flash('يرجى ملء جميع الحقول المطلوبة', 'warning')
                    return render_template('mobile/edit_maintenance.html', 
                                         maintenance=maintenance,
                                         vehicles=vehicles, 
                                         now=datetime.now())
    
                # تحويل التاريخ إلى كائن Date
                maintenance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
                # استخراج روابط الإيصالات
                receipt_image_url = request.form.get('receipt_image_url', '')
                delivery_receipt_url = request.form.get('delivery_receipt_url', '')
                pickup_receipt_url = request.form.get('pickup_receipt_url', '')
    
                # تحديث سجل الصيانة
                maintenance.vehicle_id = vehicle_id
                maintenance.date = maintenance_date
                maintenance.maintenance_type = maintenance_type
                maintenance.description = description
                maintenance.status = status
                maintenance.cost = cost
                maintenance.technician = technician
                maintenance.receipt_image_url = receipt_image_url
                maintenance.delivery_receipt_url = delivery_receipt_url
                maintenance.pickup_receipt_url = pickup_receipt_url
                maintenance.parts_replaced = parts_replaced
                maintenance.actions_taken = actions_taken
                maintenance.notes = notes
    
                # حفظ التغييرات في قاعدة البيانات
                db.session.commit()
    
                flash('تم تحديث سجل الصيانة بنجاح', 'success')
                return redirect(url_for('mobile.maintenance_details', maintenance_id=maintenance.id))
    
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث سجل الصيانة: {str(e)}', 'danger')
    
        # عرض نموذج تعديل سجل الصيانة
        return render_template('mobile/edit_maintenance.html', 
                             maintenance=maintenance, 
                             vehicles=vehicles, 
                             now=datetime.now())
    
    
    @bp.route('/vehicles/documents')
    @login_required
    def vehicle_documents():
        """صفحة وثائق المركبات"""
        from datetime import datetime, timedelta
    
        # جلب جميع المركبات
        vehicles = Vehicle.query.all()
    
        # تحديد تاريخ اليوم و30 يوم قادم
        today = datetime.now().date()
        thirty_days_later = today + timedelta(days=30)
    
        # تحليل الوثائق
        documents = []
    
        for vehicle in vehicles:
            # رخصة السير
            if vehicle.registration_expiry_date:
                days_remaining = (vehicle.registration_expiry_date - today).days
                status = 'valid' if days_remaining > 30 else 'warning' if days_remaining > 0 else 'expired'
    
                documents.append({
                    'vehicle': vehicle,
                    'type': 'registration',
                    'type_name': 'رخصة سير',
                    'icon': 'fa-id-card',
                    'expiry_date': vehicle.registration_expiry_date,
                    'days_remaining': days_remaining,
                    'status': status
                })
    
            # التفويض
            if vehicle.authorization_expiry_date:
                days_remaining = (vehicle.authorization_expiry_date - today).days
                status = 'valid' if days_remaining > 30 else 'warning' if days_remaining > 0 else 'expired'
    
                documents.append({
                    'vehicle': vehicle,
                    'type': 'authorization',
                    'type_name': 'تفويض',
                    'icon': 'fa-shield-alt',
                    'expiry_date': vehicle.authorization_expiry_date,
                    'days_remaining': days_remaining,
                    'status': status
                })
    
            # الفحص الدوري
            if vehicle.inspection_expiry_date:
                days_remaining = (vehicle.inspection_expiry_date - today).days
                status = 'valid' if days_remaining > 30 else 'warning' if days_remaining > 0 else 'expired'
    
                documents.append({
                    'vehicle': vehicle,
                    'type': 'inspection',
                    'type_name': 'فحص دوري',
                    'icon': 'fa-clipboard-check',
                    'expiry_date': vehicle.inspection_expiry_date,
                    'days_remaining': days_remaining,
                    'status': status
                })
    
        # حساب الإحصائيات
        valid_docs = len([d for d in documents if d['status'] == 'valid'])
        warning_docs = len([d for d in documents if d['status'] == 'warning'])
        expired_docs = len([d for d in documents if d['status'] == 'expired'])
        total_docs = len(documents)
    
        # ترتيب الوثائق حسب تاريخ الانتهاء
        documents.sort(key=lambda x: x['expiry_date'])
    
        return render_template('mobile/vehicle_documents.html',
                             documents=documents,
                             valid_docs=valid_docs,
                             warning_docs=warning_docs,
                             expired_docs=expired_docs,
                             total_docs=total_docs,
                             vehicles=vehicles)
    
    
    # حذف سجل صيانة - النسخة المحمولة
    @bp.route('/vehicles/maintenance/delete/<int:maintenance_id>')
    @login_required
    def delete_maintenance(maintenance_id):
        """حذف سجل صيانة للنسخة المحمولة"""
        try:
            # جلب سجل الصيانة
            maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    
            # حذف جميع الصور المرتبطة (إن وجدت)
            images = VehicleMaintenanceImage.query.filter_by(maintenance_id=maintenance_id).all()
            for image in images:
                # حذف ملف الصورة من المجلد (يمكن تنفيذه لاحقًا)
                # image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_path)
                # if os.path.exists(image_path):
                #    os.remove(image_path)
    
                # حذف السجل من قاعدة البيانات
                db.session.delete(image)
    
            # حذف سجل الصيانة
            db.session.delete(maintenance)
            db.session.commit()
    
            flash('تم حذف سجل الصيانة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء محاولة حذف سجل الصيانة: {str(e)}', 'danger')
    
        return redirect(url_for('mobile.vehicles'))
    
    # وثائق السيارات - تم نقل الوظيفة في نهاية الملف
    
    
    def save_base64_image(base64_string, subfolder):
        """
        تستقبل سلسلة Base64، تفك تشفيرها، تحفظها كملف PNG فريد،
        وتُرجع المسار النسبي للملف.
        """
        if not base64_string or not base64_string.startswith('data:image/'):
            return None
    
        try:
            # إعداد مسار الحفظ
            upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', subfolder)
            os.makedirs(upload_folder, exist_ok=True)
    
            # فك التشفير
            header, encoded_data = base64_string.split(',', 1)
            image_data = base64.b64decode(encoded_data)
    
            # إنشاء اسم ملف فريد وحفظه
            filename = f"{uuid.uuid4().hex}.png"
            file_path = os.path.join(upload_folder, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
    
            # إرجاع المسار النسبي (مهم لقاعدة البيانات و HTML)
            return os.path.join(subfolder, filename)
    
        except Exception as e:
            print(f"Error saving Base64 image: {e}")
            return None
    
    # في ملف routes.py
    
    def save_uploaded_file(file, subfolder):
        """
        تحفظ ملف مرفوع (من request.files) في مجلد فرعي داخل uploads،
        وتُرجع المسار النسبي الكامل.
        """
        if not file or not file.filename:
            return None
    
        try:
            # إعداد مسار الحفظ
            upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', subfolder)
            os.makedirs(upload_folder, exist_ok=True)
    
            # الحصول على اسم آمن للملف وإنشاء اسم فريد
            from werkzeug.utils import secure_filename
            filename_secure = secure_filename(file.filename)
            # فصل الاسم والامتداد
            name, ext = os.path.splitext(filename_secure)
            # إنشاء اسم فريد لمنع الكتابة فوق الملفات
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
    
            # إرجاع المسار النسبي الكامل (متطابق مع save_file)
            return f"static/uploads/{subfolder}/{unique_filename}"
    
        except Exception as e:
            print(f"Error saving uploaded file: {e}")
            return None
    
    def save_file(file, folder):
        """حفظ الملف (صورة أو PDF) في المجلد المحدد وإرجاع المسار ونوع الملف - مع دعم HEIC"""
        if not file:
            current_app.logger.warning("save_file: No file provided")
            return None, None
        if not file.filename:
            current_app.logger.warning("save_file: File has no filename")
            return None, None
    
        # فصل الاسم والامتداد قبل استخدام secure_filename لتجنب فقدان الامتداد
        original_filename = file.filename
        name_part, ext_part = os.path.splitext(original_filename)
        
        # استخدام secure_filename على الاسم فقط (بدون الامتداد)
        safe_name = secure_filename(name_part) or 'file'
        
        # إنشاء اسم فريد مع الامتداد الأصلي
        unique_filename = f"{uuid.uuid4()}_{safe_name}{ext_part}"
    
        # التأكد من وجود المجلد
        upload_folder = os.path.join(current_app.static_folder, 'uploads', folder)
        os.makedirs(upload_folder, exist_ok=True)
    
        # حفظ الملف
        file_path = os.path.join(upload_folder, unique_filename)
        final_file_path = file_path
        
        try:
            current_app.logger.info(f"save_file: Saving {original_filename} to {file_path}")
            file.save(file_path)
            
            # ✅ التحقق من نجاح الحفظ
            if not os.path.exists(file_path):
                current_app.logger.error(f"save_file: File NOT saved! Path: {file_path}")
                return None, None
            
            file_size = os.path.getsize(file_path)
            current_app.logger.info(f"save_file: File saved successfully! Size: {file_size} bytes")
            
            # تحويل HEIC/HEIF إلى JPEG للتوافق مع المتصفحات
            ext_lower = ext_part.lower()
            if ext_lower in ('.heic', '.heif'):
                try:
                    from PIL import Image
                    current_app.logger.info(f"save_file: Converting HEIC to JPEG: {file_path}")
                    img = Image.open(file_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    jpeg_filename = unique_filename.rsplit('.', 1)[0] + '.jpg'
                    jpeg_path = os.path.join(upload_folder, jpeg_filename)
                    img.save(jpeg_path, 'JPEG', quality=90)
                    # 💾 الملف الأصلي يبقى محفوظاً - لا حذف للملفات
                    unique_filename = jpeg_filename
                    final_file_path = jpeg_path
                    current_app.logger.info(f"save_file: HEIC conversion successful: {jpeg_path}")
                except Exception as convert_error:
                    current_app.logger.error(f"save_file: HEIC conversion failed: {convert_error}")
            
            # التحقق النهائي من وجود الملف
            if not os.path.exists(final_file_path):
                current_app.logger.error(f"save_file: Final file NOT found! Path: {final_file_path}")
                return None, None
            
            # تحديد نوع الملف
            file_type = 'pdf' if ext_lower == '.pdf' else 'image'
            relative_path = f"static/uploads/{folder}/{unique_filename}"
            current_app.logger.info(f"save_file: SUCCESS! Returning path: {relative_path}")
            return relative_path, file_type
            
        except Exception as e:
            current_app.logger.error(f"save_file: Exception occurred: {e}", exc_info=True)
            return None, None
    
    
    
    # قائمة بأنواع عمليات التسليم والاستلام
    HANDOVER_TYPE_CHOICES = [
            'delivery',  # تسليم
            'return',  # استلام
        'inspection',  # تفتيش
            'weekly_inspection',  # تفتيش اسبةعي
        'monthly_inspection'  # تفتيش شهري
    ]
    
    
    # في أعلى ملف الـ routes الخاص بالموبايل
    from datetime import datetime, date
    
    # --- دالة الموبايل الجديدة والمحدثة بالكامل ---
    
    # في ملف الراوت الخاص بالموبايل (mobile_bp.py)
    
    # =========================================================================================
    
    # في ملف الراوت الخاص بالموبايل (mobile_bp.py)
    
    # تأكد من أن كل هذه الاستيرادات موجودة في أعلى الملف
    # from datetime import datetime, date
    # from flask import (Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app)
    # from flask_login import login_required, current_user
    # from sqlalchemy import or_
    # from sqlalchemy.orm import joinedload
    # ...
    # from models import (db, Vehicle, Employee, Department, VehicleHandover, VehicleHandoverImage, OperationRequest)
    # from utils.audit_logger import log_activity
    # from routes.operations import create_operation_request
    # ...
    # والدوال المساعدة لحفظ الملفات (save_base64_image, save_file, save_uploaded_file)
    
    
    # في ملف mobile_bp.py
    
    @bp.route('/api/employee/<int:employee_id>/details')
    @login_required
    def get_employee_details_api(employee_id):
        """
        نقطة نهاية API لإرجاع تفاصيل الموظف بصيغة JSON.
        """
        employee = Employee.query.get_or_404(employee_id)
    
        # تحويل بيانات الموظف إلى قاموس (dictionary)
        departments = [dept.name for dept in employee.departments]
        employee_data = {
            'name': employee.name,
            'employee_id': employee.employee_id or 'N/A',
            'job_title': employee.job_title or 'N/A',
            'mobile': employee.mobile or 'N/A',
            'department': ', '.join(departments) if departments else 'N/A',
            'license_status': employee.license_status or 'N/A'
        }
        return jsonify(success=True, employee=employee_data)
