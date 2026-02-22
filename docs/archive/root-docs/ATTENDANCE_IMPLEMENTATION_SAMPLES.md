# نموذج توضيحي للملفات الجديدة
**التاريخ:** 2026-02-20

---

## 📝 ملف النموذج: `__init__.py`

```python
# routes/attendance/__init__.py
# -*- coding: utf-8 -*-
"""
نقطة دخول حزمة مسارات الحضور
Entry point for attendance routes package

يقوم بـ:
1. تجميع جميع الطرق من الملفات الفرعية
2. تسجيل Blueprint واحد
3. توفير واجهة موحدة للاستيراض
"""

from flask import Blueprint

# إنشاء Blueprint مركزي - نفس الاسم من الملف الأصلي!
attendance_bp = Blueprint(
    'attendance',
    __name__,
    url_prefix='/attendance'
)

# استيراد جميع الطرق من الملفات الفرعية
# ملاحظة: استيراض ثابت (static) لتجنب الدوارات
from .views import (
    index,
    department_attendance,
    all_departments_attendance,
    employee_attendance,
    department_attendance_view,
    export_page,
    get_department_employees,
)

from .recording import (
    record,
    bulk_record,
    department_bulk_attendance,
    mark_circle_employees_attendance,
)

from .export import (
    export_excel,
    export_excel_dashboard,
    export_excel_department,
    export_department_data,
    export_department_period,
    export_circle_details_excel,
)

from .statistics import (
    stats,
    department_stats,
    department_details,
    dashboard,
)

from .circles import (
    departments_circles_overview,
    circle_accessed_details,
)

from .crud import (
    confirm_delete_attendance,
    delete_attendance,
    bulk_delete_attendance,
    edit_attendance_page,
    update_attendance_page,
)

from .helpers import (
    format_time_12h_ar,
    format_time_12h_ar_short,
)

# إعادة تصدير لسهولة الاستيراض
__all__ = [
    'attendance_bp',
    'index',
    'record',
    'delete_attendance',
    'export_excel',
    'dashboard',
    'stats',
    # ... إضافة باقي الدوال حسب الحاجة
]
```

---

## 📝 ملف النموذج: `helpers.py`

```python
# routes/attendance/helpers.py
# -*- coding: utf-8 -*-
"""
دوال مساعدة لمسارات الحضور
Helper functions for attendance routes

الوظائف:
- تحويل الأوقات
- تنسيق البيانات
- معالجات عامة
"""

from datetime import datetime


def format_time_12h_ar(dt):
    """
    تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة عربية (صباح/مساء)
    
    مثال:
    >>> format_time_12h_ar(datetime(2026, 2, 20, 14, 30, 45))
    '2:30:45 م'
    
    Args:
        dt: datetime object أو None
        
    Returns:
        str: الوقت بصيغة 12 ساعة أو '-' إذا كان dt = None
    """
    if not dt:
        return '-'
    
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    
    # تحديد صباح أو مساء
    period = 'ص' if hour < 12 else 'م'
    
    # تحويل الساعة
    if hour > 12:
        hour = hour - 12
    elif hour == 0:
        hour = 12
    
    return f'{hour}:{minute:02d}:{second:02d} {period}'


def format_time_12h_ar_short(dt):
    """
    تحويل الوقت من 24 ساعة إلى 12 ساعة بصيغة قصيرة (بدون ثوانٍ)
    
    مثال:
    >>> format_time_12h_ar_short(datetime(2026, 2, 20, 14, 30))
    '2:30 م'
    
    Args:
        dt: datetime object أو None
        
    Returns:
        str: الوقت بصيغة قصيرة أو '-' إذا كان dt = None
    """
    if not dt:
        return '-'
    
    hour = dt.hour
    minute = dt.minute
    
    # تحديد صباح أو مساء
    period = 'ص' if hour < 12 else 'م'
    
    # تحويل الساعة
    if hour > 12:
        hour = hour - 12
    elif hour == 0:
        hour = 12
    
    return f'{hour}:{minute:02d} {period}'
```

