// تم إزالة كود النافذة المنبثقة - الصور تفتح الآن في صفحة منفصلة

// مشاركة تفاصيل الورشة مع الصور
async function shareWorkshopDetails() {
    try {
        // جمع معلومات الصور
        const beforeImages = [];
        const afterImages = [];
        const imageFiles = [];
        
        // الصور من الخادم (يتم معالجتها من قبل الخادم)
        const shareText = buildWorkshopShareText();

        // محاولة المشاركة مع الملفات
        const shareData = {
            title: document.querySelector('h1')?.textContent || 'تقرير سجل الورشة',
            text: shareText
        };

        if (navigator.share) {
            await navigator.share(shareData);
            console.log('تم مشاركة التقرير بنجاح!');
        } else {
            // نسخ النص للحافظة كبديل
            await navigator.clipboard.writeText(shareText);
            showSuccessToast('تم نسخ تفاصيل الورشة للحافظة!');
        }

    } catch (error) {
        console.error('خطأ في مشاركة التقرير:', error);
        showErrorToast('حدث خطأ في المشاركة. حاول مرة أخرى.');
    }
}

// بناء نص المشاركة
function buildWorkshopShareText() {
    const vehiclePlate = document.querySelector('.vehicle-plate')?.textContent || '';
    const workshopName = document.querySelector('[data-workshop-name]')?.textContent || 'غير محدد';
    const entryDate = document.querySelector('[data-entry-date]')?.textContent || 'غير محدد';
    const repairReason = document.querySelector('[data-repair-reason]')?.textContent || 'غير محدد';
    const repairStatus = document.querySelector('[data-repair-status]')?.textContent || 'غير محدد';

    let shareText = `🚗 تقرير سجل الورشة - ${vehiclePlate}
═══════════════════════════════════════

📋 معلومات السيارة الكاملة:
━━━━━━━━━━━━━━━━━━━━━━━
• رقم اللوحة: ${vehiclePlate}

🏪 معلومات الورشة:
━━━━━━━━━━━━━━━━━━━━━━━
• اسم الورشة: ${workshopName}
• تاريخ الدخول: ${entryDate}

🔧 تفاصيل الإصلاح:
━━━━━━━━━━━━━━━━━━━━━━━
• سبب الدخول: ${repairReason}
• حالة الإصلاح: ${repairStatus}

═══════════════════════════════════════
📅 تاريخ إنشاء التقرير: ${new Date().toLocaleDateString('ar-SA')}
🕒 وقت إنشاء التقرير: ${new Date().toLocaleTimeString('ar-SA')}
🏢 نظام نُظم لإدارة الأساطيل`;

    return shareText;
}

// إظهار رسالة نجاح
function showSuccessToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    toast.innerHTML = `
        <i class="fas fa-check-circle" style="margin-left: 8px;"></i>
        ${message}
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// إظهار رسالة خطأ
function showErrorToast(message) {
    const errorToast = document.createElement('div');
    errorToast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(239, 68, 68, 0.3);
        z-index: 10000;
        font-weight: 600;
    `;
    errorToast.innerHTML = `
        <i class="fas fa-exclamation-triangle" style="margin-left: 8px;"></i>
        ${message}
    `;
    
    document.body.appendChild(errorToast);
    
    setTimeout(() => errorToast.remove(), 3000);
}

// إضافة CSS للتحريك
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
