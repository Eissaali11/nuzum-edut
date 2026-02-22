#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test the attendance page - debug version"""

import sys
import os
import traceback

# Set up logging to see errors clearly
os.environ['FLASK_ENV'] = 'testing'
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(levelname)s] %(message)s',
        },
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
}

try:
    print("Importing Flask app...")
    sys.path.insert(0, '.')
    
    # Import app directly
    import app as app_module
    app = app_module.app
    
    print("✅ App imported successfully")
    print("\nTesting /attendance/ route with test client...")
    
    with app.test_client() as client:
        print("Making request to /attendance/...")
        response = client.get('/attendance/')
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 500:
            print("\n❌ ERROR 500 - Response content (first 2000 chars):")
            content = response.data.decode('utf-8', errors='replace')
            print(content[:2000])
        elif response.status_code == 200:
            print("✅ SUCCESS - Page loaded!")
            content = response.data.decode('utf-8', errors='replace')
            # Check if it has the error message
            if 'خطأ في النظام' in content:
                print("⚠️  Found error message in page - attendance data still failing")
            else:
                print("✅ Page rendered without errors!")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            
except Exception as e:
    print(f"\n❌ Exception occurred: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
