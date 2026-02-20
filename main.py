import sys
sys.path.insert(0, '.')

# استيراد Flask app الحقيقي من app.py (وليس مجلد app/)
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
sys.modules['app_module_real'] = app_module
spec.loader.exec_module(app_module)
app = app_module.app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
