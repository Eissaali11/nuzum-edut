"""
Vehicles Module - Complete vehicle management system.

This module contains the entire vehicles feature including:
- Domain models (domain/)
- Application services (application/)
- Presentation routes and templates (presentation/)

The module is registered with Flask in app.py via the vehicles_bp blueprint.
"""

from modules.vehicles.presentation.web.main_routes import get_vehicles_blueprint

# Blueprint factory is exported from this module for easy import in main app
__all__ = ['get_vehicles_blueprint']
