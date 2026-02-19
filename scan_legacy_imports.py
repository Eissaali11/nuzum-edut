"""
Legacy Import Scanner & Fixer for Domain-Driven Design Migration
Scans routes/ directory for imports from root models.py and provides fix recommendations
"""

import os
import re
from pathlib import Path

# Mapping of models to their domain locations
MODEL_DOMAIN_MAP = {
    # Vehicle models
    'Vehicle': 'modules.vehicles.domain.models',
    'VehicleRental': 'modules.vehicles.domain.models',
    'VehicleWorkshop': 'modules.vehicles.domain.models',
    'VehicleWorkshopImage': 'modules.vehicles.domain.models',
    'VehicleProject': 'modules.vehicles.domain.models',
    'VehicleHandover': 'modules.vehicles.domain.models',
    'VehicleHandoverImage': 'modules.vehicles.domain.models',
    'VehicleAccident': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleAccidentImage': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleMaintenance': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleMaintenanceImage': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleChecklist': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleChecklistItem': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleChecklistImage': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleDamageMarker': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleFuelConsumption': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleSafetyCheck': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehiclePeriodicInspection': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleExternalSafetyCheck': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleSafetyImage': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleInspectionRecord': 'modules.vehicles.domain.vehicle_maintenance_models',
    'VehicleInspectionImage': 'modules.vehicles.domain.vehicle_maintenance_models',
    
    # Employee models
    'Employee': 'modules.employees.domain.models',
    'Department': 'modules.employees.domain.models',
    'Attendance': 'modules.employees.domain.models',
    'Salary': 'modules.employees.domain.models',
    'Document': 'modules.employees.domain.models',
    'Nationality': 'modules.employees.domain.models',
    'EmployeeLocation': 'modules.employees.domain.models',
    'employee_departments': 'modules.employees.domain.models',
    'employee_geofences': 'modules.employees.domain.models',
}

def scan_file(filepath):
    """Scan a single file for legacy imports"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all 'from models import' lines
    import_pattern = r'^from models import (.+)$'
    matches = re.finditer(import_pattern, content, re.MULTILINE)
    
    legacy_imports = []
    for match in matches:
        imports_str = match.group(1)
        line_num = content[:match.start()].count('\n') + 1
        
        # Parse the imports
        imports = [i.strip() for i in imports_str.split(',')]
        
        # Check which imports should be migrated
        for imp in imports:
            if imp in MODEL_DOMAIN_MAP:
                legacy_imports.append({
                    'model': imp,
                    'domain': MODEL_DOMAIN_MAP[imp],
                    'line': line_num
                })
    
    return legacy_imports

def scan_routes_directory():
    """Scan all files in routes/ directory"""
    routes_dir = Path('routes')
    results = {}
    
    for py_file in routes_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        
        legacy = scan_file(py_file)
        if legacy:
            results[str(py_file)] = legacy
    
    return results

def generate_report():
    """Generate comprehensive report"""
    print("="*80)
    print("LEGACY IMPORT SCANNER - Domain-Driven Design Migration")
    print("="*80)
    
    results = scan_routes_directory()
    
    if not results:
        print("\n✅ No legacy imports found! All files are using domain-specific imports.")
        return
    
    print(f"\n⚠️  Found {len(results)} files with legacy imports from root models.py\n")
    
    # Group by domain
    by_domain = {}
    total_imports = 0
    
    for filepath, imports in results.items():
        for imp in imports:
            domain = imp['domain']
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append({
                'file': filepath,
                'model': imp['model'],
                'line': imp['line']
            })
            total_imports += 1
    
    print(f"Total legacy imports to fix: {total_imports}\n")
    print("-"*80)
    
    # Print grouped by domain
    for domain, items in sorted(by_domain.items()):
        print(f"\n📦 {domain}")
        print(f"   {len(items)} import(s) to migrate")
        
        files = {}
        for item in items:
            if item['file'] not in files:
                files[item['file']] = []
            files[item['file']].append(item['model'])
        
        for filepath, models in sorted(files.items()):
            print(f"   • {filepath}: {', '.join(models)}")
    
    print("\n" + "="*80)
    print("RECOMMENDED ACTION")
    print("="*80)
    print("""
Instead of:
    from models import Vehicle, Employee, VehicleAccident

Use:
    from modules.vehicles.domain.models import Vehicle
    from modules.employees.domain.models import Employee  
    from modules.vehicles.domain.vehicle_maintenance_models import VehicleAccident

OR keep using root models.py (it re-exports everything):
    from models import Vehicle, Employee, VehicleAccident
    # This works because models.py acts as a Central Registry

NOTE: The current approach (importing from root models.py) is VALID because
models.py re-exports all domain models. However, for true DDD separation,
direct domain imports are preferred.
""")
    
    print("\n" + "="*80)
    print("FILES REQUIRING ATTENTION")
    print("="*80)
    
    for filepath in sorted(results.keys()):
        print(f"\n📄 {filepath}")
        for imp in results[filepath]:
            print(f"   Line {imp['line']}: {imp['model']} → {imp['domain']}")

if __name__ == "__main__":
    generate_report()
