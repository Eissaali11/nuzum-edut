# -*- coding: utf-8 -*-
"""
Start Phase 2 on Port 5001 - Test Server
Separate server for testing new modular architecture
"""

import os
import sys

# Set Phase 2 mode
os.environ['ATTENDANCE_USE_MODULAR'] = '2'
os.environ['FLASK_DEBUG'] = 'false'
os.environ['FLASK_RUN_PORT'] = '5001'
# Use the database with actual data (nuzum_local.db)
os.environ['DATABASE_URL'] = 'sqlite:///D:/nuzm/instance/nuzum_local.db'
# Enable static file serving
os.environ['FLASK_ENV'] = 'development'

print("=" * 70)
print("Starting Phase 2 Test Server on Port 5001")
print("=" * 70)
print("Mode: ATTENDANCE_USE_MODULAR=2 (NEW optimized structure)")
print("Port: 5001")
print("=" * 70)
print()

# Import and run the app
if __name__ == "__main__":
    from core.app_factory import create_app
    
    app = create_app()
    
    print("\nApp created successfully!")
    print("Static folder: " + app.static_folder)
    print("Static URL path: " + app.static_url_path)
    print("Server starting on http://127.0.0.1:5001")
    print("Attendance routes: http://127.0.0.1:5001/attendance/")
    print("Static files: http://127.0.0.1:5001/static/")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False,
        use_reloader=False
    )