---

## 📝 نموذج من `views.py` (جزء من الملف)

```python
# routes/attendance/views.py
# -*- coding: utf-8 -*-
"""
طرق عرض البيانات - Views
Display and listing routes

يحتوي على:
- index() → قائمة الحضور الرئيسية
- department_attendance() → عرض قسم
- dashboard() → لوحة التحكم
- employee_attendance() → تفاصيل الموظف
- ... إلخ
"""

from flask import Blueprint, render_template, request, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, extract, or_
from datetime import datetime
from core.extensions import db
from models import Attendance, Employee, Department, SystemAudit, employee_departments
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from services.attendance_engine import AttendanceEngine
from services.attendance_analytics import AttendanceAnalytics
import logging

logger = logging.getLogger(__name__)

# ملاحظة: لا نسجل Blueprint هنا! يتم في __init__.py


@login_required
def index():
    """
    عرض قائمة سجلات الحضور مع خيارات الفلترة
    
    المعاملات (Query Parameters):
        - date: التاريخ (YYYY-MM-DD)
        - department_id: معرف القسم
        - status: حالة الحضور
    
    الاستجابة:
        HTML page with attendance list
    """
    try:
        # الكود الموجود... لا تغيير!
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id', '')
        status = request.args.get('status', '')
        
        # معالجة التاريخ
        try:
            date = parse_date(date_str)
        except (ValueError, TypeError):
            date = datetime.now().date()
            logger.warning(f'Invalid date provided: {date_str}, using today')
        
        # جلب الأقسام
        if current_user.is_authenticated:
            departments = current_user.get_accessible_departments()
            if current_user.assigned_department_id and not department_id:
                department_id = str(current_user.assigned_department_id)
        else:
            departments = Department.query.all()
        
        # استدعاء service
        unified_attendances = AttendanceEngine.get_unified_attendance_list(
            att_date=date,
            department_id=int(department_id) if department_id else None,
            status_filter=status if status else None
        )
        
        # حساب الإحصائيات
        present_count = sum(1 for rec in unified_attendances if rec['status'] == 'present')
        absent_count = sum(1 for rec in unified_attendances if rec['status'] == 'absent')
        leave_count = sum(1 for rec in unified_attendances if rec['status'] == 'leave')
        sick_count = sum(1 for rec in unified_attendances if rec['status'] == 'sick')
        
        # تنسيق التاريخ
        hijri_date = format_date_hijri(date)
        gregorian_date = format_date_gregorian(date)
        
        logger.info(f'Index: Loaded {len(unified_attendances)} records for {date.isoformat()}')
        
        return render_template('attendance/index.html',
                              attendances=unified_attendances,
                              departments=departments,
                              date=date,
                              hijri_date=hijri_date,
                              gregorian_date=gregorian_date,
                              selected_department=department_id,
                              selected_status=status,
                              present_count=present_count,
                              absent_count=absent_count,
                              leave_count=leave_count,
                              sick_count=sick_count)
    
    except Exception as e:
        logger.error(f'Critical error in index(): {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل البيانات. الرجاء المحاولة مرة أخرى.', 'danger')
        return render_template('error.html',
                              error_title='خطأ في النظام',
                              error_message='فشل تحميل بيانات الحضور'), 500


@login_required
def department_attendance():
    """عرض سجلات حضور قسم معين"""
    # ... الكود الموجود كما هو
    pass


# ... باقي الدوال
```

---

## 📝 نموذج من `recording.py` (جزء من الملف)

