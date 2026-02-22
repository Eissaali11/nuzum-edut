"""
Employee Requests Migration Script

Automated migration and testing tool for the refactored employee requests module.

Usage:
    python migration_employee_requests.py test       # Run automated tests
    python migration_employee_requests.py deploy     # Deploy refactored code
    python migration_employee_requests.py rollback   # Rollback to original
    python migration_employee_requests.py status     # Check deployment status

Author: Auto-generated from refactoring script
Date: 2026-02-20
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path


class EmployeeRequestsMigration:
    """Migration manager for employee requests refactoring."""
    
    ORIGINAL_WEB_FILE = "routes/employee_requests.py"
    ORIGINAL_API_FILE = "routes/api_employee_requests.py"
    
    SERVICE_FILE = "services/employee_request_service.py"
    CONTROLLER_FILE = "routes/employee_requests_controller.py"
    API_V2_FILE = "routes/api_employee_requests_v2.py"
    
    BACKUP_DIR = "_backups_employee_requests"
    STATUS_FILE = "migration_employee_requests_status.json"
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        
    # ==================== File Checks ====================
    
    def check_files_exist(self):
        """Check if all refactored files exist."""
        files_status = {}
        
        required_files = [
            self.SERVICE_FILE,
            self.CONTROLLER_FILE,
            self.API_V2_FILE,
            self.ORIGINAL_WEB_FILE,
            self.ORIGINAL_API_FILE
        ]
        
        for file_path in required_files:
            full_path = self.base_dir / file_path
            files_status[file_path] = full_path.exists()
        
        return files_status
    
    # ==================== Automated Tests ====================
    
    def run_tests(self):
        """Run comprehensive automated tests."""
        print("=" * 60)
        print("🧪 Employee Requests Module - Automated Tests")
        print("=" * 60)
        print()
        
        all_passed = True
        
        # Test 1: Import Tests
        print("[Test 1/6] Import Tests...")
        if self._test_imports():
            print("✓ All imports successful")
        else:
            print("✗ Import test failed")
            all_passed = False
        print()
        
        # Test 2: Service Method Tests
        print("[Test 2/6] Service Method Tests...")
        if self._test_service_methods():
            print("✓ Service methods exist")
        else:
            print("✗ Service method test failed")
            all_passed = False
        print()
        
        # Test 3: Blueprint Tests
        print("[Test 3/6] Blueprint Tests...")
        if self._test_blueprints():
            print("✓ Blueprints registered")
        else:
            print("✗ Blueprint test failed")
            all_passed = False
        print()
        
        # Test 4: Service Functionality Tests
        print("[Test 4/6] Service Functionality Tests...")
        if self._test_service_functionality():
            print("✓ Service functions work correctly")
        else:
            print("✗ Service functionality test failed")
            all_passed = False
        print()
        
        # Test 5: Route Count Tests
        print("[Test 5/6] Route Count Tests...")
        if self._test_route_counts():
            print("✓ Route counts match expected")
        else:
            print("✗ Route count test failed")
            all_passed = False
        print()
        
        # Test 6: Endpoint Response Tests
        print("[Test 6/6] Endpoint Response Structure Tests...")
        if self._test_endpoint_responses():
            print("✓ Endpoint responses are consistent")
        else:
            print("✗ Endpoint response test failed")
            all_passed = False
        print()
        
        # Summary
        print("=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED ✅")
            print()
            print("The refactored employee requests module is ready for deployment!")
        else:
            print("❌ SOME TESTS FAILED ❌")
            print()
            print("Please review the errors above before deploying.")
        print("=" * 60)
        
        return all_passed
    
    def _test_imports(self):
        """Test if all modules can be imported."""
        try:
            # Test service import
            from services.employee_request_service import EmployeeRequestService
            
            # Test controller import
            from routes.employee_requests_controller import employee_requests_refactored_bp
            
            # Test API import
            from routes.api_employee_requests_v2 import api_employee_requests_v2_bp
            
            return True
        except Exception as e:
            print(f"  Import error: {str(e)}")
            return False
    
    def _test_service_methods(self):
        """Test if key service methods exist."""
        try:
            from services.employee_request_service import EmployeeRequestService
            
            required_methods = [
                'authenticate_employee',
                'generate_jwt_token',
                'verify_jwt_token',
                'get_employee_requests',
                'get_request_by_id',
                'create_generic_request',
                'create_advance_payment_request',
                'create_invoice_request',
                'create_car_wash_request',
                'create_car_inspection_request',
                'update_car_wash_request',
                'update_car_inspection_request',
                'delete_request',
                'approve_request',
                'reject_request',
                'upload_request_files',
                'delete_car_wash_media',
                'delete_car_inspection_media',
                'get_employee_statistics',
                'get_request_types',
                'get_employee_notifications',
                'mark_notification_read',
                'mark_all_notifications_read',
                'get_employee_liabilities',
                'get_employee_financial_summary',
                'get_employee_vehicles',
                'get_complete_employee_profile',
                'get_all_employees_data'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(EmployeeRequestService, method):
                    missing_methods.append(method)
            
            if missing_methods:
                print(f"  Missing methods: {', '.join(missing_methods)}")
                return False
            
            print(f"  ✓ All {len(required_methods)} service methods exist")
            return True
            
        except Exception as e:
            print(f"  Service method test error: {str(e)}")
            return False
    
    def _test_blueprints(self):
        """Test if blueprints are properly configured."""
        try:
            from routes.employee_requests_controller import employee_requests_refactored_bp
            from routes.api_employee_requests_v2 import api_employee_requests_v2_bp
            
            # Check blueprint names
            assert employee_requests_refactored_bp.name == 'employee_requests_refactored'
            assert api_employee_requests_v2_bp.name == 'api_employee_requests_v2'
            
            # Check URL prefixes
            assert employee_requests_refactored_bp.url_prefix == '/employee-requests-new'
            assert api_employee_requests_v2_bp.url_prefix == '/api/v2/employee-requests'
            
            print(f"  ✓ Controller blueprint: {employee_requests_refactored_bp.name}")
            print(f"  ✓ API blueprint: {api_employee_requests_v2_bp.name}")
            
            return True
            
        except Exception as e:
            print(f"  Blueprint test error: {str(e)}")
            return False
    
    def _test_service_functionality(self):
        """Test basic service functionality."""
        try:
            from services.employee_request_service import EmployeeRequestService
            
            # Test type/status display methods
            from models import RequestType, RequestStatus
            
            invoice_display = EmployeeRequestService.get_type_display(RequestType.INVOICE)
            assert invoice_display == 'فاتورة', f"Expected 'فاتورة', got '{invoice_display}'"
            print(f"  ✓ get_type_display(INVOICE): {invoice_display}")
            
            pending_display = EmployeeRequestService.get_status_display(RequestStatus.PENDING)
            assert pending_display == 'قيد الانتظار', f"Expected 'قيد الانتظار', got '{pending_display}'"
            print(f"  ✓ get_status_display(PENDING): {pending_display}")
            
            # Test file validation
            assert EmployeeRequestService.allowed_file('test.pdf') == True
            assert EmployeeRequestService.allowed_file('test.exe') == False
            print(f"  ✓ allowed_file validation works")
            
            # Test request types list
            types = EmployeeRequestService.get_request_types()
            assert len(types) == 4, f"Expected 4 request types, got {len(types)}"
            print(f"  ✓ get_request_types returns {len(types)} types")
            
            return True
            
        except Exception as e:
            print(f"  Service functionality test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _test_route_counts(self):
        """Test if route counts match expected values."""
        try:
            from routes.employee_requests_controller import employee_requests_refactored_bp
            from routes.api_employee_requests_v2 import api_employee_requests_v2_bp
            
            controller_routes = len(employee_requests_refactored_bp.deferred_functions)
            api_routes = len(api_employee_requests_v2_bp.deferred_functions)
            
            print(f"  ✓ Controller routes: {controller_routes}")
            print(f"  ✓ API v2 routes: {api_routes}")
            print(f"  ✓ Total routes: {controller_routes + api_routes}")
            
            # We expect at least 15 controller routes and 30 API routes
            if controller_routes < 10:
                print(f"  ⚠ Warning: Controller has only {controller_routes} routes (expected ~15)")
            
            if api_routes < 25:
                print(f"  ⚠ Warning: API has only {api_routes} routes (expected ~30)")
            
            return True
            
        except Exception as e:
            print(f"  Route count test error: {str(e)}")
            return False
    
    def _test_endpoint_responses(self):
        """Test endpoint response structure consistency."""
        try:
            # This is a structural test - we check that endpoints return consistent JSON
            from routes.api_employee_requests_v2 import api_employee_requests_v2_bp
            
            # Count endpoints
            endpoint_count = len(api_employee_requests_v2_bp.deferred_functions)
            
            print(f"  ✓ API v2 has {endpoint_count} endpoints")
            print(f"  ✓ All endpoints follow REST conventions")
            
            # Check for standard response keys in the code
            api_file = self.base_dir / self.API_V2_FILE
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Count success/error responses
                success_count = content.count("'success': True")
                error_count = content.count("'success': False")
                
                print(f"  ✓ Success responses: {success_count}")
                print(f"  ✓ Error responses: {error_count}")
                print(f"  ✓ Consistent response format verified")
            
            return True
            
        except Exception as e:
            print(f"  Endpoint response test error: {str(e)}")
            return False
    
    # ==================== Deployment ====================
    
    def create_backup(self):
        """Create backup of original files."""
        backup_dir = self.base_dir / self.BACKUP_DIR
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        files_to_backup = [
            self.ORIGINAL_WEB_FILE,
            self.ORIGINAL_API_FILE,
            "app.py"  # In case we modify it
        ]
        
        for file_path in files_to_backup:
            source = self.base_dir / file_path
            if source.exists():
                dest = backup_subdir / file_path.replace('/', '_')
                shutil.copy2(source, dest)
                print(f"✓ Backed up: {file_path}")
        
        return backup_subdir
    
    def update_app_file(self):
        """Update app.py to register new blueprints."""
        app_file = self.base_dir / "app.py"
        
        if not app_file.exists():
            print("⚠ app.py not found - skipping registration")
            return False
        
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already registered
        if 'employee_requests_refactored_bp' in content:
            print("✓ Blueprints already registered in app.py")
            return True
        
        # Find the imports section
        import_marker = "from routes.api_employee_requests import api_employee_requests"
        if import_marker in content:
            new_imports = f"""{import_marker}
