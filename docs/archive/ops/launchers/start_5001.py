"""Start app.py on port 5001 with updated code"""
import os
os.environ['FLASK_DEBUG'] = 'false'
os.environ['FLASK_RUN_PORT'] = '5001'

# استيراد وتشغيل التطبيق
exec(open('app.py').read())
