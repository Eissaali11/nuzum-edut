"""Mobile documents UI routes extracted from routes/mobile.py."""

from datetime import datetime, timedelta

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from src.core.extensions import db
from models import Department, Document, Employee


def register_documents_ui_routes(mobile_bp):
    @mobile_bp.route('/documents/dashboard')
    @login_required
    def documents_dashboard():
        """داش بورد لعرض إحصائيات الوثائق"""
        current_date = datetime.now().date()

        expiring_date = current_date + timedelta(days=60)
        warning_date = current_date + timedelta(days=30)

        total_documents = Document.query.count()
        expired_documents = Document.query.filter(Document.expiry_date < current_date).count()
        expiring_soon = Document.query.filter(
            Document.expiry_date >= current_date,
            Document.expiry_date <= warning_date,
        ).count()
        expiring_later = Document.query.filter(
            Document.expiry_date > warning_date,
            Document.expiry_date <= expiring_date,
        ).count()
        valid_documents = Document.query.filter(Document.expiry_date > expiring_date).count()

        expired_docs = (
            Document.query.join(Employee)
            .filter(Document.expiry_date < current_date)
            .order_by(Document.expiry_date.desc())
            .limit(10)
            .all()
        )

        expiring_docs = (
            Document.query.join(Employee)
            .filter(Document.expiry_date >= current_date, Document.expiry_date <= warning_date)
            .order_by(Document.expiry_date)
            .limit(10)
            .all()
        )

        document_types_stats = db.session.query(
            Document.document_type,
            func.count(Document.id).label('count'),
        ).group_by(Document.document_type).all()

        department_stats = (
            db.session.query(
                Department.name,
                func.count(Document.id).label('count'),
            )
            .select_from(Department)
            .join(Employee, Employee.department_id == Department.id)
            .join(Document, Document.employee_id == Employee.id)
            .group_by(Department.name)
            .order_by(func.count(Document.id).desc())
            .limit(5)
            .all()
        )

        return render_template(
            'mobile/documents_dashboard.html',
            total_documents=total_documents,
            expired_documents=expired_documents,
            expiring_soon=expiring_soon,
            expiring_later=expiring_later,
            valid_documents=valid_documents,
            expired_docs=expired_docs,
            expiring_docs=expiring_docs,
            document_types_stats=document_types_stats,
            department_stats=department_stats,
            current_date=current_date,
        )

    @mobile_bp.route('/documents')
    @login_required
    def documents():
        """صفحة الوثائق للنسخة المحمولة"""
        employee_id_str = request.args.get('employee_id', '')
        employee_id = int(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
        document_type = request.args.get('document_type')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = 20

        employees = Employee.query.order_by(Employee.name).all()
        query = Document.query.join(Employee)

        if employee_id:
            query = query.filter(Document.employee_id == employee_id)

        if document_type:
            document_type_mapping = {
                'هوية': 'national_id',
                'جواز سفر': 'passport',
                'رخصة قيادة': 'driving_license',
                'إقامة': 'residence_permit',
                'تأمين صحي': 'health_insurance',
                'شهادة عمل': 'work_certificate',
                'أخرى': 'other',
            }
            english_type = document_type_mapping.get(document_type, document_type)
            query = query.filter(Document.document_type == english_type)

        current_date = datetime.now().date()

        if status:
            if status == 'valid':
                valid_date = current_date + timedelta(days=60)
                query = query.filter(Document.expiry_date >= valid_date)
            elif status == 'expiring':
                expiring_min_date = current_date
                expiring_max_date = current_date + timedelta(days=60)
                query = query.filter(
                    Document.expiry_date >= expiring_min_date,
                    Document.expiry_date <= expiring_max_date,
                )
            elif status == 'expired':
                query = query.filter(Document.expiry_date < current_date)

        query = query.order_by(Document.expiry_date)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        documents_items = pagination.items

        for document in documents_items:
            if document.expiry_date:
                if document.expiry_date >= current_date + timedelta(days=60):
                    document.status = 'valid'
                elif document.expiry_date >= current_date:
                    document.status = 'expiring'
                else:
                    document.status = 'expired'
            else:
                document.status = 'no_expiry'

            document_type_display = {
                'national_id': 'هوية وطنية',
                'passport': 'جواز سفر',
                'driving_license': 'رخصة قيادة',
                'residence_permit': 'إقامة',
                'health_insurance': 'تأمين صحي',
                'work_certificate': 'شهادة عمل',
                'other': 'أخرى',
            }
            document.document_type_display = document_type_display.get(document.document_type, document.document_type)

        valid_count = Document.query.filter(Document.expiry_date >= current_date + timedelta(days=60)).count()
        expiring_count = Document.query.filter(
            Document.expiry_date >= current_date,
            Document.expiry_date <= current_date + timedelta(days=60),
        ).count()
        expired_count = Document.query.filter(Document.expiry_date < current_date).count()
        total_count = Document.query.count()

        document_stats = {
            'valid': valid_count,
            'expiring': expiring_count,
            'expired': expired_count,
            'total': total_count,
        }

        return render_template(
            'mobile/documents.html',
            employees=employees,
            documents=documents_items,
            current_date=current_date,
            document_stats=document_stats,
            pagination=pagination,
        )

    @mobile_bp.route('/documents/add', methods=['GET', 'POST'])
    @login_required
    def add_document():
        """إضافة وثيقة جديدة للنسخة المحمولة"""
        employees = Employee.query.order_by(Employee.name).all()
        current_date = datetime.now().date()

        document_types = [
            'هوية وطنية',
            'إقامة',
            'جواز سفر',
            'رخصة قيادة',
            'شهادة صحية',
            'شهادة تأمين',
            'أخرى',
        ]

        return render_template(
            'mobile/add_document.html',
            employees=employees,
            document_types=document_types,
            current_date=current_date,
        )

    @mobile_bp.route('/documents/<int:document_id>')
    @login_required
    def document_details(document_id):
        """تفاصيل وثيقة للنسخة المحمولة"""
        document = Document.query.get_or_404(document_id)
        current_date = datetime.now().date()

        days_remaining = None
        if document.expiry_date:
            days_remaining = (document.expiry_date - current_date).days

        return render_template(
            'mobile/document_details.html',
            document=document,
            current_date=current_date,
            days_remaining=days_remaining,
        )

    @mobile_bp.route('/documents/<int:document_id>/update-expiry', methods=['POST'])
    @login_required
    def update_document_expiry(document_id):
        """تحديث تاريخ انتهاء الوثيقة"""
        document = Document.query.get_or_404(document_id)

        try:
            expiry_date_str = request.form.get('expiry_date')
            notes = request.form.get('notes', '').strip()

            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                document.expiry_date = expiry_date

                if notes:
                    if document.notes:
                        document.notes = f"{document.notes}\n\n[تحديث {datetime.now().strftime('%Y-%m-%d')}]: {notes}"
                    else:
                        document.notes = f"[تحديث {datetime.now().strftime('%Y-%m-%d')}]: {notes}"

                db.session.commit()
                flash('تم تحديث تاريخ انتهاء الوثيقة بنجاح', 'success')
            else:
                flash('يرجى إدخال تاريخ الانتهاء', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث الوثيقة: {str(e)}', 'error')

        return redirect(url_for('mobile.document_details', document_id=document_id))
