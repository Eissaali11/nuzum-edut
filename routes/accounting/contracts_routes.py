"""
Contracts management routes for profitability accounting.
"""

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from core.extensions import db
from models import Department
from modules.accounting.domain.profitability_models import ProjectContract
from services.accounting_service import AccountingService

contracts_bp = Blueprint('contracts', __name__, url_prefix='/accounting/contracts')


@contracts_bp.route('/')
@login_required
def index():
    contracts = ProjectContract.query.order_by(ProjectContract.created_at.desc()).all()
    total_resources = sum(c.resources.count() for c in contracts)
    return render_template('accounting/contracts/index.html', contracts=contracts, total_resources=total_resources)


@contracts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        department_id = request.form.get('department_id', type=int)
        client_name = request.form.get('client_name', '').strip()
        contract_number = request.form.get('contract_number', '').strip()
        contract_type = request.form.get('contract_type', 'manpower')
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        notes = request.form.get('notes', '').strip()

        if not department_id or not client_name or not start_date_str:
            flash('يرجى تعبئة جميع الحقول المطلوبة', 'danger')
            return render_template('accounting/contracts/form.html', departments=departments, contract=None)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            flash('تاريخ غير صالح', 'danger')
            return render_template('accounting/contracts/form.html', departments=departments, contract=None)

        contract = ProjectContract(
            department_id=department_id,
            client_name=client_name,
            contract_number=contract_number or None,
            contract_type=contract_type,
            start_date=start_date,
            end_date=end_date,
            status='active',
            notes=notes or None,
        )
        db.session.add(contract)
        db.session.commit()
        flash('تم إنشاء العقد بنجاح', 'success')
        return redirect(url_for('contracts.resources', contract_id=contract.id))

    return render_template('accounting/contracts/form.html', departments=departments, contract=None)


@contracts_bp.route('/<int:contract_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(contract_id):
    contract = ProjectContract.query.get_or_404(contract_id)
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        contract.department_id = request.form.get('department_id', type=int)
        contract.client_name = request.form.get('client_name', '').strip()
        contract.contract_number = request.form.get('contract_number', '').strip() or None
        contract.contract_type = request.form.get('contract_type', 'manpower')
        contract.status = request.form.get('status', 'active')
        contract.notes = request.form.get('notes', '').strip() or None

        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        try:
            contract.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            contract.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            flash('تاريخ غير صالح', 'danger')
            return render_template('accounting/contracts/form.html', departments=departments, contract=contract)

        db.session.commit()
        flash('تم تحديث العقد بنجاح', 'success')
        return redirect(url_for('contracts.index'))

    return render_template('accounting/contracts/form.html', departments=departments, contract=contract)


@contracts_bp.route('/<int:contract_id>/delete', methods=['POST'])
@login_required
def delete(contract_id):
    contract = ProjectContract.query.get_or_404(contract_id)
    db.session.delete(contract)
    db.session.commit()
    flash('تم حذف العقد', 'success')
    return redirect(url_for('contracts.index'))


@contracts_bp.route('/<int:contract_id>/resources', methods=['GET', 'POST'])
@login_required
def resources(contract_id):
    contract = ProjectContract.query.get_or_404(contract_id)

    if request.method == 'POST':
        ok, message = AccountingService.save_contract_resources(contract, request.form)
        flash(message, 'success' if ok else 'danger')
        return redirect(url_for('contracts.resources', contract_id=contract.id))

    view_data = AccountingService.get_contract_resources_view_data(contract)

    return render_template(
        'accounting/contracts/resources.html',
        contract=contract,
        employees_data=view_data['employees_data'],
    )


@contracts_bp.route('/<int:contract_id>/invoice', methods=['GET'])
@login_required
def invoice_issue(contract_id):
    contract = ProjectContract.query.get_or_404(contract_id)
    return render_template('accounting/contracts/invoice_issue.html', contract=contract)
