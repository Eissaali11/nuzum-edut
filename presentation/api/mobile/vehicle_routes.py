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
    db,
    employee_departments,
)
from routes.operations import create_operation_request
from modules.vehicles.application.vehicle_service import update_vehicle_driver
from utils.audit_logger import log_activity
from utils.decorators import module_access_required, permission_required
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state


def register_vehicle_routes(bp):
    """تسجيل جميع مسارات المركبات والورشة والتسليم/الاستلام والتصريحات على الـ blueprint المزوّد."""
    # صفحة السيارات - النسخة المحمولة
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
        
    
    @bp.route('/vehicles/<int:vehicle_id>/handover/create', methods=['GET', 'POST'])
    @login_required
    def create_handover_mobile(vehicle_id):
        """
        الراوت الموحد والكامل لإنشاء نموذج تسليم/استلام جديد من واجهة الموبايل.
        - يحدد نوع العملية تلقائياً.
        - يتكامل مع نظام الموافقات عبر OperationRequest.
        """
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        status_arabic_map = {
            'available': 'متاحة',
            'rented': 'مؤجرة',
            'in_project': 'في المشروع',
            'in_workshop': 'في الورشة',
            'accident': 'حادث',
            'out_of_service': 'خارج الخدمة'
        }
    
        current_status_ar = status_arabic_map.get(vehicle.status, vehicle.status) # إذا لم يجد الترجمة، يستخدم الاسم الإنجليزي
    
    
        unsuitable_statuses = {
            'in_workshop': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"',
            'accident': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"',
            'out_of_service': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"'
        }
        # احصل على الترجمة للحالة الحالية للمركبة
    
    
        # === الخطوة 1: التحقق من أهلية السيارة للعملية ===
    
        if vehicle.status in unsuitable_statuses:
            flash(unsuitable_statuses[vehicle.status], 'danger')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
        # === الخطوة 2: المنطق الذكي لتحديد نوع العملية (GET & POST) ===
        # هذا المنطق يُستخدم للتحقق من صحة الطلب عند الحفظ (POST)
        # ولإعداد النموذج بشكل صحيح عند العرض (GET)
        force_mode = 'delivery'
        info_message = "المركبة متاحة حالياً. النموذج معد لعملية التسليم لسائق جديد."
        current_driver_info = None
    
        # نستخدم نفس منطق الويب للبحث عن آخر عملية رسمية معتمدة
        approved_handover_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.status == 'approved',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()
    
        all_handover_request_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()
    
        base_official_query = VehicleHandover.query.filter(
            VehicleHandover.vehicle_id == vehicle_id,
            or_(
                VehicleHandover.id.in_(approved_handover_ids_subquery),
                ~VehicleHandover.id.in_(all_handover_request_ids_subquery)
            )
        )
    
        latest_delivery = base_official_query.filter(VehicleHandover.handover_type == 'delivery').order_by(VehicleHandover.created_at.desc()).first()
        latest_return = base_official_query.filter(VehicleHandover.handover_type == 'return').order_by(VehicleHandover.created_at.desc()).first()
    
        if latest_delivery and (not latest_return or latest_delivery.created_at > latest_return.created_at):
            force_mode = 'return'
            current_driver_info = latest_delivery # كائن كامل
            info_message = f"تنبيه: المركبة مسلمة حالياً لـِ '{latest_delivery.person_name}'. النموذج معد لعملية الاستلام فقط."
    
        # === معالجة طلب GET (عرض النموذج) ===
        if request.method == 'GET':
            employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
            departments = Department.query.order_by(Department.name).all()
    
            return render_template(
                'mobile/vehicle_checklist.html',
                is_editing=False,
                form_action=url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id),
                vehicle=vehicle,
                force_mode=force_mode,
                current_driver_info=current_driver_info.to_dict() if current_driver_info else None,
                info_message=info_message,
                employees=employees,
                departments=departments
            )
    
        # === معالجة طلب POST (إنشاء السجل) ===
        if request.method == 'POST':
            try:
                handover_type_from_form = request.form.get('handover_type')
                if handover_type_from_form != force_mode:
                    flash("خطأ في منطق العملية. تم تحديث الصفحة، يرجى المحاولة مرة أخرى.", "danger")
                    return redirect(url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id))
    
                # --- 3. استخراج شامل للبيانات من النموذج ---
                handover_date_str = request.form.get('handover_date')
                handover_time_str = request.form.get('handover_time')
                employee_id_str = request.form.get('employee_id')
                supervisor_employee_id_str = request.form.get('supervisor_employee_id')
                person_name_from_form = request.form.get('person_name', '').strip()
                supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
                mileage = int(request.form.get('mileage', 0))
                fuel_level = request.form.get('fuel_level')
                project_name = request.form.get('project_name')
                city = request.form.get('city')
                reason_for_change = request.form.get('reason_for_change')
                vehicle_status_summary = request.form.get('vehicle_status_summary')
                notes = request.form.get('notes')
                reason_for_authorization = request.form.get('reason_for_authorization')
                authorization_details = request.form.get('authorization_details')
                movement_officer_name = request.form.get('movement_officer_name')
                form_link = request.form.get('form_link')
                form_link_2 = request.form.get('form_link_2')
                custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
                # Checklist
                has_spare_tire = 'has_spare_tire' in request.form
                has_fire_extinguisher = 'has_fire_extinguisher' in request.form
                has_first_aid_kit = 'has_first_aid_kit' in request.form
                has_warning_triangle = 'has_warning_triangle' in request.form
                has_tools = 'has_tools' in request.form
                has_oil_leaks = 'has_oil_leaks' in request.form
                has_gear_issue = 'has_gear_issue' in request.form
                has_clutch_issue = 'has_clutch_issue' in request.form
                has_engine_issue = 'has_engine_issue' in request.form
                has_windows_issue = 'has_windows_issue' in request.form
                has_tires_issue = 'has_tires_issue' in request.form
                has_body_issue = 'has_body_issue' in request.form
                has_electricity_issue = 'has_electricity_issue' in request.form
                has_lights_issue = 'has_lights_issue' in request.form
                has_ac_issue = 'has_ac_issue' in request.form
    
                handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
                handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
                saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams') or None
                saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures') or None
                saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures') or None
                movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature_data'), 'signatures') # تصحيح الاسم هنا
                custom_logo_file = request.files.get('custom_logo_file')
                saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
                driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
                # إذا لم يتم اختيار موظف من القائمة، ابحث عنه بالاسم
                if not driver and person_name_from_form:
                    driver = Employee.query.filter(Employee.name.ilike(f"%{person_name_from_form.strip()}%")).first()
                
                supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
                # --- 4. إنشاء كائن VehicleHandover وتعبئته ---
                handover = VehicleHandover(
                    vehicle_id=vehicle.id, handover_type=handover_type_from_form, handover_date=handover_date,
                    handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
                    vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
                    vehicle_model_year=str(vehicle.year), employee_id=driver.id if driver else (current_driver_info.employee_id if force_mode == 'return' else None),
                    person_name=driver.name if driver else (person_name_from_form if force_mode == 'delivery' else current_driver_info.person_name),
                    driver_company_id=driver.employee_id if driver else (current_driver_info.driver_company_id if force_mode == 'return' else None),
                    driver_work_phone=driver.mobile if driver else (current_driver_info.driver_work_phone if force_mode == 'return' else None),
                    driver_phone_number=driver.mobilePersonal if driver else (current_driver_info.driver_phone_number if force_mode == 'return' else None),
                    driver_residency_number=driver.national_id if driver else (current_driver_info.driver_residency_number if force_mode == 'return' else None),
                    driver_contract_status=driver.contract_status if driver else None,
                    driver_license_status=driver.license_status if driver else None,
                    driver_signature_path=saved_driver_sig_path,
                    supervisor_employee_id=supervisor.id if supervisor else None,
                    supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
                    supervisor_company_id=supervisor.mobile if supervisor else None,
                    supervisor_phone_number=supervisor.mobilePersonal if supervisor else None,
                    supervisor_residency_number=supervisor.national_id if supervisor else None,
                    supervisor_contract_status=supervisor.contract_status if supervisor else None,
                    supervisor_license_status=supervisor.license_status if supervisor else None,
                    supervisor_signature_path=saved_supervisor_sig_path, reason_for_change=reason_for_change,
                    vehicle_status_summary=vehicle_status_summary, notes=notes,
                    reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
                    fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
                    has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
                    has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
                    has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
                    has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
                    has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
                    has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
                    movement_officer_name=movement_officer_name,
                    movement_officer_signature_path=movement_officer_signature_path,
                    damage_diagram_path=saved_diagram_path, form_link=form_link, form_link_2=form_link_2,
                    custom_company_name=custom_company_name, custom_logo_path=saved_custom_logo_path
                )
    
                db.session.add(handover)
                db.session.flush()
    
                # --- 5. إنشاء طلب موافقة (Operation Request) ---
                action_type = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
                operation_title = f"موافقة على {action_type} مركبة {vehicle.plate_number} (جوال)"
                operation_description = f"تم إنشاء نموذج {action_type} للمركبة {vehicle.plate_number} بواسطة {current_user.username} عبر الجوال. الرجاء المراجعة والموافقة."
    
                create_operation_request(
                    operation_type="handover", 
                    related_record_id=handover.id, 
                    vehicle_id=vehicle.id,
                    title=operation_title, 
                    description=operation_description, 
                    requested_by=current_user.id
                )
    
                # --- 6. حفظ المرفقات الإضافية ---
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename:
                        file_path, file_type = save_file(file, 'handover')
                        if file_path:
                            desc = request.form.get(f'description_{file.filename}', '')
                            attachment = VehicleHandoverImage(
                                handover_record_id=handover.id, file_path=file_path, file_type=file_type, 
                                image_path=file_path, file_description=desc, image_description=desc
                            )
                            db.session.add(attachment)
    
                db.session.commit()
    
                log_activity('create', 'vehicle_handover', handover.id, f"إنشاء طلب {action_type} للمركبة {vehicle.plate_number} عبر الجوال (بانتظار الموافقة)")
    
                flash(f'تم إنشاء طلب {action_type} بنجاح، وهو الآن بانتظار الموافقة.', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
                return redirect(url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id))
    
    
    
    
    
    
    # في ملف mobile_bp.py
    
    # ... تأكد من وجود كل الاستيرادات اللازمة والدوال المساعدة ...
    
    
    @bp.route('/handover/<int:handover_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_handover_mobile(handover_id):
        """
        راوت لتعديل نموذج تسليم/استلام حالي.
        """
        existing_handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = existing_handover.vehicle
    
        # === معالجة طلب GET (عرض النموذج مع البيانات الحالية) ===
        if request.method == 'GET':
            employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
            departments = Department.query.order_by(Department.name).all()
    
            return render_template(
                'mobile/vehicle_checklist.html',
                is_editing=True,
                form_action=url_for('mobile.edit_handover_mobile', handover_id=handover_id),
                vehicle=vehicle,
                existing_handover=existing_handover.to_dict(),
                employees=employees,
                departments=departments
            )
    
        # === معالجة طلب POST (حفظ التعديلات على السجل الحالي) ===
        if request.method == 'POST':
            try:
                # --- استخراج شامل للبيانات من النموذج ---
                handover_type = request.form.get('handover_type')
                handover_date_str = request.form.get('handover_date')
                handover_time_str = request.form.get('handover_time')
                employee_id_str = request.form.get('employee_id')
                supervisor_employee_id_str = request.form.get('supervisor_employee_id')
                person_name_from_form = request.form.get('person_name', '').strip()
                supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
                mileage = int(request.form.get('mileage', 0))
                fuel_level = request.form.get('fuel_level')
                project_name = request.form.get('project_name')
                city = request.form.get('city')
                reason_for_change = request.form.get('reason_for_change')
                vehicle_status_summary = request.form.get('vehicle_status_summary')
                notes = request.form.get('notes')
                reason_for_authorization = request.form.get('reason_for_authorization')
                authorization_details = request.form.get('authorization_details')
                movement_officer_name = request.form.get('movement_officer_name')
                form_link = request.form.get('form_link')
                form_link_2 = request.form.get('form_link_2')
                custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
                # Checklist
                has_spare_tire = 'has_spare_tire' in request.form
                has_fire_extinguisher = 'has_fire_extinguisher' in request.form
                has_first_aid_kit = 'has_first_aid_kit' in request.form
                has_warning_triangle = 'has_warning_triangle' in request.form
                has_tools = 'has_tools' in request.form
                has_oil_leaks = 'has_oil_leaks' in request.form
                has_gear_issue = 'has_gear_issue' in request.form
                has_clutch_issue = 'has_clutch_issue' in request.form
                has_engine_issue = 'has_engine_issue' in request.form
                has_windows_issue = 'has_windows_issue' in request.form
                has_tires_issue = 'has_tires_issue' in request.form
                has_body_issue = 'has_body_issue' in request.form
                has_electricity_issue = 'has_electricity_issue' in request.form
                has_lights_issue = 'has_lights_issue' in request.form
                has_ac_issue = 'has_ac_issue' in request.form
    
                existing_handover.handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else existing_handover.handover_date
                existing_handover.handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else existing_handover.handover_time
    
                driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
                supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
                # --- تحديث حقول السجل `existing_handover` ---
                existing_handover.handover_type = handover_type
                existing_handover.mileage = mileage
                existing_handover.project_name = project_name
                existing_handover.city = city
                existing_handover.employee_id = driver.id if driver else None
                existing_handover.person_name = driver.name if driver else person_name_from_form
                existing_handover.supervisor_employee_id = supervisor.id if supervisor else None
                existing_handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
                existing_handover.reason_for_change = reason_for_change
                existing_handover.vehicle_status_summary = vehicle_status_summary
                existing_handover.notes = notes
                existing_handover.reason_for_authorization = reason_for_authorization
                existing_handover.authorization_details = authorization_details
                existing_handover.fuel_level = fuel_level
                existing_handover.has_spare_tire, existing_handover.has_fire_extinguisher, existing_handover.has_first_aid_kit, existing_handover.has_warning_triangle, existing_handover.has_tools = has_spare_tire, has_fire_extinguisher, has_first_aid_kit, has_warning_triangle, has_tools
                existing_handover.has_oil_leaks, existing_handover.has_gear_issue, existing_handover.has_clutch_issue, existing_handover.has_engine_issue, existing_handover.has_windows_issue, existing_handover.has_tires_issue, existing_handover.has_body_issue, existing_handover.has_electricity_issue, existing_handover.has_lights_issue, existing_handover.has_ac_issue = has_oil_leaks, has_gear_issue, has_clutch_issue, has_engine_issue, has_windows_issue, has_tires_issue, has_body_issue, has_electricity_issue, has_lights_issue, has_ac_issue
                existing_handover.movement_officer_name = movement_officer_name
                existing_handover.form_link = form_link
                existing_handover.form_link_2 = form_link_2
                existing_handover.custom_company_name = custom_company_name
                existing_handover.updated_at = datetime.utcnow()
    
                # تحديث الصور والتواقيع فقط إذا تم تقديم بيانات جديدة
                new_diagram_data = request.form.get('damage_diagram_data')
                if new_diagram_data: existing_handover.damage_diagram_path = save_base64_image(new_diagram_data, 'diagrams')
    
                new_supervisor_sig = request.form.get('supervisor_signature_data')
                if new_supervisor_sig: existing_handover.supervisor_signature_path = save_base64_image(new_supervisor_sig, 'signatures')
    
                new_driver_sig = request.form.get('driver_signature_data')
                if new_driver_sig: existing_handover.driver_signature_path = save_base64_image(new_driver_sig, 'signatures')
    
                new_movement_sig = request.form.get('movement_officer_signature_data')
                if new_movement_sig: existing_handover.movement_officer_signature_path = save_base64_image(new_movement_sig, 'signatures')
    
                # معالجة رفع الملفات الجديدة
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename:
                        try:
                            file_path, file_type = save_file(file, 'handover')
                            if file_path:
                                file_description = request.form.get(f'description_{file.filename}', '')
                                file_record = VehicleHandoverImage(
                                    handover_record_id=existing_handover.id, 
                                    image_path=file_path,
                                    image_description=file_description,
                                    file_path=file_path, 
                                    file_type=file_type,
                                    file_description=file_description
                                )
                                db.session.add(file_record)
                        except Exception as e:
                            import logging
                            logging.error(f"خطأ في حفظ الملف {file.filename}: {str(e)}")
                            flash(f'خطأ في حفظ الملف {file.filename}', 'warning')
    
                db.session.commit()
                log_activity('update', 'vehicle_handover', existing_handover.id, f"تعديل نموذج {existing_handover.handover_type} للمركبة {vehicle.plate_number} عبر الجوال")
    
                flash('تم تحديث النموذج بنجاح.', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                flash(f'حدث خطأ أثناء تحديث النموذج: {str(e)}', 'danger')
                return redirect(url_for('mobile.edit_handover_mobile', handover_id=handover_id))
    
    @bp.route('/handover/<int:handover_id>/save_as_next', methods=['POST'])
    @login_required
    def save_as_next_handover_mobile(handover_id):
        """
        راوت لإنشاء سجل جديد بناءً على تعديلات سجل حالي، مع عكس نوع العملية.
        """
        original_handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = original_handover.vehicle
    
        try:
            # --- استخراج شامل للبيانات من النموذج ---
            handover_type = request.form.get('handover_type') # هذا سيكون نوع العملية القديمة
            handover_date_str = request.form.get('handover_date')
            handover_time_str = request.form.get('handover_time')
            employee_id_str = request.form.get('employee_id')
            supervisor_employee_id_str = request.form.get('supervisor_employee_id')
            person_name_from_form = request.form.get('person_name', '').strip()
            supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
            mileage = int(request.form.get('mileage', 0))
            fuel_level = request.form.get('fuel_level')
            project_name = request.form.get('project_name')
            city = request.form.get('city')
            reason_for_change = request.form.get('reason_for_change')
            vehicle_status_summary = request.form.get('vehicle_status_summary')
            notes = request.form.get('notes')
            reason_for_authorization = request.form.get('reason_for_authorization')
            authorization_details = request.form.get('authorization_details')
            movement_officer_name = request.form.get('movement_officer_name')
            form_link = request.form.get('form_link')
            form_link_2 = request.form.get('form_link_2')
            custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
            # Checklist
            has_spare_tire = 'has_spare_tire' in request.form; has_fire_extinguisher = 'has_fire_extinguisher' in request.form; has_first_aid_kit = 'has_first_aid_kit' in request.form; has_warning_triangle = 'has_warning_triangle' in request.form; has_tools = 'has_tools' in request.form; has_oil_leaks = 'has_oil_leaks' in request.form; has_gear_issue = 'has_gear_issue' in request.form; has_clutch_issue = 'has_clutch_issue' in request.form; has_engine_issue = 'has_engine_issue' in request.form; has_windows_issue = 'has_windows_issue' in request.form; has_tires_issue = 'has_tires_issue' in request.form; has_body_issue = 'has_body_issue' in request.form; has_electricity_issue = 'has_electricity_issue' in request.form; has_lights_issue = 'has_lights_issue' in request.form; has_ac_issue = 'has_ac_issue' in request.form
    
            handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
            handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
            # --- إنشاء كائن `VehicleHandover` جديد وتعبئته بالبيانات ---
            new_handover = VehicleHandover(
                vehicle_id=vehicle.id, handover_date=handover_date,
                handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
                vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
                vehicle_model_year=str(vehicle.year), 
                # (سيتم تعبئة حقول السائق والمشرف أدناه)
                reason_for_change=reason_for_change,
                vehicle_status_summary=vehicle_status_summary, notes=notes,
                reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
                fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
                has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
                has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
                has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
                has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
                has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
                has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
                movement_officer_name=movement_officer_name,
                form_link=form_link, form_link_2=form_link_2,
                custom_company_name=custom_company_name,
                # created_by=current_user.id
            )
    
            # !! --- المنطق الذكي: عكس نوع العملية وتحديد السائق والمشرف --- !!
            driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
            supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
            # المشرف دائماً هو من تم اختياره في الفورم
            new_handover.supervisor_employee_id = supervisor.id if supervisor else None
            new_handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
    
            if original_handover.handover_type == 'delivery':
                new_handover.handover_type = 'return'
                # السائق هو نفس سائق عملية التسليم الأصلية
                new_handover.person_name = original_handover.person_name
                new_handover.employee_id = original_handover.employee_id
            else: # إذا كانت العملية الأصلية 'return'
                new_handover.handover_type = 'delivery'
                # السائق هو من تم اختياره في النموذج الحالي
                new_handover.employee_id = driver.id if driver else None
                new_handover.person_name = driver.name if driver else person_name_from_form
    
            db.session.add(new_handover)
            db.session.flush()
    
            # --- إنشاء طلب موافقة للسجل الجديد ---
            action_type = 'تسليم' if new_handover.handover_type == 'delivery' else 'استلام'
            operation_title = f"موافقة على {action_type} (نسخة جديدة) لمركبة {vehicle.plate_number}"
            create_operation_request(
                operation_type="handover", related_record_id=new_handover.id, vehicle_id=vehicle.id,
                title=operation_title, description=f"تم إنشاؤها كنسخة من سجل سابق بواسطة {current_user.username}.", 
                requested_by=current_user.id
            )
    
            db.session.commit()
    
            flash(f'تم حفظ نسخة جديدة كعملية "{action_type}" وهي الآن بانتظار الموافقة.', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'حدث خطأ أثناء حفظ النسخة الجديدة: {str(e)}', 'danger')
            return redirect(url_for('mobile.edit_handover_mobile', handover_id=handover_id))
    
    
    
    # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # @bp.route('/vehicles/checklist/<int:handover_id>', methods=['GET', 'POST'])
    # @login_required
    # def create_handover_mobile(handover_id=None):
        
    #     """
    #     النسخة المحسنة لإنشاء وتعديل نموذج تسليم/استلام السيارة (للموبايل).
    #     تدمج هذه النسخة المنطق الكامل من نسخة الويب مع واجهة الموبايل.
    #     """
    
    #     # === معالجة طلب GET (عرض النموذج) ===
    #     if request.method == 'GET':
    #         vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    #         employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    #         departments = Department.query.order_by(Department.name).all()
    #         employees_as_dicts = [e.to_dict() for e in employees]
    
    #         now_date = datetime.now().strftime('%Y-%m-%d')
    #         now_time = datetime.now().strftime('%H:%M')
    
    #         existing_handover_data = None
    #         is_editing = False
    #         if handover_id:
    #             existing_handover = VehicleHandover.query.get(handover_id)
    #             if existing_handover:
    #                 is_editing = True
    #                 existing_handover_data = existing_handover.to_dict()
    #                 now_date = existing_handover.handover_date.strftime('%Y-%m-%d') if existing_handover.handover_date else now_date
    #                 now_time = existing_handover.handover_time.strftime('%H:%M') if existing_handover.handover_time else now_time
    
    #         return render_template(
    #             'mobile/vehicle_checklist.html', 
    #             vehicles=vehicles,
    #             employees=employees,
    #             departments=departments,
    #             handover_types=HANDOVER_TYPE_CHOICES,
    #             employeeData=employees_as_dicts,
    #             now_date=now_date,
    #             now_time=now_time,
    #             existing_handover=existing_handover_data,
    #             is_editing=is_editing
    #         )
    
    #     # === معالجة طلب POST (حفظ النموذج) ===
    #     if request.method == 'POST':
    #         vehicle_id_str = request.form.get('vehicle_id')
    #         if not vehicle_id_str:
    #             flash('يجب اختيار مركبة أولاً.', 'danger')
    #             return redirect(url_for('mobile.create_handover_mobile'))
    
    #         vehicle = Vehicle.query.get_or_404(int(vehicle_id_str))
    
    #         # 1. التحقق من حالة السيارة (منطق من نسخة الويب)
    #         unsuitable_statuses = {
    #             'in_workshop': 'لا يمكن تسليم أو استلام المركبة لأنها حالياً في الورشة.',
    #             'accident': 'لا يمكن تسليم أو استلام المركبة لأنه مسجل عليها حادث نشط.',
    #             'out_of_service': 'لا يمكن تسليم أو استلام المركبة لأنها "خارج الخدمة".'
    #         }
    #         if vehicle.status in unsuitable_statuses:
    #             flash(f'❌ عملية مرفوضة: {unsuitable_statuses[vehicle.status]}', 'danger')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         try:
    #             # 2. استخراج شامل للبيانات من النموذج (مطابق لنسخة الويب)
    #             handover_type = request.form.get('handover_type')
    #             handover_date_str = request.form.get('handover_date')
    #             handover_time_str = request.form.get('handover_time')
    #             employee_id_str = request.form.get('employee_id')
    #             supervisor_employee_id_str = request.form.get('supervisor_employee_id')
    #             person_name_from_form = request.form.get('person_name', '').strip()
    #             supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
    #             mileage = int(request.form.get('mileage', 0))
    #             fuel_level = request.form.get('fuel_level')
    #             project_name = request.form.get('project_name')
    #             city = request.form.get('city')
    #             reason_for_change = request.form.get('reason_for_change')
    #             vehicle_status_summary = request.form.get('vehicle_status_summary')
    #             notes = request.form.get('notes')
    #             reason_for_authorization = request.form.get('reason_for_authorization')
    #             authorization_details = request.form.get('authorization_details')
    #             movement_officer_name = request.form.get('movement_officer_name')
    #             form_link = request.form.get('form_link')
    #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    #             # Checklist
    #             has_spare_tire = 'has_spare_tire' in request.form
    #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    #             has_warning_triangle = 'has_warning_triangle' in request.form
    #             has_tools = 'has_tools' in request.form
    #             has_oil_leaks = 'has_oil_leaks' in request.form
    #             has_gear_issue = 'has_gear_issue' in request.form
    #             has_clutch_issue = 'has_clutch_issue' in request.form
    #             has_engine_issue = 'has_engine_issue' in request.form
    #             has_windows_issue = 'has_windows_issue' in request.form
    #             has_tires_issue = 'has_tires_issue' in request.form
    #             has_body_issue = 'has_body_issue' in request.form
    #             has_electricity_issue = 'has_electricity_issue' in request.form
    #             has_lights_issue = 'has_lights_issue' in request.form
    #             has_ac_issue = 'has_ac_issue' in request.form
    
    #             handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
    #             handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
    #             # حفظ الصور والتواقيع
    #             saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams')
    #             saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures')
    #             saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures')
    #             movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature'), 'signatures')
    #             custom_logo_file = request.files.get('custom_logo_file')
    #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
    #             driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
    #             supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
    #             # 3. إنشاء كائن VehicleHandover وتعبئته بالبيانات الكاملة
    #             handover = VehicleHandover(
    #                 vehicle_id=vehicle.id, handover_type=handover_type, handover_date=handover_date,
    #                 handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
    #                 vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
    #                 vehicle_model_year=str(vehicle.year), employee_id=driver.id if driver else None,
    #                 person_name=driver.name if driver else person_name_from_form,
    #                 driver_company_id=driver.employee_id if driver else None,
    #                 driver_phone_number=driver.mobile if driver else None,
    #                 driver_residency_number=driver.national_id if driver else None,
    #                 driver_contract_status=driver.contract_status if driver else None,
    #                 driver_license_status=driver.license_status if driver else None,
    #                 driver_signature_path=saved_driver_sig_path,
    #                 supervisor_employee_id=supervisor.id if supervisor else None,
    #                 supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
    #                 supervisor_company_id=supervisor.employee_id if supervisor else None,
    #                 supervisor_phone_number=supervisor.mobile if supervisor else None,
    #                 supervisor_residency_number=supervisor.national_id if supervisor else None,
    #                 supervisor_contract_status=supervisor.contract_status if supervisor else None,
    #                 supervisor_license_status=supervisor.license_status if supervisor else None,
    #                 supervisor_signature_path=saved_supervisor_sig_path, reason_for_change=reason_for_change,
    #                 vehicle_status_summary=vehicle_status_summary, notes=notes,
    #                 reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
    #                 fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
    #                 has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
    #                 has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
    #                 has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
    #                 has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
    #                 has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    #                 has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
    #                 movement_officer_name=movement_officer_name,
    #                 movement_officer_signature_path=movement_officer_signature_path,
    #                 damage_diagram_path=saved_diagram_path, form_link=form_link,
    #                 custom_company_name=custom_company_name, custom_logo_path=saved_custom_logo_path
    #             )
    
    #             db.session.add(handover)
    #             db.session.flush() # الحصول على ID
    
    #             # 4. إنشاء طلب عملية تلقائي (منطق الويب)
    #             action_type = 'تسليم' if handover_type == 'delivery' else 'استلام'
    #             operation_title = f"طلب موافقة على {action_type} مركبة {vehicle.plate_number}"
    #             operation_description = f"تم إنشاء {action_type} للمركبة {vehicle.plate_number} عبر الجوال ويحتاج للموافقة."
    
    #             create_operation_request(
    #                 operation_type="handover", 
    #                 related_record_id=handover.id, 
    #                 vehicle_id=vehicle.id,
    #                 title=operation_title, 
    #                 description=operation_description, 
    #                 requested_by=current_user.id
    #             )
    
    #             # 5. حفظ المرفقات الإضافية (منطق الويب)
    #             files = request.files.getlist('files')
    #             for file in files:
    #                 if file and file.filename:
    #                     file_path, file_type = save_file(file, 'handover')
    #                     if file_path:
    #                         desc = request.form.get(f'description_{file.filename}', '')
    #                         attachment = VehicleHandoverImage(
    #                             handover_record_id=handover.id, file_path=file_path, file_type=file_type, 
    #                             image_path=file_path, file_description=desc, image_description=desc
    #                         )
    #                         db.session.add(attachment)
    
    #             db.session.commit()
    
    #             flash(f'تم إنشاء طلب {action_type} بنجاح، وهو الآن بانتظار الموافقة.', 'success')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         except Exception as e:
    #             db.session.rollback()
    #             import traceback
    #             traceback.print_exc()
    #             flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
    #             return redirect(url_for('mobile.create_handover_mobile', handover_id=handover_id))
    
    
    # # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # # @bp.route('/vehicles/checklist/<int:handover_id>', methods=['GET', 'POST'])
    # # @login_required
    # # def create_handover_mobile(handover_id=None):
    # #     """
    # #     عرض ومعالجة نموذج تسليم/استلام السيارة (نسخة الهواتف المحمولة).
    # #     هذه النسخة مطابقة للمنطق الشامل الموجود في نسخة الويب.
    # #     """
    
    
        
    # #     # === معالجة طلب POST (عند إرسال النموذج) ===
    # #     if request.method == 'POST':
    # #         # فحص حجم البيانات المرسلة
    # #         content_length = request.content_length
    # #         if content_length and content_length > 20 * 1024 * 1024:  # 20 MB
    # #             size_mb = content_length / (1024 * 1024)
    # #             flash(f'حجم البيانات كبير جداً ({size_mb:.1f} ميجابايت). الحد الأقصى 20 ميجابايت. يرجى تقليل عدد الصور أو ضغطها قبل الإرسال.', 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #         # يجب اختيار المركبة أولاً في نسخة الموبايل
    # #         vehicle_id_str = request.form.get('vehicle_id')
    # #         if not vehicle_id_str:
    # #             flash('يجب اختيار مركبة أولاً.', 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile')) # أعد توجيه المستخدم لنفس الصفحة
    
    # #         vehicle = Vehicle.query.get_or_404(int(vehicle_id_str))
    
    # #         unsuitable_statuses = {
    # #             'in_workshop': 'لا يمكن تسليم أو استلام المركبة لأنها حالياً في الورشة.',
    # #             'accident': 'لا يمكن تسليم أو استلام المركبة لأنه مسجل عليها حادث نشط.',
    # #             'out_of_service': 'لا يمكن تسليم أو استلام المركبة لأنها "خارج الخدمة".'
    # #         }
    
    # #         if vehicle.status in unsuitable_statuses:
    # #             flash(f'❌ عملية مرفوضة: {unsuitable_statuses[vehicle.status]}', 'danger')
    # #             # أعد توجيهه إلى صفحة تفاصيل السيارة حيث يمكنه رؤية المشكلة
    # #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    # #         # 3. التحقق من منطق تسليم/استلام (نفس منطقك الحالي ولكن بشكل أنظف)
    # #         handover_type = request.form.get('handover_type')
    # #         if vehicle.status != 'available' and handover_type == 'delivery':
    # #             flash('⚠️ تنبيه: هذه المركبة غير متاحة للتسليم. النموذج تم تعديله لعملية "استلام" تلقائياً.', 'warning')
    # #             # يمكن أن يقوم Javasript في الواجهة بتغيير نوع العملية تلقائياً
    # #             # حالياً سنخبره أن يصحح ويعيد الإرسال
    # #             return redirect(url_for('mobile.create_handover_mobile', handover_id=handover_id))
            
    # #         print(vehicle)
    # #         if vehicle.status != 'available':
    # #                 # تحقق من أن العملية استلام أو تسليم
    # #                 handover_type = request.form.get('handover_type')
    # #                 if handover_type != 'return':
    # #                     flash('هذه المركبة غير متاحة للتسليم. يمكن فقط إجراء عملية استلام.', 'warning')
    # #                     return redirect(url_for('mobile.create_handover_mobile'))
    
    
    # #         # فحص قيود العمليات للمركبات خارج الخدمة
    # #         from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
    # #         restrictions = check_vehicle_operation_restrictions(vehicle)
    # #         if restrictions['blocked']:
    # #             flash(restrictions['message'], 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #         try:
    # #             # === 1. استخراج كل البيانات من النموذج (نفس منطق الويب) ===
    
    # #             # --- البيانات الأساسية للعملية ---
    # #             handover_type = request.form.get('handover_type')
    # #             handover_date_str = request.form.get('handover_date')
    # #             handover_time_str = request.form.get('handover_time')
                
    # #             # --- تحديد ما إذا كنا نعدل سجل موجود أم ننشئ جديد ---
    # #             is_editing = handover_id is not None
    # #             existing_handover = None
    # #             action = request.form.get('action', 'create')  # 'update', 'save_as_new', or 'create'
                
    # #             if is_editing:
    # #                 existing_handover = VehicleHandover.query.get_or_404(handover_id)
                
    # #             # --- معرفات الموظفين (السائق والمشرف) ---
    # #             employee_id_str = request.form.get('employee_id')
    # #             supervisor_employee_id_str = request.form.get('supervisor_employee_id')
    
    # #             # --- البيانات النصية والمتغيرة الأخرى ---
    # #             person_name_from_form = request.form.get('person_name', '').strip()
    # #             supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
    # #             mileage = int(request.form.get('mileage', 0))
    # #             fuel_level = request.form.get('fuel_level')
    # #             project_name = request.form.get('project_name')
    # #             city = request.form.get('city')
    # #             reason_for_change = request.form.get('reason_for_change')
    # #             vehicle_status_summary = request.form.get('vehicle_status_summary')
    # #             notes = request.form.get('notes')
    # #             reason_for_authorization = request.form.get('reason_for_authorization')
    # #             authorization_details = request.form.get('authorization_details')
    # #             movement_officer_name = request.form.get('movement_officer_name')
    # #             form_link = request.form.get('form_link')
    # #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    # #             # --- بيانات قائمة الفحص (Checklist) ---
    # #             has_spare_tire = 'has_spare_tire' in request.form
    # #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    # #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    # #             has_warning_triangle = 'has_warning_triangle' in request.form
    # #             has_tools = 'has_tools' in request.form
    # #             has_oil_leaks = 'has_oil_leaks' in request.form
    # #             has_gear_issue = 'has_gear_issue' in request.form
    # #             has_clutch_issue = 'has_clutch_issue' in request.form
    # #             has_engine_issue = 'has_engine_issue' in request.form
    # #             has_windows_issue = 'has_windows_issue' in request.form
    # #             has_tires_issue = 'has_tires_issue' in request.form
    # #             has_body_issue = 'has_body_issue' in request.form
    # #             has_electricity_issue = 'has_electricity_issue' in request.form
    # #             has_lights_issue = 'has_lights_issue' in request.form
    # #             has_ac_issue = 'has_ac_issue' in request.form
    
    # #             # --- معالجة التواريخ والأوقات ---
    # #             handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
    # #             handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
    # #             # --- معالجة الصور والتواقيع (Base64) والملفات ---
    # #             saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams')
    # #             saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures')
    # #             saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures')
    # #             movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature'), 'signatures')
    
    # #             custom_logo_file = request.files.get('custom_logo_file')
    # #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
    # #             # === 2. جلب الكائنات الكاملة من قاعدة البيانات ===
    # #             driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
    # #             supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
                
    # #             # === 3. إنشاء أو تحديث كائن VehicleHandover ===
    # #             if is_editing and action == 'update':
    # #                 # تحديث السجل الموجود
    # #                 handover = existing_handover
    # #                 handover.vehicle_id = vehicle.id
    # #                 handover.handover_type = handover_type
    # #                 handover.handover_date = handover_date
    # #                 handover.handover_time = handover_time
    # #                 handover.mileage = mileage
    # #                 handover.project_name = project_name
    # #                 handover.city = city
                    
    # #                 # تحديث بيانات المركبة
    # #                 handover.vehicle_car_type = f"{vehicle.make} {vehicle.model}"
    # #                 handover.vehicle_plate_number = vehicle.plate_number
    # #                 handover.vehicle_model_year = str(vehicle.year)
    
    # #                 # تحديث بيانات السائق
    # #                 handover.employee_id = driver.id if driver else None
    # #                 handover.person_name = driver.name if driver else person_name_from_form
    # #                 handover.driver_company_id = driver.employee_id if driver else None
    # #                 handover.driver_phone_number = driver.mobile if driver else None
    # #                 handover.driver_residency_number = driver.national_id if driver else None
    # #                 handover.driver_contract_status = driver.contract_status if driver else None
    # #                 handover.driver_license_status = driver.license_status if driver else None
    # #                 if saved_driver_sig_path:
    # #                     handover.driver_signature_path = saved_driver_sig_path
    
    # #                 # تحديث بيانات المشرف
    # #                 handover.supervisor_employee_id = supervisor.id if supervisor else None
    # #                 handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
    # #                 handover.supervisor_company_id = supervisor.employee_id if supervisor else None
    # #                 handover.supervisor_phone_number = supervisor.mobile if supervisor else None
    # #                 handover.supervisor_residency_number = supervisor.national_id if supervisor else None
    # #                 handover.supervisor_contract_status = supervisor.contract_status if supervisor else None
    # #                 handover.supervisor_license_status = supervisor.license_status if supervisor else None
    # #                 if saved_supervisor_sig_path:
    # #                     handover.supervisor_signature_path = saved_supervisor_sig_path
                    
    # #                 # تحديث باقي الحقول
    # #                 handover.reason_for_change = reason_for_change
    # #                 handover.vehicle_status_summary = vehicle_status_summary
    # #                 handover.notes = notes
    # #                 handover.reason_for_authorization = reason_for_authorization
    # #                 handover.authorization_details = authorization_details
    # #                 handover.fuel_level = fuel_level
                    
    # #                 # تحديث قائمة الفحص
    # #                 handover.has_spare_tire = has_spare_tire
    # #                 handover.has_fire_extinguisher = has_fire_extinguisher
    # #                 handover.has_first_aid_kit = has_first_aid_kit
    # #                 handover.has_warning_triangle = has_warning_triangle
    # #                 handover.has_tools = has_tools
    # #                 handover.has_oil_leaks = has_oil_leaks
    # #                 handover.has_gear_issue = has_gear_issue
    # #                 handover.has_clutch_issue = has_clutch_issue
    # #                 handover.has_engine_issue = has_engine_issue
    # #                 handover.has_windows_issue = has_windows_issue
    # #                 handover.has_tires_issue = has_tires_issue
    # #                 handover.has_body_issue = has_body_issue
    # #                 handover.has_electricity_issue = has_electricity_issue
    # #                 handover.has_lights_issue = has_lights_issue
    # #                 handover.has_ac_issue = has_ac_issue
                    
    # #                 # تحديث الحقول الإضافية
    # #                 handover.movement_officer_name = movement_officer_name
    # #                 if movement_officer_signature_path:
    # #                     handover.movement_officer_signature_path = movement_officer_signature_path
    # #                 if saved_diagram_path:
    # #                     handover.damage_diagram_path = saved_diagram_path
    # #                 handover.form_link = form_link
    # #                 handover.custom_company_name = custom_company_name
    # #                 if saved_custom_logo_path:
    # #                     handover.custom_logo_path = saved_custom_logo_path
    # #             else:
    # #                 # إنشاء سجل جديد (إما إنشاء جديد أو حفظ كنسخة جديدة)
    # #                 handover = VehicleHandover(
    # #                     vehicle_id=vehicle.id,
    # #                     handover_type=handover_type,
    # #                     handover_date=handover_date,
    # #                     handover_time=handover_time,
    # #                     mileage=mileage,
    # #                     project_name=project_name,
    # #                     city=city,
                        
    # #                     # نسخ بيانات المركبة "وقت التسليم"
    # #                     vehicle_car_type=f"{vehicle.make} {vehicle.model}",
    # #                     vehicle_plate_number=vehicle.plate_number,
    # #                     vehicle_model_year=str(vehicle.year),
    
    # #                 # نسخ بيانات السائق "وقت التسليم"
    # #                 employee_id=driver.id if driver else None,
    # #                 person_name=driver.name if driver else person_name_from_form,
    # #                 driver_company_id=driver.employee_id if driver else None,
    # #                 driver_phone_number=driver.mobile if driver else None,
    # #                 driver_residency_number=driver.national_id if driver else None,
    # #                 driver_contract_status=driver.contract_status if driver else None,
    # #                 driver_license_status=driver.license_status if driver else None,
    # #                 driver_signature_path=saved_driver_sig_path,
    
    # #                 # نسخ بيانات المشرف "وقت التسليم"
    # #                 supervisor_employee_id=supervisor.id if supervisor else None,
    # #                 supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
    # #                 supervisor_company_id=supervisor.employee_id if supervisor else None,
    # #                 supervisor_phone_number=supervisor.mobile if supervisor else None,
    # #                 supervisor_residency_number=supervisor.national_id if supervisor else None,
    # #                 supervisor_contract_status=supervisor.contract_status if supervisor else None,
    # #                 supervisor_license_status=supervisor.license_status if supervisor else None,
    # #                 supervisor_signature_path=saved_supervisor_sig_path,
    
    # #                 # باقي الحقول التفصيلية
    # #                 reason_for_change=reason_for_change,
    # #                 vehicle_status_summary=vehicle_status_summary,
    # #                 notes=notes,
    # #                 reason_for_authorization=reason_for_authorization,
    # #                 authorization_details=authorization_details,
    # #                 fuel_level=fuel_level,
    
    # #                 # قائمة الفحص
    # #                 has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
    # #                 has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
    # #                 has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
    # #                 has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
    # #                 has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
    # #                 has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    # #                 has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
    
    # #                 # حقول إضافية
    # #                 movement_officer_name=movement_officer_name,
    # #                 movement_officer_signature_path=movement_officer_signature_path,
    # #                 damage_diagram_path=saved_diagram_path,
    # #                 form_link=form_link,
    # #                 custom_company_name=custom_company_name,
    # #                 custom_logo_path=saved_custom_logo_path
    # #             )
    
    # #             db.session.add(handover)
                
    # #             # تحديث حالة السيارة تلقائياً إلى "متاحة" بعد عملية الاستلام
    # #             if handover_type == 'return':
    # #                 vehicle.status = 'available'
    # #                 vehicle.updated_at = datetime.utcnow()
    # #                 log_audit('update', 'vehicle_status', vehicle.id, 
    # #                          f'تم تحديث حالة السيارة {vehicle.plate_number} إلى "متاحة" بعد عملية الاستلام')
                
    # #             db.session.commit()
    
    # #             # === 4. حفظ المرفقات الإضافية وتحديث حالة السائق ===
    # #             # (استخدام نفس منطق الويب المنظم)
    # #             update_vehicle_driver(vehicle.id) # دالة مساعدة لتحديث السائق المرتبط بالمركبة
    # #             update_vehicle_state(vehicle.id)
    
    # #             files = request.files.getlist('files')
    # #             for file in files:
    # #                 if file and file.filename:
    # #                     file_path, file_type = save_file(file, 'handover')
    # #                     if file_path:
    # #                         file_description = request.form.get(f'description_{file.filename}', '')
    # #                         file_record = VehicleHandoverImage(
    # #                             handover_record_id=handover.id,
    # #                             file_path=file_path, file_type=file_type, file_description=file_description,
    # #                             image_path=file_path, image_description=file_description # للتوافق
    # #                         )
    # #                         db.session.add(file_record)
    # #             db.session.commit()
    
    # #             action_type = 'تسليم' if handover_type == 'delivery' else 'استلام'
    # #             if is_editing and action == 'update':
    # #                 log_audit('update', 'vehicle_handover', handover.id, f'تم تعديل نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم تحديث نموذج {action_type} بنجاح!', 'success')
    # #             elif is_editing and action == 'save_as_new':
    # #                 log_audit('create', 'vehicle_handover', handover.id, f'تم إنشاء نسخة جديدة من نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم حفظ نسخة جديدة من نموذج {action_type} بنجاح!', 'success')
    # #             else:
    # #                 log_audit('create', 'vehicle_handover', handover.id, f'تم إنشاء نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم إنشاء نموذج {action_type} بنجاح!', 'success')
                
    
    # #             # إنشاء طلب عملية تلقائياً لإدارة العمليات
    # #             try:
    # #                 operation_title = f"طلب موافقة على {action_type} مركبة {vehicle.plate_number}"
    # #                 operation_description = f"تم إنشاء {action_type} للمركبة {vehicle.plate_number} من قبل {current_user.username} ويحتاج للموافقة الإدارية"
                    
    # #                 operation = create_operation_request(
    # #                     operation_type="handover",
    # #                     related_record_id=handover.id,
    # #                     vehicle_id=vehicle.id,
    # #                     title=operation_title,
    # #                     description=operation_description,
    # #                     requested_by=current_user.id,
    # #                     priority="normal"
    # #                 )
                    
    # #                 # حفظ طلب العملية والإشعارات
    # #                 db.session.commit()
                    
    # #                 print(f"تم تسجيل عملية {action_type} بنجاح: {operation.id}")
    # #                 current_app.logger.debug(f"تم إنشاء طلب عملية للتسليم والاستلام: {handover.id} برقم عملية: {operation.id}")
                    
    # #                 # التحقق من وجود العملية في قاعدة البيانات
    # #                 saved_operation = OperationRequest.query.get(operation.id)
    # #                 if saved_operation:
    # #                     print(f"تأكيد: عملية {action_type} {operation.id} محفوظة في قاعدة البيانات")
    # #                 else:
    # #                     print(f"تحذير: عملية {action_type} {operation.id} غير موجودة في قاعدة البيانات!")
                    
    # #             except Exception as e:
    # #                 print(f"خطأ في إنشاء طلب العملية للتسليم والاستلام: {str(e)}")
    # #                 current_app.logger.error(f"خطأ في إنشاء طلب العملية للتسليم والاستلام: {str(e)}")
    # #                 import traceback
    # #                 current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
    # #                 # لا نوقف العملية إذا فشل إنشاء طلب العملية
    # #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    # #         except Exception as e:
    # #             db.session.rollback()
    # #             import traceback
    # #             traceback.print_exc()
    # #             flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
    # #             # لا حاجة لإعادة عرض الصفحة مع البيانات، الأفضل إعادة التوجيه مع رسالة خطأ
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #     # === معالجة طلب GET (عند عرض الصفحة لأول مرة) ===
    # #     # جلب القوائم اللازمة لعرضها في النموذج
    # #     vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    
    # #     # جلب الموظفين مع تحميل علاقة الأقسام
    # #     from sqlalchemy.orm import joinedload
    # #     employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    # #     departments = Department.query.order_by(Department.name).all()
    
    # #     # تحويل بيانات الموظفين إلى JSON لاستخدامها في JavaScript
    # #     employees_as_dicts = [e.to_dict() for e in employees]
    # #     now = datetime.now()
    # #     now_date = now.strftime('%Y-%m-%d')
    # #     now_time = now.strftime('%H:%M')
        
    # #     # جلب بيانات التعديل إذا كان موجوداً
    # #     existing_handover = None
    # #     is_editing = False
    # #     if handover_id:
    # #         existing_handover = VehicleHandover.query.get(handover_id)
    # #         if existing_handover:
    # #             is_editing = True
    # #             # استخدام بيانات السجل الموجود للتاريخ والوقت
    # #             now_date = existing_handover.handover_date.strftime('%Y-%m-%d') if existing_handover.handover_date else now_date
    # #             now_time = existing_handover.handover_time.strftime('%H:%M') if existing_handover.handover_time else now_time
    # #             # تحويل الكائن إلى قاموس للاستخدام في JavaScript
    # #             existing_handover = existing_handover.to_dict()
        
    # #     return render_template(
    # #         'mobile/vehicle_checklist.html', 
    # #         vehicles=vehicles,
    # #         employees=employees,
    # #         departments=departments,
    # #         handover_types=HANDOVER_TYPE_CHOICES, # استخدام نفس قائمة الويب
    # #         employeeData=employees_as_dicts,
    # #         now_date=now_date,
    # #         now_time=now_time,
    # #         existing_handover=existing_handover,  # تمرير بيانات التعديل
    # #         is_editing=is_editing  # تمرير حالة التعديل
    # #     )
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # # @login_required
    # # def create_handover_mobile():
    # #     """
    # #     عرض ومعالجة نموذج تسليم/استلام السيارة (نسخة الهواتف المحمولة).
    # #     """
    # #      # 1. جلب البيانات الأساسية
    # #     vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    
    # #     # 1. معالجة إرسال النموذج (POST request)
    # #     if request.method == 'POST':
    # #         try:
    # #             vehicle_id = request.form.get('vehicle_id')
    # #             if not vehicle_id:
    # #                 flash('يجب اختيار مركبة أولاً.', 'danger')
    
    # #                 # إعادة تحميل الصفحة مع البيانات القديمة (سنتعامل مع هذا لاحقاً إذا لزم الأمر)
    
    # #             # --- استخراج البيانات من النموذج ---
    # #             # القسم 1: معلومات أساسية
    # #             handover_type = request.form.get('handover_type')
    # #             handover_date = datetime.strptime(request.form.get('handover_date'), '%Y-%m-%d').date()
    # #             mileage = int(request.form.get('mileage'))
    # #             fuel_level = request.form.get('fuel_level')
    # #             person_name = request.form.get('person_name')
    # #             employee_id = request.form.get('employee_id')
    
    # #             # القسم 2: فحص وتجهيزات
    # #             # التجهيزات
    # #             has_spare_tire = 'has_spare_tire' in request.form
    # #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    # #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    # #             has_warning_triangle = 'has_warning_triangle' in request.form
    # #             has_tools = 'has_tools' in request.form
    # #             # فحص المشاكل
    # #             has_oil_leaks = 'has_oil_leaks' in request.form
    # #             has_gear_issue = 'has_gear_issue' in request.form
    # #             has_clutch_issue = 'has_clutch_issue' in request.form
    # #             has_engine_issue = 'has_engine_issue' in request.form
    # #             has_ac_issue = 'has_ac_issue' in request.form
    # #             has_windows_issue = 'has_windows_issue' in request.form
    # #             has_tires_issue = 'has_tires_issue' in request.form
    # #             has_body_issue = 'has_body_issue' in request.form
    # #             has_electricity_issue = 'has_electricity_issue' in request.form
    # #             has_lights_issue = 'has_lights_issue' in request.form
    
    # #             # القسم 4: ملاحظات وتوثيق
    # #             vehicle_condition = request.form.get('vehicle_condition')
    # #             notes = request.form.get('notes')
    # #             form_link = request.form.get('form_link')
    
    # #             # القسم 5: تخصيص التقرير
    # #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    # #             # --- معالجة الملفات المرفوعة والتواقيع المرسومة ---
    # #             # (سنستخدم نفس الدوال المساعدة التي أنشأناها سابقاً)
    # #             custom_logo_file = request.files.get('custom_logo_file')
    # #             damage_diagram_base64 = request.form.get('damage_diagram_data')
    # #             supervisor_sig_base64 = request.form.get('supervisor_signature_data')
    # #             driver_sig_base64 = request.form.get('driver_signature_data')
    
    # #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    # #             saved_diagram_path = save_base64_image(damage_diagram_base64, 'diagrams')
    # #             saved_supervisor_sig_path = save_base64_image(supervisor_sig_base64, 'signatures')
    # #             saved_driver_sig_path = save_base64_image(driver_sig_base64, 'signatures')
    
    # #             # --- إنشاء السجل في قاعدة البيانات ---
    # #             new_handover = VehicleHandover(
    # #                 vehicle_id=int(vehicle_id),
    # #                 handover_type=handover_type,
    # #                 handover_date=handover_date,
    # #                 mileage=mileage,
    # #                 fuel_level=fuel_level,
    # #                 person_name=person_name,
    # #                 employee_id=int(employee_id) if employee_id else None,
    # #                 # التجهيزات
    # #                 has_spare_tire=has_spare_tire,
    # #                 has_fire_extinguisher=has_fire_extinguisher,
    # #                 has_first_aid_kit=has_first_aid_kit,
    # #                 has_warning_triangle=has_warning_triangle,
    # #                 has_tools=has_tools,
    # #                 # فحص المشاكل
    # #                 has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue, has_clutch_issue=has_clutch_issue,
    # #                 has_engine_issue=has_engine_issue, has_ac_issue=has_ac_issue, has_windows_issue=has_windows_issue,
    # #                 has_tires_issue=has_tires_issue, has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    # #                 has_lights_issue=has_lights_issue,
    # #                 # التوثيق
    # #                 vehicle_condition=vehicle_condition, notes=notes, form_link=form_link,
    # #                 # التخصيص
    # #                 custom_company_name=custom_company_name,
    # #                 custom_logo_path=saved_custom_logo_path,
    # #                 # الصور المحفوظة
    # #                 damage_diagram_path=saved_diagram_path,
    # #                 supervisor_signature_path=saved_supervisor_sig_path,
    # #                 driver_signature_path=saved_driver_sig_path
    # #             )
    
    # #             db.session.add(new_handover)
    # #             db.session.commit()
    
    # #             # معالجة رفع الملفات المتعددة
    # #             files = request.files.getlist('files')
    # #             for file in files:
    # #                 # استخدم دالة حفظ الملفات التي لديك
    # #                 saved_path, file_type = save_file(file, 'handover_docs')
    # #                 if saved_path:
    # #                     # احفظ المسار في جدول الملفات المرتبط
    # #                     pass # أضف هنا منطق حفظ الملفات في جدول VehicleHandoverImage
    
    # #             # تحديث حالة السيارة إذا لزم الأمر
    # #             vehicle = Vehicle.query.get_or_404(vehicle_id)
    # #             if handover_type == 'return': vehicle.status = 'available'
    # #             elif handover_type == 'delivery': vehicle.status = 'in_project'
    # #             db.session.commit()
    
    # #             flash('تم حفظ النموذج بنجاح!', 'success')
    # #             return redirect(url_for('mobile.vehicle_checklist_list', id=id))
    
    # #         except Exception as e:
    # #             db.session.rollback()
    # #             flash(f'حدث خطأ أثناء حفظ النموذج: {e}', 'danger')
    
    
    
    
    # #     # 2. جلب القوائم اللازمة للنموذج (الموظفين، الأقسام)
    # #     # من الأفضل جلبها دائماً لتعمل واجهة البحث بشكل صحيح
    # #     employees = Employee.query.order_by(Employee.name).all()
    # #     departments = Department.query.order_by(Department.name).all()
    
    # #     # 3. تعريف أنواع العمليات كنص удобочитаемый
    # #     handover_types = {
    # #         'delivery': 'تسليم سيارة جديدة',
    # #         'return': 'استلام سيارة عائدة'
    # #     }
    
    # #     # 3. تحديد نوع العملية الافتراضي (إذا تم تمريره كمعلمة)
    # #     # هذا مفيد إذا أتيت من زر "تسليم" أو "استلام" محدد
    
    # #     # تعريف أنواع العمليات كنص удобочитаемый
    # #     handover_types = {
    # #         'delivery': 'تسليم السيارة',
    # #         'return': 'استلام السيارة'
    # #         # يمكنك إضافة أنواع أخرى هنا مثل 'receive_from_workshop'
    # #     }
    
    # #     # في أعلى ملف الـ routes
    
    # #       # داخل دالة create_handover_mobile، عند استدعاء render_template
    # #     # الكود الجديد والأبسط في route
    # #     employees_as_dicts = [e.to_dict() for e in employees]
    
    # #    # 4. عرض القالب وتمرير قائمة المركبات إليه
    
    # #     # 5. عرض القالب للـ GET request
    # #     return render_template(
    # #         'mobile/vehicle_checklist.html',
    # #         vehicles=vehicles, # <<-- المتغير الجديد والمهم
    # #         employees=employees,
    # #         departments=departments,
    # #         handover_types=handover_types,
    # #         employeeData=employees_as_dicts # إرسال البيانات كقائمة من القواميس
    # #     )
    
    
    
    
    
    
    # # قائمة فحوصات السيارة - النسخة المحمولة
    # @bp.route('/vehicles/checklist/list')
    # @login_required
    # def vehicle_checklist_list():
    #     """قائمة فحوصات السيارة للنسخة المحمولة"""
    #     page = request.args.get('page', 1, type=int)
    #     per_page = 20  # عدد العناصر في الصفحة الواحدة
    
    #     # فلترة حسب السيارة
    #     vehicle_id = request.args.get('vehicle_id', '')
    #     # فلترة حسب نوع الفحص
    #     inspection_type = request.args.get('inspection_type', '')
    #     # فلترة حسب التاريخ
    #     from_date = request.args.get('from_date', '')
    #     to_date = request.args.get('to_date', '')
    
    #     # بناء استعلام قاعدة البيانات
    #     query = VehicleChecklist.query
    
    #     # تطبيق الفلاتر إذا تم تحديدها
    #     if vehicle_id:
    #         query = query.filter(VehicleChecklist.vehicle_id == vehicle_id)
    
    #     if inspection_type:
    #         query = query.filter(VehicleChecklist.inspection_type == inspection_type)
    
    #     if from_date:
    #         try:
    #             from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
    #             query = query.filter(VehicleChecklist.inspection_date >= from_date_obj)
    #         except ValueError:
    #             pass
    
    #     if to_date:
    #         try:
    #             to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    #             query = query.filter(VehicleChecklist.inspection_date <= to_date_obj)
    #         except ValueError:
    #             pass
    
    #     # تنفيذ الاستعلام مع الترتيب والتصفح
    #     paginator = query.order_by(VehicleChecklist.inspection_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    #     checklists = paginator.items
    
    #     # الحصول على بيانات السيارات لعرضها في القائمة
    #     vehicles = Vehicle.query.all()
    
    #     print(vehicles)
    
    #     # تحويل بيانات الفحوصات إلى تنسيق مناسب للعرض
    #     checklists_data = []
    #     for checklist in checklists:
    #         vehicle = Vehicle.query.get(checklist.vehicle_id)
    #         if vehicle:
    #             checklist_data = {
    #                 'id': checklist.id,
    #                 'vehicle_name': f"{vehicle.make} {vehicle.model}",
    #                 'vehicle_plate': vehicle.plate_number,
    #                 'inspection_date': checklist.inspection_date,
    #                 'inspection_type': checklist.inspection_type,
    #                 'inspector_name': checklist.inspector_name,
    #                 'status': checklist.status,
    #                 'completion_percentage': checklist.completion_percentage,
    #                 'summary': checklist.summary
    #             }
    #             checklists_data.append(checklist_data)
    
    #     return render_template('mobile/vehicle_checklist_list.html',
    #                           checklists=checklists_data,
    #                           pagination=paginator,
    #                           vehicles=vehicles,
    #                           selected_vehicle=vehicle_id,
    #                           selected_type=inspection_type,
    #                           from_date=from_date,
    #                           to_date=to_date)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # # تفاصيل فحص السيارة - النسخة المحمولة
    # @bp.route('/vehicles/checklist/<int:checklist_id>')
    # @login_required
    # def vehicle_checklist_details(checklist_id):
    #     """تفاصيل فحص السيارة للنسخة المحمولة"""
    #     # الحصول على بيانات الفحص من قاعدة البيانات
    #     checklist = VehicleChecklist.query.get_or_404(checklist_id)
    
        
    #     # الحصول على بيانات السيارة وإضافة تحذير عند المراجعة
    #     vehicle = Vehicle.query.get(checklist.vehicle_id)
        
    #     # فحص حالة السيارة لإضافة تحذير في واجهة المراجعة
    #     from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
    #     restrictions = check_vehicle_operation_restrictions(vehicle)
    #     vehicle_warning = restrictions['message'] if restrictions['blocked'] else None
        
    
    #     # جمع بيانات عناصر الفحص مرتبة حسب الفئة
    #     checklist_items = {}
    #     for item in checklist.checklist_items:
    #         if item.category not in checklist_items:
    #             checklist_items[item.category] = []
    
    #         checklist_items[item.category].append(item)
    
    #     # الحصول على علامات التلف المرتبطة بهذا الفحص
    #     damage_markers = VehicleDamageMarker.query.filter_by(checklist_id=checklist_id).all()
    
    #     # الحصول على صور الفحص المرفقة
    #     checklist_images = VehicleChecklistImage.query.filter_by(checklist_id=checklist_id).all()
    
    #     return render_template('mobile/vehicle_checklist_details.html',
    #                           checklist=checklist,
    #                           vehicle=vehicle,
    #                           checklist_items=checklist_items,
    #                           damage_markers=damage_markers,
    #                           checklist_images=checklist_images,
    #                           vehicle_warning=vehicle_warning)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # تصدير فحص السيارة إلى PDF - النسخة المحمولة
    @bp.route('/vehicles/checklist/<int:checklist_id>/pdf')
    @login_required
    def mobile_vehicle_checklist_pdf(checklist_id):
        """تصدير تقرير فحص المركبة إلى PDF مع عرض علامات التلف"""
        try:
            # الحصول على بيانات الفحص
            checklist = VehicleChecklist.query.get_or_404(checklist_id)
    
            
            # الحصول على بيانات المركبة وفحص حالتها
            vehicle = Vehicle.query.get_or_404(checklist.vehicle_id)
            
            # فحص حالة السيارة - إضافة تحذير للسيارات خارج الخدمة
            from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
            restrictions = check_vehicle_operation_restrictions(vehicle)
            if restrictions['blocked']:
                print(f"تحذير: {restrictions['message']}")
            
    
            # جمع بيانات عناصر الفحص مرتبة حسب الفئة
            checklist_items = {}
            for item in checklist.checklist_items:
                if item.category not in checklist_items:
                    checklist_items[item.category] = []
    
                checklist_items[item.category].append(item)
    
            # الحصول على علامات التلف المرتبطة بهذا الفحص
            damage_markers = VehicleDamageMarker.query.filter_by(checklist_id=checklist_id).all()
    
            # الحصول على صور الفحص المرفقة
            checklist_images = VehicleChecklistImage.query.filter_by(checklist_id=checklist_id).all()
    
            # استيراد تابع إنشاء PDF
            from utils.vehicle_checklist_pdf import create_vehicle_checklist_pdf
    
            # إنشاء ملف PDF
            pdf_buffer = create_vehicle_checklist_pdf(
                checklist=checklist,
                vehicle=vehicle,
                checklist_items=checklist_items,
                damage_markers=damage_markers,
                checklist_images=checklist_images
            )
    
            # إنشاء استجابة تحميل للملف
            from flask import make_response
            response = make_response(pdf_buffer.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=vehicle_checklist_{checklist_id}.pdf'
    
            return response
    
        except Exception as e:
            # تسجيل الخطأ للمساعدة في تشخيص المشكلة
            import traceback
            error_traceback = traceback.format_exc()
            app.logger.error(f"خطأ في إنشاء PDF لفحص المركبة: {str(e)}\n{error_traceback}")
            flash(f'حدث خطأ أثناء إنشاء ملف PDF: {str(e)}', 'danger')
            return redirect(url_for('mobile.vehicle_checklist_details', checklist_id=checklist_id))
    
    
    # صفحة الرسوم والتكاليف - النسخة المحمولة (النسخة الأصلية)
    @bp.route('/fees_old')
    @login_required
    def fees_old():
        """صفحة الرسوم والتكاليف للنسخة المحمولة (النسخة القديمة)"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # فلترة حسب نوع الوثيقة
        document_type = request.args.get('document_type', '')
        # فلترة حسب حالة الرسوم
        status = request.args.get('status', '')
        # فلترة حسب التاريخ
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
    
        # بناء استعلام قاعدة البيانات
        query = Fee.query
    
        # تطبيق الفلاتر إذا تم تحديدها
        if document_type:
            query = query.filter(Fee.document_type == document_type)
    
        if status:
            query = query.filter(Fee.payment_status == status)
    
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                query = query.filter(Fee.due_date >= from_date_obj)
            except ValueError:
                pass
    
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                query = query.filter(Fee.due_date <= to_date_obj)
            except ValueError:
                pass
    
        # تنفيذ الاستعلام مع الترتيب والتصفح
        paginator = query.order_by(Fee.due_date.asc()).paginate(page=page, per_page=per_page, error_out=False)
        fees = paginator.items
    
        # الحصول على أنواع الوثائق المتاحة
        document_types = db.session.query(Fee.document_type).distinct().all()
        document_types = [d[0] for d in document_types if d[0]]
    
        # حساب إجماليات الرسوم
        all_fees = query.all()
        fees_summary = {
            'pending_fees': sum(fee.total_fees for fee in all_fees if fee.payment_status == 'pending'),
            'paid_fees': sum(fee.total_fees for fee in all_fees if fee.payment_status == 'paid'),
            'total_fees': sum(fee.total_fees for fee in all_fees)
        }
    
        return render_template('mobile/fees.html', 
                              fees=fees, 
                              fees_summary=fees_summary,
                              pagination=paginator,
                              document_types=document_types,
                              selected_type=document_type,
                              selected_status=status,
                              from_date=from_date,
                              to_date=to_date)
    
    # إضافة رسم جديد - النسخة المحمولة
    @bp.route('/fees/add', methods=['GET', 'POST'])
    @login_required
    def add_fee():
        """إضافة رسم جديد للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/add_fee.html')
    
    # تعديل رسم - النسخة المحمولة
    @bp.route('/fees/<int:fee_id>/edit', methods=['POST'])
    @login_required
    def edit_fee(fee_id):
        """تعديل رسم قائم للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        if request.method == 'POST':
            # تحديث بيانات الرسم من النموذج
            fee.document_type = request.form.get('document_type')
    
            # تحديث تاريخ الاستحقاق
            due_date_str = request.form.get('due_date')
            if due_date_str:
                fee.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    
            # تحديث حالة الدفع
            fee.payment_status = request.form.get('payment_status')
    
            # تحديث تاريخ السداد إذا كانت الحالة "مدفوع"
            if fee.payment_status == 'paid':
                payment_date_str = request.form.get('payment_date')
                if payment_date_str:
                    fee.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            else:
                fee.payment_date = None
    
            # تحديث قيم الرسوم
            fee.passport_fee = float(request.form.get('passport_fee', 0))
            fee.labor_office_fee = float(request.form.get('labor_office_fee', 0))
            fee.insurance_fee = float(request.form.get('insurance_fee', 0))
            fee.social_insurance_fee = float(request.form.get('social_insurance_fee', 0))
    
            # تحديث حالة نقل الكفالة
            fee.transfer_sponsorship = 'transfer_sponsorship' in request.form
    
            # تحديث الملاحظات
            fee.notes = request.form.get('notes', '')
    
            # حفظ التغييرات في قاعدة البيانات
            try:
                db.session.commit()
                flash('تم تحديث الرسم بنجاح', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث الرسم: {str(e)}', 'danger')
    
        # العودة إلى صفحة تفاصيل الرسم
        return redirect(url_for('mobile.fee_details', fee_id=fee_id))
    
    # تسجيل رسم كمدفوع - النسخة المحمولة
    @bp.route('/fees/<int:fee_id>/mark-as-paid', methods=['POST'])
    @login_required
    def mark_fee_as_paid(fee_id):
        """تسجيل رسم كمدفوع للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        if request.method == 'POST':
            # تحديث حالة الدفع
            fee.payment_status = 'paid'
    
            # تحديث تاريخ السداد
            payment_date_str = request.form.get('payment_date')
            if payment_date_str:
                fee.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            else:
                fee.payment_date = datetime.now().date()
    
            # إضافة ملاحظات السداد إلى ملاحظات الرسم
            payment_notes = request.form.get('payment_notes')
            if payment_notes:
                if fee.notes:
                    fee.notes = f"{fee.notes}\n\nملاحظات السداد ({fee.payment_date}):\n{payment_notes}"
                else:
                    fee.notes = f"ملاحظات السداد ({fee.payment_date}):\n{payment_notes}"
    
            # حفظ التغييرات في قاعدة البيانات
            try:
                db.session.commit()
                flash('تم تسجيل الرسم كمدفوع بنجاح', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تسجيل الرسم كمدفوع: {str(e)}', 'danger')
    
        # العودة إلى صفحة تفاصيل الرسم
        return redirect(url_for('mobile.fee_details', fee_id=fee_id))
    
    # تفاصيل الرسم - النسخة المحمولة 
    @bp.route('/fees/<int:fee_id>')
    @login_required
    def fee_details(fee_id):
        """تفاصيل الرسم للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        # إرسال التاريخ الحالي لاستخدامه في النموذج
        now = datetime.now()
    
        return render_template('mobile/fee_details.html', fee=fee, now=now)
    
    # صفحة الإشعارات - النسخة المحمولة
    @bp.route('/notifications')
    def notifications():
        """صفحة الإشعارات للنسخة المحمولة"""
        # إنشاء بيانات إشعارات تجريبية
        notifications = [
            {
                'id': '1',
                'type': 'document',
                'title': 'وثيقة على وشك الانتهاء: جواز سفر',
                'message': 'متبقي 10 أيام على انتهاء جواز السفر',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': False
            },
            {
                'id': '2',
                'type': 'fee',
                'title': 'رسوم مستحقة قريباً: تأشيرة',
                'message': 'رسوم مستحقة بعد 5 أيام بقيمة 2000.00',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': False
            },
            {
                'id': '3',
                'type': 'system',
                'title': 'تحديث في النظام',
                'message': 'تم تحديث النظام إلى الإصدار الجديد',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': True
            }
        ]
    
        pagination = {
            'page': 1,
            'per_page': 20,
            'total': len(notifications),
            'pages': 1,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None,
            'iter_pages': lambda: range(1, 2)
        }
    
        return render_template('mobile/notifications.html',
                              notifications=notifications,
                              pagination=pagination)
    
    # API endpoint لتعليم إشعار كمقروء
    @bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
    def mark_notification_as_read(notification_id):
        """تعليم إشعار كمقروء"""
        # في الإصدار الحقيقي سيتم حفظ حالة قراءة الإشعارات في قاعدة البيانات
    
        # للإصدار الحالي البسيط نستخدم session لتخزين الإشعارات المقروءة
        read_notifications = session.get('read_notifications', [])
    
        if notification_id not in read_notifications:
            read_notifications.append(notification_id)
            session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # API endpoint لتعليم جميع الإشعارات كمقروءة
    @bp.route('/api/notifications/read-all', methods=['POST'])
    def mark_all_notifications_as_read():
        """تعليم جميع الإشعارات كمقروءة"""
        # في الإصدار التجريبي، نعلم فقط الإشعارات التجريبية كمقروءة
        read_notifications = ['1', '2', '3']
        session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # API endpoint لحذف إشعار
    @bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
    def delete_notification(notification_id):
        """حذف إشعار"""
        # في الإصدار الحقيقي سيتم حذف الإشعار من قاعدة البيانات أو تحديث حالته
    
        # للإصدار الحالي البسيط نستخدم session لتخزين الإشعارات المحذوفة
        deleted_notifications = session.get('deleted_notifications', [])
    
        if notification_id not in deleted_notifications:
            deleted_notifications.append(notification_id)
            session['deleted_notifications'] = deleted_notifications
    
        # إذا كان الإشعار مقروءاً، نحذفه من قائمة الإشعارات المقروءة
        read_notifications = session.get('read_notifications', [])
        if notification_id in read_notifications:
            read_notifications.remove(notification_id)
            session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # صفحة الإعدادات - النسخة المحمولة
    @bp.route('/settings')
    @login_required
    def settings():
        """صفحة الإعدادات للنسخة المحمولة"""
        current_year = datetime.now().year
        return render_template('mobile/settings.html', current_year=current_year)
    
    # صفحة شروط الاستخدام - النسخة المحمولة
    @bp.route('/terms')
    def terms():
        """صفحة شروط الاستخدام للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/terms.html')
    
    # صفحة سياسة الخصوصية - النسخة المحمولة
    @bp.route('/privacy')
    def privacy():
        """صفحة سياسة الخصوصية للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/privacy.html')
    
    # صفحة تواصل معنا - النسخة المحمولة
    @bp.route('/contact')
    def contact():
        """صفحة تواصل معنا للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/contact.html')
    
    # صفحة التطبيق غير متصل بالإنترنت - النسخة المحمولة
    @bp.route('/offline')
    def offline():
        """صفحة التطبيق غير متصل بالإنترنت للنسخة المحمولة"""
        return render_template('mobile/offline.html')
    
    # نقطة نهاية للتحقق من حالة الاتصال - النسخة المحمولة
    @bp.route('/api/check-connection')
    def check_connection():
        """نقطة نهاية للتحقق من حالة الاتصال والتتبع للنسخة المحمولة"""
        try:
            # ✅ التحقق من اتصال قاعدة البيانات
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            
            return jsonify({
                'status': 'online',
                'tracking_status': 'active',
                'database': 'connected',
                'timestamp': datetime.now().isoformat(),
                'message': 'تطبيق النُظم جاهز'
            }), 200
        except Exception as e:
            # ❌ في حالة فشل الاتصال
            current_app.logger.error(f"Connection check failed: {str(e)}")
            return jsonify({
                'status': 'offline',
                'tracking_status': 'stopped',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
    
    
    @bp.route('/api/tracking-status/<int:employee_id>')
    def tracking_status(employee_id):
        """الحصول على حالة التتبع والموقع الحالي للموظف"""
        try:
            employee = Employee.query.get(employee_id)
            if not employee:
                return jsonify({
                    'success': False,
                    'tracking_status': 'unknown',
                    'error': 'الموظف غير موجود'
                }), 404
            
            # جلب آخر موقع
            latest_location = EmployeeLocation.query.filter_by(
                employee_id=employee_id
            ).order_by(EmployeeLocation.recorded_at.desc()).first()
            
            # جلب آخر جلسة جيوفنس
            from models import GeofenceSession
            latest_session = GeofenceSession.query.filter_by(
                employee_id=employee_id
            ).order_by(GeofenceSession.entry_time.desc()).first()
            
            tracking_active = latest_location is not None and (
                datetime.utcnow() - latest_location.recorded_at
            ).total_seconds() < 3600  # آخر ساعة
            
            return jsonify({
                'success': True,
                'tracking_status': 'active' if tracking_active else 'inactive',
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'employee_id': employee.employee_id
                },
                'location': {
                    'latitude': float(latest_location.latitude) if latest_location else None,
                    'longitude': float(latest_location.longitude) if latest_location else None,
                    'accuracy': float(latest_location.accuracy_m) if latest_location and latest_location.accuracy_m else None,
                    'recorded_at': latest_location.recorded_at.isoformat() if latest_location else None
                } if latest_location else None,
                'session': {
                    'entry_time': latest_session.entry_time.isoformat() if latest_session else None,
                    'exit_time': latest_session.exit_time.isoformat() if latest_session else None
                } if latest_session else None,
                'timestamp': datetime.now().isoformat()
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error getting tracking status: {str(e)}")
            return jsonify({
                'success': False,
                'tracking_status': 'error',
                'error': str(e)
            }), 500
    
    
    # تم حذف صفحة مصروفات الوقود كما هو مطلوب
    
    
    # ==================== مسارات إدارة المستخدمين - النسخة المحمولة المطورة ====================
    
    # صفحة إدارة المستخدمين - النسخة المحمولة المطورة
    @bp.route('/users_new')
    @login_required
    @module_access_required('users')
    def users_new():
        """صفحة إدارة المستخدمين للنسخة المحمولة المطورة"""
    
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # إنشاء الاستعلام الأساسي
        query = User.query
    
        # تطبيق الفلترة حسب الاستعلام
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(
                (User.name.like(search_term)) |
                (User.email.like(search_term))
            )
    
        # ترتيب النتائج
        query = query.order_by(User.name)
    
        # تنفيذ الاستعلام مع الصفحات
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
    
        return render_template('mobile/users_new.html',
                              users=users,
                              pagination=pagination)
    
    # إضافة مستخدم جديد - النسخة المحمولة المطورة
    @bp.route('/users_new/add', methods=['GET', 'POST'])
    @login_required
    @module_access_required('users')
    def add_user_new():
        """إضافة مستخدم جديد للنسخة المحمولة المطورة"""
    
        # معالجة النموذج المرسل
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
    
            # التحقق من البيانات المطلوبة
            if not (username and email and password and role):
                flash('جميع الحقول المطلوبة يجب ملؤها', 'danger')
                return render_template('mobile/add_user_new.html', roles=UserRole)
    
            # التحقق من عدم وجود البريد الإلكتروني مسبقاً
            if User.query.filter_by(email=email).first():
                flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                return render_template('mobile/add_user_new.html', roles=UserRole)
    
            # إنشاء مستخدم جديد
            new_user = User(
                username=username,
                email=email,
                role=role
            )
            new_user.set_password(password)
    
            try:
                db.session.add(new_user)
                db.session.commit()
    
                flash('تم إضافة المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.users_new'))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إضافة المستخدم: {str(e)}', 'danger')
    
        # عرض النموذج
        return render_template('mobile/add_user_new.html', roles=UserRole)
    
    # تفاصيل المستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>')
    @login_required
    @module_access_required('users')
    def user_details_new(user_id):
        """تفاصيل المستخدم للنسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        return render_template('mobile/user_details_new.html', user=user)
    
    # تعديل بيانات المستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>/edit', methods=['GET', 'POST'])
    @login_required
    @module_access_required('users')
    def edit_user_new(user_id):
        """تعديل بيانات المستخدم للنسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        # معالجة النموذج المرسل
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            role = request.form.get('role')
            is_active = request.form.get('is_active') == 'on'
    
            # التحقق من البيانات المطلوبة
            if not (username and email and role):
                flash('جميع الحقول المطلوبة يجب ملؤها', 'danger')
                return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
            # التحقق من عدم وجود البريد الإلكتروني لمستخدم آخر
            email_user = User.query.filter_by(email=email).first()
            if email_user and email_user.id != user.id:
                flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
            # تحديث بيانات المستخدم
            user.name = username
            user.email = email
            user.role = role
            user.is_active = is_active
    
            # تحديث كلمة المرور إذا تم تقديمها
            new_password = request.form.get('password')
            if new_password:
                user.set_password(new_password)
    
            try:
                db.session.commit()
                flash('تم تحديث بيانات المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.user_details_new', user_id=user.id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث بيانات المستخدم: {str(e)}', 'danger')
    
        # عرض النموذج
        return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
    # حذف مستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>/delete', methods=['GET', 'POST'])
    @login_required
    @permission_required('users', 'delete')
    def delete_user_new(user_id):
        """حذف مستخدم من النسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        # منع حذف المستخدم الحالي
        if user.id == current_user.id:
            flash('لا يمكنك حذف المستخدم الحالي', 'danger')
            return redirect(url_for('mobile.users_new'))
    
        if request.method == 'POST':
            try:
                # حذف المستخدم
                db.session.delete(user)
                db.session.commit()
    
                flash('تم حذف المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.users_new'))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء حذف المستخدم: {str(e)}', 'danger')
                return redirect(url_for('mobile.user_details_new', user_id=user.id))
    
        return render_template('mobile/delete_user_new.html', user=user)
    
    
    # ==================== مسارات الرسوم والتكاليف - النسخة المحمولة المطورة ====================
    
    # صفحة إدارة الرسوم والتكاليف - النسخة المحمولة المطورة
    @bp.route('/fees_new')
    @login_required
    @module_access_required('fees')
    def fees_new():
        """صفحة الرسوم والتكاليف للنسخة المحمولة المطورة"""
    
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
        status = request.args.get('status', 'all')
        document_type = request.args.get('document_type', 'all')
    
        # إنشاء الاستعلام الأساسي
        query = Fee.query.join(Document)
    
        # تطبيق الفلاتر
        if status != 'all':
            query = query.filter(Fee.payment_status == status)
    
        if document_type != 'all':
            query = query.filter(Fee.document_type == document_type)
    
        # البحث
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.join(Document.employee).filter(
                (Employee.name.like(search_term)) |
                (Employee.employee_id.like(search_term)) |
                (Document.document_number.like(search_term))
            )
    
        # ترتيب النتائج حسب تاريخ الاستحقاق (الأقرب أولاً)
        query = query.order_by(Fee.due_date)
    
        # تنفيذ الاستعلام مع الصفحات
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        fees = pagination.items
    
        # حساب إحصائيات الرسوم
        current_date = datetime.now().date()
        due_count = Fee.query.filter(Fee.due_date <= current_date, Fee.payment_status == 'pending').count()
        paid_count = Fee.query.filter(Fee.payment_status == 'paid').count()
        overdue_count = Fee.query.filter(Fee.due_date < current_date, Fee.payment_status == 'pending').count()
    
        stats = {
            'due': due_count,
            'paid': paid_count,
            'overdue': overdue_count,
            'total': Fee.query.count()
        }
    
        # أنواع الوثائق للفلترة
        document_types = [
            'هوية وطنية',
            'إقامة',
            'جواز سفر',
            'رخصة قيادة',
            'شهادة صحية',
            'شهادة تأمين',
            'أخرى'
        ]
    
        return render_template('mobile/fees_new.html',
                              fees=fees,
                              pagination=pagination,
                              stats=stats,
                              document_types=document_types,
                              current_date=current_date,
                              selected_status=status,
                              selected_document_type=document_type)
    
    # ==================== مسارات الإشعارات - النسخة المحمولة المطورة ====================
    
    @bp.route('/notifications_new')
    @login_required
    def notifications_new():
        """صفحة الإشعارات للنسخة المحمولة المطورة"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # هنا يمكن تنفيذ استعلام الإشعارات بناءً على نظام الإشعارات المستخدم
    
        # مثال: استعلام للوثائق التي على وشك الانتهاء كإشعارات
        current_date = datetime.now().date()
        expiring_30_days = current_date + timedelta(days=30)
        expiring_documents = Document.query.filter(
            Document.expiry_date > current_date,
            Document.expiry_date <= expiring_30_days
        ).order_by(Document.expiry_date).all()
    
        # مثال: الرسوم المستحقة (استخدام النموذج المتاح Fee المستورد من FeesCost)
        # ملاحظة: تم تعديل هذا الجزء لاستخدام النموذج المتاح بدلاً من الأصلي
        due_fees = Fee.query.join(Document).filter(
            Document.expiry_date > current_date,
            Document.expiry_date <= current_date + timedelta(days=30)
        ).order_by(Document.expiry_date).all()
    
        # تحضير قائمة الإشعارات المدمجة
        notifications = []
    
        for doc in expiring_documents:
            remaining_days = (doc.expiry_date - current_date).days
            notifications.append({
                'id': f'doc_{doc.id}',
                'type': 'document',
                'title': f'وثيقة على وشك الانتهاء: {doc.document_type}',
                'description': f'متبقي {remaining_days} يوم على انتهاء {doc.document_type} للموظف {doc.employee.name}',
                'date': doc.expiry_date,
                'url': url_for('mobile.document_details', document_id=doc.id),
                'is_read': False  # يمكن تنفيذ حالة القراءة لاحقاً
            })
    
        for fee in due_fees:
            # استخدام تاريخ انتهاء الوثيقة المرتبطة بالرسوم
            doc = Document.query.get(fee.document_id)
            if not doc:
                continue
    
            remaining_days = (doc.expiry_date - current_date).days
            document_type = fee.document_type
            total_amount = sum([
                fee.passport_fee or 0,
                fee.labor_office_fee or 0,
                fee.insurance_fee or 0,
                fee.social_insurance_fee or 0
            ])
            notifications.append({
                'id': f'fee_{fee.id}',
                'type': 'fee',
                'title': f'رسوم مستحقة قريباً: {document_type}',
                'description': f'رسوم مستحقة بعد {remaining_days} يوم بقيمة {total_amount:.2f}',
                'date': doc.expiry_date,
                'url': url_for('mobile.fee_details', fee_id=fee.id),
                'is_read': False
            })
    
        # ترتيب الإشعارات حسب التاريخ (الأقرب أولاً)
        notifications.sort(key=lambda x: x['date'])
    
        # تقسيم النتائج
        total_notifications = len(notifications)
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_notifications)
        current_notifications = notifications[start_idx:end_idx]
    
        # إنشاء كائن تقسيم صفحات بسيط
        # نستخدم قاموس بدلاً من كائن Pagination لتبسيط التنفيذ
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_notifications,
            'pages': (total_notifications + per_page - 1) // per_page,
            'items': current_notifications,
            'has_prev': page > 1,
            'has_next': page < ((total_notifications + per_page - 1) // per_page),
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < ((total_notifications + per_page - 1) // per_page) else None
        }
    
        return render_template('mobile/notifications_new.html',
                              notifications=current_notifications,
                              pagination=pagination,
                              current_date=current_date)
    
    # إنشاء نموذج تسليم/استلام - النسخة المحمولة
    @bp.route('/vehicles/handover/create/<int:vehicle_id>', methods=['GET', 'POST'])
    @login_required
    def create_handover(vehicle_id):
        """إنشاء نموذج تسليم/استلام للسيارة للنسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        # فحص قيود العمليات للسيارات خارج الخدمة
        from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        if request.method == 'POST':
            # استخراج البيانات من النموذج
            handover_type = request.form.get('handover_type')
            handover_date = datetime.strptime(request.form.get('handover_date'), '%Y-%m-%d').date()
            person_name = request.form.get('person_name')
            supervisor_name = request.form.get('supervisor_name', '')
            form_link = request.form.get('form_link', '')
            vehicle_condition = request.form.get('vehicle_condition')
            fuel_level = request.form.get('fuel_level')
            mileage_str = request.form.get('mileage', '0')
            mileage = int(mileage_str) if mileage_str and mileage_str.isdigit() else 0
            has_spare_tire = 'has_spare_tire' in request.form
            has_fire_extinguisher = 'has_fire_extinguisher' in request.form
            has_tools = 'has_tools' in request.form
            has_first_aid_kit = 'has_first_aid_kit' in request.form
            has_warning_triangle = 'has_warning_triangle' in request.form
            notes = request.form.get('notes', '')
    
            # إنشاء سجل تسليم/استلام جديد
            handover = VehicleHandover(
                vehicle_id=vehicle_id,
                handover_type=handover_type,
                handover_date=handover_date,
                person_name=person_name,
                supervisor_name=supervisor_name,
                form_link=form_link,
                vehicle_condition=vehicle_condition,
                fuel_level=fuel_level,
                mileage=mileage,
                has_spare_tire=has_spare_tire,
                has_fire_extinguisher=has_fire_extinguisher,
                has_tools=has_tools,
                has_first_aid_kit=has_first_aid_kit,
                has_warning_triangle=has_warning_triangle,
                notes=notes
            )
    
            try:
                db.session.add(handover)
                db.session.commit()
    
                # تسجيل نشاط النظام
                description = f"تم إنشاء نموذج {'تسليم' if handover_type == 'delivery' else 'استلام'} للسيارة {vehicle.plate_number}"
                SystemAudit.create_audit_record(
                    current_user.id,
                    'إنشاء',
                    'VehicleHandover',
                    handover.id,
                    description,
                    entity_name=f"سيارة: {vehicle.plate_number}"
                )
    
                flash('تم إنشاء نموذج التسليم/الاستلام بنجاح', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إنشاء النموذج: {str(e)}', 'danger')
    
        # عرض نموذج إنشاء تسليم/استلام
        return render_template('mobile/create_handover.html', 
                               vehicle=vehicle,
                               now=datetime.now())
    
    # عرض تفاصيل نموذج تسليم/استلام - النسخة المحمولة
    @bp.route('/vehicles/handover/<int:handover_id>')
    @login_required
    def view_handover(handover_id):
        """عرض تفاصيل نموذج تسليم/استلام للنسخة المحمولة"""
        handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
        images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
    
        # تنسيق التاريخ للعرض
        handover.formatted_handover_date = handover.handover_date.strftime('%Y-%m-%d')
    
        handover_type_name = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
    
        return render_template('mobile/handover_view.html',
                               handover=handover,
                               vehicle=vehicle,
                               images=images,
                               handover_type_name=handover_type_name)
    
    # إنشاء ملف PDF لنموذج تسليم/استلام - النسخة المحمولة
    @bp.route('/vehicles/handover/<int:handover_id>/pdf')
    @login_required
    def handover_pdf(handover_id):
        """إنشاء نموذج تسليم/استلام كملف PDF للنسخة المحمولة"""
        from flask import send_file, flash, redirect, url_for
        import io
        import os
        from datetime import datetime
        from utils.fpdf_handover_pdf import generate_handover_report_pdf_weasyprint
    
        try:
            # الحصول على بيانات التسليم/الاستلام
            handover = VehicleHandover.query.get_or_404(handover_id)
            vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
            images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
    
            # تجهيز البيانات لملف PDF
            handover_data = {
                'vehicle': {
                    'plate_number': str(vehicle.plate_number),
                    'make': str(vehicle.make),
                    'model': str(vehicle.model),
                    'year': int(vehicle.year),
                    'color': str(vehicle.color)
                },
                'handover_type': 'تسليم' if handover.handover_type == 'delivery' else 'استلام',
                'handover_date': handover.handover_date.strftime('%Y-%m-%d'),
                'person_name': str(handover.person_name),
                'supervisor_name': str(handover.supervisor_name) if handover.supervisor_name else "",
                'vehicle_condition': str(handover.vehicle_condition),
                'fuel_level': str(handover.fuel_level),
                'mileage': int(handover.mileage),
                'has_spare_tire': bool(handover.has_spare_tire),
                'has_fire_extinguisher': bool(handover.has_fire_extinguisher),
                'has_first_aid_kit': bool(handover.has_first_aid_kit),
                'has_warning_triangle': bool(handover.has_warning_triangle),
                'has_tools': bool(handover.has_tools),
                'notes': str(handover.notes) if handover.notes else "",
                'form_link': str(handover.form_link) if handover.form_link else "",
                'image_paths': [image.image_path for image in images] if images else []
            }
    
            # إنشاء ملف PDF باستخدام WeasyPrint مع خط beIN-Normal
            pdf_buffer = generate_handover_report_pdf_weasyprint(handover)
    
            if not pdf_buffer:
                flash('حدث خطأ أثناء إنشاء ملف PDF', 'danger')
                return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
            # تحديد اسم الملف
            filename = f"handover_form_{vehicle.plate_number}.pdf"
    
            # إرسال الملف للمستخدم
            return send_file(
                pdf_buffer,
                download_name=filename,
                as_attachment=True,
                mimetype='application/pdf'
            )
    
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء ملف PDF: {str(e)}', 'danger')
            return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
    # اختبار حفظ سجل الورشة تجريبياً - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/workshop/test', methods=['GET'])
    @login_required
    def test_workshop_save(vehicle_id):
        """اختبار حفظ سجل الورشة تجريبياً"""
        try:
            # إنشاء سجل ورشة تجريبي
            workshop_record = VehicleWorkshop(
                vehicle_id=vehicle_id,
                entry_date=datetime.now().date(),
                reason='maintenance',
                description='اختبار تجريبي من النظام',
                repair_status='in_progress',
                cost=500.0,
                workshop_name='ورشة الاختبار',
                technician_name='فني الاختبار',
                delivery_link='https://example.com/delivery',
                reception_link='https://example.com/pickup',
                notes='سجل تجريبي للاختبار - تم إنشاؤه تلقائياً'
            )
    
            db.session.add(workshop_record)
            db.session.commit()
    
            flash(f'تم إضافة سجل الورشة التجريبي رقم {workshop_record.id} بنجاح!', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في الاختبار التجريبي للسيارة {vehicle_id}: {str(e)}")
            flash(f'فشل الاختبار التجريبي: {str(e)}', 'danger')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    # إضافة سجل ورشة جديد - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/workshop/add', methods=['GET', 'POST'])
    @login_required
    def add_workshop_record(vehicle_id):
        """إضافة سجل ورشة جديد للسيارة من النسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        # فحص قيود العمليات للسيارات خارج الخدمة
        from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        if request.method == 'POST':
            try:
                current_app.logger.debug(f"تجهيز بيانات النموذج لسجل الورشة للسيارة {vehicle_id}")
    
                # استخراج البيانات من النموذج
                entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
                exit_date_str = request.form.get('exit_date')
                exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
                reason = request.form.get('reason')
                description = request.form.get('description')
                repair_status = request.form.get('repair_status')
                cost = float(request.form.get('cost') or 0)
                workshop_name = request.form.get('workshop_name')
                technician_name = request.form.get('technician_name')
                notes = request.form.get('notes')
                delivery_link = request.form.get('delivery_form_link')
                reception_link = request.form.get('pickup_form_link')
    
                current_app.logger.debug(f"البيانات المستخرجة: {reason}, {description}, {repair_status}")
    
                # إنشاء سجل ورشة جديد
                workshop_record = VehicleWorkshop(
                    vehicle_id=vehicle_id,
                    entry_date=entry_date,
                    exit_date=exit_date,
                    reason=reason,
                    description=description,
                    repair_status=repair_status,
                    cost=cost,
                    workshop_name=workshop_name,
                    technician_name=technician_name,
                    notes=notes,
                    delivery_link=delivery_link,
                    reception_link=reception_link
                )
    
                db.session.add(workshop_record)
                db.session.flush()  # للحصول على معرف سجل الورشة
    
                # معالجة الصور قبل الإصلاح
                before_images = request.files.getlist('before_images')
                for image in before_images:
                    if image and image.filename:
                        # حفظ الصورة
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        folder_path = os.path.join(current_app.static_folder, 'uploads', 'workshop')
                        os.makedirs(folder_path, exist_ok=True)
                        image_path = os.path.join(folder_path, unique_filename)
                        image.save(image_path)
    
                        # إنشاء سجل الصورة
                        workshop_image = VehicleWorkshopImage(
                            workshop_record_id=workshop_record.id,
                            image_path=f'uploads/workshop/{unique_filename}',
                            image_type='before',
                            notes='صورة قبل الإصلاح'
                        )
                        db.session.add(workshop_image)
    
                # معالجة الصور بعد الإصلاح
                after_images = request.files.getlist('after_images')
                for image in after_images:
                    if image and image.filename:
                        # حفظ الصورة
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        folder_path = os.path.join(current_app.static_folder, 'uploads', 'workshop')
                        os.makedirs(folder_path, exist_ok=True)
                        image_path = os.path.join(folder_path, unique_filename)
                        image.save(image_path)
    
                        # إنشاء سجل الصورة
                        workshop_image = VehicleWorkshopImage(
                            workshop_record_id=workshop_record.id,
                            image_path=f'uploads/workshop/{unique_filename}',
                            image_type='after',
                            notes='صورة بعد الإصلاح'
                        )
                        db.session.add(workshop_image)
    
                # تحديث حالة السيارة
                if not exit_date:
                    vehicle.status = 'in_workshop'
                vehicle.updated_at = datetime.utcnow()
    
                db.session.commit()
    
                # تسجيل الإجراء
                log_activity('create', 'vehicle_workshop', workshop_record.id, 
                           f'تم إضافة سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال')
    
                
                # إنشاء طلب عملية تلقائياً لإدارة العمليات
                try:
                    operation_title = f"ورشة جديدة - {vehicle.plate_number}"
                    operation_description = f"تم إنشاء سجل ورشة جديد: {reason} - {description}"
                    
                    operation = create_operation_request(
                        operation_type='workshop_record',
                        related_record_id=workshop_record.id,
                        vehicle_id=vehicle_id,
                        title=operation_title,
                        description=operation_description,
                        requested_by=current_user.id,
                        priority='normal'
                    )
                    
                    # حفظ طلب العملية والإشعارات
                    db.session.commit()
                    
                    current_app.logger.debug(f"تم إنشاء طلب عملية للورشة: {workshop_record.id} برقم عملية: {operation.id}")
                    
                except Exception as e:
                    current_app.logger.error(f"خطأ في إنشاء طلب العملية للورشة: {str(e)}")
                    import traceback
                    current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
                    # لا نوقف العملية إذا فشل إنشاء طلب العملية
                
    
                flash('تم إضافة سجل الورشة بنجاح!', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"خطأ في إضافة سجل الورشة للسيارة {vehicle_id}: {str(e)}")
                flash(f'حدث خطأ أثناء إضافة سجل الورشة: {str(e)}', 'danger')
    
        # قوائم الخيارات
        workshop_reasons = [
            ('maintenance', 'صيانة دورية'),
            ('breakdown', 'عطل'),
            ('accident', 'حادث')
        ]
    
        repair_statuses = [
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'تم الإصلاح'),
            ('pending_approval', 'بانتظار الموافقة')
        ]
    
        return render_template('mobile/add_workshop_record.html',
                             vehicle=vehicle,
                             workshop_reasons=workshop_reasons,
                             repair_statuses=repair_statuses,
                             now=datetime.now())
    
    # تعديل سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_workshop_record(workshop_id):
        """تعديل سجل ورشة موجود للنسخة المحمولة"""
        workshop_record = VehicleWorkshop.query.get_or_404(workshop_id)
        vehicle = workshop_record.vehicle
    
        # تسجيل debug للبيانات الحالية
        current_app.logger.debug(f"تحرير سجل الورشة {workshop_id} - البيانات الحالية:")
        current_app.logger.debug(f"السبب: {workshop_record.reason}")
        current_app.logger.debug(f"الحالة: {workshop_record.repair_status}")
        current_app.logger.debug(f"الوصف: {workshop_record.description}")
        current_app.logger.debug(f"اسم الورشة: {workshop_record.workshop_name}")
        current_app.logger.debug(f"اسم الفني: {workshop_record.technician_name}")
        current_app.logger.debug(f"التكلفة: {workshop_record.cost}")
        current_app.logger.debug(f"رابط التسليم: {workshop_record.delivery_link}")
        current_app.logger.debug(f"رابط الاستلام: {workshop_record.reception_link}")
        current_app.logger.debug(f"الملاحظات: {workshop_record.notes}")
        
        current_app.logger.info(f"★ WORKSHOP EDIT - Method: {request.method}, Workshop ID: {workshop_id}")
        print(f"★ WORKSHOP EDIT - Method: {request.method}, Workshop ID: {workshop_id}")
        
        if request.method == 'POST':
            current_app.logger.info(f"★ POST data received: {dict(request.form)}")
            print(f"★ POST data received: {dict(request.form)}")
    
        if request.method == 'POST':
            try:
                # تحديث البيانات
                workshop_record.entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
                exit_date_str = request.form.get('exit_date')
                workshop_record.exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
                workshop_record.reason = request.form.get('reason')
                workshop_record.description = request.form.get('description')
                workshop_record.repair_status = request.form.get('repair_status')
                workshop_record.cost = float(request.form.get('cost') or 0)
                workshop_record.workshop_name = request.form.get('workshop_name')
                workshop_record.technician_name = request.form.get('technician_name')
                workshop_record.delivery_link = request.form.get('delivery_form_link')
                workshop_record.reception_link = request.form.get('pickup_form_link')
                workshop_record.notes = request.form.get('notes')
                workshop_record.updated_at = datetime.utcnow()
    
                # معالجة الصور المرفوعة
                import os
                from PIL import Image
                import uuid
    
                uploaded_images = []
    
                
                # دالة مساعدة لرفع الصور
                def process_workshop_images(files_list, image_type, type_name):
                    uploaded_count = 0
                    if files_list:
                        for file in files_list:
                            if file and file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                try:
                                    # إنشاء اسم ملف فريد
                                    filename = f"workshop_{image_type}_{workshop_record.id}_{uuid.uuid4().hex[:8]}_{file.filename}"
                                    
                                    # إنشاء المجلد إذا لم يكن موجوداً
                                    upload_dir = os.path.join('static', 'uploads', 'workshop')
                                    os.makedirs(upload_dir, exist_ok=True)
                                    
                                    # حفظ الملف
                                    file_path = os.path.join(upload_dir, filename)
                                    file.save(file_path)
                                    
                                    # ضغط الصورة إذا كانت كبيرة
                                    try:
                                        with Image.open(file_path) as img:
                                            if img.width > 1200 or img.height > 1200:
                                                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                                                img.save(file_path, optimize=True, quality=85)
                                    except Exception as e:
                                        current_app.logger.warning(f"تعذر ضغط الصورة {filename}: {str(e)}")
                                    
                                    # إضافة سجل الصورة لقاعدة البيانات
                                    image_record = VehicleWorkshopImage(
                                        workshop_record_id=workshop_record.id,
                                        image_type=image_type,
                                        image_path=f"uploads/workshop/{filename}",
                                        notes=f"{type_name} - تم الرفع في {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                                    )
                                    db.session.add(image_record)
                                    uploaded_images.append(filename)
                                    uploaded_count += 1
                                    
                                except Exception as e:
                                    current_app.logger.error(f"خطأ في رفع {type_name}: {str(e)}")
                    return uploaded_count
    
                # دالة مساعدة لرفع الإيصالات (PDF وصور)
                def save_receipt_file(file, field_name, type_name):
                    """رفع وحفظ إيصال (PDF أو صورة)"""
                    if file and file.filename:
                        try:
                            # التحقق من نوع الملف
                            allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
                            file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
                            
                            if file_ext in allowed_extensions:
                                # إنشاء اسم ملف فريد
                                filename = f"receipt_{field_name}_{workshop_record.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
                                
                                # إنشاء المجلد إذا لم يكن موجوداً
                                upload_dir = os.path.join('static', 'uploads', 'workshop', 'receipts')
                                os.makedirs(upload_dir, exist_ok=True)
                                
                                # حفظ الملف
                                file_path = os.path.join(upload_dir, filename)
                                file.save(file_path)
                                
                                # ضغط الصورة إذا كانت صورة وكبيرة
                                if file_ext in {'png', 'jpg', 'jpeg', 'gif'}:
                                    try:
                                        with Image.open(file_path) as img:
                                            if img.width > 1200 or img.height > 1200:
                                                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                                                img.save(file_path, optimize=True, quality=85)
                                    except Exception as e:
                                        current_app.logger.warning(f"تعذر ضغط الصورة {filename}: {str(e)}")
                                
                                return f"uploads/workshop/receipts/{filename}"
                            
                        except Exception as e:
                            current_app.logger.error(f"خطأ في رفع {type_name}: {str(e)}")
                            flash(f'خطأ في رفع {type_name}: {str(e)}', 'warning')
                    
                    return None
    
                # معالجة إيصالات التسليم والاستلام
                receipt_updates = []
                
                # إيصال تسليم الورشة
                if 'delivery_receipt' in request.files:
                    delivery_receipt_file = request.files['delivery_receipt']
                    delivery_receipt_path = save_receipt_file(delivery_receipt_file, 'delivery', 'إيصال تسليم الورشة')
                    if delivery_receipt_path:
                        workshop_record.delivery_receipt = delivery_receipt_path
                        receipt_updates.append('إيصال تسليم الورشة')
                
                # إيصال استلام من الورشة
                if 'pickup_receipt' in request.files:
                    pickup_receipt_file = request.files['pickup_receipt']
                    pickup_receipt_path = save_receipt_file(pickup_receipt_file, 'pickup', 'إيصال استلام من الورشة')
                    if pickup_receipt_path:
                        workshop_record.pickup_receipt = pickup_receipt_path
                        receipt_updates.append('إيصال استلام من الورشة')
    
                # معالجة الصور الجديدة
                delivery_count = 0
                pickup_count = 0
                notes_count = 0
                
                # صور إيصال التسليم للورشة
                if 'delivery_images' in request.files:
                    delivery_files = request.files.getlist('delivery_images')
                    delivery_count = process_workshop_images(delivery_files, 'delivery', 'صورة إيصال التسليم للورشة')
                
                # صور إيصال الاستلام من الورشة
                if 'pickup_images' in request.files:
                    pickup_files = request.files.getlist('pickup_images')
                    pickup_count = process_workshop_images(pickup_files, 'pickup', 'صورة إيصال الاستلام من الورشة')
                
                # صور ملاحظات السيارة قبل التسليم للورشة
                if 'notes_images' in request.files:
                    notes_files = request.files.getlist('notes_images')
                    notes_count = process_workshop_images(notes_files, 'notes', 'صورة ملاحظات السيارة قبل التسليم')
                
                # معالجة الصور القديمة (للتوافق مع النظام القديم)
                if 'before_images' in request.files:
                    before_files = request.files.getlist('before_images')
                    process_workshop_images(before_files, 'before', 'صورة قبل الإصلاح')
                
                if 'after_images' in request.files:
                    after_files = request.files.getlist('after_images')
                    process_workshop_images(after_files, 'after', 'صورة بعد الإصلاح')
                
    
                db.session.commit()
    
                # تسجيل العملية
                log_activity(
                    action='update',
                    entity_type='vehicle_workshop',
                    details=f'تم تعديل سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال وإضافة {len(uploaded_images)} صورة'
                )
    
                # إنشاء طلب عملية تلقائياً لإدارة العمليات
                try:
                    operation_title = f"تحديث ورشة - {vehicle.plate_number}"
                    operation_description = f"تم تحديث سجل الورشة: {workshop_record.reason} - {workshop_record.description}"
                    
                    operation = create_operation_request(
                        operation_type="workshop_update",
                        related_record_id=workshop_record.id,
                        vehicle_id=vehicle.id,
                        title=operation_title,
                        description=operation_description,
                        requested_by=current_user.id,
                        priority="normal"
                    )
                    
                    # حفظ طلب العملية والإشعارات
                    db.session.commit()
    
                    # update_vehicle_driver(vehicle.id)
                    update_vehicle_state(vehicle.id)
                    
                    print(f"تم تسجيل عملية التحديث بنجاح: {operation.id}")
                    current_app.logger.debug(f"تم إنشاء طلب عملية لتحديث الورشة: {workshop_record.id} برقم عملية: {operation.id}")
                    
                    # التحقق من وجود العملية في قاعدة البيانات
                    saved_operation = OperationRequest.query.get(operation.id)
                    if saved_operation:
                        print(f"تأكيد: عملية التحديث {operation.id} محفوظة في قاعدة البيانات")
                    else:
                        print(f"تحذير: عملية التحديث {operation.id} غير موجودة في قاعدة البيانات!")
                    
                except Exception as e:
                    print(f"خطأ في إنشاء طلب العملية لتحديث الورشة: {str(e)}")
                    current_app.logger.error(f"خطأ في إنشاء طلب العملية لتحديث الورشة: {str(e)}")
                    import traceback
                    current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
                    # لا نوقف العملية إذا فشل إنشاء طلب العملية
    
                success_message = f'تم تحديث سجل الورشة بنجاح!'
                
                # إضافة تفاصيل الملفات المرفوعة
                updates = []
                
                # إضافة الإيصالات المرفوعة
                if receipt_updates:
                    updates.extend(receipt_updates)
                if uploaded_images:
    
    
    
                    details = []
                    if delivery_count > 0:
                        details.append(f'{delivery_count} صورة إيصال تسليم')
                    if pickup_count > 0:
                        details.append(f'{pickup_count} صورة إيصال استلام')
                    if notes_count > 0:
                        details.append(f'{notes_count} صورة ملاحظات')
                    
                    if details:
                        success_message += f' تم رفع {" و ".join(details)}.'
                    else:
                        success_message += f' تم رفع {len(uploaded_images)} صورة جديدة.'
                
    
                flash(success_message, 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"خطأ في تعديل سجل الورشة {workshop_id}: {str(e)}")
                flash(f'حدث خطأ أثناء تحديث سجل الورشة: {str(e)}', 'danger')
    
        
        
        
        
        
        
        
        
        
        
        
        # خيارات النموذج
        workshop_reasons = [
            ('maintenance', 'صيانة دورية'),
            ('breakdown', 'عطل'),
            ('accident', 'حادث'),
            ('periodic_inspection', 'فحص دوري'),
            ('other', 'أخرى')
        ]
    
        repair_statuses = [
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'تم الإصلاح'),
            ('pending_approval', 'بانتظار الموافقة')
        ]
    
        return render_template('mobile/edit_workshop_record_simple.html',
                               workshop_record=workshop_record,
                               vehicle=vehicle,
                               workshop_reasons=workshop_reasons,
                               repair_statuses=repair_statuses,
                               now=datetime.now())
    
    # حذف سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/delete', methods=['POST'])
    @login_required
    def delete_workshop_record(workshop_id):
        """حذف سجل ورشة للنسخة المحمولة"""
        try:
            workshop_record = VehicleWorkshop.query.get_or_404(workshop_id)
            vehicle = workshop_record.vehicle
    
            # تسجيل العملية قبل الحذف
            log_activity(
                action='delete',
                entity_type='vehicle_workshop',
                details=f'تم حذف سجل دخول الورشة للسيارة: {vehicle.plate_number} - الوصف: {workshop_record.description[:50]} من الجوال'
            )
    
            db.session.delete(workshop_record)
            db.session.commit()
    
            flash('تم حذف سجل الورشة بنجاح!', 'success')
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في حذف سجل الورشة {workshop_id}: {str(e)}")
            flash(f'حدث خطأ أثناء حذف سجل الورشة: {str(e)}', 'danger')
    
        return redirect(url_for('mobile.vehicle_details', vehicle_id=workshop_record.vehicle.id))
    
    # عرض تفاصيل سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/details')
    @login_required
    def view_workshop_details(workshop_id):
        """عرض تفاصيل سجل ورشة للنسخة المحمولة"""
        workshop_record = VehicleWorkshop.query.options(
            joinedload(VehicleWorkshop.images)
        ).get_or_404(workshop_id)
        vehicle = workshop_record.vehicle
    
        # فحص وجود الصور الفعلي على الخادم مع البحث في مسارات متعددة
        valid_images = []
        if workshop_record.images:
            for image in workshop_record.images:
                # محاولة أولى: المسار المحفوظ في قاعدة البيانات
                image_path = os.path.join(current_app.static_folder, image.image_path)
    
                # إذا لم يوجد، نبحث عن نفس الملف في مجلد الورشة
                if not os.path.exists(image_path):
                    filename = os.path.basename(image.image_path)
                    # البحث عن أي ملف يحتوي على اسم مشابه
                    workshop_dir = os.path.join(current_app.static_folder, 'uploads/workshop')
                    if os.path.exists(workshop_dir):
                        for file in os.listdir(workshop_dir):
                            # البحث عن الجزء المميز من اسم الملف
                            if 'WhatsApp_Image_2025-07-14_at_11.29.07_ef6d7df0' in file:
                                # تحديث المسار ليشير للملف الموجود
                                image.image_path = f'uploads/workshop/{file}'
                                image_path = os.path.join(current_app.static_folder, image.image_path)
                                break
    
                if os.path.exists(image_path):
                    valid_images.append(image)
                    current_app.logger.info(f"الصورة موجودة: {image.image_path}")
                else:
                    current_app.logger.warning(f"الصورة غير موجودة: {image_path}")
    
        # تحديث قائمة الصور بالصور الموجودة فقط
        workshop_record.valid_images = valid_images
    
        return render_template('mobile/workshop_details.html',
                               workshop_record=workshop_record,
                               vehicle=vehicle)
    
    # # تعديل سجل التسليم والاستلام - النسخة المحمولة
    # @bp.route('/vehicles/handover/<int:handover_id>/edit', methods=['GET', 'POST'])
    # @login_required
    # def edit_handover_mobile(handover_id):
    #     """تعديل سجل التسليم والاستلام للنسخة المحمولة"""
    #     handover = VehicleHandover.query.get_or_404(handover_id)
    #     vehicle = handover.vehicle
    
    #     if request.method == 'POST':
    #         try:
    #             # تحديث البيانات
    #             handover.handover_type = request.form.get('handover_type')
    #             handover.person_name = request.form.get('person_name')
    #             handover.person_phone = request.form.get('person_phone')
    #             handover.person_national_id = request.form.get('person_national_id')
    #             handover.notes = request.form.get('notes')
    
    #             # تحديث التاريخ إذا تم تقديمه
    #             handover_date = request.form.get('handover_date')
    #             if handover_date:
    #                 handover.handover_date = datetime.strptime(handover_date, '%Y-%m-%d').date()
    
    #             # تحديث الحقول الاختيارية
    #             handover.mileage = request.form.get('mileage', type=int)
    #             handover.vehicle_condition = request.form.get('vehicle_condition')
    #             handover.fuel_level = request.form.get('fuel_level')
    
    #             # تسجيل النشاط
    #             log_activity(
    #                 action='update',
    #                 entity_type='vehicle_handover',
    #                 details=f'تم تعديل سجل {handover.handover_type} للسيارة: {vehicle.plate_number} - الشخص: {handover.person_name} من الجوال'
    #             )
    
    #             db.session.commit()
    #             flash('تم تحديث سجل التسليم والاستلام بنجاح!', 'success')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         except Exception as e:
    #             db.session.rollback()
    #             current_app.logger.error(f"خطأ في تعديل سجل التسليم والاستلام {handover_id}: {str(e)}")
    #             flash(f'حدث خطأ أثناء تحديث السجل: {str(e)}', 'danger')
    
    #     return render_template('mobile/edit_handover.html',
    #                            handover=handover,
    #                            vehicle=vehicle)
    
    
    
    # مسارات التفويضات الخارجية للموبايل
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/view')
    @login_required
    def view_external_authorization(vehicle_id, auth_id):
        """عرض تفاصيل التفويض الخارجي في الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        return render_template('mobile/view_external_authorization.html',
                             vehicle=vehicle,
                             authorization=authorization)
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_external_authorization(vehicle_id, auth_id):
        """تعديل التفويض الخارجي في الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        if request.method == 'POST':
            try:
                # تحديث البيانات
                authorization.employee_id = request.form.get('employee_id')
                authorization.project_name = request.form.get('project_name')
                authorization.authorization_type = request.form.get('authorization_type')
                authorization.city = request.form.get('city')
                authorization.external_link = request.form.get('form_link')
                authorization.notes = request.form.get('notes')
    
                # معالجة رفع الملف الجديد
                if 'file' in request.files and request.files['file'].filename:
                    file = request.files['file']
                    if file:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
    
                        # إنشاء مجلد الرفع إذا لم يكن موجوداً
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
    
                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)
    
                        # 💾 لا حذف للملفات القديمة - الاحتفاظ بجميع الملفات للأمان
                        authorization.file_path = f"uploads/authorizations/{filename}"
    
                db.session.commit()
                flash('تم تحديث التفويض بنجاح', 'success')
                return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث التفويض: {str(e)}', 'error')
    
        # الحصول على البيانات للنموذج
        departments = Department.query.all()
        employees = Employee.query.all()
    
        return render_template('mobile/edit_external_authorization.html',
                             vehicle=vehicle,
                             authorization=authorization,
                             departments=departments,
                             employees=employees)
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/delete')
    @login_required
    def delete_external_authorization(vehicle_id, auth_id):
        """حذف التفويض الخارجي من الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        try:
            # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
            # لا حذف للملفات الفعلية
            db.session.delete(authorization)
            db.session.commit()
            flash('تم حذف التفويض بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف التفويض: {str(e)}', 'error')
    
        return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/create', methods=['GET', 'POST'])
    @login_required
    def create_external_authorization(vehicle_id):
        """إنشاء تفويض خارجي جديد من الموبايل"""
        from models import Vehicle, Employee, Department, ExternalAuthorization
        from werkzeug.utils import secure_filename
        import os
    
        try:
            # الحصول على السيارة
            vehicle = Vehicle.query.get_or_404(vehicle_id)
    
            # فحص قيود العمليات للسيارات خارج الخدمة
            from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
            restrictions = check_vehicle_operation_restrictions(vehicle)
            if restrictions['blocked']:
                flash(restrictions['message'], 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            # الحصول على الموظفين والأقسام
            employees = Employee.query.all()
            departments = Department.query.all()
    
            if request.method == 'POST':
                # إنشاء تفويض جديد
                authorization = ExternalAuthorization(
                    vehicle_id=vehicle_id,
                    employee_id=request.form.get('employee_id'),
                    authorization_type=request.form.get('authorization_type'),
                    project_name=request.form.get('project_name'),
                    city=request.form.get('city'),
    
                    external_link=request.form.get('external_link'),
                    notes=request.form.get('notes'),
                    status='pending'
                )
    
                # معالجة رفع الملف
                if 'file' in request.files:
                    file = request.files['file']
                    if file and file.filename:
                        # حفظ الملف
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
    
                        upload_dir = os.path.join('static', 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
    
                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)
                        authorization.file_path = file_path
    
                db.session.add(authorization)
                db.session.commit()
    
                flash('تم إنشاء التفويض بنجاح', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            return render_template('mobile/create_external_authorization.html',
                                 vehicle=vehicle,
                                 employees=employees,
                                 departments=departments)
    
        except Exception as e:
            print(f"خطأ في إنشاء التفويض: {str(e)}")
            flash(f'خطأ في إنشاء التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/approve', methods=['GET', 'POST'])
    @login_required
    def approve_external_authorization(vehicle_id, auth_id):
        """موافقة على تفويض خارجي"""
        try:
            authorization = ExternalAuthorization.query.filter_by(
                id=auth_id, 
                vehicle_id=vehicle_id
            ).first()
    
            if not authorization:
                flash('التفويض غير موجود', 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            authorization.status = 'approved'
            authorization.updated_at = datetime.utcnow()
            db.session.commit()
    
            flash('تم الموافقة على التفويض بنجاح', 'success')
            return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
        except Exception as e:
            print(f"خطأ في موافقة التفويض: {str(e)}")
            flash(f'خطأ في موافقة التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/reject', methods=['GET', 'POST'])
    @login_required
    def reject_external_authorization(vehicle_id, auth_id):
        """رفض تفويض خارجي"""
        try:
            authorization = ExternalAuthorization.query.filter_by(
                id=auth_id, 
                vehicle_id=vehicle_id
            ).first()
    
            if not authorization:
                flash('التفويض غير موجود', 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            authorization.status = 'rejected'
            authorization.updated_at = datetime.utcnow()
            db.session.commit()
    
            flash('تم رفض التفويض', 'info')
            return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
        except Exception as e:
            print(f"خطأ في رفض التفويض: {str(e)}")
            flash(f'خطأ في رفض التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/handover/<int:handover_id>/delete', methods=['POST'])
    @login_required
    def delete_handover(handover_id):
        """حذف سجل تسليم أو استلام"""
        try:
            # الحصول على سجل التسليم/الاستلام
            handover = VehicleHandover.query.get_or_404(handover_id)
            vehicle_id = handover.vehicle_id
            handover_type = handover.handover_type
            person_name = handover.person_name
    
            # 💾 حذف الصور من قاعدة البيانات فقط - الملفات تبقى محفوظة
            images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
            for image in images:
                # لا حذف للملفات الفعلية - الاحتفاظ بجميع الصور للأمان
                db.session.delete(image)
    
            # حذف سجل التسليم/الاستلام
            db.session.delete(handover)
            db.session.commit()
    
            # تسجيل العملية في السجل
            log_activity(
                action='delete',
                entity_type='vehicle_handover',
                entity_id=handover_id,
                details=f'تم حذف سجل {"تسليم" if handover_type == "delivery" else "استلام"} للسيارة - الشخص: {person_name}'
            )
    
            # تحديث اسم السائق في السيارة بعد الحذف
            update_vehicle_driver(vehicle_id)
    
            flash(f'تم حذف سجل {"التسليم" if handover_type == "delivery" else "الاستلام"} بنجاح', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        except Exception as e:
            db.session.rollback()
            print(f"خطأ في حذف سجل التسليم/الاستلام: {str(e)}")
            flash(f'خطأ في حذف السجل: {str(e)}', 'error')
            return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
    # --- New Quick Return Functions ---
    
    def get_current_driver_info(vehicle_id):
        """الحصول على معلومات السائق الحالي للسيارة"""
        try:
            # البحث عن آخر سجل تسليم (delivery) للسيارة
            last_delivery = VehicleHandover.query.filter_by(
                vehicle_id=vehicle_id,
                handover_type='delivery'
            ).order_by(VehicleHandover.handover_date.desc()).first()
            
            if last_delivery:
                driver_info = {
                    'name': last_delivery.person_name or '',
                    'phone': last_delivery.driver_phone_number or '',
                    'national_id': last_delivery.driver_residency_number or '',
                    'employee_id': last_delivery.employee_id or ''
                }
                
                # إذا كان هناك معرف موظف، اجلب معلومات إضافية
                if last_delivery.employee_id:
                    employee = Employee.query.get(last_delivery.employee_id)
                    if employee:
                        driver_info['name'] = employee.name
                        driver_info['phone'] = employee.mobilePersonal or employee.mobile or ''
                        driver_info['national_id'] = employee.national_id or ''
                        driver_info['department'] = employee.departments[0].name if employee.departments else 'غير محدد'
                
                return driver_info
        except Exception as e:
            current_app.logger.error(f'خطأ في جلب معلومات السائق الحالي: {str(e)}')
        
        return {'name': '', 'phone': '', 'national_id': '', 'employee_id': ''}
    
    @bp.route('/vehicles/quick_return', methods=['POST'])
    @login_required
    def quick_vehicle_return():
        """استلام سريع للسيارة لتحريرها للاستخدام"""
        try:
            vehicle_id = request.form.get('vehicle_id')
            return_date = request.form.get('return_date')
            return_time = request.form.get('return_time') 
            return_reason = request.form.get('return_reason')
            current_mileage = request.form.get('current_mileage')
            notes = request.form.get('notes', '')
            
            if not vehicle_id or not return_date or not return_time:
                flash('جميع الحقول مطلوبة', 'error')
                return redirect(url_for('mobile.create_handover_mobile'))
            
            # التحقق من وجود السيارة
            vehicle = Vehicle.query.get_or_404(vehicle_id)
            
            # الحصول على معلومات السائق الحالي
            current_driver = get_current_driver_info(vehicle_id)
            
            # إنشاء سجل استلام جديد
            return_handover = VehicleHandover(
                vehicle_id=vehicle_id,
                handover_type='return',
                handover_date=datetime.strptime(return_date, '%Y-%m-%d').date(),
                handover_time=datetime.strptime(return_time, '%H:%M').time() if return_time else None,
                person_name=current_driver.get('name', ''),
                person_phone=current_driver.get('phone', ''),
                person_national_id=current_driver.get('national_id', ''),
                employee_id=current_driver.get('employee_id'),
                mileage=int(current_mileage) if current_mileage else 0,
                notes=f"استلام سريع - {return_reason}. {notes}".strip(),
                created_by=current_user.id,
                created_at=datetime.now()
            )
            
            db.session.add(return_handover)
            
            # تحديث حالة السيارة لتصبح متاحة
            vehicle.status = 'available'
            vehicle.current_driver = None
            
            db.session.commit()
            
            flash(f'تم استلام السيارة {vehicle.plate_number} بنجاح وأصبحت متاحة للاستخدام', 'success')
            return redirect(url_for('mobile.create_handover_mobile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'خطأ في الاستلام السريع: {str(e)}')
            flash('حدث خطأ أثناء استلام السيارة. يرجى المحاولة مرة أخرى.', 'error')
            return redirect(url_for('mobile.create_handover_mobile'))
    
    @bp.route('/get_vehicle_driver_info/<int:vehicle_id>')
    @login_required
    def get_vehicle_driver_info(vehicle_id):
        """API لجلب معلومات السائق الحالي للسيارة"""
        try:
            vehicle = Vehicle.query.get_or_404(vehicle_id)
            current_driver = get_current_driver_info(vehicle_id)
            
            return jsonify({
                'success': True,
                'vehicle_info': {
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'status': vehicle.status
                },
                'driver_info': current_driver
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # تعديل سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/edit', methods=['GET', 'POST'])
    @login_required  
    def edit_workshop_mobile(workshop_id):
        """تعديل سجل الورشة للنسخة المحمولة"""
        return redirect(url_for('vehicles.edit_workshop', id=workshop_id))
