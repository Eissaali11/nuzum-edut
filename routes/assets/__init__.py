"""
قسم الأصول (Assets) - الجوالات والأجهزة
═══════════════════════════════════════════════════════════════════════════

يضم:
- إدارة الهواتف والأجهزة المحمولة (Mobile Devices)
- توزيع الأجهزة (Device Assignment)
- إدارة الجهاز (Device Management)

═══════════════════════════════════════════════════════════════════════════
"""

assets_blueprints = []

try:
    from .mobile_devices import mobile_devices_bp
    assets_blueprints.append(mobile_devices_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد mobile_devices: {e}")

try:
    from .device_assignment import device_assignment_bp
    assets_blueprints.append(device_assignment_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد device_assignment: {e}")

try:
    from .device_management import device_management_bp
    assets_blueprints.append(device_management_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد device_management: {e}")

__all__ = [
    'assets_blueprints'
]
