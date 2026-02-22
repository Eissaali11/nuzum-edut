import urllib.request
import json

try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/debug/routes', timeout=5)
    data = json.loads(response.read())
    
    print(f"Total routes: {data['total_routes']}")
    print(f"Backup routes found: {len(data['backup_routes'])}")
    
    if data['backup_routes']:
        print("\nBackup routes:")
        for route in data['backup_routes']:
            print(f"  {route['path']} -> {route['endpoint']} {route['methods']}")
    else:
        print("\nERROR: No backup routes found!")
        
except Exception as e:
    print(f"ERROR: {e}")
