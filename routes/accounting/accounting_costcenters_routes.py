"""
════════════════════════════════════════════════════════════════════════════
💰 مراكز التكلفة - Cost Centers Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: إدارة مراكزالتكلفة والميزانيات
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc

from core.extensions import db
from models import UserRole, Module
from models_accounting import CostCenter, TransactionEntry
from forms.accounting import CostCenterForm
from utils.helpers import log_activity

# ────────────────────────────────────────────────────────────────────────────
# 🔧 إنشاء البلوبرينت
# ────────────────────────────────────────────────────────────────────────────

costcenters_bp = Blueprint(
    'accounting_costcenters',
    __name__,
    url_prefix='/accounting'
)


# ════════════════════════════════════════════════════════════════════════════
# 💰 مراكز التكلفة والعمليات
# ════════════════════════════════════════════════════════════════════════════

@costcenters_bp.route('/cost-centers')
@login_required
def cost_centers():
    """عرض مراكز التكلفة"""
    if not (current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    cost_centers = CostCenter.query.order_by(CostCenter.code).all()
    main_centers = CostCenter.query.filter_by(parent_id=None).order_by(CostCenter.code).all()
    
    total_budget = sum(center.budget_amount or 0 for center in cost_centers)
    total_expenses = sum(center.get_actual_expenses() for center in cost_centers)
    active_centers = len([c for c in cost_centers if c.is_active])
    
    return render_template('accounting/cost_centers.html',
                         cost_centers=cost_centers,
                         main_centers=main_centers,
                         total_budget=total_budget,
                         total_expenses=total_expenses,
                         active_centers=active_centers)


@costcenters_bp.route('/cost-centers/create', methods=['GET', 'POST'])
@login_required
def create_cost_center():
    """إنشاء مركز تكلفة جديد"""
    if not current_user.role == UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('accounting_costcenters.cost_centers'))
    
    if request.method == 'POST':
        try:
            center = CostCenter()
            center.code = request.form.get('code')
            center.name = request.form.get('name')
            center.name_en = request.form.get('name_en', '')
            center.description = request.form.get('description', '')
            
            parent_id = request.form.get('parent_id')
            if parent_id and parent_id != '':
                center.parent_id = int(parent_id)
            
            budget_amount = request.form.get('budget_amount', '0')
            center.budget_amount = float(budget_amount) if budget_amount else 0
            
            center.is_active = request.form.get('is_active') == 'on'
            
            db.session.add(center)
            db.session.commit()
            
            log_activity(f"إنشاء مركز تكلفة: {center.code} - {center.name}")
            flash(f'تم إنشاء مركز التكلفة {center.name} بنجاح', 'success')
            
            return redirect(url_for('accounting_costcenters.cost_centers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في إنشاء مركز التكلفة: {str(e)}', 'danger')
            return redirect(request.url)
    
    parent_centers = CostCenter.query.filter_by(is_active=True).order_by(CostCenter.code).all()
    
    return render_template('accounting/create_cost_center.html',
                         parent_centers=parent_centers)


@costcenters_bp.route('/cost-centers/<int:center_id>')
@login_required
def view_cost_center(center_id):
    """عرض تفاصيل مركز التكلفة"""
    if not (current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    center = CostCenter.query.get_or_404(center_id)
    
    transactions = TransactionEntry.query.filter_by(cost_center_id=center_id).order_by(
        desc(TransactionEntry.created_at)).limit(20).all()
    
    return render_template('accounting/view_cost_center.html',
                         center=center,
                         transactions=transactions)


@costcenters_bp.route('/cost-centers/<int:center_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_cost_center(center_id):
    """تعديل مركز التكلفة"""
    if not current_user.role == UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('accounting_costcenters.cost_centers'))
    
    center = CostCenter.query.get_or_404(center_id)
    
    form = CostCenterForm(obj=center)
    
    parent_centers = CostCenter.query.filter(
        CostCenter.id != center.id, 
        CostCenter.is_active == True
    ).order_by(CostCenter.code).all()
    
    form.parent_id.choices = [('', 'لا يوجد')] + [(c.id, f"{c.code} - {c.name}") for c in parent_centers]
    
    if form.validate_on_submit():
        try:
            if form.parent_id.data and form.parent_id.data == center.id:
                flash('لا يمكن اختيار المركز نفسه كمركز أب', 'danger')
                return render_template('accounting/edit_cost_center.html', form=form, center=center)
            
            center.code = form.code.data
            center.name = form.name.data
            center.name_en = form.name_en.data or ''
            center.description = form.description.data or ''
            center.parent_id = form.parent_id.data
            center.budget_amount = form.budget_amount.data or 0
            center.is_active = form.is_active.data
            center.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            log_activity(f"تعديل مركز تكلفة: {center.code} - {center.name}")
            flash(f'تم تعديل مركز التكلفة {center.name} بنجاح', 'success')
            
            return redirect(url_for('accounting_costcenters.view_cost_center', center_id=center.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في تعديل مركز التكلفة: {str(e)}', 'danger')
    
    return render_template('accounting/edit_cost_center.html', form=form, center=center)


@costcenters_bp.route('/cost-centers/<int:center_id>/delete', methods=['POST'])
@login_required
def delete_cost_center(center_id):
    """حذف مركز التكلفة"""
    if not current_user.role == UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('accounting_costcenters.cost_centers'))
    
    try:
        center = CostCenter.query.get_or_404(center_id)
        
        children_count = CostCenter.query.filter_by(parent_id=center_id).count()
        if children_count > 0:
            flash(f'لا يمكن حذف المركز لأنه يحتوي على {children_count} مركز فرعي', 'danger')
            return redirect(url_for('accounting_costcenters.view_cost_center', center_id=center_id))
        
        transactions_count = TransactionEntry.query.filter_by(cost_center_id=center_id).count()
        if transactions_count > 0:
            flash(f'لا يمكن حذف المركز لأنه يحتوي على {transactions_count} معاملة مسجلة', 'danger')
            return redirect(url_for('accounting_costcenters.view_cost_center', center_id=center_id))
        
        center_info = f"{center.code} - {center.name}"
        
        db.session.delete(center)
        db.session.commit()
        
        log_activity(f"حذف مركز تكلفة: {center_info}")
        flash(f'تم حذف مركز التكلفة {center_info} بنجاح', 'success')
        return redirect(url_for('accounting_costcenters.cost_centers'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ في حذف مركز التكلفة: {str(e)}', 'danger')
        return redirect(url_for('accounting_costcenters.view_cost_center', center_id=center_id))
