"""
إدارة العقارات - Blueprint مركزي
يجمع كل المسارات الفرعية لـ properties
"""

from flask import Blueprint
from routes.properties_mgmt.properties_helpers import (
    allowed_file, 
    process_and_save_image, 
    process_and_save_contract,
    get_property_stats,
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS
)

def register_properties_routes(app):
    """تسجيل مسارات العقارات المستأجرة"""
    # استيراد المسارات الأصلية كبديل مؤقت
    try:
        from routes.properties import properties_bp
        app.register_blueprint(properties_bp)
    except ImportError:
        pass

__all__ = [
    'register_properties_routes',
    'allowed_file',
    'process_and_save_image',
    'process_and_save_contract',
    'get_property_stats'
]