```python
# routes/attendance/recording.py
# -*- coding: utf-8 -*-
"""
طرق تسجيل الحضور - Recording Routes

يحتوي على:
- record() → تسجيل فردي
- bulk_record() → تسجيل جماعي
- department_bulk_attendance() → تسجيل قسم
- mark_circle_employees_attendance() → تسجيل دائرة
"""

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from core.extensions import db
from models import Attendance, Employee, Department
from utils.date_converter import parse_date
from utils.audit_logger import log_activity
from services.attendance_engine import AttendanceEngine
import logging

logger = logging.getLogger(__name__)


@login_required
def record():
    """
    تسجيل حضور موظف (GET: نموذج، POST: حفظ)
    
    معاملات POST:
        - employee_id: معرف الموظف
        - date: التاريخ
        - status: الحالة (present, absent, leave, sick)
        - check_in: وقت الدخول (اختياري)
        - check_out: وقت الخروج (اختياري)
        - notes: ملاحظات (اختياري)
    """
    if request.method == 'POST':
        try:
            employee_id = request.form['employee_id']
            date_str = request.form['date']
            status = request.form['status']
            notes = request.form.get('notes', '')
            
            # معالجة التاريخ
            date = parse_date(date_str)
            
            # معالجة الأوقات (إن وجدت)
            check_in = None
            check_out = None
            
            if status == 'present':
                check_in_str = request.form.get('check_in')
                check_out_str = request.form.get('check_out')
                
                if check_in_str:
                    try:
                        check_in = parse_date(check_in_str)
                    except:
                        pass
                
                if check_out_str:
                    try:
                        check_out = parse_date(check_out_str)
                    except:
                        pass
            
            # تسجيل الحضور
            attendance, is_new, message = AttendanceEngine.record_attendance(
                employee_id=employee_id,
                att_date=date,
                status=status,
                check_in=check_in,
                check_out=check_out,
                notes=notes
            )
            
            flash(message, 'success')
            logger.info(f'Recorded attendance for employee {employee_id}')
            return redirect(url_for('attendance.index'))
        
        except Exception as e:
            logger.error(f'Error recording attendance: {str(e)}', exc_info=True)
            flash('حدث خطأ في تسجيل الحضور', 'danger')
            return redirect(url_for('attendance.record'))
    
    # GET: عرض نموذج
    employees = Employee.query.filter_by(status='active').all()
    return render_template('attendance/record.html', employees=employees)


@login_required
def bulk_record():
    """تسجيل جماعي للحضور"""
    # ... الكود الموجود كما هو
    pass


# ... باقي الدوال
```

---

## 📝 نموذج من `export.py` (جزء من الملف)

```python
# routes/attendance/export.py
# -*- coding: utf-8 -*-
"""
طرق التصدير - Export Routes

يحتوي على:
- export_excel() → تصدير Excel عام
- export_excel_dashboard() → تصدير الداشبورد
- export_department_data() → تصدير بيانات القسم
- ... إلخ
"""

from flask import render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from io import BytesIO
from core.extensions import db
from models import Attendance, Employee, Department
from utils.date_converter import parse_date
from services.attendance_reports import AttendanceReportService
import logging

logger = logging.getLogger(__name__)


@login_required
def export_excel():
    """
    تصدير بيانات الحضور إلى ملف Excel
    
    معاملات POST/GET:
        - date: التاريخ
        - department_id: الأقسام المختارة
        - status_filter: حالة الفلترة
    """
    try:
        # معالجة المعاملات
        department_ids = request.form.getlist('department_ids')
        date_str = request.form.get('date')
        
        if not department_ids:
            flash('يرجى اختيار قسم واحد على الأقل', 'warning')
            return redirect(url_for('attendance.export_page'))
        
        # استدعاء خدمة التصدير
        service = AttendanceReportService()
        
        # ... منطق التصدير
        
        logger.info(f'Exported attendance for {len(department_ids)} departments')
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'attendance_export_{date_str}.xlsx'
        )
    
    except Exception as e:
        logger.error(f'Error exporting Excel: {str(e)}', exc_info=True)
        flash('خطأ في تصدير الملف', 'danger')
        return redirect(url_for('attendance.export_page'))


def export_page():
    """صفحة خيارات التصدير (GET فقط)"""
    departments = Department.query.all()
    return render_template('attendance/export.html', departments=departments)


# ... باقي الدوال
```

