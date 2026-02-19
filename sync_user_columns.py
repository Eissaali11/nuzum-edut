"""
Database Column Sync Script
Check and add missing columns to the user table
"""
import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "instance" / "nuzum_local.db"

def get_table_columns(cursor, table_name):
    """Get all columns for a table"""
    cursor.execute(f"PRAGMA table_info({table_name});")
    return {row[1]: row[2] for row in cursor.fetchall()}  # {column_name: type}

def check_and_add_columns():
    """Check user table and add missing columns"""
    
    # Expected columns based on User model
    expected_columns = {
        'id': 'INTEGER',
        'email': 'VARCHAR(100)',
        'username': 'VARCHAR(100)',
        'password_hash': 'VARCHAR(255)',
        'full_name': 'VARCHAR(150)',  # MISSING
        'phone': 'VARCHAR(20)',  # MIGHT BE MISSING
        'role': 'VARCHAR(50)',
        'is_active': 'BOOLEAN',
        'is_admin': 'BOOLEAN',
        'last_login': 'DATETIME',
        'employee_id': 'INTEGER',
        'assigned_department_id': 'INTEGER',
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME'  # MIGHT BE MISSING
    }
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("DATABASE COLUMN SYNC - USER TABLE")
        print("=" * 80)
        
        # Get current columns
        current_columns = get_table_columns(cursor, 'user')
        
        print(f"\n✓ Current columns in 'user' table: {len(current_columns)}")
        for col, col_type in current_columns.items():
            print(f"  - {col}: {col_type}")
        
        # Find missing columns
        missing_columns = []
        for col, col_type in expected_columns.items():
            if col not in current_columns:
                missing_columns.append((col, col_type))
        
        if not missing_columns:
            print("\n✓ All columns exist! Database is in sync.")
            return True
        
        print(f"\n⚠ Missing columns: {len(missing_columns)}")
        for col, col_type in missing_columns:
            print(f"  - {col}: {col_type}")
        
        # Add missing columns
        print("\n" + "=" * 80)
        print("ADDING MISSING COLUMNS")
        print("=" * 80)
        
        for col, col_type in missing_columns:
            # Construct ALTER TABLE command
            if col_type.startswith('VARCHAR'):
                sql = f"ALTER TABLE user ADD COLUMN {col} {col_type}"
            elif col_type == 'BOOLEAN':
                sql = f"ALTER TABLE user ADD COLUMN {col} BOOLEAN DEFAULT 1"
            elif col_type == 'DATETIME':
                sql = f"ALTER TABLE user ADD COLUMN {col} DATETIME"
            elif col_type == 'INTEGER':
                sql = f"ALTER TABLE user ADD COLUMN {col} INTEGER"
            else:
                sql = f"ALTER TABLE user ADD COLUMN {col} {col_type}"
            
            try:
                print(f"\n→ Executing: {sql}")
                cursor.execute(sql)
                print(f"  ✓ Added column: {col}")
            except sqlite3.OperationalError as e:
                print(f"  ✗ Error adding {col}: {e}")
                continue
        
        conn.commit()
        
        # Verify additions
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        updated_columns = get_table_columns(cursor, 'user')
        print(f"\n✓ Updated columns in 'user' table: {len(updated_columns)}")
        
        all_present = True
        for col in expected_columns.keys():
            status = "✓" if col in updated_columns else "✗"
            print(f"  {status} {col}")
            if col not in updated_columns:
                all_present = False
        
        # Show sample user data
        print("\n" + "=" * 80)
        print("SAMPLE USER DATA")
        print("=" * 80)
        
        cursor.execute("SELECT id, email, username, full_name, phone, role FROM user LIMIT 3")
        users = cursor.fetchall()
        
        if users:
            print(f"\nFound {len(users)} user(s):")
            for user in users:
                print(f"\n  ID: {user[0]}")
                print(f"  Email: {user[1]}")
                print(f"  Username: {user[2]}")
                print(f"  Full Name: {user[3] if user[3] else '(NULL)'}")
                print(f"  Phone: {user[4] if user[4] else '(NULL)'}")
                print(f"  Role: {user[5]}")
        else:
            print("\n⚠ No users found in database!")
        
        conn.close()
        
        if all_present:
            print("\n" + "=" * 80)
            print("✓ SUCCESS - All columns synchronized!")
            print("=" * 80)
            return True
        else:
            print("\n" + "=" * 80)
            print("✗ INCOMPLETE - Some columns still missing")
            print("=" * 80)
            return False
            
    except sqlite3.Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_and_add_columns()
    sys.exit(0 if success else 1)
