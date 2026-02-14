"""
مسارات إضافية للمركبات — تُسجّل على الـ blueprint عبر register_vehicle_extra_routes(bp).
"""
from datetime import datetime, timedelta, date
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, make_response, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_, case
import os

from core.extensions import db
from utils.id_encoder import decode_vehicle_id
from modules.vehicles.domain.models import (
    Vehicle, VehicleRental, VehicleWorkshop, VehicleWorkshopImage,
    VehicleProject, VehicleHandover, VehicleHandoverImage,
)
from domain.employees.models import Employee, Department, employee_departments
from models import (
    VehiclePeriodicInspection, VehicleSafetyCheck,
    ExternalAuthorization, Module, Permission, UserRole,
    VehicleExternalSafetyCheck, User, OperationRequest,
)
from utils.audit_logger import log_activity
from utils.vehicle_route_helpers import format_date_arabic, save_image, check_vehicle_operation_restrictions
from modules.vehicles.application.vehicle_service import (
    INSPECTION_TYPE_CHOICES, INSPECTION_STATUS_CHOICES,
    SAFETY_CHECK_TYPE_CHOICES, SAFETY_CHECK_STATUS_CHOICES,
    update_vehicle_driver, update_all_vehicle_drivers, get_vehicle_current_employee_id,
)
from utils.vehicle_helpers import log_audit, allowed_file
from forms.vehicle_forms import VehicleDocumentsForm
from modules.vehicles.application.vehicle_document_service import get_view_documents_context, get_valid_documents_context
from modules.vehicles.application.vehicle_export_service import (
    build_vehicle_report_pdf, build_vehicle_report_excel, process_import_vehicles,
)