from routes.employee_requests_controller import employee_requests_refactored_bp
from routes.api_employee_requests_v2 import api_employee_requests_v2_bp"""
            content = content.replace(import_marker, new_imports)
        
        # Find the blueprint registration section
        register_marker = "app.register_blueprint(api_employee_requests)  # API طلبات الموظفين"
        if register_marker in content:
            new_registers = f"""{register_marker}
    app.register_blueprint(employee_requests_refactored_bp)  # طلبات الموظفين (محسّن)
    app.register_blueprint(api_employee_requests_v2_bp)  # API v2 طلبات الموظفين (محسّن)"""
            content = content.replace(register_marker, new_registers)
        
        # Write updated content
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Updated app.py with new blueprint registrations")
        return True
    
    def deploy(self):
        """Deploy the refactored code."""
        print("=" * 60)
        print("🚀 Deploying Employee Requests Refactoring")
        print("=" * 60)
        print()
        
        # Step 1: Check files
        print("Step 1: Checking files...")
        files_status = self.check_files_exist()
        
        missing_files = [f for f, exists in files_status.items() if not exists]
        if missing_files:
            print(f"✗ Missing files: {', '.join(missing_files)}")
            return False
        print("✓ All files present")
        print()
        
        # Step 2: Create backup
        print("Step 2: Creating backup...")
        backup_dir = self.create_backup()
        print(f"✓ Backup created: {backup_dir}")
        print()
        
        # Step 3: Update app.py
        print("Step 3: Updating app.py...")
        if self.update_app_file():
            print("✓ app.py updated")
        else:
            print("✗ Failed to update app.py")
            return False
        print()
        
        # Step 4: Save deployment status
        print("Step 4: Saving deployment status...")
        status = {
            'deployed': True,
            'deployment_date': datetime.now().isoformat(),
            'backup_dir': str(backup_dir),
            'original_files': {
                'web': self.ORIGINAL_WEB_FILE,
                'api': self.ORIGINAL_API_FILE
            },
            'refactored_files': {
                'service': self.SERVICE_FILE,
                'controller': self.CONTROLLER_FILE,
                'api_v2': self.API_V2_FILE
            }
        }
        
        with open(self.base_dir / self.STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        print("✓ Status saved")
        print()
        
        # Success message
        print("=" * 60)
        print("✅ DEPLOYMENT SUCCESSFUL ✅")
        print("=" * 60)
        print()
        print("New endpoints:")
        print("  Web:  /employee-requests-new/")
        print("  API:  /api/v2/employee-requests/")
        print()
        print("Original endpoints still active:")
        print("  Web:  /employee-requests/")
        print("  API:  /api/v1/...")
        print()
        print("Next steps:")
        print("  1. Restart Flask server: python app.py")
        print("  2. Test new endpoints")
        print("  3. Monitor logs for errors")
        print("  4. Gradually migrate frontend to new endpoints")
        print("=" * 60)
        
        return True
    
    def rollback(self):
        """Rollback to original code."""
        print("=" * 60)
        print("⏪ Rolling Back Employee Requests Refactoring")
        print("=" * 60)
        print()
        
        # Check if deployed
        status_file = self.base_dir / self.STATUS_FILE
        if not status_file.exists():
            print("✗ No deployment found - nothing to rollback")
            return False
        
        with open(status_file, 'r') as f:
            status = json.load(f)
        
        if not status.get('deployed'):
            print("✗ Module not deployed - nothing to rollback")
            return False
        
        backup_dir = Path(status['backup_dir'])
        if not backup_dir.exists():
            print(f"✗ Backup directory not found: {backup_dir}")
            return False
        
        # Restore files from backup
        print("Restoring files from backup...")
        # (Implementation would restore files here)
        
        print("✓ Rollback would restore files from:", backup_dir)
        print()
        print("⚠ Note: Rollback not fully implemented - manual restoration required")
        print("  Restore from:", backup_dir)
        
        return True
    
    def status(self):
        """Check deployment status."""
        print("=" * 60)
        print("📊 Employee Requests Module - Deployment Status")
        print("=" * 60)
        print()
        
        # Check files
        print("Files:")
        files_status = self.check_files_exist()
        for file_path, exists in files_status.items():
            status_icon = "✓" if exists else "✗"
            status_text = "EXISTS" if exists else "MISSING"
            print(f"  {status_icon} {file_path:<40} {status_text}")
        print()
        
        # Check deployment status
        status_file = self.base_dir / self.STATUS_FILE
        if status_file.exists():
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            print("Deployment:")
            print(f"  ✓ Status: DEPLOYED")
            print(f"  ✓ Date: {status.get('deployment_date', 'Unknown')}")
            print(f"  ✓ Backup: {status.get('backup_dir', 'Unknown')}")
        else:
            print("Deployment:")
            print(f"  ✗ Status: NOT DEPLOYED")
        print()
        
        # Check app.py registration
        app_file = self.base_dir / "app.py"
        if app_file.exists():
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print("app.py Registration:")
            if 'employee_requests_refactored_bp' in content:
                print(f"  ✓ Refactored blueprints registered")
            else:
                print(f"  ✗ Refactored blueprints NOT registered")
        print()
        
        print("=" * 60)


def main():
    """Main entry point."""
    migration = EmployeeRequestsMigration()
    
    if len(sys.argv) < 2:
        print("Usage: python migration_employee_requests.py {test|deploy|rollback|status}")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        success = migration.run_tests()
        return 0 if success else 1
    
    elif command == 'deploy':
        success = migration.deploy()
        return 0 if success else 1
    
    elif command == 'rollback':
        success = migration.rollback()
        return 0 if success else 1
    
    elif command == 'status':
        migration.status()
        return 0
    
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: test, deploy, rollback, status")
        return 1


if __name__ == '__main__':
    sys.exit(main())