---

## 📝 نموذج من `statistics.py` (جزء من الملف)

```python
# routes/attendance/statistics.py
# -*- coding: utf-8 -*-
"""
طرق الإحصائيات - Statistics Routes

يحتوي على:
- stats() → إحصائيات عامة
- department_stats() → إحصائيات الأقسام
- dashboard() → لوحة التحكم
- department_details() → تفاصيل القسم
"""

from flask import render_template, request
from flask_login import login_required, current_user
from core.extensions import db
from models import Attendance, Employee, Department
from services.attendance_engine import AttendanceEngine
from services.attendance_analytics import AttendanceAnalytics
import logging

logger = logging.getLogger(__name__)


@login_required
def stats():
    """الإحصائيات العامة"""
    try:
        analytics = AttendanceAnalytics()
        stats_data = analytics.get_general_statistics()
        
        return render_template('attendance/stats.html', stats=stats_data)
    
    except Exception as e:
        logger.error(f'Error in stats(): {str(e)}', exc_info=True)
        flash('خطأ في تحميل الإحصائيات', 'danger')
        return render_template('error.html'), 500


@login_required
def dashboard():
    """
    لوحة التحكم الرئيسية (409 سطر في الملف الأصلي!)
    
    ملاحظة: هذا المسار كبير جداً وقد يحتاج تقسيم داخلي
    """
    try:
        # منطق معقد هنا...
        logger.info('Dashboard accessed')
        return render_template('attendance/dashboard.html')
    
    except Exception as e:
        logger.error(f'Error in dashboard(): {str(e)}', exc_info=True)
        return render_template('error.html'), 500


# ... باقي الدوال
```

---

## 📝 نموذج من `crud.py` (جزء من الملف)

```python
# routes/attendance/crud.py
# -*- coding: utf-8 -*-
"""
عمليات الحذف والتعديل - CRUD Routes

يحتوي على:
- delete_attendance() → حذف السجل
- bulk_delete_attendance() → حذف جماعي
- edit_attendance_page() → صفحة التعديل
- update_attendance_page() → حفظ التعديل
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from core.extensions import db
from models import Attendance
from utils.audit_logger import log_activity
import logging

logger = logging.getLogger(__name__)


@login_required
def delete_attendance(id):
    """حذف سجل حضور (POST فقط)"""
    try:
        attendance = Attendance.query.get(id)
        if not attendance:
            flash('السجل غير موجود', 'warning')
            return redirect(url_for('attendance.index'))
        
        db.session.delete(attendance)
        db.session.commit()
        
        flash('تم حذف السجل بنجاح', 'success')
        logger.info(f'Deleted attendance record {id}')
        
        return redirect(url_for('attendance.index'))
    
    except Exception as e:
        logger.error(f'Error deleting attendance: {str(e)}', exc_info=True)
        flash('خطأ في حذف السجل', 'danger')
        return redirect(url_for('attendance.index'))


@login_required
def bulk_delete_attendance():
    """حذف جماعي للسجلات (POST فقط)"""
    try:
        ids = request.form.getlist('ids')
        
        if not ids:
            flash('يرجى تحديد سجلات', 'warning')
            return redirect(url_for('attendance.index'))
        
        # حذف السجلات
        Attendance.query.filter(Attendance.id.in_(ids)).delete()
        db.session.commit()
        
        flash(f'تم حذف {len(ids)} سجل بنجاح', 'success')
        logger.info(f'Bulk deleted {len(ids)} records')
        
        return redirect(url_for('attendance.index'))
    
    except Exception as e:
        logger.error(f'Error in bulk_delete: {str(e)}', exc_info=True)
        flash('خطأ في الحذف الجماعي', 'danger')
        return redirect(url_for('attendance.index'))


@login_required
def edit_attendance_page(id):
    """عرض صفحة التعديل (GET فقط)"""
    attendance = Attendance.query.get_or_404(id)
    return render_template('attendance/edit.html', attendance=attendance)


@login_required
def update_attendance_page(id):
    """حفظ التعديل (POST فقط)"""
    try:
        attendance = Attendance.query.get_or_404(id)
        
        # تحديث البيانات
        attendance.status = request.form['status']
        attendance.notes = request.form.get('notes', '')
        
        db.session.commit()
        
        flash('تم تحديث السجل بنجاح', 'success')
        logger.info(f'Updated attendance record {id}')
        
        return redirect(url_for('attendance.index'))
    
    except Exception as e:
        logger.error(f'Error updating attendance: {str(e)}', exc_info=True)
        flash('خطأ في تحديث السجل', 'danger')
        return redirect(url_for('attendance.edit_attendance_page', id=id))
```

