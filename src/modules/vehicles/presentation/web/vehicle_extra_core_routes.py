"""Core extra vehicle routes: documents, access, rental/project, reports."""

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required
from sqlalchemy import func, or_

from src.core.extensions import db
from src.core.domain.models import User
from src.forms.vehicle_forms import VehicleDocumentsForm
from src.modules.vehicles.application.vehicle_document_service import get_view_documents_context
from src.modules.vehicles.application.vehicle_export_service import build_vehicle_report_pdf
from src.modules.vehicles.domain.models import (
    Vehicle,
    VehicleProject,
    VehicleRental,
    VehicleWorkshop,
)
from src.utils.audit_logger import log_activity
from src.utils.vehicle_helpers import log_audit


def register_vehicle_extra_core_routes(bp):
    @bp.route('/v/<string:encoded_id>')
    @login_required
    def view_encoded(encoded_id):
        from src.utils.id_encoder import decode_vehicle_id

        try:
            vehicle_id = decode_vehicle_id(encoded_id)
            return redirect(url_for('vehicles.view', id=vehicle_id))
        except ValueError:
            flash('رابط غير صالح', 'error')
            return redirect(url_for('vehicles.index'))

    @bp.route('/documents/view/<int:id>', methods=['GET'])
    @login_required
    def view_documents(id):
        data = get_view_documents_context(id)
        if data is None:
            abort(404)
        return render_template('vehicles/views/view_documents.html', **data)

    @bp.route('/documents/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_documents(id):
        vehicle = Vehicle.query.get_or_404(id)
        form = VehicleDocumentsForm()
        from_operations = request.args.get('from_operations')
        operation_id = from_operations if from_operations else None

        if request.method == 'GET':
            form.authorization_expiry_date.data = vehicle.authorization_expiry_date
            form.registration_expiry_date.data = vehicle.registration_expiry_date
            form.inspection_expiry_date.data = vehicle.inspection_expiry_date

        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    vehicle.authorization_expiry_date = form.authorization_expiry_date.data
                    if not from_operations:
                        vehicle.registration_expiry_date = form.registration_expiry_date.data
                        vehicle.inspection_expiry_date = form.inspection_expiry_date.data
                else:
                    auth_date = request.form.get('authorization_expiry_date')
                    if auth_date:
                        vehicle.authorization_expiry_date = datetime.strptime(auth_date, '%Y-%m-%d').date()

                    if not from_operations:
                        reg_date = request.form.get('registration_expiry_date')
                        if reg_date:
                            vehicle.registration_expiry_date = datetime.strptime(reg_date, '%Y-%m-%d').date()

                        insp_date = request.form.get('inspection_expiry_date')
                        if insp_date:
                            vehicle.inspection_expiry_date = datetime.strptime(insp_date, '%Y-%m-%d').date()

                vehicle.updated_at = datetime.utcnow()

                if not from_operations or not operation_id:
                    db.session.commit()

                log_audit('update', 'vehicle_documents', vehicle.id, f'تم تحديث تواريخ وثائق المركبة: {vehicle.plate_number}')

                if from_operations:
                    flash('تم تحديد فترة التفويض وإنشاء سجل التسليم بنجاح!', 'success')
                    return redirect('/operations')

                flash('تم تحديث تواريخ الوثائق بنجاح!', 'success')
                return redirect(url_for('vehicles.view', id=id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ في تحديث التواريخ: {str(e)}', 'danger')

        return render_template(
            'vehicles/forms/edit_documents.html',
            form=form,
            vehicle=vehicle,
            from_operations=bool(from_operations),
            operation_id=operation_id,
        )

    @bp.route('/<int:id>/manage-user-access', methods=['POST'])
    @login_required
    def manage_user_access(id):
        vehicle = Vehicle.query.get_or_404(id)
        authorized_user_ids = request.form.getlist('authorized_users')

        vehicle.authorized_users.clear()
        if authorized_user_ids:
            authorized_users = User.query.filter(User.id.in_(authorized_user_ids)).all()
            for user in authorized_users:
                vehicle.authorized_users.append(user)

        db.session.commit()
        user_names = [user.name or user.username or user.email for user in vehicle.authorized_users]
        log_audit(
            'update',
            'vehicle_user_access',
            vehicle.id,
            f'تم تحديث وصول المستخدمين للمركبة {vehicle.plate_number}. المستخدمون: {", ".join(user_names) if user_names else "لا يوجد"}',
        )

        flash(f'تم تحديث إعدادات الوصول بنجاح! المستخدمون المخولون: {len(vehicle.authorized_users)}', 'success')
        return redirect(url_for('vehicles.edit', id=id))

    @bp.route('/<int:id>/rental/create', methods=['GET', 'POST'])
    @login_required
    def create_rental(id):
        vehicle = Vehicle.query.get_or_404(id)
        existing_rental = VehicleRental.query.filter_by(vehicle_id=id, is_active=True).first()
        if existing_rental and request.method == 'GET':
            flash('يوجد إيجار نشط بالفعل لهذه السيارة!', 'warning')
            return redirect(url_for('vehicles.view', id=id))

        if request.method == 'POST':
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date_str = request.form.get('end_date')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

            rental = VehicleRental(
                vehicle_id=id,
                start_date=start_date,
                end_date=end_date,
                monthly_cost=float(request.form.get('monthly_cost')),
                is_active=True,
                lessor_name=request.form.get('lessor_name'),
                lessor_contact=request.form.get('lessor_contact'),
                contract_number=request.form.get('contract_number'),
                city=request.form.get('city'),
                notes=request.form.get('notes'),
            )

            if existing_rental:
                existing_rental.is_active = False
                existing_rental.updated_at = datetime.utcnow()

            db.session.add(rental)
            vehicle.status = 'rented'
            vehicle.updated_at = datetime.utcnow()
            db.session.commit()

            log_audit('create', 'vehicle_rental', rental.id, f'تم إضافة معلومات إيجار للسيارة: {vehicle.plate_number}')
            flash('تم إضافة معلومات الإيجار بنجاح!', 'success')
            return redirect(url_for('vehicles.view', id=id))

        return render_template('vehicles/forms/rental_create.html', vehicle=vehicle)

    @bp.route('/rental/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_rental(id):
        rental = VehicleRental.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(rental.vehicle_id)

        if request.method == 'POST':
            rental.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date_str = request.form.get('end_date')
            rental.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            rental.monthly_cost = float(request.form.get('monthly_cost'))
            rental.is_active = bool(request.form.get('is_active'))
            rental.lessor_name = request.form.get('lessor_name')
            rental.lessor_contact = request.form.get('lessor_contact')
            rental.contract_number = request.form.get('contract_number')
            rental.city = request.form.get('city')
            rental.notes = request.form.get('notes')
            rental.updated_at = datetime.utcnow()

            vehicle.status = 'rented' if rental.is_active else 'available'
            vehicle.updated_at = datetime.utcnow()
            db.session.commit()

            log_audit('update', 'vehicle_rental', rental.id, f'تم تعديل معلومات إيجار السيارة: {vehicle.plate_number}')
            flash('تم تعديل معلومات الإيجار بنجاح!', 'success')
            return redirect(url_for('vehicles.view', id=vehicle.id))

        return render_template('vehicles/forms/rental_edit.html', rental=rental, vehicle=vehicle)

    @bp.route('/<int:id>/project/create', methods=['GET', 'POST'])
    @login_required
    def create_project(id):
        vehicle = Vehicle.query.get_or_404(id)
        existing_assignment = VehicleProject.query.filter_by(vehicle_id=id, is_active=True).first()
        if existing_assignment and request.method == 'GET':
            flash('هذه السيارة مخصصة بالفعل لمشروع نشط!', 'warning')
            return redirect(url_for('vehicles.view', id=id))

        if request.method == 'POST':
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date_str = request.form.get('end_date')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

            if existing_assignment:
                existing_assignment.is_active = False
                existing_assignment.updated_at = datetime.utcnow()

            project = VehicleProject(
                vehicle_id=id,
                project_name=request.form.get('project_name'),
                location=request.form.get('location'),
                manager_name=request.form.get('manager_name'),
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                notes=request.form.get('notes'),
            )
            db.session.add(project)

            vehicle.status = 'in_project'
            vehicle.updated_at = datetime.utcnow()
            db.session.commit()

            log_audit('create', 'vehicle_project', project.id, f'تم تخصيص السيارة {vehicle.plate_number} لمشروع {project.project_name}')
            flash('تم تخصيص السيارة للمشروع بنجاح!', 'success')
            return redirect(url_for('vehicles.view', id=id))

        return render_template('vehicles/forms/project_create.html', vehicle=vehicle)

    @bp.route('/project/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_project(id):
        project = VehicleProject.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(project.vehicle_id)

        if request.method == 'POST':
            project.project_name = request.form.get('project_name')
            project.location = request.form.get('location')
            project.manager_name = request.form.get('manager_name')
            project.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date_str = request.form.get('end_date')
            project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            project.is_active = bool(request.form.get('is_active'))
            project.notes = request.form.get('notes')
            project.updated_at = datetime.utcnow()

            if project.is_active:
                vehicle.status = 'in_project'
            else:
                active_rental = VehicleRental.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()
                vehicle.status = 'rented' if active_rental else 'available'
            vehicle.updated_at = datetime.utcnow()

            db.session.commit()
            log_audit('update', 'vehicle_project', project.id, f'تم تعديل تخصيص السيارة {vehicle.plate_number} للمشروع {project.project_name}')
            flash('تم تعديل تخصيص المشروع بنجاح!', 'success')
            return redirect(url_for('vehicles.view', id=vehicle.id))

        return render_template('vehicles/forms/project_edit.html', project=project, vehicle=vehicle)

    @bp.route('/reports')
    @login_required
    def reports():
        make_stats = db.session.query(Vehicle.make, func.count(Vehicle.id)).group_by(Vehicle.make).all()
        year_stats = db.session.query(Vehicle.year, func.count(Vehicle.id)).group_by(Vehicle.year).order_by(Vehicle.year).all()
        workshop_reason_stats = db.session.query(VehicleWorkshop.reason, func.count(VehicleWorkshop.id)).group_by(VehicleWorkshop.reason).all()
        top_maintenance_costs = (
            db.session.query(
                Vehicle.plate_number,
                Vehicle.make,
                Vehicle.model,
                func.sum(VehicleWorkshop.cost).label('total_cost'),
            )
            .join(VehicleWorkshop, Vehicle.id == VehicleWorkshop.vehicle_id)
            .group_by(Vehicle.id, Vehicle.plate_number, Vehicle.make, Vehicle.model)
            .order_by(func.sum(VehicleWorkshop.cost).desc())
            .limit(10)
            .all()
        )

        return render_template(
            'vehicles/reports.html',
            make_stats=make_stats,
            year_stats=year_stats,
            workshop_reason_stats=workshop_reason_stats,
            top_maintenance_costs=top_maintenance_costs,
        )

    @bp.route('/detailed')
    @login_required
    def detailed_list():
        status = request.args.get('status')
        make = request.args.get('make')
        year = request.args.get('year')
        project = request.args.get('project')
        location = request.args.get('location')
        sort = request.args.get('sort', 'plate_number')
        search = request.args.get('search', '')

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
                    Vehicle.color.ilike(f'%{search}%'),
                )
            )

        if project:
            vehicle_ids = [v[0] for v in db.session.query(VehicleProject.vehicle_id).filter_by(project_name=project, is_active=True).all()]
            query = query.filter(Vehicle.id.in_(vehicle_ids))

        if location:
            vehicle_ids = [v[0] for v in db.session.query(VehicleProject.vehicle_id).filter_by(location=location, is_active=True).all()]
            query = query.filter(Vehicle.id.in_(vehicle_ids))

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

        page = request.args.get('page', 1, type=int)
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        vehicles = pagination.items

        for vehicle in vehicles:
            vehicle.active_rental = VehicleRental.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()
            vehicle.latest_workshop = VehicleWorkshop.query.filter_by(vehicle_id=vehicle.id).order_by(VehicleWorkshop.entry_date.desc()).first()
            vehicle.active_project = VehicleProject.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()

        makes = [m[0] for m in db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()]
        years = [y[0] for y in db.session.query(Vehicle.year).distinct().order_by(Vehicle.year.desc()).all()]
        locations = [l[0] for l in db.session.query(VehicleProject.location).distinct().order_by(VehicleProject.location).all()]

        return render_template(
            'vehicles/detailed_list.html',
            vehicles=vehicles,
            pagination=pagination,
            makes=makes,
            years=years,
            locations=locations,
            total_count=Vehicle.query.count(),
            request=request,
        )

    @bp.route('/vehicle-report-pdf/<int:id>')
    @login_required
    def generate_vehicle_report_pdf(id):
        try:
            buffer, filename, mimetype = build_vehicle_report_pdf(id)
            if buffer is None:
                abort(404)
            return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء التقرير PDF: {str(e)}', 'danger')
            return redirect(url_for('vehicles.view', id=id))
