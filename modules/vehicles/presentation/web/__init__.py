"""Blueprint المركبات — طبقة العرض (Vertical Slice). مسارات التسليم والورشة تُسجَّل على vehicles_bp من routes/vehicles (استيراد مباشر من handover_routes/workshop_routes لتجنب استيراد دائري)."""
from .routes import vehicles_web_bp

__all__ = ["vehicles_web_bp"]