---

## 📝 نموذج من `circles.py` (جزء من الملف)

```python
# routes/attendance/circles.py
# -*- coding: utf-8 -*-
"""
عمليات الدوائر - Circles Routes

يحتوي على:
- departments_circles_overview() → نظرة عامة
- circle_accessed_details() → تفاصيل الدائرة
"""

from flask import render_template, request, send_file
from flask_login import login_required
from core.extensions import db
from models import Attendance, Employee, Department
import logging

logger = logging.getLogger(__name__)


@login_required
def departments_circles_overview():
    """نظرة عامة على الدوائر (322 سطر في الأصلي)"""
    try:
        # منطق معقد للبيانات...
        return render_template('attendance/circles_overview.html')
    except Exception as e:
        logger.error(f'Error in circles overview: {str(e)}', exc_info=True)
        return render_template('error.html'), 500


@login_required
def circle_accessed_details(department_id, circle_name):
    """تفاصيل دائرة معينة"""
    try:
        # جلب البيانات...
        return render_template('attendance/circle_details.html')
    except Exception as e:
        logger.error(f'Error in circle details: {str(e)}', exc_info=True)
        return render_template('error.html'), 500
```

---

## 🔄 كيفية الاستيراض في app.py

**قبل:**
```python
# app.py (الطريقة القديمة)
from routes.attendance import attendance_bp
app.register_blueprint(attendance_bp, url_prefix='/attendance')
```

**بعد:**
```python
# app.py (نفس الطريقة، لا تحتاج تغيير!)
from routes.attendance import attendance_bp
app.register_blueprint(attendance_bp, url_prefix='/attendance')

# السبب: __init__.py ينشئ Blueprint نفسه!
```

---

## ✅ معايير الجودة للملفات الجديدة

كل ملف جديد يجب أن يحتوي على:

```python
# 1. -*- coding: utf-8 -*-  (في الأعلى)

# 2. Docstring شامل للملف
"""
وصف الملف وما يحتويه
مثال: طرق تسجيل الحضور
"""

# 3. الواردات المنظمة
from flask import ...
from flask_login import ...
from models import ...
from services import ...

# 4. Logger محلي
import logging
logger = logging.getLogger(__name__)

# 5. كل دالة لها docstring
def my_function():
    """
    وصف الدالة
    
    معاملات:
        ...
    
    الاستجابة:
        ...
    
    الأخطاء:
        - تفاصيل الأخطاء المحتملة
    """

# 6. معالجة الأخطاء (try/except)
try:
    # الكود الرئيسي
except Exception as e:
    logger.error(f'Error: {str(e)}', exc_info=True)
    flash('رسالة خطأ', 'danger')

# 7. Logging نشط
logger.info('Successfully completed action')

# 8. Flash messages للمستخدم
flash('تم العملية بنجاح', 'success')
```

---

هذه النماذج جاهزة للاستخدام والتطويرعند البدء بالتنفيذ الفعلي.

**آخر تحديث:** 2026-02-20
