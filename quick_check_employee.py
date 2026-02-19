"""Quick check for employee 260 directly from database."""
import sqlite3

db_path = "instance/nuzum_local.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if employee 260 exists
    cursor.execute("SELECT id, name, status FROM employee WHERE id = 260")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Employee 260 EXISTS")
        print(f"   ID: {result[0]}")
        print(f"   Name: {result[1]}")
        print(f"   Status: {result[2]}")
    else:
        print(f"❌ Employee 260 NOT FOUND")
        
        # Find employees near 260
        cursor.execute("SELECT id, name FROM employee WHERE id >= 250 AND id <= 270 ORDER BY id")
        nearby = cursor.fetchall()
        
        if nearby:
            print(f"\nEmployees near 260:")
            for emp in nearby:
                print(f"   ID {emp[0]}: {emp[1]}")
        else:
            print("\nNo employees found in range 250-270")
            
        # Count total employees
        cursor.execute("SELECT COUNT(*) FROM employee")
        total = cursor.fetchone()[0]
        print(f"\nTotal employees in database: {total}")
        
        # Show max ID
        cursor.execute("SELECT MAX(id) FROM employee")
        max_id = cursor.fetchone()[0]
        print(f"Max employee ID: {max_id}")
    
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
