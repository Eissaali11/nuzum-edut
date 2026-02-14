"""
مسارات المركبات — تعريف الـ Blueprint وتسجيل المسارات فقط.
جميع معالجات المسارات في presentation/web/ (vehicle_routes, vehicle_extra_routes, handover_routes, workshop_routes, accident_routes).
"""
from flask import Blueprint
import logging
import traceback

# Setup logger for diagnostic
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

vehicles_bp = Blueprint("vehicles", __name__)

# ========== DIAGNOSTIC WIRING WITH TRY-EXCEPT BLOCKS ==========

# 1. Handover Routes
try:
    from presentation.web.vehicles.handover_routes import register_handover_routes
    register_handover_routes(vehicles_bp)
    logger.info("✅ Handover routes registered successfully")
except Exception as e:
    logger.error("❌ FAILED to register handover routes:")
    logger.error(traceback.format_exc())
    print("\n" + "="*80)
    print("❌ ERROR: Failed to import/register HANDOVER routes")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")

# 2. Workshop Routes
try:
    from presentation.web.vehicles.workshop_routes import register_workshop_routes
    register_workshop_routes(vehicles_bp)
    logger.info("✅ Workshop routes registered successfully")
except Exception as e:
    logger.error("❌ FAILED to register workshop routes:")
    logger.error(traceback.format_exc())
    print("\n" + "="*80)
    print("❌ ERROR: Failed to import/register WORKSHOP routes")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")

# 3. Accident Routes
try:
    from presentation.web.vehicles.accident_routes import register_accident_routes
    register_accident_routes(vehicles_bp)
    logger.info("✅ Accident routes registered successfully")
except Exception as e:
    logger.error("❌ FAILED to register accident routes:")
    logger.error(traceback.format_exc())
    print("\n" + "="*80)
    print("❌ ERROR: Failed to import/register ACCIDENT routes")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")

# 4. Main Vehicle Routes
try:
    from presentation.web.vehicle_routes import register_vehicle_routes
    register_vehicle_routes(vehicles_bp)
    logger.info("✅ Main vehicle routes registered successfully")
except Exception as e:
    logger.error("❌ FAILED to register main vehicle routes:")
    logger.error(traceback.format_exc())
    print("\n" + "="*80)
    print("❌ ERROR: Failed to import/register MAIN VEHICLE routes")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")

# 5. Extra Vehicle Routes
try:
    from presentation.web.vehicles.vehicle_extra_routes import register_vehicle_extra_routes
    register_vehicle_extra_routes(vehicles_bp)
    logger.info("✅ Vehicle extra routes registered successfully")
except Exception as e:
    logger.error("❌ FAILED to register vehicle extra routes:")
    logger.error(traceback.format_exc())
    print("\n" + "="*80)
    print("❌ ERROR: Failed to import/register VEHICLE EXTRA routes")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")

# Log all registered routes for verification
logger.info("="*60)
logger.info("Vehicles Blueprint Route Summary:")
logger.info(f"Total routes registered: {len(vehicles_bp.url_map._rules) if hasattr(vehicles_bp, 'url_map') else 'N/A'}")
logger.info("="*60)
