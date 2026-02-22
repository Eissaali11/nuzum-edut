"""Test if endpoint_exists is available in template context"""
import sys
import time
import urllib.request
import urllib.error

def test_dashboard():
    """Try to load dashboard page"""
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"Attempt {i+1}/{max_retries}...")
            time.sleep(2)
            response = urllib.request.urlopen('http://127.0.0.1:5000/dashboard', timeout=10)
            status = response.getcode()
            print(f"✅ Dashboard loaded successfully! Status: {status}")
            print("✅ endpoint_exists context processor is working!")
            return 0
        except urllib.error.HTTPError as e:
            print(f"❌ HTTP Error {e.code}: {e.reason}")
            if e.code == 500:
                print("Server error - endpoint_exists may still be undefined")
            return 1
        except Exception as e:
            print(f"⚠️  Connection error: {e}")
            if i < max_retries - 1:
                print("Waiting for server to start...")
                time.sleep(3)
    
    print("❌ Failed to connect after multiple attempts")
    return 1

if __name__ == "__main__":
    sys.exit(test_dashboard())
