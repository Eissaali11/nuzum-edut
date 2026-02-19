"""
Populate User Data After Column Sync
Set full_name and is_admin for existing users
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "instance" / "nuzum_local.db"

def populate_user_data():
    """Populate missing user data"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("POPULATING USER DATA")
        print("=" * 80)
        
        # Step 1: Set full_name from name column where available
        print("\n→ Setting full_name from existing 'name' column...")
        cursor.execute("UPDATE user SET full_name = name WHERE name IS NOT NULL AND (full_name IS NULL OR full_name = '')")
        updated = cursor.rowcount
        print(f"  ✓ Updated {updated} user(s)")
        
        # Step 2: Set full_name from username where full_name is still null
        print("\n→ Setting full_name from username where still empty...")
        cursor.execute("UPDATE user SET full_name = username WHERE username IS NOT NULL AND (full_name IS NULL OR full_name = '')")
        updated = cursor.rowcount
        print(f"  ✓ Updated {updated} user(s)")
        
        # Step 3: Set is_admin based on role
        print("\n→ Setting is_admin flag based on role...")
        cursor.execute("UPDATE user SET is_admin = 1 WHERE role = 'ADMIN'")
        admin_count = cursor.rowcount
        cursor.execute("UPDATE user SET is_admin = 0 WHERE role != 'ADMIN'")
        non_admin_count = cursor.rowcount
        print(f"  ✓ Set is_admin=1 for {admin_count} admin(s)")
        print(f"  ✓ Set is_admin=0 for {non_admin_count} non-admin(s)")
        
        # Step 4: Set updated_at to created_at where null
        print("\n→ Initializing updated_at timestamps...")
        cursor.execute("UPDATE user SET updated_at = created_at WHERE updated_at IS NULL")
        updated = cursor.rowcount
        print(f"  ✓ Updated {updated} user(s)")
        
        conn.commit()
        
        # Verification
        print("\n" + "=" * 80)
        print("FINAL USER DATA")
        print("=" * 80)
        
        cursor.execute("""
            SELECT id, email, username, full_name, phone, role, is_admin, is_active 
            FROM user 
            ORDER BY id
        """)
        users = cursor.fetchall()
        
        if users:
            print(f"\nTotal users: {len(users)}")
            for user in users:
                print(f"\n  ID: {user[0]}")
                print(f"  Email: {user[1]}")
                print(f"  Username: {user[2] if user[2] else '(NULL)'}")
                print(f"  Full Name: {user[3] if user[3] else '(NULL)'}")
                print(f"  Phone: {user[4] if user[4] else '(NULL)'}")
                print(f"  Role: {user[5]}")
                print(f"  Is Admin: {'Yes' if user[6] else 'No'}")
                print(f"  Active: {'Yes' if user[7] else 'No'}")
        
        # Test login query
        print("\n" + "=" * 80)
        print("LOGIN SIMULATION TEST")
        print("=" * 80)
        
        test_email = "admin@nuzum.com"
        print(f"\n→ Testing login query for: {test_email}")
        
        cursor.execute("""
            SELECT id, email, username, full_name, role, is_admin, is_active, password_hash
            FROM user 
            WHERE email = ? AND is_active = 1
        """, (test_email,))
        
        user = cursor.fetchone()
        
        if user:
            print(f"\n  ✓ User found:")
            print(f"    ID: {user[0]}")
            print(f"    Email: {user[1]}")
            print(f"    Username: {user[2]}")
            print(f"    Full Name: {user[3]}")
            print(f"    Role: {user[4]}")
            print(f"    Is Admin: {user[5]}")
            print(f"    Is Active: {user[6]}")
            print(f"    Has Password: {'Yes' if user[7] else 'No'}")
        else:
            print(f"\n  ✗ User not found or inactive!")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("✓ DATA POPULATION COMPLETE")
        print("=" * 80)
        print("\nYou can now try logging in at http://127.0.0.1:5000")
        print("Email: admin@nuzum.com")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    populate_user_data()
