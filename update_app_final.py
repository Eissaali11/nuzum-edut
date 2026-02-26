import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove legacy redirects
legacy_redirects_pattern = re.compile(r'# إضافة route مختصر للتوافق مع الروابط القديمة.*?return redirect\(url_for\(\'payroll\.dashboard\'\)\)', re.DOTALL)
content = legacy_redirects_pattern.sub('', content)

# Remove Google Verification
google_verification_pattern = re.compile(r'# Google Search Console verification route.*?return Response\(\'google-site-verification: googleab59b7c3bfbdd81d\.html\', mimetype=\'text/html\'\)', re.DOTALL)
content = google_verification_pattern.sub('', content)

# Remove uploads routes
uploads_pattern = re.compile(r'    @app\.route\(\'/uploads/<path:filename>\'\).*?abort\(404\)', re.DOTALL)
content = uploads_pattern.sub('', content)

# Remove static pages
static_pages_pattern = re.compile(r'# ================== صفحات المعلومات الثابتة ==================.*?# ================== نهاية صفحات المعلومات الثابتة ==================', re.DOTALL)
content = static_pages_pattern.sub('', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py updated successfully.")
