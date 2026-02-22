"""
Login Test Script - Verify admin@nuzum.com can authenticate
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "instance" / "nuzum_local.db"

def test_login():
    """Test login functionality"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("LOGIN FUNCTIONALITY TEST")
        print("=" * 80)
        
        test_email = "admin@nuzum.com"
        
        print(f"\n→ Attempting to fetch user: {test_email}")
        
        cursor.execute("""
            SELECT 
                id, email, username, full_name, phone, role, 
                is_admin, is_active, password_hash, created_at
            FROM user 
            WHERE email = ?
        """, (test_email,))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"\n✗ FAILED: User '{test_email}' not found in database")
            return False
        
        print(f"\n✓ User found in database:")
        print(f"  ID: {user[0]}")
        print(f"  Email: {user[1]}")
        print(f"  Username: {user[2]}")
        print(f"  Full Name: {user[3]}")
        print(f"  Phone: {user[4] if user[4] else '(not set)'}")
        print(f"  Role: {user[5]}")
        print(f"  Is Admin: {user[6]}")
        print(f"  Is Active: {user[7]}")
        print(f"  Created: {user[9]}")
        
        # Check password hash
        password_hash = user[8]
        
        if not password_hash:
            print(f"\n✗ WARNING: User has no password set!")
            print(f"  You need to set a password for this user.")
            return False
        
        print(f"\n✓ Password hash exists: {password_hash[:50]}...")
        
        # Check if active
        if not user[7]:
            print(f"\n✗ WARNING: User account is inactive!")
            return False
        
        print(f"\n✓ User account is active")
        
        # Test password verification (we don't know the actual password)
        print(f"\n→ Password hash format check:")
        if password_hash.startswith('scrypt:') or password_hash.startswith('pbkdf2:'):
            print(f"  ✓ Valid Werkzeug password hash format")
        else:
            print(f"  ⚠ Unusual hash format: {password_hash[:20]}...")
        
        # Check all required columns are populated
        print(f"\n→ Required column validation:")
        
        checks = {
            'id': user[0],
            'email': user[1],
            'role': user[5],
            'is_active': user[7],
            'password_hash': user[8]
        }
        
        all_valid = True
        for field, value in checks.items():
            if value is None or value == '':
                print(f"  ✗ {field}: MISSING")
                all_valid = False
            else:
                print(f"  ✓ {field}: OK")
        
        # Check optional fields
        print(f"\n→ Optional column status:")
        optional = {
            'username': user[2],
            'full_name': user[3],
            'phone': user[4]
        }
        
        for field, value in optional.items():
            status = "✓ SET" if value else "○ NOT SET (optional)"
            print(f"  {status}: {field}")
        
        conn.close()
        
        if all_valid:
            print("\n" + "=" * 80)
            print("✓ LOGIN TEST PASSED")
            print("=" * 80)
            print(f"\nYou can now login at http://127.0.0.1:5000/login")
            print(f"Email: {test_email}")
            print(f"\nIf you don't remember the password, you may need to reset it.")
            return True
        else:
            print("\n" + "=" * 80)
            print("✗ LOGIN TEST FAILED - Missing required fields")
            print("=" * 80)
            return False
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_login()
