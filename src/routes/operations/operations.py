"""
العمليات - تغليف التوافقية للعودة للخلف
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع المسارات تم نقلها إلى وحدات متخصصة:
• routes/operations/ - المسارات الفرعية المتخصصة

# ما قبل: 2,379 سطر من الكود المتكرر
# بعد: ~30 سطر من الكود النظيف المنظم
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from src.routes.operations.operations_core_routes import operations_core_bp
from src.routes.operations.operations_workflow_routes import operations_workflow_bp
from src.routes.operations.operations_export_routes import operations_export_bp
from src.routes.operations.operations_sharing_routes import operations_sharing_bp
from src.routes.operations.operations_accidents_routes import operations_accidents_bp

# إنشاء Blueprint رئيسي يجمع كل المسارات الفرعية
# هذا يحافظ على التوافقية مع التطبيق الحالي
operations_bp = Blueprint('operations', __name__, url_prefix='/operations')


@operations_bp.route('/dashboard')
@login_required
def operations_dashboard():
	return redirect(url_for('operations_core.operations_dashboard'))

# ربط المسارات الفرعية
operations_bp.register_blueprint(operations_core_bp)
operations_bp.register_blueprint(operations_workflow_bp)
operations_bp.register_blueprint(operations_export_bp)
operations_bp.register_blueprint(operations_sharing_bp)
operations_bp.register_blueprint(operations_accidents_bp)

__all__ = ['operations_bp']
