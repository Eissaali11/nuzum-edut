"""
Attendance Refactoring Migration Script
========================================
Automated testing and deployment for attendance module refactoring

Usage:
    python migration_attendance.py test      # Run tests
    python migration_attendance.py deploy    # Deploy to production
    python migration_attendance.py rollback  # Rollback changes
    python migration_attendance.py status    # Check status

Author: Auto-generated
Date: 2026-02-20
"""

import os
import sys
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
BASE_DIR = Path(__file__).parent
OLD_FILE = BASE_DIR / 'routes' / '_attendance_main.py'
SERVICE_FILE = BASE_DIR / 'services' / 'attendance_service.py'
CONTROLLER_FILE = BASE_DIR / 'routes' / 'attendance_controller.py'
API_FILE = BASE_DIR / 'routes' / 'api_attendance_v2.py'
APP_FILE = BASE_DIR / 'app.py'
BACKUP_DIR = BASE_DIR / '_graveyard_archive' / 'attendance_migration_backup'


class AttendanceMigration:
    """Manage attendance module migration"""
    
    def __init__(self):
        self.status_file = BASE_DIR / '.attendance_migration_status'
    
    def check_files_exist(self):
        """Check if all required files exist"""
        logger.info("Checking files...")
        
        required_files = {
            'Old file': OLD_FILE,
            'Service': SERVICE_FILE,
            'Controller': CONTROLLER_FILE,
            'API': API_FILE,
            'App': APP_FILE
        }
        
        missing = []
        for name, path in required_files.items():
            if path.exists():
                logger.info(f"  ✓ {name}: {path}")
            else:
                logger.error(f"  ✗ {name}: {path} NOT FOUND")
                missing.append(name)
        
        if missing:
            logger.error(f"Missing files: {', '.join(missing)}")
            return False
        
        logger.info("All files found!")
        return True
    
    def run_tests(self):
        """Run automated tests"""
        logger.info("=" * 60)
        logger.info("RUNNING TESTS")
        logger.info("=" * 60)
        
        if not self.check_files_exist():
            logger.error("Cannot run tests - missing files")
            return False
        
        # Test 1: Import tests
        logger.info("\n[Test 1/5] Import Tests...")
        try:
            from services.attendance_service import AttendanceService
            from routes.attendance_controller import attendance_refactored_bp
            from routes.api_attendance_v2 import api_attendance_v2_bp
            logger.info("  ✓ All imports successful")
        except Exception as e:
            logger.error(f"  ✗ Import failed: {str(e)}")
            return False
        
        # Test 2: Service methods exist
        logger.info("\n[Test 2/5] Service Method Tests...")
        required_methods = [
            'get_unified_attendance_list',
            'calculate_stats_from_attendances',
            'record_attendance',
            'bulk_record_department',
            'delete_attendance',
            'get_stats_for_period',
            'export_to_excel'
        ]
        
        for method_name in required_methods:
            if hasattr(AttendanceService, method_name):
                logger.info(f"  ✓ {method_name} exists")
            else:
                logger.error(f"  ✗ {method_name} missing")
                return False
        
        # Test 3: Blueprint registration
        logger.info("\n[Test 3/5] Blueprint Tests...")
        try:
            assert attendance_refactored_bp.name == 'attendance_refactored'
            logger.info(f"  ✓ Controller blueprint: {attendance_refactored_bp.name}")
            
            assert api_attendance_v2_bp.name == 'api_attendance_v2'
            assert api_attendance_v2_bp.url_prefix == '/api/v2/attendance'
            logger.info(f"  ✓ API blueprint: {api_attendance_v2_bp.name}")
        except AssertionError as e:
            logger.error(f"  ✗ Blueprint test failed: {str(e)}")
            return False
        
        # Test 4: Service functionality (unit tests)
        logger.info("\n[Test 4/5] Service Functionality Tests...")
        try:
            # Test format_time_12h_ar
            from services.attendance_service import AttendanceService
            from datetime import datetime
            
            test_dt = datetime(2026, 2, 20, 8, 30, 0)
            result = AttendanceService.format_time_12h_ar(test_dt)
            assert result == '8:30:00 ص', f"Expected '8:30:00 ص', got '{result}'"
            logger.info(f"  ✓ format_time_12h_ar: {result}")
            
            # Test calculate_stats
            test_attendances = [
                {'status': 'present'},
                {'status': 'present'},
                {'status': 'absent'},
                {'status': 'leave'}
            ]
            stats = AttendanceService.calculate_stats_from_attendances(test_attendances)
            assert stats['present'] == 2
            assert stats['absent'] == 1
            assert stats['leave'] == 1
            assert stats['total'] == 4
            logger.info(f"  ✓ calculate_stats: {stats}")
            
        except Exception as e:
            logger.error(f"  ✗ Service test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 5: Route count
        logger.info("\n[Test 5/5] Route Count Tests...")
        try:
            controller_routes = len([r for r in attendance_refactored_bp.deferred_functions])
            api_routes = len([r for r in api_attendance_v2_bp.deferred_functions])
            
            logger.info(f"  ✓ Controller routes: {controller_routes}")
            logger.info(f"  ✓ API routes: {api_routes}")
            logger.info(f"  ✓ Total routes: {controller_routes + api_routes}")
        except Exception as e:
            logger.warning(f"  ⚠ Could not count routes: {str(e)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 60)
        return True
    
    def create_backup(self):
        """Create backup of original files"""
        logger.info("Creating backup...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUP_DIR / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            OLD_FILE,
            APP_FILE
        ]
        
        for file_path in files_to_backup:
            if file_path.exists():
                dest = backup_path / file_path.name
                shutil.copy2(file_path, dest)
                logger.info(f"  ✓ Backed up: {file_path.name}")
        
        logger.info(f"Backup created at: {backup_path}")
        return backup_path
    
    def update_app_file(self):
        """Update app.py to register new blueprints"""
        logger.info("Updating app.py...")
        
        if not APP_FILE.exists():
            logger.error("app.py not found")
            return False
        
        content = APP_FILE.read_text(encoding='utf-8')
        
        # Check if already updated
        if 'attendance_refactored_bp' in content:
            logger.info("  ℹ app.py already updated")
            return True
        
        # Backup first
        backup_path = APP_FILE.with_suffix('.py.backup')
        shutil.copy2(APP_FILE, backup_path)
        logger.info(f"  ✓ Backed up app.py to {backup_path.name}")
        
        # Add imports
        import_line = "\n# Attendance Refactored (NEW)\nfrom routes.attendance_controller import attendance_refactored_bp\nfrom routes.api_attendance_v2 import api_attendance_v2_bp\n"
        
        # Find where to insert import
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if 'from routes' in line or 'import' in line:
                insert_index = i + 1
        
        lines.insert(insert_index, import_line)
        
        # Add blueprint registration
        register_lines = [
            "\n# Register Attendance Refactored Blueprints (NEW)",
            "app.register_blueprint(attendance_refactored_bp, url_prefix='/attendance-new')",
            "app.register_blueprint(api_attendance_v2_bp)  # Uses /api/v2/attendance",
            ""
        ]
        
        # Find where to insert registration
        for i, line in enumerate(lines):
            if 'register_blueprint' in line:
                insert_index = i + 1
        
        for reg_line in reversed(register_lines):
            lines.insert(insert_index, reg_line)
        
        # Write back
        APP_FILE.write_text('\n'.join(lines), encoding='utf-8')
        logger.info("  ✓ Updated app.py with new blueprints")
        
        return True
    
    def deploy(self):
        """Deploy refactored code"""
        logger.info("=" * 60)
        logger.info("DEPLOYING ATTENDANCE REFACTORING")
        logger.info("=" * 60)
        
        # Step 1: Run tests
        if not self.run_tests():
            logger.error("Tests failed! Aborting deployment.")
            return False
        
        # Step 2: Create backup
        backup_path = self.create_backup()
        
        # Step 3: Update app.py
        if not self.update_app_file():
            logger.error("Failed to update app.py")
            return False
        
        # Step 4: Write status file
        self.status_file.write_text(f"deployed:{datetime.now().isoformat()}\nbackup:{backup_path}")
        
        logger.info("\n" + "=" * 60)
        logger.info("DEPLOYMENT SUCCESSFUL ✓")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Restart Flask app")
        logger.info("2. Test at: http://localhost:5001/attendance-new/")
        logger.info("3. Compare with old: http://localhost:5001/attendance/")
        logger.info("4. Monitor logs for errors")
        logger.info("\nTo rollback: python migration_attendance.py rollback")
        
        return True
    
    def rollback(self):
        """Rollback deployment"""
        logger.info("=" * 60)
        logger.info("ROLLING BACK ATTENDANCE REFACTORING")
        logger.info("=" * 60)
        
        if not self.status_file.exists():
            logger.error("No deployment found to rollback")
            return False
        
        status_info = self.status_file.read_text()
        backup_line = [l for l in status_info.split('\n') if l.startswith('backup:')]
        
        if not backup_line:
            logger.error("Backup path not found in status file")
            return False
        
        backup_path = Path(backup_line[0].split(':', 1)[1])
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False
        
        logger.info(f"Restoring from: {backup_path}")
        
        # Restore app.py
        backup_app = backup_path / 'app.py'
        if backup_app.exists():
            shutil.copy2(backup_app, APP_FILE)
            logger.info(f"  ✓ Restored app.py")
        
        # Remove status file
        self.status_file.unlink()
        logger.info("  ✓ Removed deployment status")
        
        logger.info("\n" + "=" * 60)
        logger.info("ROLLBACK COMPLETE ✓")
        logger.info("=" * 60)
        logger.info("\nRestart Flask app to apply changes")
        
        return True
    
    def status(self):
        """Check deployment status"""
        logger.info("=" * 60)
        logger.info("ATTENDANCE REFACTORING STATUS")
        logger.info("=" * 60)
        
        # Check files
        files_status = {
            'Service Layer': SERVICE_FILE.exists(),
            'Controller Layer': CONTROLLER_FILE.exists(),
            'API Layer': API_FILE.exists(),
            'Original File': OLD_FILE.exists()
        }
        
        logger.info("\nFiles:")
        for name, exists in files_status.items():
            status = "✓ EXISTS" if exists else "✗ MISSING"
            logger.info(f"  {name}: {status}")
        
        # Check deployment
        if self.status_file.exists():
            status_info = self.status_file.read_text()
            logger.info("\nDeployment: ✓ DEPLOYED")
            logger.info(f"Details:\n{status_info}")
        else:
            logger.info("\nDeployment: ✗ NOT DEPLOYED")
        
        # Check app.py
        if APP_FILE.exists():
            content = APP_FILE.read_text(encoding='utf-8')
            is_registered = 'attendance_refactored_bp' in content
            logger.info(f"\napp.py Registration: {'✓ REGISTERED' if is_registered else '✗ NOT REGISTERED'}")
        
        logger.info("\n" + "=" * 60)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migration_attendance.py test      # Run tests")
        print("  python migration_attendance.py deploy    # Deploy refactoring")
        print("  python migration_attendance.py rollback  # Rollback changes")
        print("  python migration_attendance.py status    # Check status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    migration = AttendanceMigration()
    
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
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
