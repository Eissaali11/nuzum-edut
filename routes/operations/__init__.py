"""
Operations registrar:
Central aggregator for all operations-related routes
"""

from .operations import operations_bp

# Import all sub-blueprints
from .operations_core_routes import operations_core_bp
from .operations_workflow_routes import operations_workflow_bp
from .operations_export_routes import operations_export_bp
from .operations_sharing_routes import operations_sharing_bp
from .operations_accidents_routes import operations_accidents_bp
from .operations_workflow_routes import create_operation_request


def register_operations_routes(bp):
    """
    تسجيل جميع مسارات العمليات في Blueprint رئيسي
    
    Args:
        bp: Flask Blueprint الرئيسي لتسجيل المسارات فيه
    """
    
    # تسجيل جميع فرق العمليات
    bp.register_blueprint(operations_core_bp)
    bp.register_blueprint(operations_workflow_bp)
    bp.register_blueprint(operations_export_bp)
    bp.register_blueprint(operations_sharing_bp)
    bp.register_blueprint(operations_accidents_bp)


__all__ = [
    'operations_bp',
    'register_operations_routes',
    'create_operation_request',
]
