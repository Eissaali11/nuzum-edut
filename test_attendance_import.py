#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test to verify attendance blueprint imports correctly"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test 1: Import from routes.attendance package
    print("🔍 Test 1: Importing from routes.attendance...")
    from routes.attendance import attendance_bp
    print(f"✅ Blueprint imported: {attendance_bp.name}")
    print(f"   URL prefix: {attendance_bp.url_prefix}")
    
    # Test 2: Verify routes are registered
    print("\n🔍 Test 2: Checking registered routes...")
    route_count = len([r for r in attendance_bp.deferred_functions if hasattr(r, '__name__')])
    print(f"   Routes defined in blueprint: {len(list(attendance_bp.routes)) if hasattr(attendance_bp, 'routes') else 'N/A'}")
    
    # Test 3: Check if blueprint has view functions
    print("\n🔍 Test 3: Checking blueprint structure...")
    print(f"   Blueprint name: {attendance_bp.name}")
    print(f"   Blueprint module: {attendance_bp.__module__}")
    print(f"   Blueprint package: {attendance_bp.import_name}")
    
    print("\n✅ All import tests passed!")
    
except Exception as e:
    print(f"\n❌ Import test failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
