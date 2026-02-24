# هيكلة النواة — نُظم (Enterprise)

## المجلدات المنشأة

```
core/                 # النواة: Extensions, App Factory, Celery
config/               # Base, Development, Production
domain/               # النماذج والمنطق: employees, vehicles, accounting
infrastructure/       # Database, Redis, Storage
presentation/web/     # Static, Templates, Blueprints
shared/               # Utils, Responses, Validators
```

## الملفات الرئيسية

| الغرض | الملف |
|--------|--------|
| مصنع التطبيق | `core/app_factory.py` |
| الملحقات (DB, Migrate, Login, CORS) | `core/extensions.py` |
| Celery | `core/celery_app.py` |
| إعدادات | `config/base.py`, `config/development.py`, `config/production.py` |
| ردود JSON موحدة | `shared/utils/responses.py` |
| محققون | `shared/utils/validators.py` |
| القالب الحاكم | `presentation/web/templates/layout/base.html` |
| ثيم (ألوان النظام) | `presentation/web/static/css/theme.css` |
| WSGI | `wsgi.py` |

## القيود

- **400 سطر:** لا يتجاوز أي ملف 400 سطر.
- **لا Inline:** لا CSS أو JS مضمن في القوالب؛ كل شيء في ملفات منفصلة (theme.css، موديولات JS لاحقاً).

## التشغيل

**PowerShell (Windows):**
```powershell
# الطريقة الأسهل: سكريبت واحد (ينشئ venv ويثبت المتطلبات إن لزم)
.\ops\launchers\run.ps1
```
أو يدوياً:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_APP = "wsgi:app"
$env:FLASK_ENV = "development"
python -m flask run --host=0.0.0.0 --port=5000
```

**Bash / CMD:**
```bash
# تطوير (Bash)
export FLASK_APP=wsgi:app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

**إنتاج (Docker):**
```bash
docker-compose up -d
```

## API موحد

استخدم من مسارات API:

```python
from shared.utils.responses import json_success, json_error, json_created
return json_success(data={"key": "value"})
return json_error("رسالة خطأ", status=400)
```
