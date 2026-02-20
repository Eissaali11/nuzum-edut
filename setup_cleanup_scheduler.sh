#!/bin/bash
# Setup script for Auto-Cleanup on Linux/Mac using cron
#
# هذا السكريبت ينشئ مهمة مجدولة باستخدام cron لتشغيل auto_cleanup.py يومياً

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="${SCRIPT_DIR}/venv/bin/python"
SCRIPT_PATH="${SCRIPT_DIR}/auto_cleanup.py"
CRON_USER=$(whoami)

echo ""
echo "═════════════════════════════════════════════════════"
echo "  🔧 إعداد جدولة Auto-Cleanup لـ Nuzum HR"
echo "═════════════════════════════════════════════════════"
echo ""

# التحقق من وجود Python
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ لم يتم العثور على Python في المسار المتوقع"
    echo "المسار المتوقع: $PYTHON_PATH"
    exit 1
fi

# التحقق من وجود السكريبت
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ لم يتم العثور على السكريبت في المسار المتوقع"
    echo "المسار المتوقع: $SCRIPT_PATH"
    exit 1
fi

echo "✅ تم التحقق من المتطلبات"
echo ""

# تحديد وقت التشغيل (2:00 صباحاً)
SCHEDULE_TIME="0 2 * * *"
CRON_COMMAND="$SCHEDULE_TIME $PYTHON_PATH $SCRIPT_PATH >> $SCRIPT_DIR/cleanup.log 2>&1"

echo "⏳ جاري إعداد cron..."
echo ""

# حذف أي مهام سابقة
crontab -l 2>/dev/null | grep -v "auto_cleanup" | crontab - 2>/dev/null || true

# إضافة المهمة الجديدة
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

echo ""
echo "✅ تم إنشاء جدولة التنظيف بنجاح!"
echo ""
echo "📋 تفاصيل المهمة:"
echo "  ├─ الجدول: $SCHEDULE_TIME (يومياً في 2:00 صباحاً)"
echo "  ├─ السكريبت: $SCRIPT_PATH"
echo "  ├─ المستخدم: $CRON_USER"
echo "  └─ السجلات: $SCRIPT_DIR/cleanup.log"
echo ""

echo "📊 سيتم تشغيل التنظيف تلقائياً:"
echo "  • حذف التقارير المؤقتة (أقدم من 48 ساعة)"
echo "  • تنظيف ملفات Cache"
echo "  • حذف الملفات المرفوعة (أقدم من 90 يوم)"
echo "  • حذف ملفات السجلات (أقدم من 30 يوم)"
echo "  • تنظيف ملفات Python المؤقتة"
echo ""

# عرض الـ crontab الحالي
echo "═════════════════════════════════════════════════════"
echo "  📋 جدول Cron الحالي"
echo "═════════════════════════════════════════════════════"
echo ""
crontab -l | grep -v "^#" | grep -v "^$" || true
echo ""

echo "═════════════════════════════════════════════════════"
echo "  ✅ انتهت عملية الإعداد"
echo "═════════════════════════════════════════════════════"
echo ""
echo "💡 نصائح مفيدة:"
echo "  • لتشغيل التنظيف يدوياً الآن: python auto_cleanup.py"
echo "  • لحذف المهمة: crontab -e (ثم احذف الخط)"
echo "  • لعرض السجلات: tail -f cleanup.log"
echo ""
