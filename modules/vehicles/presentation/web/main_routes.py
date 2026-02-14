"""
Vehicles Module Routes Factory
Blueprint creation and registration for the vehicles module.
This file replaces routes/vehicles.py with the new module structure.
"""
from flask import Blueprint
import logging
import traceback

# Setup logger for diagnostic
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_vehicles_blueprint():
    """
    Create and register the vehicles blueprint with all route handlers.
    
    Returns:
        Flask Blueprint configured with all vehicle routes (handover, workshop, 
        accident, main vehicle, extra routes).
    """
    vehicles_bp = Blueprint(
        "vehicles",
        __name__,
        template_folder="../templates",
    )

    # ========== DIAGNOSTIC WIRING WITH TRY-EXCEPT BLOCKS ==========

    # 1. Handover Routes
    try:
        from modules.vehicles.presentation.web.handover_routes import register_handover_routes
        register_handover_routes(vehicles_bp)
        logger.info("OK Handover routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register handover routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register HANDOVER routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # 2. Workshop Routes
    try:
        from modules.vehicles.presentation.web.workshop_routes import register_workshop_routes
        register_workshop_routes(vehicles_bp)
        logger.info("OK Workshop routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register workshop routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register WORKSHOP routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # 2b. Workshop Reports Routes
    try:
        from modules.vehicles.presentation.web.workshop_reports import register_workshop_reports_routes
        register_workshop_reports_routes(vehicles_bp)
        logger.info("OK Workshop reports routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register workshop reports routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register WORKSHOP REPORTS routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # 3. Accident Routes
    try:
        from modules.vehicles.presentation.web.accident_routes import register_accident_routes
        register_accident_routes(vehicles_bp)
        logger.info("OK Accident routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register accident routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register ACCIDENT routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # 4. Main Vehicle Routes
    try:
        from modules.vehicles.presentation.web.vehicle_routes import register_vehicle_routes
        register_vehicle_routes(vehicles_bp)
        logger.info("OK Main vehicle routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register main vehicle routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register MAIN VEHICLE routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # 5. Extra Vehicle Routes
    try:
        from modules.vehicles.presentation.web.vehicle_extra_routes import register_vehicle_extra_routes
        register_vehicle_extra_routes(vehicles_bp)
        logger.info("OK Vehicle extra routes registered successfully")
    except Exception as e:
        logger.error("ERROR failed to register vehicle extra routes:")
        logger.error(traceback.format_exc())
        print("\n" + "="*80)
        print("ERROR: Failed to import/register VEHICLE EXTRA routes")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

    # Log all registered routes for verification
    logger.info("="*60)
    logger.info("Vehicles Blueprint Route Summary:")
    logger.info(f"Total routes registered: {len(list(vehicles_bp.url_map._rules)) if hasattr(vehicles_bp, 'url_map') else 'N/A'}")
    logger.info("="*60)

    return vehicles_bp
