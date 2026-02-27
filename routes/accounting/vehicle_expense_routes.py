"""
Vehicle expense routes for accounting extended blueprint.
"""

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from models import Vehicle, Module
from models_accounting import (
    Vendor,
)
from forms.accounting import VehicleExpenseForm
from services.accounting_service import AccountingService
from utils.helpers import log_activity


def register_vehicle_expense_routes(accounting_ext_bp):
    @accounting_ext_bp.route('/vehicle-expenses', methods=['GET', 'POST'])
    @login_required
    def vehicle_expenses():
        if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
            flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
            return redirect(url_for('dashboard.index'))

        form = VehicleExpenseForm()

        vehicles = Vehicle.query.all()
        vendors = Vendor.query.filter_by(is_active=True).all()

        form.vehicle_id.choices = [(v.id, f"{v.plate_number} - {v.make} {v.model}") for v in vehicles]
        form.vendor_id.choices = [('', 'لا يوجد')] + [(v.id, v.name) for v in vendors]

        if form.validate_on_submit():
            ok, payload = AccountingService.create_vehicle_expense_transaction(form_data=form, user_id=current_user.id)
            if ok:
                log_activity(
                    f"إضافة مصروف مركبة: {payload['vehicle_plate']} - {payload['amount']} ريال"
                )
                flash('تم إضافة مصروف المركبة بنجاح', 'success')
                return redirect(url_for('accounting.transactions'))

            flash(payload, 'danger')

        return render_template('accounting/vehicle/expense_form.html', form=form)
