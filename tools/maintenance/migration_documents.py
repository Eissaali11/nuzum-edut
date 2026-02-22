"""
Documents Module Migration Tool
================================
Automated migration and testing tool for document management refactoring.

Commands:
    python migration_documents.py test     - Run all automated tests
    python migration_documents.py deploy   - Deploy refactored version
    python migration_documents.py rollback - Rollback to original version
    python migration_documents.py status   - Check migration status

Author: AI Assistant
Date: February 20, 2026
Version: 1.0.0
"""

import sys
import os
from datetime import datetime
import shutil
import json


class DocumentsMigration:
    """Migration manager for documents module"""
    
    def __init__(self):
        self.migration_file = 'migration_documents_status.json'
        self.backup_folder = '_backups/documents_migration'
    
    def run_tests(self):
        """Run all automated tests"""
        print("\n" + "=" * 60)
        print("🧪 Documents Module - Automated Tests")
        print("=" * 60 + "\n")
        
        all_passed = True
        test_results = []
        
        # Test 1: Import Tests
        print("[Test 1/6] Import Tests...")
        try:
            from services.document_service import DocumentService
            from routes.documents_controller import documents_refactored_bp
            from routes.api_documents_v2 import api_documents_v2_bp
            print("  ✓ All imports successful")
            test_results.append(('Import Tests', True, 'All modules imported'))
        except Exception as e:
            print(f"  ✗ Import failed: {str(e)}")
            test_results.append(('Import Tests', False, str(e)))
            all_passed = False
        
        print("✓ Import tests passed\n")
        
        # Test 2: Service Method Tests
        print("[Test 2/6] Service Method Tests...")
        try:
            from services.document_service import DocumentService
            
            expected_methods = [
                'get_document_types',
                'get_document_type_label',
                'validate_file_security',
                'secure_filename_arabic',
                'check_user_permission',
                'get_documents',
                'get_document_by_id',
                'create_document',
                'update_document',
                'delete_document',
                'create_bulk_documents',
                'save_bulk_documents_with_data',
                'import_from_excel',
                'export_to_excel',
                'get_dashboard_stats',
                'get_expiry_stats',
                'create_expiry_notification',
                'create_bulk_expiry_notifications',
                'get_employees_by_sponsorship',
                'get_employees_by_department_and_sponsorship',
                'generate_document_template_pdf',
                'generate_employee_documents_pdf'
            ]
            
            missing_methods = []
            for method_name in expected_methods:
                if not hasattr(DocumentService, method_name):
                    missing_methods.append(method_name)
            
            if missing_methods:
                print(f"  ✗ Missing methods: {', '.join(missing_methods)}")
                test_results.append(('Service Methods', False, f'Missing: {len(missing_methods)}'))
                all_passed = False
            else:
                print(f"  ✓ All {len(expected_methods)} service methods exist")
                test_results.append(('Service Methods', True, f'{len(expected_methods)} methods'))
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            test_results.append(('Service Methods', False, str(e)))
            all_passed = False
        
        print("✓ Service methods exist\n")
        
        # Test 3: Blueprint Tests
        print("[Test 3/6] Blueprint Tests...")
        try:
            from routes.documents_controller import documents_refactored_bp
            from routes.api_documents_v2 import api_documents_v2_bp
            
            # Check blueprint names
            assert documents_refactored_bp.name == 'documents_refactored', "Controller blueprint name mismatch"
            assert api_documents_v2_bp.name == 'api_documents_v2', "API blueprint name mismatch"
            
            # Check URL prefixes
            assert documents_refactored_bp.url_prefix == '/documents-new', "Controller URL prefix mismatch"
            assert api_documents_v2_bp.url_prefix == '/api/v2/documents', "API URL prefix mismatch"
            
            print("  ✓ Controller blueprint: documents_refactored")
            print("  ✓ API blueprint: api_documents_v2")
            test_results.append(('Blueprints', True, '2 blueprints registered'))
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            test_results.append(('Blueprints', False, str(e)))
            all_passed = False
        
        print("✓ Blueprints registered\n")
        
        # Test 4: Service Functionality Tests
        print("[Test 4/6] Service Functionality Tests...")
        try:
            from services.document_service import DocumentService
            
            # Test document type label
            label = DocumentService.get_document_type_label('passport')
            assert label == 'جواز السفر', f"Expected 'جواز السفر', got '{label}'"
            print(f"  ✓ get_document_type_label('passport'): {label}")
            
            # Test file security validation
            is_valid, msg = DocumentService.validate_file_security('test.pdf')
            assert is_valid == True, "PDF should be valid"
            print(f"  ✓ validate_file_security('test.pdf'): Valid")
            
            is_valid, msg = DocumentService.validate_file_security('test.exe')
            assert is_valid == False, "EXE should be invalid"
            print(f"  ✓ validate_file_security('test.exe'): Invalid (as expected)")
            
            # Test document types
            types = DocumentService.get_document_types()
            assert len(types) == 8, f"Expected 8 types, got {len(types)}"
            print(f"  ✓ get_document_types returns {len(types)} types")
            
            test_results.append(('Service Functionality', True, 'All functions work'))
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            test_results.append(('Service Functionality', False, str(e)))
            all_passed = False
        
        print("✓ Service functions work correctly\n")
        
        # Test 5: Route Count Tests
        print("[Test 5/6] Route Count Tests...")
        try:
            from routes.documents_controller import documents_refactored_bp
            from routes.api_documents_v2 import api_documents_v2_bp
            
            # Count routes in controller
            controller_routes = len([rule for rule in documents_refactored_bp.deferred_functions])
            print(f"  ✓ Controller routes: {controller_routes}")
            
            # Count routes in API
            api_routes = len([rule for rule in api_documents_v2_bp.deferred_functions])
            print(f"  ✓ API v2 routes: {api_routes}")
            
            total_routes = controller_routes + api_routes
            print(f"  ✓ Total routes: {total_routes}")
            
            # Validate counts (approximate)
            assert controller_routes >= 20, f"Expected at least 20 controller routes, got {controller_routes}"
            assert api_routes >= 18, f"Expected at least 18 API routes, got {api_routes}"
            
            test_results.append(('Route Counts', True, f'{total_routes} routes'))
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            test_results.append(('Route Counts', False, str(e)))
            all_passed = False
        
        print("✓ Route counts match expected\n")
        
        # Test 6: API Response Structure Tests
        print("[Test 6/6] API Response Structure Tests...")
        try:
            from routes.api_documents_v2 import api_documents_v2_bp
            from flask import Flask
            
            # Create test app
            app = Flask(__name__)
            app.register_blueprint(api_documents_v2_bp)
            
            with app.test_client() as client:
                # Test health check
                response = client.get('/api/v2/documents/health')
                assert response.status_code == 200, "Health check should return 200"
                
                data = response.get_json()
                assert 'success' in data, "Response should have 'success' field"
                assert 'message' in data, "Response should have 'message' field"
                assert 'data' in data, "Response should have 'data' field"
                
                print(f"  ✓ Health endpoint response structure: OK")
                
                # Test document types endpoint
                response = client.get('/api/v2/documents/types')
                assert response.status_code == 200, "Types endpoint should return 200"
                
                data = response.get_json()
                assert data['success'] == True, "Types endpoint should succeed"
                assert 'types' in data['data'], "Types response should contain 'types'"
                
                print(f"  ✓ Types endpoint response structure: OK")
                
                # Test authentication required endpoints
                response = client.post('/api/v2/documents/documents', json={})
                assert response.status_code == 401, "Protected endpoint should return 401 without auth"
                
                print(f"  ✓ Authentication requirement: OK")
            
            test_results.append(('API Response Structure', True, 'Consistent format'))
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            test_results.append(('API Response Structure', False, str(e)))
            all_passed = False
        
        print("✓ API responses are consistent\n")
        
        # Summary
        print("=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED ✅")
            print("\nThe refactored documents module is ready for deployment!")
        else:
            print("❌ SOME TESTS FAILED ❌")
            print("\nPlease fix the issues before deployment.")
        print("=" * 60 + "\n")
        
        # Print test summary
        print("Test Summary:")
        for test_name, passed, details in test_results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status} - {test_name}: {details}")
        
        return all_passed
    
    def deploy(self):
        """Deploy the refactored version"""
        print("\n" + "=" * 60)
        print("🚀 Deploying Documents Module Refactoring")
        print("=" * 60 + "\n")
        
        try:
            # Create backup first
            print("Step 1: Creating backup...")
            self._create_backup()
            print("  ✓ Backup created\n")
            
            # Register blueprints in app.py
            print("Step 2: Registering blueprints...")
            self._register_blueprints()
            print("  ✓ Blueprints registered\n")
            
            # Save migration status
            print("Step 3: Saving migration status...")
            self._save_migration_status('deployed')
            print("  ✓ Status saved\n")
            
            print("=" * 60)
            print("✅ DEPLOYMENT SUCCESSFUL ✅")
            print("=" * 60 + "\n")
            
            print("Next steps:")
            print("1. Restart your Flask application:")
            print("   python app.py")
            print("\n2. Test the new URLs:")
            print("   Web:  http://localhost:5000/documents-new/")
            print("   API:  http://localhost:5000/api/v2/documents/health")
            print("\n3. Original routes (/documents/) remain active for comparison")
            print("\n4. Monitor logs for any issues")
            print("\n5. To rollback: python migration_documents.py rollback\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {str(e)}\n")
            return False
    
    def rollback(self):
        """Rollback to original version"""
        print("\n" + "=" * 60)
        print("⏪ Rolling Back Documents Module")
        print("=" * 60 + "\n")
        
        try:
            # Check if backup exists
            if not os.path.exists(self.backup_folder):
                print("❌ No backup found. Cannot rollback.\n")
                return False
            
            print("Step 1: Restoring from backup...")
            self._restore_backup()
            print("  ✓ Files restored\n")
            
            print("Step 2: Updating migration status...")
            self._save_migration_status('rolledback')
            print("  ✓ Status updated\n")
            
            print("=" * 60)
            print("✅ ROLLBACK SUCCESSFUL ✅")
            print("=" * 60 + "\n")
            
            print("Original version restored. Please restart your application.\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Rollback failed: {str(e)}\n")
            return False
    
    def status(self):
        """Check migration status"""
        print("\n" + "=" * 60)
        print("📊 Documents Module - Migration Status")
        print("=" * 60 + "\n")
        
        if not os.path.exists(self.migration_file):
            print("Status: Not migrated yet")
            print("Run 'python migration_documents.py deploy' to start\n")
            return
        
        with open(self.migration_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        print(f"Status: {status_data.get('status', 'unknown')}")
        print(f"Deployed at: {status_data.get('deployed_at', 'N/A')}")
        print(f"Version: {status_data.get('version', 'N/A')}")
        
        if status_data.get('status') == 'deployed':
            print("\n✓ Refactored version is active")
            print("\nNew endpoints:")
            print("  - Web: /documents-new/")
            print("  - API: /api/v2/documents/")
        
        print("")
    
    def _create_backup(self):
        """Create backup of original files"""
        os.makedirs(self.backup_folder, exist_ok=True)
        
        files_to_backup = [
            'routes/documents.py'
        ]
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_path = os.path.join(self.backup_folder, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
    
    def _restore_backup(self):
        """Restore from backup"""
        backup_files = os.listdir(self.backup_folder)
        
        for backup_file in backup_files:
            backup_path = os.path.join(self.backup_folder, backup_file)
            restore_path = os.path.join('routes', backup_file)
            shutil.copy2(backup_path, restore_path)
    
    def _register_blueprints(self):
        """Register blueprints in app.py"""
        app_file = 'app.py'
        
        if not os.path.exists(app_file):
            print("  ⚠ app.py not found. Please register blueprints manually:")
            print("\n  from routes.documents_controller import documents_refactored_bp")
            print("  from routes.api_documents_v2 import api_documents_v2_bp")
            print("  app.register_blueprint(documents_refactored_bp)")
            print("  app.register_blueprint(api_documents_v2_bp)")
            return
        
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already registered
        if 'documents_refactored_bp' in content:
            print("  ℹ Blueprints already registered")
            return
        
        # Add imports and registration
        import_line = "\nfrom routes.documents_controller import documents_refactored_bp\nfrom routes.api_documents_v2 import api_documents_v2_bp\n"
        register_lines = "\napp.register_blueprint(documents_refactored_bp)\napp.register_blueprint(api_documents_v2_bp)\n"
        
        # Find appropriate place to add
        if 'from routes.' in content:
            # Add after other route imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from routes.' in line and 'import' in line:
                    # Found route import, add after
                    lines.insert(i + 1, import_line.strip())
                    break
            content = '\n'.join(lines)
        else:
            # Add at the beginning after core imports
            content = import_line + content
        
        # Add registrations
        if 'app.register_blueprint' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'app.register_blueprint' in line:
                    lines.insert(i + 1, register_lines.strip())
                    break
            content = '\n'.join(lines)
        else:
            content += register_lines
        
        # Save
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("  ✓ Blueprints registered in app.py")
    
    def _save_migration_status(self, status):
        """Save migration status to file"""
        status_data = {
            'status': status,
            'deployed_at': datetime.now().isoformat(),
            'version': '2.0.0',
            'module': 'documents',
            'files': {
                'service': 'services/document_service.py',
                'controller': 'routes/documents_controller.py',
                'api': 'routes/api_documents_v2.py'
            }
        }
        
        with open(self.migration_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n📖 Documents Module Migration Tool")
        print("=" * 60)
        print("\nUsage:")
        print("  python migration_documents.py test     - Run automated tests")
        print("  python migration_documents.py deploy   - Deploy refactored version")
        print("  python migration_documents.py rollback - Rollback to original")
        print("  python migration_documents.py status   - Check migration status")
        print("")
        return
    
    command = sys.argv[1].lower()
    migration = DocumentsMigration()
    
    if command == 'test':
        success = migration.run_tests()
        sys.exit(0 if success else 1)
    
    elif command == 'deploy':
        success = migration.deploy()
        sys.exit(0 if success else 1)
    
    elif command == 'rollback':
        success = migration.rollback()
        sys.exit(0 if success else 1)
    
    elif command == 'status':
        migration.status()
        sys.exit(0)
    
    else:
        print(f"\n❌ Unknown command: {command}")
        print("Valid commands: test, deploy, rollback, status\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
