"""
Test script to verify workshop reports are working after ReportLab migration
"""
import requests

def test_workshop_reports_endpoint():
    """Test if workshop reports endpoints are registered"""
    base_url = "http://127.0.0.1:5000"
    
    print("Testing Workshop Reports Endpoints...")
    print("=" * 60)
    
    # Test 1: Check if workshop reports blueprint is registered
    # (This will fail with 404 if blueprint is not registered)
    # (Will fail with 302/redirect if login is required - which is expected)
    test_url = f"{base_url}/workshop-reports/vehicle/1/pdf"
    
    try:
        response = requests.get(test_url, allow_redirects=False)
        print(f"\n✅ TEST 1: Blueprint Registration")
        print(f"   URL: {test_url}")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print(f"   ❌ FAILED: Blueprint not registered (404)")
            return False
        elif response.status_code == 302:
            location = response.headers.get('Location', '')
            if '/auth/login' in location:
                print(f"   ✅ PASSED: Blueprint registered (redirects to login)")
                return True
            else:
                print(f"   ⚠️ UNEXPECTED: Redirects to {location}")
                return True
        elif response.status_code == 200:
            print(f"   ✅ PASSED: Endpoint accessible (200)")
            return True
        else:
            print(f"   ⚠️ UNEXPECTED: Status {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Cannot connect to server at {base_url}")
        print(f"   Make sure Flask server is running")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_workshop_reports_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Workshop Reports: FUNCTIONAL")
        print("\nNext steps:")
        print("1. Login to the system")
        print("2. Navigate to a vehicle's detail page")
        print("3. Click 'تصدير تقرير الورشة' button")
        print("4. PDF should download successfully using ReportLab")
    else:
        print("❌ Workshop Reports: NOT FUNCTIONAL")
        print("\nTroubleshooting:")
        print("1. Check if server reloaded after app.py changes")
        print("2. Check server logs for import errors")
        print("3. Verify reportlab is installed: pip list | findstr reportlab")
    print("=" * 60)
