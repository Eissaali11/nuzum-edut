"""
Comprehensive Database Schema Verification
Check all critical tables for missing columns
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "instance" / "nuzum_local.db"

def check_all_tables():
    """Verify schema for all critical tables"""
    
    # Expected schemas for critical tables
    expected_schemas = {
        'user': [
            'id', 'email', 'username', 'password_hash', 'full_name', 'phone',
            'role', 'is_active', 'is_admin', 'last_login', 'employee_id',
            'assigned_department_id', 'created_at', 'updated_at'
        ],
        'employee': [
            'id', 'name', 'department_id', 'position', 'hire_date', 'email',
            'phone', 'national_id', 'is_active', 'created_at'
        ],
        'vehicle': [
            'id', 'plate_number', 'make', 'model', 'year', 'vin', 
            'registration_expiry', 'insurance_expiry', 'is_active'
        ],
        'department': [
            'id', 'name', 'description', 'is_active', 'created_at'
        ],
        'notifications': [
            'id', 'user_id', 'notification_type', 'title', 'description',
            'is_read', 'created_at', 'read_at'
        ]
    }
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("DATABASE SCHEMA VERIFICATION")
        print("=" * 80)
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n✓ Total tables in database: {len(all_tables)}")
        print(f"✓ Critical tables to verify: {len(expected_schemas)}")
        
        issues_found = False
        
        for table_name, expected_cols in expected_schemas.items():
            if table_name not in all_tables:
                print(f"\n✗ TABLE MISSING: {table_name}")
                issues_found = True
                continue
            
            # Get current columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            current_cols = [row[1] for row in cursor.fetchall()]
            
            # Find missing columns
            missing = [col for col in expected_cols if col not in current_cols]
            
            if missing:
                print(f"\n⚠ Table '{table_name}':")
                print(f"  Current columns: {len(current_cols)}")
                print(f"  Expected columns: {len(expected_cols)}")
                print(f"  Missing: {', '.join(missing)}")
                issues_found = True
            else:
                print(f"\n✓ Table '{table_name}': All critical columns present ({len(current_cols)} cols)")
        
        # Check row counts
        print("\n" + "=" * 80)
        print("TABLE ROW COUNTS")
        print("=" * 80)
        
        for table in ['user', 'employee', 'vehicle', 'department', 'attendance']:
            if table in all_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
        
        conn.close()
        
        if not issues_found:
            print("\n" + "=" * 80)
            print("✓ ALL CRITICAL SCHEMAS VERIFIED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠ SOME ISSUES FOUND - Review above")
            print("=" * 80)
        
        return not issues_found
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_all_tables()
