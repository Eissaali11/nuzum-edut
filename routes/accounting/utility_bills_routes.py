"""
Utility bills routes for properties accounting.
"""

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from core.extensions import db
from routes.accounting.accounting_helpers import get_arabic_months, parse_non_negative_float
from modules.properties.domain.models import RentalProperty, PropertyUtilityBill


utility_bp = Blueprint('utility_bills', __name__, url_prefix='/accounting/utility-bills')


@utility_bp.route('/')
@login_required
def index():
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    properties = RentalProperty.query.filter_by(status='active').order_by(RentalProperty.city).all()

    props_data = []
    for prop in properties:
        resident_count = len([r for r in prop.residents if r.status == 'active'])
        bills = PropertyUtilityBill.query.filter_by(
            property_id=prop.id, month=month, year=year
        ).all()
        bills_dict = {b.bill_type: float(b.amount) for b in bills}
        bills_total = sum(bills_dict.values())

        props_data.append({
            'property': prop,
            'residents': resident_count,
            'bills': bills_dict,
            'bills_total': bills_total,
            'monthly_rent': prop.annual_rent_amount / 12 if prop.annual_rent_amount else 0,
            'per_person': (bills_total + (prop.annual_rent_amount / 12 if prop.annual_rent_amount else 0)) / resident_count if resident_count > 0 else 0,
        })

    months = get_arabic_months()

    return render_template(
        'accounting/utility_bills/index.html',
        properties=props_data,
        months=months,
        selected_month=month,
        selected_year=year,
        bill_types=PropertyUtilityBill.BILL_TYPES,
    )


@utility_bp.route('/<int:property_id>', methods=['GET', 'POST'])
@login_required
def manage(property_id):
    prop = RentalProperty.query.get_or_404(property_id)
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    if request.method == 'POST':
        month = int(request.form.get('month', month))
        year = int(request.form.get('year', year))

        for bill_type in PropertyUtilityBill.BILL_TYPES.keys():
            amount_str = request.form.get(f'amount_{bill_type}', '0')
            amount = parse_non_negative_float(amount_str, default=0)

            existing = PropertyUtilityBill.query.filter_by(
                property_id=property_id, bill_type=bill_type, month=month, year=year
            ).first()

            if amount > 0:
                if existing:
                    existing.amount = amount
                else:
                    bill = PropertyUtilityBill(
                        property_id=property_id,
                        bill_type=bill_type,
                        month=month,
                        year=year,
                        amount=amount,
                    )
                    db.session.add(bill)
            elif existing:
                db.session.delete(existing)

        db.session.commit()
        flash('تم حفظ الفواتير بنجاح', 'success')
        return redirect(url_for('utility_bills.index', month=month, year=year))

    bills = PropertyUtilityBill.query.filter_by(
        property_id=property_id, month=month, year=year
    ).all()
    bills_dict = {b.bill_type: float(b.amount) for b in bills}

    residents = [r for r in prop.residents if r.status == 'active']

    months = get_arabic_months()

    return render_template(
        'accounting/utility_bills/manage.html',
        prop=prop,
        bills=bills_dict,
        residents=residents,
        months=months,
        selected_month=month,
        selected_year=year,
        bill_types=PropertyUtilityBill.BILL_TYPES,
    )
