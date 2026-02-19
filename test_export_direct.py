"""Test Power BI export generation directly"""
import sys
sys.path.insert(0, 'D:/nuzm')

try:
    print("Importing modules...")
    from application.services.powerbi_exporter import export_to_powerbi
    
    print("Generating Power BI export...")
    buffer, filename, mimetype = export_to_powerbi()
    
    print(f"✅ Success!")
    print(f"   Filename: {filename}")
    print(f"   MIME Type: {mimetype}")
    print(f"   Buffer size: {len(buffer.getvalue())} bytes")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"   Message: {str(e)}")
    import traceback
    traceback.print_exc()
