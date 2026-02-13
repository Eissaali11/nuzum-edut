# دستور المشروع — نُظم (Enterprise Grade)

## المبادئ الصارمة

### 1. الهيكل الموديولي (Modular Clean Architecture)
- **المجلدات الإلزامية:** `core/`, `infrastructure/`, `domain/`, `application/`, `presentation/web/`.
- الفصل بين: النواة، البنية التحتية، النطاق، طبقة التطبيق، والعرض.

### 2. قاعدة الـ 400 سطر
- **يُمنع** أن يتجاوز أي ملف 400 سطر.
- عند التجاوُز: تفكيك الملف إلى موديولات/ملفات أصغر.

### 3. القالب الأساسي الوحيد
- **المرجع الوحيد للتصميم:** `presentation/web/templates/layout/base.html`.
- نسخة واحدة: **Bootstrap 5.3**، **Font Awesome 6.5**.
- دعم **RTL** وخط **Cairo** أصيل.
- ألوان النظام عبر **متغيرات CSS** في `presentation/web/static/css/theme.css`.

### 4. نظام المكونات (UI Macros)
- عدم تكرار HTML: استخدام **Jinja2 Macros** من `templates/macros/` (جداول، بطاقات، نماذج).

### 5. قاعدة البيانات
- نماذج SQLAlchemy في مجلدات منفصلة لكل موديول: **Employees**, **Vehicles**, **Accounting**.
- فهارس (Indexes) ومفاتيح أجنبية (Foreign Keys) لتحمّل 10,000+ مستخدم.

### 6. الأداء والتحمل
- **Redis** للـ Caching والـ Session.
- **Celery** للعمليات الثقيلة (تقارير PDF/Excel، واتساب) في الخلفية.
- **docker-compose**: PostgreSQL, Redis, Web, Worker.

---

## تشغيل المرحلة الأولى

**PowerShell (Windows):**
```powershell
. .\venv\Scripts\Activate.ps1   # إن وُجدت
$env:FLASK_APP = "wsgi:app"
$env:FLASK_ENV = "development"
python -m flask run --host=0.0.0.0 --port=5000
```

**Bash:**
```bash
export FLASK_APP=wsgi:app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

**إنتاج (Docker):**
```bash
docker-compose up -d
```

---

## مسار الملفات الرئيسية

| الغرض | المسار |
|--------|--------|
| مصنع التطبيق | `core/app_factory.py` |
| القالب الأساسي | `presentation/web/templates/layout/base.html` |
| ثيم التصميم | `presentation/web/static/css/theme.css` |
| مكوّنات الواجهة | `presentation/web/templates/macros/*.html` |
| إعدادات البيئة | `config/base.py`, `config/development.py`, `config/production.py` |
| Celery | `core/celery_app.py` |
