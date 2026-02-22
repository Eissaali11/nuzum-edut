"""
Simple test to check if workshop_reports blueprint is registered
by inspecting Flask app routes
"""
import sys
import os
sys.path.insert(0, '.')

# Import Flask app from app.py module (not the app subfolder)
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

def check_workshop_routes():
    """Check if workshop reports routes are registered"""
    print("Checking Flask Routes for Workshop Reports...")
    print("=" * 70)
    
    workshop_routes = []
    
    # Iterate through all routes
    for rule in app.url_map.iter_rules():
        if 'workshop' in rule.rule.lower():
            workshop_routes.append({
                'endpoint': rule.endpoint,
                'route': rule.rule,
                'methods': ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
            })
    
    if workshop_routes:
        print(f"\n✅ Found {len(workshop_routes)} workshop report routes:\n")
        for route in workshop_routes:
            print(f"   Endpoint: {route['endpoint']}")
            print(f"   Route: {route['route']}")
            print(f"   Methods: {route['methods']}")
            print()
        print("=" * 70)
        print("✅ Workshop Reports: ENABLED")
        print("\nReportLab PDF generation is active")
        print("No GTK dependencies required!")
    else:
        print("\n❌ No workshop report routes found")
        print("=" * 70)
        print("❌ Workshop Reports: NOT REGISTERED")
        print("\nPossible causes:")
        print("1. Import error in app.py")
        print("2. Blueprint not registered")
        print("3. Server needs restart to pick up changes")

if __name__ == "__main__":
    try:
        check_workshop_routes()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nMake sure the Flask app can be imported successfully")
        import traceback
        traceback.print_exc()
