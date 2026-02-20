# 📦 دليل التثبيت والإعداد

## ✅ المتطلبات

```bash
Python 3.8+
Flask 3.x
openpyxl
xlsxwriter
pandas
```

## 🚀 الخطوات السريعة

### 1. التحقق من المتطلبات مثبتة

```bash
pip list | grep -E "openpyxl|xlsxwriter|pandas|Flask"
```

### 2. التأكد من وجود المجلد

```bash
# سيُنشأ تلقائياً، لكن يمكنك إنشاؤه يدويًا
mkdir -p instance/reports
```

### 3. اختبار النظام

```bash
python test_professional_report.py
```

يجب أن ترى:
```
✅ نجح:  6
❌ فشل:  0
📈 النسبة: 100%

🎉 جميع الاختبارات نجحت!
```

### 4. بدء خادم Flask

```bash
python app.py
```

### 5. اختبار المسار

```
http://localhost:5000/analytics/export/professional-report
```

---

## 🔧 التثبيت اليدوي

إذا كان لديك مشاكل:

```bash
# 1. قم بتفعيل البيئة الافتراضية
.\venv\Scripts\Activate

# 2. حدّث pip
python -m pip install --upgrade pip

# 3. ثبّت المتطلبات
pip install openpyxl xlsxwriter pandas flask

# 4. اختبر التثبيت
python -c "import openpyxl, pandas; print('✅ جميع المتطلبات مثبتة')"
```

---

## 🐛 حل المشاكل الشائعة

### مشكلة 1: ModuleNotFoundError
```
خطأ: ModuleNotFoundError: No module named 'openpyxl'

الحل:
pip install openpyxl xlsxwriter pandas
```

### مشكلة 2: Permission denied
```
خطأ: Permission denied for 'instance/reports'

الحل:
mkdir -p instance/reports
chmod 755 instance/reports
```

### مشكلة 3: تقرير فارغ
```
الملف ينشأ لكن بدون بيانات

الحل:
- تأكد من قاعدة البيانات متصلة
- اختبر DataExtractor مباشرة
- تحقق من السجلات (logs)
```

---

## 📊 التحقق من الحالة

```bash
# 1. اختبار الاستيراد
python -c "from application.services.excel.exporter import ExcelExporter; print('✅')"

# 2. اختبار الملفات
ls application/services/excel/

# 3. اختبر المسار
python -c "
from application.services.excel.exporter import ExcelExporter
e = ExcelExporter()
b, f = e.generate_report()
print(f'✅ تقرير نجح: {f}')
"
```

---

## 🎯 الخطوات التالية

بعد التثبيت الناجح:

1. **اختبر المسار**: انسخ الرابط في المتصفح
2. **انزّل الملف**: اختبر بتنزيل التقرير
3. **افتح الملف**: افتح Excel وتحقق من المحتوى
4. **استخدمه**: دمّجه في تطبيقك

---

## 📞 الدعم الإضافي

إذا واجهت مشاكل:

1. تحقق من `PROFESSIONAL_EXCEL_SYSTEM.md`
2. اقرأ `QUICKSTART.md`
3. اختبر مع `test_professional_report.py`
4. اقرأ سجلات Flask

---

تم التثبيت بنجاح! 🎉

الآن يمكنك الاستمتاع بنظام تصدير Excel الاحترافي.
