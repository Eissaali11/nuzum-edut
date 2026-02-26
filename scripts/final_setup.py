#!/usr/bin/env python3
"""Final setup: install deps, fix DB schema, run health checks."""
import subprocess
import sys
import os
import sqlite3
from pathlib import Path

def run_cmd(cmd, desc=""):
    """Run shell command and print output."""
    print(f"\n{'='*60}")
    print(f"🔍 {desc or cmd}")
    print('='*60)
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    return result.returncode == 0

def check_and_fix_db_column():
    """Ensure is_approved column exists in vehicle_handover table."""
    print("\n" + "="*60)
    print("🔧 Checking DB schema...")
    print("="*60)
    db_paths = ['instance/nuzm_local.db', 'nuzum_local.db']
    for db_path in db_paths:
        if not Path(db_path).exists():
            print(f"  ⓘ {db_path} not found")
            continue
        try:
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute("PRAGMA table_info(vehicle_handover)")
            cols = {r[1] for r in cur.fetchall()}
            if 'is_approved' in cols:
                print(f"  ✅ {db_path}: is_approved present")
            else:
                print(f"  ⚠️  {db_path}: is_approved MISSING, adding...")
                try:
                    cur.execute("ALTER TABLE vehicle_handover ADD COLUMN is_approved INTEGER DEFAULT 0")
                    con.commit()
                    print(f"  ✅ {db_path}: is_approved added")
                except Exception as e:
                    print(f"  ✗ {db_path}: {e}")
            con.close()
        except Exception as e:
            print(f"  ✗ Error checking {db_path}: {e}")

def main():
    os.chdir(Path(__file__).parent.parent)
    print("\n" + "🚀 "*30)
    print("NUZUM FINAL SETUP & VALIDATION")
    print("🚀 "*30)
    
    # Step 1: Install dependencies
    print("\n[1/4] Installing dependencies...")
    pkgs = "flask-wtf flask-login sqlalchemy flask-migrate flask-sqlalchemy flask-cors flask-limiter"
    cmd = f"{sys.executable} -m pip install -q {pkgs} 2>&1 && echo INSTALL_OK || echo INSTALL_FAIL"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "INSTALL_OK" in result.stdout:
        print("✅ All packages installed successfully")
    else:
        print(f"⚠️  Install output: {result.stdout}")
    
    # Step 2: Verify installed packages
    print("\n[2/4] Verifying Flask packages...")
    cmd = f"{sys.executable} -m pip list | grep -i flask"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        if line:
            print(f"  {line}")
    
    # Step 3: Check and fix DB
    print("\n[3/4] Database schema check...")
    check_and_fix_db_column()
    
    # Step 4: Run health check
    print("\n[4/4] Running health check...")
    cmd = f"{sys.executable} tools/diagnostics/health_check.py"
    subprocess.run(cmd, shell=True)
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