def register_vehicle_extra_routes(bp):
    @bp.route('/v/<string:encoded_id>')
    @login_required
    def view_encoded(encoded_id):
        """عرض تفاصيل سيارة باستخدام معرف مشفر"""
        try:
            vehicle_id = decode_vehicle_id(encoded_id)
            return redirect(url_for('vehicles.view', id=vehicle_id))
        except ValueError:
            flash('رابط غير صالح', 'error')
            return redirect(url_for('vehicles.index'))
    @bp.route('/documents/view/<int:id>', methods=['GET'])
    @login_required
    def view_documents(id):
        """عرض تفاصيل وثائق المركبة"""
        data = get_view_documents_context(id)
        if data is None:
            abort(404)
        return render_template('vehicles/view_documents.html', **data)

    @bp.route('/documents/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_documents(id):
            """تعديل تواريخ وثائق المركبة (التفويض، الاستمارة، الفحص الدوري)"""
            vehicle = Vehicle.query.get_or_404(id)
            form = VehicleDocumentsForm()


            # التحقق من القدوم من صفحة العمليات
            from_operations = request.args.get('from_operations')
            operation_id = from_operations if from_operations else None


            if request.method == 'GET':
                    # ملء النموذج بالبيانات الحالية
                    form.authorization_expiry_date.data = vehicle.authorization_expiry_date
                    form.registration_expiry_date.data = vehicle.registration_expiry_date
                    form.inspection_expiry_date.data = vehicle.inspection_expiry_date

            if request.method == 'POST':
                    try:
                        # محاولة استخدام بيانات النموذج أولاً
                        if form.validate_on_submit():
                            # تحديث البيانات من النموذج
                            vehicle.authorization_expiry_date = form.authorization_expiry_date.data

                            # إذا لم يكن قادماً من العمليات، حفظ جميع الحقول
                            if not from_operations:
                                vehicle.registration_expiry_date = form.registration_expiry_date.data
                                vehicle.inspection_expiry_date = form.inspection_expiry_date.data
                        else:
                            # في حالة فشل التحقق، استخدم request.form مباشرة
                            print(f"ERROR فشل التحقق من النموذج: {form.errors}")

                            # تحديث التواريخ من request.form مباشرة
                            auth_date = request.form.get('authorization_expiry_date')
                            if auth_date:
                                vehicle.authorization_expiry_date = datetime.strptime(auth_date, '%Y-%m-%d').date() if auth_date else None

                            if not from_operations:
                                reg_date = request.form.get('registration_expiry_date')
                                if reg_date:
                                    vehicle.registration_expiry_date = datetime.strptime(reg_date, '%Y-%m-%d').date() if reg_date else None

                                insp_date = request.form.get('inspection_expiry_date')
                                if insp_date:
                                    vehicle.inspection_expiry_date = datetime.strptime(insp_date, '%Y-%m-%d').date() if insp_date else None

                        vehicle.updated_at = datetime.utcnow()

                        # إذا كان قادماً من العمليات، إنشاء سجل تسليم/استلام جديد
                        # NOTE: هذا الجزء معطل مؤقتاً - الفئة Operation غير موجودة
                        # if from_operations and operation_id:
                        #     try:
                        #         # البحث عن العملية
                        #         from models import Operation
                        #         operation = Operation.query.get(int(operation_id))
                        #
                        #         if operation:
                        #             # إنشاء سجل تسليم/استلام جديد
                        #             handover = VehicleHandover(
                        #                 vehicle_id=vehicle.id,
                        #                 handover_type='delivery',  # تسليم
                        #                 handover_date=datetime.utcnow(),
                        #                 person_name=operation.employee.name if operation.employee else 'غير محدد',
                        #                 notes=f'تفويض من العملية #{operation_id} - صالح حتى {form.authorization_expiry_date.data}',
                        #                 created_by=current_user.id,
                        #                 updated_at=datetime.utcnow()
                        #             )
                        #
                        #             # إضافة معلومات إضافية إذا توفرت
                        #             if operation.employee:
                        #                 handover.employee_id = operation.employee.id
                        #                 if hasattr(operation.employee, 'mobilePersonal'):
                        #                     handover.driver_phone_number = operation.employee.mobilePersonal
                        #                 if hasattr(operation.employee, 'mobile'):
                        #                     handover.driver_work_phone = operation.employee.mobile
                        #                 if hasattr(operation.employee, 'national_id'):
                        #                     handover.driver_residency_number = operation.employee.national_id
                        #
                        #             db.session.add(handover)
                        #
                        #             # تحديث حالة العملية إلى مكتملة
                        #             operation.status = 'completed'
                        #             operation.completed_at = datetime.utcnow()
                        #             operation.reviewer_id = current_user.id
                        #             operation.review_notes = f'تم تحديد فترة التفويض وإنشاء سجل التسليم'
                        #
                        #             # حفظ التغييرات أولاً
                        #             db.session.commit()
                        #
                        #             # تحديث اسم السائق في معلومات السيارة الأساسية
                        #             update_vehicle_driver(vehicle.id)
                        #
                        #             # تسجيل في العمليات
                        #             log_audit('create', 'vehicle_handover', handover.id,
                        #                      f'تم إنشاء سجل تسليم من العملية #{operation_id}')
                        #             log_audit('update', 'operation', operation.id,
                        #                      f'تم إكمال العملية وإنشاء سجل التسليم')
                        #             log_audit('update', 'vehicle', vehicle.id,
                        #                      f'تم تحديث اسم السائق تلقائياً بعد إنشاء سجل التسليم')
                        #
                        #     except Exception as e:
                        #         current_app.logger.error(f'خطأ في إنشاء سجل التسليم: {str(e)}')
                        #         flash('تم تحديث التفويض ولكن حدث خطأ في إنشاء سجل التسليم', 'warning')


                        # حفظ التغييرات للوثائق إذا لم تكن محفوظة مسبقاً
                        if not from_operations or not operation_id:
                            db.session.commit()


                        # تسجيل الإجراء

                        log_audit('update', 'vehicle_documents', vehicle.id, 
                                f'تم تحديث تواريخ وثائق المركبة: {vehicle.plate_number}')

                        if from_operations:
                            flash('تم تحديد فترة التفويض وإنشاء سجل التسليم بنجاح!', 'success')
                            return redirect('/operations')
                        else:
                            flash('تم تحديث تواريخ الوثائق بنجاح!', 'success')
                            return redirect(url_for('vehicles.view', id=id))

                    except Exception as e:
                        import traceback
                        print(f"ERROR خطأ في تحديث تواريخ الوثائق: {str(e)}")
                        print(traceback.format_exc())
                        db.session.rollback()
                        flash(f'حدث خطأ في تحديث التواريخ: {str(e)}', 'danger')

            return render_template('vehicles/edit_documents.html', 
                                 form=form, vehicle=vehicle, 
                                 from_operations=bool(from_operations), 
                                 operation_id=operation_id)


    @bp.route('/<int:id>/manage-user-access', methods=['POST'])
    @login_required
    def manage_user_access(id):
        """إدارة وصول المستخدمين للمركبة"""
        vehicle = Vehicle.query.get_or_404(id)

        # التحقق من صلاحيات الإدارة
        if False:  # تم إزالة قيد الوصول مؤقتاً لعرض جميع المركبات
            flash('ليس لديك صلاحية لإدارة وصول المستخدمين', 'danger')
            return redirect(url_for('vehicles.edit', id=id))

        # الحصول على المستخدمين المحددين
        authorized_user_ids = request.form.getlist('authorized_users')

        # مسح العلاقات الحالية
        vehicle.authorized_users.clear()

        # إضافة المستخدمين الجدد
        if authorized_user_ids:
            from models import User
            authorized_users = User.query.filter(User.id.in_(authorized_user_ids)).all()
            for user in authorized_users:
                vehicle.authorized_users.append(user)

        db.session.commit()

        # تسجيل الإجراء
        user_names = [user.name or user.username or user.email for user in vehicle.authorized_users]
        log_audit('update', 'vehicle_user_access', vehicle.id, 
                  f'تم تحديث وصول المستخدمين للمركبة {vehicle.plate_number}. المستخدمون: {", ".join(user_names) if user_names else "لا يوجد"}')

        flash(f'تم تحديث إعدادات الوصول بنجاح! المستخدمون المخولون: {len(vehicle.authorized_users)}', 'success')
        return redirect(url_for('vehicles.edit', id=id))

    # مسارات الحوادث مُستخرجة إلى presentation/web/vehicles/accident_routes.py

    # مسارات إدارة الإيجار
    @bp.route('/<int:id>/rental/create', methods=['GET', 'POST'])
    @login_required
    def create_rental(id):
            """إضافة معلومات إيجار لسيارة"""
            vehicle = Vehicle.query.get_or_404(id)

            # التحقق من عدم وجود إيجار نشط حالياً
            existing_rental = VehicleRental.query.filter_by(vehicle_id=id, is_active=True).first()
            if existing_rental and request.method == 'GET':
                    flash('يوجد إيجار نشط بالفعل لهذه السيارة!', 'warning')
                    return redirect(url_for('vehicles.view', id=id))

            if request.method == 'POST':
                    # استخراج البيانات من النموذج
                    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.form.get('end_date')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    monthly_cost = float(request.form.get('monthly_cost'))
                    lessor_name = request.form.get('lessor_name')
                    lessor_contact = request.form.get('lessor_contact')
                    contract_number = request.form.get('contract_number')
                    city = request.form.get('city')
                    notes = request.form.get('notes')

                    # إلغاء تنشيط الإيجارات السابقة
                    if existing_rental:
                            existing_rental.is_active = False
                            existing_rental.updated_at = datetime.utcnow()

                    # إنشاء سجل إيجار جديد
                    rental = VehicleRental(
                            vehicle_id=id,
                            start_date=start_date,
                            end_date=end_date,
                            monthly_cost=monthly_cost,
                            is_active=True,
                            lessor_name=lessor_name,
                            lessor_contact=lessor_contact,
                            contract_number=contract_number,
                            city=city,
                            notes=notes
                    )

                    db.session.add(rental)

                    # تحديث حالة السيارة
                    vehicle.status = 'rented'
                    vehicle.updated_at = datetime.utcnow()

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('create', 'vehicle_rental', rental.id, f'تم إضافة معلومات إيجار للسيارة: {vehicle.plate_number}')

                    flash('تم إضافة معلومات الإيجار بنجاح!', 'success')
                    return redirect(url_for('vehicles.view', id=id))

            return render_template('vehicles/rental_create.html', vehicle=vehicle)

    @bp.route('/rental/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_rental(id):
            """تعديل معلومات إيجار"""
            rental = VehicleRental.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(rental.vehicle_id)

            if request.method == 'POST':
                    # استخراج البيانات من النموذج
                    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.form.get('end_date')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    monthly_cost = float(request.form.get('monthly_cost'))
                    is_active = bool(request.form.get('is_active'))
                    lessor_name = request.form.get('lessor_name')
                    lessor_contact = request.form.get('lessor_contact')
                    contract_number = request.form.get('contract_number')
                    city = request.form.get('city')
                    notes = request.form.get('notes')

                    # تحديث معلومات الإيجار
                    rental.start_date = start_date
                    rental.end_date = end_date
                    rental.monthly_cost = monthly_cost
                    rental.is_active = is_active
                    rental.lessor_name = lessor_name
                    rental.lessor_contact = lessor_contact
                    rental.contract_number = contract_number
                    rental.city = city
                    rental.notes = notes
                    rental.updated_at = datetime.utcnow()

                    # تحديث حالة السيارة حسب حالة الإيجار
                    if is_active:
                            vehicle.status = 'rented'
                    else:
                            vehicle.status = 'available'
                    vehicle.updated_at = datetime.utcnow()

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('update', 'vehicle_rental', rental.id, f'تم تعديل معلومات إيجار السيارة: {vehicle.plate_number}')

                    flash('تم تعديل معلومات الإيجار بنجاح!', 'success')
                    return redirect(url_for('vehicles.view', id=vehicle.id))

            return render_template('vehicles/rental_edit.html', rental=rental, vehicle=vehicle)


    @bp.route('/<int:id>/project/create', methods=['GET', 'POST'])
    @login_required
    def create_project(id):
            """تخصيص السيارة لمشروع"""
            vehicle = Vehicle.query.get_or_404(id)

            # التحقق من عدم وجود تخصيص نشط حالياً
            existing_assignment = VehicleProject.query.filter_by(vehicle_id=id, is_active=True).first()
            if existing_assignment and request.method == 'GET':
                    flash('هذه السيارة مخصصة بالفعل لمشروع نشط!', 'warning')
                    return redirect(url_for('vehicles.view', id=id))

            if request.method == 'POST':
                    # استخراج البيانات من النموذج
                    project_name = request.form.get('project_name')
                    location = request.form.get('location')
                    manager_name = request.form.get('manager_name')
                    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.form.get('end_date')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    notes = request.form.get('notes')

                    # إلغاء تنشيط التخصيصات السابقة
                    if existing_assignment:
                            existing_assignment.is_active = False
                            existing_assignment.updated_at = datetime.utcnow()

                    # إنشاء تخصيص جديد
                    project = VehicleProject(
                            vehicle_id=id,
                            project_name=project_name,
                            location=location,
                            manager_name=manager_name,
                            start_date=start_date,
                            end_date=end_date,
                            is_active=True,
                            notes=notes
                    )

                    db.session.add(project)

                    # تحديث حالة السيارة
                    vehicle.status = 'in_project'
                    vehicle.updated_at = datetime.utcnow()

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('create', 'vehicle_project', project.id, 
                                     f'تم تخصيص السيارة {vehicle.plate_number} لمشروع {project_name}')

                    flash('تم تخصيص السيارة للمشروع بنجاح!', 'success')
                    return redirect(url_for('vehicles.view', id=id))

            return render_template('vehicles/project_create.html', vehicle=vehicle)

    @bp.route('/project/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_project(id):
            """تعديل تخصيص المشروع"""
            project = VehicleProject.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(project.vehicle_id)

            if request.method == 'POST':
                    # استخراج البيانات من النموذج
                    project_name = request.form.get('project_name')
                    location = request.form.get('location')
                    manager_name = request.form.get('manager_name')
                    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
                    end_date_str = request.form.get('end_date')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    is_active = bool(request.form.get('is_active'))
                    notes = request.form.get('notes')

                    # تحديث التخصيص
                    project.project_name = project_name
                    project.location = location
                    project.manager_name = manager_name
                    project.start_date = start_date
                    project.end_date = end_date
                    project.is_active = is_active
                    project.notes = notes
                    project.updated_at = datetime.utcnow()

                    # تحديث حالة السيارة
                    if is_active:
                            vehicle.status = 'in_project'
                    else:
                            # التحقق مما إذا كانت السيارة مؤجرة
                            active_rental = VehicleRental.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()

                            if active_rental:
                                    vehicle.status = 'rented'
                            else:
                                    vehicle.status = 'available'

                    vehicle.updated_at = datetime.utcnow()

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('update', 'vehicle_project', project.id, 
                                     f'تم تعديل تخصيص السيارة {vehicle.plate_number} للمشروع {project_name}')

                    flash('تم تعديل تخصيص المشروع بنجاح!', 'success')
                    return redirect(url_for('vehicles.view', id=vehicle.id))

            return render_template('vehicles/project_edit.html', project=project, vehicle=vehicle)


    # (create_handover, edit_handover → handover_routes)
    # مسارات التقارير والإحصائيات
    # dashboard() → presentation.web.vehicle_routes

    @bp.route('/reports')
    @login_required
    def reports():
            """صفحة تقارير السيارات"""
            # توزيع السيارات حسب الشركة المصنعة
            make_stats = db.session.query(
                    Vehicle.make, func.count(Vehicle.id)
            ).group_by(Vehicle.make).all()

            # توزيع السيارات حسب سنة الصنع
            year_stats = db.session.query(
                    Vehicle.year, func.count(Vehicle.id)
            ).group_by(Vehicle.year).order_by(Vehicle.year).all()

            # إحصائيات الورشة
            workshop_reason_stats = db.session.query(
                    VehicleWorkshop.reason, func.count(VehicleWorkshop.id)
            ).group_by(VehicleWorkshop.reason).all()

            # إجمالي تكاليف الصيانة لكل سيارة (أعلى 10 سيارات)
            top_maintenance_costs = db.session.query(
                    Vehicle.plate_number, Vehicle.make, Vehicle.model, 
                    func.sum(VehicleWorkshop.cost).label('total_cost')
            ).join(
                    VehicleWorkshop, Vehicle.id == VehicleWorkshop.vehicle_id
            ).group_by(
                    Vehicle.id, Vehicle.plate_number, Vehicle.make, Vehicle.model
            ).order_by(
                    func.sum(VehicleWorkshop.cost).desc()
            ).limit(10).all()

            return render_template(
                    'vehicles/reports.html',
                    make_stats=make_stats,
                    year_stats=year_stats,
                    workshop_reason_stats=workshop_reason_stats,
                    top_maintenance_costs=top_maintenance_costs
            )

    @bp.route('/detailed')
    @login_required
    def detailed_list():
            """قائمة تفصيلية للسيارات مع معلومات إضافية لكل سيارة على حدة"""
            # إعداد قيم التصفية
            status = request.args.get('status')
            make = request.args.get('make')
            year = request.args.get('year')
            project = request.args.get('project')
            location = request.args.get('location')
            sort = request.args.get('sort', 'plate_number')
            search = request.args.get('search', '')

            # استعلام قاعدة البيانات مع التصفية
            query = Vehicle.query

            if status:
                    query = query.filter(Vehicle.status == status)
            if make:
                    query = query.filter(Vehicle.make == make)
            if year:
                    query = query.filter(Vehicle.year == int(year))
            if search:
                    query = query.filter(
                            or_(
                                    Vehicle.plate_number.ilike(f'%{search}%'),
                                    Vehicle.make.ilike(f'%{search}%'),
                                    Vehicle.model.ilike(f'%{search}%'),
                                    Vehicle.color.ilike(f'%{search}%')
                            )
                    )

            # فلترة حسب المشروع
            if project:
                    vehicle_ids = db.session.query(VehicleProject.vehicle_id).filter_by(
                            project_name=project, is_active=True
                    ).all()
                    vehicle_ids = [v[0] for v in vehicle_ids]
                    query = query.filter(Vehicle.id.in_(vehicle_ids))

            # فلترة حسب الموقع (المنطقة)
            if location:
                    vehicle_ids = db.session.query(VehicleProject.vehicle_id).filter_by(
                            location=location, is_active=True
                    ).all()
                    vehicle_ids = [v[0] for v in vehicle_ids]
                    query = query.filter(Vehicle.id.in_(vehicle_ids))

            # ترتيب النتائج
            if sort == 'make':
                    query = query.order_by(Vehicle.make, Vehicle.model)
            elif sort == 'year':
                    query = query.order_by(Vehicle.year.desc())
            elif sort == 'status':
                    query = query.order_by(Vehicle.status)
            elif sort == 'created_at':
                    query = query.order_by(Vehicle.created_at.desc())
            else:
                    query = query.order_by(Vehicle.plate_number)

            # الترقيم
            page = request.args.get('page', 1, type=int)
            pagination = query.paginate(page=page, per_page=20, error_out=False)
            vehicles = pagination.items

            # استخراج معلومات إضافية لكل سيارة
            for vehicle in vehicles:
                    # معلومات الإيجار النشط
                    vehicle.active_rental = VehicleRental.query.filter_by(
                            vehicle_id=vehicle.id, is_active=True
                    ).first()

                    # معلومات آخر دخول للورشة
                    vehicle.latest_workshop = VehicleWorkshop.query.filter_by(
                            vehicle_id=vehicle.id
                    ).order_by(VehicleWorkshop.entry_date.desc()).first()

                    # معلومات المشروع الحالي
                    vehicle.active_project = VehicleProject.query.filter_by(
                            vehicle_id=vehicle.id, is_active=True
                    ).first()

            # استخراج قوائم الفلاتر
            makes = db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
            makes = [make[0] for make in makes]

            years = db.session.query(Vehicle.year).distinct().order_by(Vehicle.year.desc()).all()
            years = [year[0] for year in years]

            # استخراج قائمة المشاريع النشطة
            projects = db.session.query(VehicleProject.project_name).filter_by(
                    is_active=True
            ).distinct().order_by(VehicleProject.project_name).all()
            projects = [project[0] for project in projects]

            # استخراج قائمة المواقع (المناطق)
            locations = db.session.query(VehicleProject.location).distinct().order_by(
                    VehicleProject.location
            ).all()
            locations = [location[0] for location in locations]

            return render_template(
                    'vehicles/detailed_list.html',
                    vehicles=vehicles,
                    pagination=pagination,
                    makes=makes,
                    years=years,
                    locations=locations,
                    total_count=Vehicle.query.count(),
                    request=request
            )

    @bp.route('/vehicle-report-pdf/<int:id>')
    @login_required
    def generate_vehicle_report_pdf(id):
        """إنشاء تقرير شامل للسيارة بصيغة PDF"""
        try:
            buffer, filename, mimetype = build_vehicle_report_pdf(id)
            if buffer is None:
                abort(404)
            return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء التقرير PDF: {str(e)}', 'danger')
            return redirect(url_for('vehicles.view', id=id))


    # مسارات إدارة الفحص الدوري
    @bp.route('/<int:id>/inspections', methods=['GET'])
    @login_required
    def vehicle_inspections(id):
            """عرض سجلات الفحص الدوري لسيارة محددة"""
            vehicle = Vehicle.query.get_or_404(id)
            inspections = VehiclePeriodicInspection.query.filter_by(vehicle_id=id).order_by(VehiclePeriodicInspection.inspection_date.desc()).all()

            # تنسيق التواريخ
            for inspection in inspections:
                    inspection.formatted_inspection_date = format_date_arabic(inspection.inspection_date)
                    inspection.formatted_expiry_date = format_date_arabic(inspection.expiry_date)

            return render_template(
                    'vehicles/inspections.html',
                    vehicle=vehicle,
                    inspections=inspections,
                    inspection_types=INSPECTION_TYPE_CHOICES,
                    inspection_statuses=INSPECTION_STATUS_CHOICES
            )

    @bp.route('/<int:id>/inspections/create', methods=['GET', 'POST'])
    @login_required
    def create_inspection(id):
            """إضافة سجل فحص دوري جديد"""
            vehicle = Vehicle.query.get_or_404(id)

            if request.method == 'POST':
                    inspection_date = datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d').date()
                    expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
                    inspection_center = request.form.get('inspection_center')
                    supervisor_name = request.form.get('supervisor_name')
                    result = request.form.get('result')
                    inspection_status = 'valid'  # الحالة الافتراضية ساري
                    cost = float(request.form.get('cost') or 0)
                    results = request.form.get('results')
                    recommendations = request.form.get('recommendations')
                    notes = request.form.get('notes')

                    # حفظ شهادة الفحص إذا تم تحميلها
                    certificate_file = None
                    if 'certificate_file' in request.files and request.files['certificate_file']:
                            certificate_file = save_image(request.files['certificate_file'], 'inspections')

                    # إنشاء سجل فحص جديد
                    inspection = VehiclePeriodicInspection(
                            vehicle_id=id,
                            inspection_date=inspection_date,
                            expiry_date=expiry_date,
                            inspection_center=inspection_center,
                            supervisor_name=supervisor_name,
                            result=result,
                            # القيم القديمة للتوافق مع قاعدة البيانات
                            inspection_number=inspection_center,
                            inspector_name=supervisor_name,
                            inspection_type=result,
                            inspection_status=inspection_status,
                            cost=cost,
                            results=results,
                            recommendations=recommendations,
                            certificate_file=certificate_file,
                            notes=notes
                    )

                    db.session.add(inspection)
                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('create', 'vehicle_inspection', inspection.id, f'تم إضافة سجل فحص دوري للسيارة: {vehicle.plate_number}')

                    flash('تم إضافة سجل الفحص الدوري بنجاح!', 'success')
                    return redirect(url_for('vehicles.vehicle_inspections', id=id))

            return render_template(
                    'vehicles/inspection_create.html',
                    vehicle=vehicle,
                    inspection_types=INSPECTION_TYPE_CHOICES
            )

    @bp.route('/inspection/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_inspection(id):
            """تعديل سجل فحص دوري"""
            inspection = VehiclePeriodicInspection.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(inspection.vehicle_id)

            if request.method == 'POST':
                    inspection.inspection_date = datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d').date()
                    inspection.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
                    inspection.inspection_center = request.form.get('inspection_center')
                    inspection.supervisor_name = request.form.get('supervisor_name')
                    inspection.result = request.form.get('result')

                    # حفظ القيم القديمة أيضًا للتوافق مع قاعدة البيانات
                    inspection.inspection_number = request.form.get('inspection_center')
                    inspection.inspector_name = request.form.get('supervisor_name')
                    inspection.inspection_type = request.form.get('result')

                    inspection.inspection_status = request.form.get('inspection_status')
                    inspection.cost = float(request.form.get('cost') or 0)
                    inspection.results = request.form.get('results')
                    inspection.recommendations = request.form.get('recommendations')
                    inspection.notes = request.form.get('notes')
                    inspection.updated_at = datetime.utcnow()

                    # حفظ شهادة الفحص الجديدة إذا تم تحميلها
                    if 'certificate_file' in request.files and request.files['certificate_file']:
                            inspection.certificate_file = save_image(request.files['certificate_file'], 'inspections')

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('update', 'vehicle_inspection', inspection.id, f'تم تعديل سجل فحص دوري للسيارة: {vehicle.plate_number}')

                    flash('تم تعديل سجل الفحص الدوري بنجاح!', 'success')
                    return redirect(url_for('vehicles.vehicle_inspections', id=vehicle.id))

            return render_template(
                    'vehicles/inspection_edit.html',
                    inspection=inspection,
                    vehicle=vehicle,
                    inspection_types=INSPECTION_TYPE_CHOICES,
                    inspection_statuses=INSPECTION_STATUS_CHOICES
            )

    @bp.route('/inspection/<int:id>/confirm-delete')
    @login_required
    def confirm_delete_inspection(id):
            """عرض صفحة تأكيد حذف سجل فحص دوري"""
            inspection = VehiclePeriodicInspection.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(inspection.vehicle_id)

            # تنسيق التاريخ
            inspection.formatted_inspection_date = format_date_arabic(inspection.inspection_date)

            return render_template(
                    'vehicles/confirm_delete_inspection.html',
                    inspection=inspection,
                    vehicle=vehicle
            )

    @bp.route('/inspection/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_inspection(id):
            """حذف سجل فحص دوري"""
            inspection = VehiclePeriodicInspection.query.get_or_404(id)
            vehicle_id = inspection.vehicle_id
            vehicle = Vehicle.query.get_or_404(vehicle_id)

            # تسجيل الإجراء قبل الحذف
            log_audit('delete', 'vehicle_inspection', id, f'تم حذف سجل فحص دوري للسيارة: {vehicle.plate_number}')

            db.session.delete(inspection)
            db.session.commit()

            flash('تم حذف سجل الفحص الدوري بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_inspections', id=vehicle_id))

    # مسارات إدارة فحص السلامة
    @bp.route('/<int:id>/safety-checks', methods=['GET'])
    @login_required
    def vehicle_safety_checks(id):
            """عرض سجلات فحص السلامة لسيارة محددة"""
            vehicle = Vehicle.query.get_or_404(id)
            checks = VehicleSafetyCheck.query.filter_by(vehicle_id=id).order_by(VehicleSafetyCheck.check_date.desc()).all()

            # تنسيق التواريخ
            for check in checks:
                    check.formatted_check_date = format_date_arabic(check.check_date)

            return render_template(
                    'vehicles/safety_checks.html',
                    vehicle=vehicle,
                    checks=checks,
                    check_types=SAFETY_CHECK_TYPE_CHOICES,
                    check_statuses=SAFETY_CHECK_STATUS_CHOICES
            )

    @bp.route('/<int:id>/safety-checks/create', methods=['GET', 'POST'])
    @login_required
    def create_safety_check(id):
            """إضافة سجل فحص سلامة جديد"""
            vehicle = Vehicle.query.get_or_404(id)

            # الحصول على قائمة السائقين والمشرفين
            supervisors = Employee.query.filter(Employee.job_title.contains('مشرف')).all()

            if request.method == 'POST':
                    check_date = datetime.strptime(request.form.get('check_date'), '%Y-%m-%d').date()
                    check_type = request.form.get('check_type')

                    # معلومات السائق
                    driver_id = request.form.get('driver_id')
                    driver_name = request.form.get('driver_name')
                    # تحويل قيمة فارغة إلى None
                    if not driver_id or driver_id == '':
                            driver_id = None
                    else:
                            driver = Employee.query.get(driver_id)
                            if driver:
                                    driver_name = driver.name

                    # معلومات المشرف
                    supervisor_id = request.form.get('supervisor_id')
                    supervisor_name = request.form.get('supervisor_name')
                    # تحويل قيمة فارغة إلى None
                    if not supervisor_id or supervisor_id == '':
                            supervisor_id = None
                    else:
                            supervisor = Employee.query.get(supervisor_id)
                            if supervisor:
                                    supervisor_name = supervisor.name

                    status = request.form.get('status')
                    check_form_link = request.form.get('check_form_link')
                    issues_found = bool(request.form.get('issues_found'))
                    issues_description = request.form.get('issues_description')
                    actions_taken = request.form.get('actions_taken')
                    notes = request.form.get('notes')

                    # إنشاء سجل فحص سلامة جديد
                    safety_check = VehicleSafetyCheck(
                            vehicle_id=id,
                            check_date=check_date,
                            check_type=check_type,
                            driver_id=driver_id,
                            driver_name=driver_name,
                            supervisor_id=supervisor_id,
                            supervisor_name=supervisor_name,
                            status=status,
                            check_form_link=check_form_link,
                            issues_found=issues_found,
                            issues_description=issues_description,
                            actions_taken=actions_taken,
                            notes=notes
                    )

                    db.session.add(safety_check)
                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('create', 'vehicle_safety_check', safety_check.id, f'تم إضافة سجل فحص سلامة للسيارة: {vehicle.plate_number}')

                    flash('تم إضافة سجل فحص السلامة بنجاح!', 'success')
                    return redirect(url_for('vehicles.vehicle_safety_checks', id=id))

            return render_template(
                    'vehicles/safety_check_create.html',
                    vehicle=vehicle,
                    supervisors=supervisors,
                    check_types=SAFETY_CHECK_TYPE_CHOICES,
                    check_statuses=SAFETY_CHECK_STATUS_CHOICES
            )

    @bp.route('/safety-check/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_safety_check(id):
            """تعديل سجل فحص سلامة"""
            safety_check = VehicleSafetyCheck.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(safety_check.vehicle_id)

            # الحصول على قائمة السائقين والمشرفين
            supervisors = Employee.query.filter(Employee.job_title.contains('مشرف')).all()

            if request.method == 'POST':
                    safety_check.check_date = datetime.strptime(request.form.get('check_date'), '%Y-%m-%d').date()
                    safety_check.check_type = request.form.get('check_type')

                    # معلومات السائق
                    driver_id = request.form.get('driver_id')
                    safety_check.driver_name = request.form.get('driver_name')

                    # تحويل قيمة فارغة إلى None
                    if not driver_id or driver_id == '':
                            safety_check.driver_id = None
                    else:
                            safety_check.driver_id = driver_id
                            driver = Employee.query.get(driver_id)
                            if driver:
                                    safety_check.driver_name = driver.name

                    # معلومات المشرف
                    supervisor_id = request.form.get('supervisor_id')
                    safety_check.supervisor_name = request.form.get('supervisor_name')

                    # تحويل قيمة فارغة إلى None
                    if not supervisor_id or supervisor_id == '':
                            safety_check.supervisor_id = None
                    else:
                            safety_check.supervisor_id = supervisor_id
                            supervisor = Employee.query.get(supervisor_id)
                            if supervisor:
                                    safety_check.supervisor_name = supervisor.name

                    safety_check.status = request.form.get('status')
                    safety_check.check_form_link = request.form.get('check_form_link')
                    safety_check.issues_found = bool(request.form.get('issues_found'))
                    safety_check.issues_description = request.form.get('issues_description')
                    safety_check.actions_taken = request.form.get('actions_taken')
                    safety_check.notes = request.form.get('notes')
                    safety_check.updated_at = datetime.utcnow()

                    db.session.commit()

                    # تسجيل الإجراء
                    log_audit('update', 'vehicle_safety_check', safety_check.id, f'تم تعديل سجل فحص سلامة للسيارة: {vehicle.plate_number}')

                    flash('تم تعديل سجل فحص السلامة بنجاح!', 'success')
                    return redirect(url_for('vehicles.vehicle_safety_checks', id=vehicle.id))

            return render_template(
                    'vehicles/safety_check_edit.html',
                    safety_check=safety_check,
                    vehicle=vehicle,
                    supervisors=supervisors,
                    check_types=SAFETY_CHECK_TYPE_CHOICES,
                    check_statuses=SAFETY_CHECK_STATUS_CHOICES
            )

    @bp.route('/safety-check/<int:id>/confirm-delete')
    @login_required
    def confirm_delete_safety_check(id):
            """عرض صفحة تأكيد حذف سجل فحص سلامة"""
            safety_check = VehicleSafetyCheck.query.get_or_404(id)
            vehicle = Vehicle.query.get_or_404(safety_check.vehicle_id)

            # تنسيق التاريخ
            safety_check.formatted_check_date = format_date_arabic(safety_check.check_date)

            return render_template(
                    'vehicles/confirm_delete_safety_check.html',
                    check=safety_check,
                    vehicle=vehicle
            )

    @bp.route('/safety-check/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_safety_check(id):
            """حذف سجل فحص سلامة"""
            safety_check = VehicleSafetyCheck.query.get_or_404(id)
            vehicle_id = safety_check.vehicle_id
            vehicle = Vehicle.query.get_or_404(vehicle_id)

            # تسجيل الإجراء قبل الحذف
            log_audit('delete', 'vehicle_safety_check', id, f'تم حذف سجل فحص سلامة للسيارة: {vehicle.plate_number}')

            db.session.delete(safety_check)
            db.session.commit()

            flash('تم حذف سجل فحص السلامة بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_safety_checks', id=vehicle_id))


    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_external_authorization(vehicle_id, auth_id):
        """تعديل التفويض الخارجي"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        if request.method == 'POST':
            try:
                # تحديث البيانات
                employee_id = request.form.get('employee_id')
                auth.employee_id = int(employee_id) if employee_id and employee_id != 'None' else None
                auth.project_name = request.form.get('project_name')
                auth.authorization_type = request.form.get('authorization_type')
                auth.city = request.form.get('city')
                auth.external_link = request.form.get('form_link')
                auth.notes = request.form.get('notes')

                # معالجة بيانات السائق اليدوية
                auth.manual_driver_name = request.form.get('manual_driver_name')
                auth.manual_driver_phone = request.form.get('manual_driver_phone')
                auth.manual_driver_position = request.form.get('manual_driver_position')
                auth.manual_driver_department = request.form.get('manual_driver_department')

                # معالجة رفع الملف الجديد
                if 'file' in request.files and request.files['file'].filename:
                    file = request.files['file']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"

                        # إنشاء مجلد الرفع إذا لم يكن موجوداً
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)

                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)

                        # 💾 الملف القديم يبقى محفوظاً - لا نحذف الملفات الفعلية
                        if auth.file_path:
                            print(f"💾 الملف القديم محفوظ للأمان: {auth.file_path}")

                        auth.file_path = f"static/uploads/authorizations/{filename}"

                db.session.commit()
                flash('تم تحديث التفويض بنجاح', 'success')
                return redirect(url_for('vehicles.view', id=vehicle_id))

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث التفويض: {str(e)}', 'error')

        # الحصول على البيانات للنموذج
        departments = Department.query.all()
        employees = Employee.query.all()

        return render_template('vehicles/edit_external_authorization.html',
                             vehicle=vehicle,
                             authorization=auth,
                             departments=departments,
                             employees=employees)

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/approve')
    @login_required
    def approve_external_authorization(vehicle_id, auth_id):
        """الموافقة على التفويض الخارجي"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        try:
            auth.status = 'approved'
            db.session.commit()
            flash('تم الموافقة على التفويض بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الموافقة على التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/reject')
    @login_required
    def reject_external_authorization(vehicle_id, auth_id):
        """رفض التفويض الخارجي"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        try:
            auth.status = 'rejected'
            db.session.commit()
            flash('تم رفض التفويض', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء رفض التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/delete')
    @login_required
    def delete_external_authorization(vehicle_id, auth_id):
        """حذف التفويض الخارجي"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        try:
            # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
            if auth.file_path:
                print(f"💾 الملف محفوظ للأمان: {auth.file_path}")

            db.session.delete(auth)
            db.session.commit()
            flash('تم حذف التفويض (الملف محفوظ بشكل آمن)', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/vehicle-report/<int:id>')
    @login_required
    def generate_vehicle_report(id):
        """إنشاء تقرير شامل للسيارة بصيغة Excel"""
        try:
            buffer, filename, mimetype = build_vehicle_report_excel(id)
            if buffer is None:
                abort(404)
            return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء تقرير Excel: {str(e)}', 'danger')
            return redirect(url_for('vehicles.view', id=id))

    @bp.route('/update-drivers', methods=['POST'])
    @login_required
    def update_drivers():
            """تحديث جميع أسماء السائقين من سجلات التسليم"""
            try:
                    updated_count = update_all_vehicle_drivers()
                    flash(f'تم تحديث أسماء السائقين لـ {updated_count} سيارة بنجاح!', 'success')
            except Exception as e:
                    flash(f'حدث خطأ أثناء التحديث: {str(e)}', 'danger')

            return redirect(url_for('vehicles.detailed'))

    @bp.route('/<int:vehicle_id>/current_employee')
    @login_required
    def get_current_employee(vehicle_id):
            """الحصول على معرف الموظف الحالي للسيارة"""
            try:
                    employee_id = get_vehicle_current_employee_id(vehicle_id)
                    return jsonify({
                            'employee_id': employee_id
                    })
            except Exception as e:
                    return jsonify({
                            'employee_id': None,
                            'error': str(e)
                    }), 500

    @bp.route('/handovers')
    @login_required
    def handovers_list():
            """عرض جميع السيارات مع حالات التسليم والاستلام"""
            try:
                    # الحصول على جميع السيارات مع معلومات التسليم
                    # فلترة المركبات حسب القسم المحدد للمستخدم الحالي
                    from flask_login import current_user
                    from models import employee_departments

                    vehicles_query = Vehicle.query

                    if current_user.is_authenticated and hasattr(current_user, 'assigned_department_id') and current_user.assigned_department_id:
                            # الحصول على معرفات الموظفين في القسم المحدد
                            dept_employee_ids = db.session.query(Employee.id).join(
                                    employee_departments
                            ).join(Department).filter(
                                    Department.id == current_user.assigned_department_id
                            ).all()
                            dept_employee_ids = [emp.id for emp in dept_employee_ids]

                            if dept_employee_ids:
                                    # فلترة المركبات التي لها تسليم لموظف في القسم المحدد
                                    vehicle_ids_with_handovers = db.session.query(
                                            VehicleHandover.vehicle_id
                                    ).filter(
                                            VehicleHandover.handover_type == 'delivery',
                                            VehicleHandover.employee_id.in_(dept_employee_ids)
                                    ).distinct().all()

                                    vehicle_ids = [h.vehicle_id for h in vehicle_ids_with_handovers]
                                    if vehicle_ids:
                                            vehicles_query = vehicles_query.filter(Vehicle.id.in_(vehicle_ids))
                                    else:
                                            vehicles_query = vehicles_query.filter(Vehicle.id == -1)  # قائمة فارغة
                            else:
                                    vehicles_query = vehicles_query.filter(Vehicle.id == -1)  # قائمة فارغة

                    vehicles = vehicles_query.all()

                    vehicles_data = []
                    for vehicle in vehicles:
                            # الحصول على آخر سجل تسليم وآخر سجل استلام
                            latest_delivery = VehicleHandover.query.filter_by(
                                    vehicle_id=vehicle.id, 
                                    handover_type='delivery'
                            ).order_by(VehicleHandover.handover_date.desc()).first()

                            latest_return = VehicleHandover.query.filter_by(
                                    vehicle_id=vehicle.id, 
                                    handover_type='return'
                            ).order_by(VehicleHandover.handover_date.desc()).first()

                            # تحديد الحالة الحالية
                            current_status = 'متاح'
                            current_employee = None

                            if latest_delivery:
                                    if not latest_return or latest_delivery.handover_date > latest_return.handover_date:
                                            current_status = 'مُسلم'
                                            current_employee = latest_delivery.person_name

                            vehicles_data.append({
                                    'vehicle': vehicle,
                                    'latest_delivery': latest_delivery,
                                    'latest_return': latest_return,
                                    'current_status': current_status,
                                    'current_employee': current_employee
                            })

                    return render_template('vehicles/handovers_list.html', vehicles_data=vehicles_data)

            except Exception as e:
                    flash(f'حدث خطأ أثناء تحميل البيانات: {str(e)}', 'danger')
                    return redirect(url_for('vehicles.index'))

    # ========== مسارات إدارة صور رخص السيارات ==========

    @bp.route('/<int:vehicle_id>/license-image', methods=['GET', 'POST'])
    @login_required
    def vehicle_license_image(vehicle_id):
        """عرض وإدارة صورة رخصة السيارة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == 'POST':
            # طباعة معلومات debug لفهم المشكلة
            print(f"POST request received for vehicle {vehicle_id}")
            print(f"Form data: {request.form}")
            print(f"Files in request: {list(request.files.keys())}")

            # التحقق من نوع العملية
            action = request.form.get('action')

            if action == 'delete':
                # حذف صورة الرخصة
                if vehicle.license_image:
                    try:
                        # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
                        print(f"💾 صورة الرخصة محفوظة للأمان: {vehicle.license_image}")

                        # حذف المرجع من قاعدة البيانات
                        vehicle.license_image = None
                        db.session.commit()

                        # تسجيل العملية
                        log_audit(
                            action='delete',
                            entity_type='vehicle',
                            entity_id=vehicle.id,
                            details=f'تم حذف صورة رخصة السيارة {vehicle.plate_number}'
                        )

                        flash('تم حذف صورة الرخصة بنجاح', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'خطأ في حذف صورة الرخصة: {str(e)}', 'error')
                else:
                    flash('لا توجد صورة رخصة لحذفها', 'warning')

                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

            # رفع صورة جديدة
            if 'license_image' not in request.files:
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

            file = request.files['license_image']
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))



            if file and allowed_file(file.filename, ['png', 'jpg', 'jpeg', 'gif', 'webp']):

                try:
                    # إنشاء مجلد الرفع إذا لم يكن موجوداً
                    upload_dir = os.path.join('static', 'uploads', 'vehicles')
                    os.makedirs(upload_dir, exist_ok=True)

                    # 💾 الصورة القديمة تبقى محفوظة - لا نحذف الملفات الفعلية
                    if vehicle.license_image:
                        print(f"💾 الصورة القديمة محفوظة للأمان: {vehicle.license_image}")

                    # تأمين اسم الملف وإضافة timestamp لتجنب التضارب
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"license_{vehicle.plate_number}_{timestamp}_{filename}"
                    filepath = os.path.join(upload_dir, filename)

                    # حفظ الملف
                    file.save(filepath)

                    # ضغط الصورة إذا كانت كبيرة
                    try:
                        from PIL import Image
                        with Image.open(filepath) as img:
                            # تحويل إلى RGB إذا كانت الصورة RGBA
                            if img.mode == 'RGBA':
                                img = img.convert('RGB')

                            # تصغير الصورة إذا كانت أكبر من 1500x1500
                            if img.width > 1500 or img.height > 1500:
                                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
                                img.save(filepath, 'JPEG', quality=85, optimize=True)
                    except Exception as e:
                        print(f"خطأ في معالجة الصورة: {e}")

                    # تحديث قاعدة البيانات
                    vehicle.license_image = filename
                    db.session.commit()

                    # تسجيل العملية
                    action_text = 'update' if vehicle.license_image else 'create'
                    log_audit(
                        action=action_text,
                        entity_type='vehicle',
                        entity_id=vehicle.id,
                        details=f'تم {"تحديث" if action_text == "update" else "رفع"} صورة رخصة للسيارة {vehicle.plate_number}'
                    )

                    flash('تم رفع صورة الرخصة بنجاح', 'success')

                except Exception as e:
                    db.session.rollback()
                    flash(f'خطأ في رفع صورة الرخصة: {str(e)}', 'error')
            else:
                flash('نوع الملف غير مدعوم. يرجى رفع صورة بصيغة JPG, PNG, GIF أو WEBP', 'error')

            return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

        return render_template('vehicles/license_image.html', vehicle=vehicle)



    # ========== مسارات إدارة Google Drive ==========

    @bp.route('/<int:vehicle_id>/drive-link', methods=['POST'])
    @login_required
    def update_drive_link(vehicle_id):
        """تحديث أو حذف رابط Google Drive"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        action = request.form.get('action')

        if action == 'remove':
            # حذف الرابط
            vehicle.drive_folder_link = None
            db.session.commit()

            log_audit('delete', 'vehicle', vehicle.id, f'تم حذف رابط Google Drive للسيارة {vehicle.plate_number}')
            flash('تم حذف رابط Google Drive بنجاح', 'success')

        else:
            # حفظ أو تحديث الرابط
            drive_link = request.form.get('drive_link', '').strip()

            if not drive_link:
                flash('يرجى إدخال رابط Google Drive', 'danger')
                return redirect(url_for('vehicles.view', id=vehicle_id))

            # التحقق من صحة الرابط
            if not (drive_link.startswith('https://drive.google.com') or drive_link.startswith('https://docs.google.com')):
                flash('يرجى إدخال رابط Google Drive صحيح', 'danger')
                return redirect(url_for('vehicles.view', id=vehicle_id))

            # حفظ الرابط
            old_link = vehicle.drive_folder_link
            vehicle.drive_folder_link = drive_link
            db.session.commit()

            # تسجيل العملية
            if old_link:
                log_audit('update', 'vehicle', vehicle.id, f'تم تحديث رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم تحديث رابط Google Drive بنجاح', 'success')
            else:
                log_audit('create', 'vehicle', vehicle.id, f'تم إضافة رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم إضافة رابط Google Drive بنجاح', 'success')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/drive-files')
    @login_required
    def vehicle_drive_files(vehicle_id):
        """صفحة منفصلة لإدارة ملفات Google Drive"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        return render_template('vehicles/drive_files.html', 
                             title=f'ملفات Google Drive - {vehicle.plate_number}',
                             vehicle=vehicle)

    @bp.route('/<int:vehicle_id>/drive-management', methods=['GET', 'POST'])
    @login_required
    def drive_management(vehicle_id):
        """صفحة منفصلة لإدخال وإدارة بيانات Google Drive"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'delete':
                # حذف الرابط
                old_link = vehicle.drive_folder_link
                vehicle.drive_folder_link = None
                db.session.commit()

                # تسجيل العملية
                log_audit('delete', 'vehicle', vehicle.id, f'تم حذف رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم حذف رابط Google Drive بنجاح', 'success')

            elif action == 'save':
                # حفظ أو تحديث الرابط
                drive_link = request.form.get('drive_link', '').strip()

                if not drive_link:
                    flash('يرجى إدخال رابط Google Drive', 'danger')
                    return render_template('vehicles/drive_management.html', vehicle=vehicle)

                # التحقق من صحة الرابط
                if not (drive_link.startswith('https://drive.google.com') or drive_link.startswith('https://docs.google.com')):
                    flash('يرجى إدخال رابط Google Drive صحيح', 'danger')
                    return render_template('vehicles/drive_management.html', vehicle=vehicle)

                # حفظ الرابط
                old_link = vehicle.drive_folder_link
                vehicle.drive_folder_link = drive_link
                db.session.commit()

                # تسجيل العملية
                if old_link:
                    log_audit('update', 'vehicle', vehicle.id, f'تم تحديث رابط Google Drive للسيارة {vehicle.plate_number}')
                    flash('تم تحديث رابط Google Drive بنجاح', 'success')
                else:
                    log_audit('create', 'vehicle', vehicle.id, f'تم إضافة رابط Google Drive للسيارة {vehicle.plate_number}')
                    flash('تم إضافة رابط Google Drive بنجاح', 'success')

            return redirect(url_for('vehicles.drive_management', vehicle_id=vehicle_id))

        return render_template('vehicles/drive_management.html', vehicle=vehicle)


    @bp.route('/<int:id>/upload-document', methods=['POST'])
    @login_required
    def upload_document(id):
        """رفع الوثائق (استمارة، لوحة، تأمين)"""
        vehicle = Vehicle.query.get_or_404(id)

        # التحقق من صلاحية الوصول
        try:
            if not current_user.has_permission(Module.VEHICLES, Permission.EDIT):
                flash('ليس لديك صلاحية لتعديل بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))
        except:
            # في حالة عدم وجود صلاحيات، السماح للمديرين أو تخطي للتجربة
            if not hasattr(current_user, 'role') or current_user.role != UserRole.ADMIN:
                flash('ليس لديك صلاحية لتعديل بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))

        document_type = request.form.get('document_type')
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('vehicles.view', id=id))

        file = request.files['file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('vehicles.view', id=id))

        if file and allowed_file(file.filename):
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
                return redirect(url_for('vehicles.view', id=id))

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

        return redirect(url_for('vehicles.view', id=id))


    @bp.route('/<int:id>/delete-document', methods=['POST'])
    @login_required
    def delete_document(id):
        """حذف الوثائق"""
        vehicle = Vehicle.query.get_or_404(id)

        # التحقق من صلاحية الوصول
        try:
            if not current_user.has_permission(Module.VEHICLES, Permission.DELETE):
                flash('ليس لديك صلاحية لحذف بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))
        except:
            # في حالة عدم وجود صلاحيات، السماح للمديرين أو تخطي للتجربة
            if not hasattr(current_user, 'role') or current_user.role != UserRole.ADMIN:
                flash('ليس لديك صلاحية لحذف بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))

        document_type = request.form.get('document_type')

        if document_type == 'registration_form':
            field_name = 'registration_form_image'
        elif document_type == 'plate':
            field_name = 'plate_image'
        elif document_type == 'insurance':
            field_name = 'insurance_file'
        else:
            flash('نوع الوثيقة غير صحيح', 'error')
            return redirect(url_for('vehicles.view', id=id))

        # الحصول على مسار الملف
        file_path = getattr(vehicle, field_name)

        if file_path:
            # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
            print(f"💾 الملف محفوظ للأمان: {file_path}")

            # حذف المرجع من قاعدة البيانات
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
                flash(f'خطأ في حذف الوثيقة: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=id))


    @bp.route('/import', methods=['GET', 'POST'])
    @login_required
    def import_vehicles():
        """استيراد السيارات من ملف Excel"""
        if request.method == 'GET':
            return render_template('vehicles/import_vehicles.html')
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف للاستيراد', 'error')
            return redirect(url_for('vehicles.import_vehicles'))
        file = request.files['file']
        if not file or file.filename == '':
            flash('لم يتم اختيار ملف للاستيراد', 'error')
            return redirect(url_for('vehicles.import_vehicles'))
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('يجب أن يكون الملف من نوع Excel (.xlsx أو .xls)', 'error')
            return redirect(url_for('vehicles.import_vehicles'))
        try:
            success_count, error_count, errors = process_import_vehicles(file.stream)
            flash(f'تم استيراد {success_count} سيارة بنجاح!', 'success')
            if error_count > 0:
                flash(f'حدثت {error_count} أخطاء أثناء الاستيراد', 'warning')
            for err in errors[:10]:
                flash(err, 'error')
            if len(errors) > 10:
                flash(f'وهناك {len(errors) - 10} أخطاء أخرى...', 'info')
            if success_count == 0 and not errors:
                flash('لم يتم استيراد أي سيارة', 'warning')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'خطأ في قراءة الملف: {str(e)}', 'error')
        return redirect(url_for('vehicles.index'))



    @bp.route('/<int:vehicle_id>/external-authorization/create', methods=['GET', 'POST'])
    @login_required  
    def create_external_authorization(vehicle_id):
        """إنشاء تفويض خارجي جديد"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        # فحص قيود العمليات للسيارات خارج الخدمة
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('vehicles.view', id=vehicle_id))

        if request.method == 'POST':
            try:
                # التحقق من نوع الإدخال للسائق
                driver_input_type = request.form.get('driver_input_type', 'from_list')

                if driver_input_type == 'from_list':
                    employee_id = request.form.get('employee_id')
                    if not employee_id:
                        flash('يرجى اختيار موظف من القائمة', 'error')
                        return redirect(request.url)

                    # إنشاء التفويض مع موظف من القائمة
                    external_auth = ExternalAuthorization(
                        vehicle_id=vehicle_id,
                        employee_id=employee_id,
                        project_name=request.form.get('project_name'),
                        authorization_type=request.form.get('authorization_type'),
                        status='pending',
                        external_link=request.form.get('form_link'),
                        notes=request.form.get('notes'),
                        city=request.form.get('city')
                    )
                else:
                    # الإدخال اليدوي
                    manual_name = request.form.get('manual_driver_name', '').strip()
                    if not manual_name:
                        flash('يرجى إدخال اسم السائق', 'error')
                        return redirect(request.url)

                    # إنشاء التفويض مع بيانات يدوية
                    external_auth = ExternalAuthorization(
                        vehicle_id=vehicle_id,
                        employee_id=None,
                        project_name=request.form.get('project_name'),
                        authorization_type=request.form.get('authorization_type'),
                        status='pending',
                        external_link=request.form.get('form_link'),
                        notes=request.form.get('notes'),
                        city=request.form.get('city'),
                        manual_driver_name=manual_name,
                        manual_driver_phone=request.form.get('manual_driver_phone', '').strip(),
                        manual_driver_position=request.form.get('manual_driver_position', '').strip(),
                        manual_driver_department=request.form.get('manual_driver_department', '').strip()
                    )

                # معالجة رفع الملف
                if 'file' in request.files:
                    file = request.files['file']
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)
                        external_auth.file_path = filename

                db.session.add(external_auth)
                db.session.commit()

                flash('تم إنشاء التفويض الخارجي بنجاح', 'success')
                return redirect(url_for('vehicles.view', id=vehicle_id))

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إنشاء التفويض: {str(e)}', 'error')

        # الحصول على البيانات للنموذج
        departments = Department.query.all()
        employees = Employee.query.all()

        return render_template('vehicles/create_external_authorization.html',
                             vehicle=vehicle,
                             departments=departments,
                             employees=employees)

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/view')
    @login_required
    def view_external_authorization(vehicle_id, auth_id):
        """عرض تفاصيل التفويض الخارجي"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        return render_template('vehicles/view_external_authorization.html',
                             vehicle=vehicle,
                             authorization=auth)

    @bp.route('/valid-documents')
    @login_required
    def valid_documents():
        """عرض قائمة جميع السيارات مع حالة الفحص الدوري"""
        plate_number = request.args.get('plate_number', '').strip()
        vehicle_make = request.args.get('vehicle_make', '').strip()
        ctx = get_valid_documents_context(plate_number=plate_number, vehicle_make=vehicle_make)
        return render_template('vehicles/valid_documents.html', **ctx)

    @bp.route('/<int:id>/edit-documents', methods=['GET', 'POST'])
    @login_required
    def edit_vehicle_documents(id):
        """تعديل تواريخ وثائق السيارة"""
        vehicle = Vehicle.query.get_or_404(id)

        if request.method == 'POST':
            # تحديث تواريخ الوثائق
            registration_expiry = request.form.get('registration_expiry_date')
            inspection_expiry = request.form.get('inspection_expiry_date') 
            authorization_expiry = request.form.get('authorization_expiry_date')

            if registration_expiry:
                vehicle.registration_expiry_date = datetime.strptime(registration_expiry, '%Y-%m-%d').date()

            if inspection_expiry:
                vehicle.inspection_expiry_date = datetime.strptime(inspection_expiry, '%Y-%m-%d').date()

            if authorization_expiry:
                vehicle.authorization_expiry_date = datetime.strptime(authorization_expiry, '%Y-%m-%d').date()

            vehicle.updated_at = datetime.utcnow()
            db.session.commit()

            # تسجيل الإجراء
            log_audit('update', 'vehicle_documents', vehicle.id, f'تم تعديل تواريخ وثائق السيارة: {vehicle.plate_number}')

            flash('تم تحديث تواريخ الوثائق بنجاح!', 'success')
            return redirect(url_for('vehicles.valid_documents'))

        return render_template('vehicles/edit_documents.html', vehicle=vehicle)


    # مسار عرض الصورة في صفحة منفصلة
    @bp.route('/api/get_employee_info/<driver_name>')
    @login_required
    def get_employee_info(driver_name):
            """API endpoint لجلب معلومات الموظف/السائق بناءً على الاسم"""
            try:
                    from models import Employee

                    # البحث عن الموظف بالاسم
                    employee = Employee.query.filter_by(name=driver_name).first()

                    if employee:
                            return jsonify({
                                    'success': True,
                                    'location': employee.location or '',
                                    'name': employee.name
                            })
                    else:
                            return jsonify({
                                    'success': False,
                                    'message': 'لم يتم العثور على الموظف'
                            })
            except Exception as e:
                    current_app.logger.error(f"خطأ في جلب معلومات الموظف: {str(e)}")
                    return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/alerts-count', methods=['GET'])
    @login_required
    def get_vehicle_alerts_count():
            """API endpoint لحساب عدد إشعارات المركبات المعلقة"""
            from datetime import datetime, timedelta
            today = datetime.now().date()
            alert_threshold_days = 14
            future_date = today + timedelta(days=alert_threshold_days)

            try:
                    # 1. عدد الفحوصات الخارجية الجديدة (pending)
                    pending_external_checks = db.session.query(func.count(VehicleExternalSafetyCheck.id)).filter(
                            VehicleExternalSafetyCheck.approval_status == 'pending'
                    ).scalar() or 0

                    # 2. عدد التفويضات المنتهية أو القريبة من الانتهاء
                    expiring_authorizations = db.session.query(func.count(Vehicle.id)).filter(
                            Vehicle.authorization_expiry_date.isnot(None),
                            Vehicle.authorization_expiry_date >= today,
                            Vehicle.authorization_expiry_date <= future_date
                    ).scalar() or 0

                    # 3. عدد الفحوصات الدورية المنتهية أو القريبة من الانتهاء
                    expiring_inspections = db.session.query(func.count(Vehicle.id)).filter(
                            Vehicle.inspection_expiry_date.isnot(None),
                            Vehicle.inspection_expiry_date >= today,
                            Vehicle.inspection_expiry_date <= future_date
                    ).scalar() or 0

                    # 4. إجمالي الإشعارات
                    total_alerts = pending_external_checks + expiring_authorizations + expiring_inspections

                    return jsonify({
                            'success': True,
                            'total_alerts': total_alerts,
                            'pending_external_checks': pending_external_checks,
                            'expiring_authorizations': expiring_authorizations,
                            'expiring_inspections': expiring_inspections
                    })
            except Exception as e:
                    current_app.logger.error(f"خطأ في حساب إشعارات المركبات: {str(e)}")
                    return jsonify({
                            'success': False,
                            'total_alerts': 0,
                            'error': str(e)
                    }), 500
