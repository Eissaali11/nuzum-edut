document.addEventListener('DOMContentLoaded', function() {
    const configEl = document.getElementById('workshop-config');

    if (configEl) {
        try {
            window.workshopConfig = JSON.parse(configEl.textContent);
        } catch (error) {
            window.workshopConfig = {};
        }
    } else {
        window.workshopConfig = window.workshopConfig || {};
    }

    const imageCards = document.querySelectorAll('.image-card-modern[data-image-link]');
    imageCards.forEach(card => {
        card.addEventListener('click', () => {
            const target = card.getAttribute('data-image-link');
            if (target) {
                window.location.href = target;
            }
        });
    });

    const shareButton = document.querySelector('.js-share-workshop');
    if (shareButton) {
        shareButton.addEventListener('click', () => {
            shareWorkshopDetails();
        });
    }

    const confirmButtons = document.querySelectorAll('.js-confirm-action');
    confirmButtons.forEach(button => {
        button.addEventListener('click', event => {
            const message = button.getAttribute('data-confirm-message');
            if (message && !confirm(message)) {
                event.preventDefault();
            }
        });
    });
});

async function shareWorkshopDetails() {
    try {
        const config = window.workshopConfig || {};
        const images = Array.isArray(config.images) ? config.images : [];
        const beforeImages = images.filter(image => image.type === 'before');
        const afterImages = images.filter(image => image.type === 'after');
        const imageFiles = [];

        for (const image of beforeImages.concat(afterImages)) {
            if (!image.url) {
                continue;
            }
            try {
                const response = await fetch(image.url);
                const blob = await response.blob();
                const fileName = image.type === 'after'
                    ? `بعد_الإصلاح_${config.vehicle?.plateNumber || ''}.jpg`
                    : `قبل_الإصلاح_${config.vehicle?.plateNumber || ''}.jpg`;
                const file = new File([blob], fileName, { type: blob.type });
                imageFiles.push(file);
            } catch (error) {
                console.log('خطأ في تحميل الصورة:', error);
            }
        }

        const shareText = buildWorkshopShareText(config, beforeImages, afterImages);
        const shareData = {
            title: config.title || 'تقرير سجل الورشة',
            text: shareText
        };

        if (navigator.canShare && imageFiles.length > 0) {
            shareData.files = imageFiles;
        }

        if (navigator.share) {
            await navigator.share(shareData);
        } else {
            await navigator.clipboard.writeText(shareText);
            showToast('تم نسخ تفاصيل الورشة للحافظة!', 'success');
        }
    } catch (error) {
        console.error('خطأ في مشاركة التقرير:', error);
        showToast('حدث خطأ في المشاركة. حاول مرة أخرى.', 'error');
    }
}

function buildWorkshopShareText(config, beforeImages, afterImages) {
    const vehicle = config.vehicle || {};
    const record = config.record || {};

    let shareText = `🚗 تقرير سجل الورشة - ${vehicle.plateNumber || ''}
═══════════════════════════════════════

📋 معلومات السيارة الكاملة:
━━━━━━━━━━━━━━━━━━━━━━━
• رقم اللوحة: ${vehicle.plateNumber || ''}
• الماركة: ${vehicle.make || ''}
• الموديل: ${vehicle.model || ''}
• السنة: ${vehicle.year || ''}

🏪 معلومات الورشة:
━━━━━━━━━━━━━━━━━━━━━━━
• اسم الورشة: ${record.workshopName || 'غير محدد'}
• تاريخ الدخول: ${record.entryDate || 'غير محدد'}`;

    if (record.exitDate) {
        shareText += `
• تاريخ الخروج: ${record.exitDate}`;
    }

    if (record.technicianName) {
        shareText += `
• الفني المسؤول: ${record.technicianName}`;
    }

    shareText += `

🔧 تفاصيل الإصلاح:
━━━━━━━━━━━━━━━━━━━━━━━
• سبب الدخول: ${record.reasonLabel || record.reason || 'غير محدد'}
• حالة الإصلاح: ${record.repairStatusLabel || record.repairStatus || 'غير محدد'}`;

    if (record.costFormatted) {
        shareText += `
• التكلفة الإجمالية: ${record.costFormatted} ريال سعودي`;
    }

    if (record.description) {
        shareText += `

📝 وصف المشكلة والأعمال المنفذة:
━━━━━━━━━━━━━━━━━━━━━━━
${record.description}`;
    }

    if (beforeImages.length > 0 || afterImages.length > 0) {
        shareText += `

📸 الصور المرفقة (${beforeImages.length + afterImages.length} صورة):
━━━━━━━━━━━━━━━━━━━━━━━`;

        if (beforeImages.length > 0) {
            shareText += `
📷 صور قبل الإصلاح (${beforeImages.length} صورة):`;
            beforeImages.forEach((img, index) => {
                const label = img.notes && img.notes !== 'صورة قبل الإصلاح'
                    ? img.notes
                    : 'صورة قبل الإصلاح';
                shareText += `
  ${index + 1}. ${label}`;
            });
        }

        if (afterImages.length > 0) {
            shareText += `
✅ صور بعد الإصلاح (${afterImages.length} صورة):`;
            afterImages.forEach((img, index) => {
                const label = img.notes && img.notes !== 'صورة بعد الإصلاح'
                    ? img.notes
                    : 'صورة بعد الإصلاح';
                shareText += `
  ${index + 1}. ${label}`;
            });
        }
    } else {
        shareText += `

📸 الصور المرفقة:
━━━━━━━━━━━━━━━━━━━━━━━
لا توجد صور مرفقة لهذا السجل`;
    }

    if (record.deliveryLink || record.receptionLink) {
        shareText += `

🔗 الروابط الخارجية:
━━━━━━━━━━━━━━━━━━━━━━━`;
        if (record.deliveryLink) {
            shareText += `
• رابط تسليم الورشة:
  ${record.deliveryLink}`;
        }
        if (record.receptionLink) {
            shareText += `
• رابط استلام من الورشة:
  ${record.receptionLink}`;
        }
    }

    if (record.notes) {
        shareText += `

📝 ملاحظات إضافية:
━━━━━━━━━━━━━━━━━━━━━━━
${record.notes}`;
    }

    shareText += `

═══════════════════════════════════════
📅 تاريخ إنشاء التقرير: ${new Date().toLocaleDateString('ar-SA')}
🕒 وقت إنشاء التقرير: ${new Date().toLocaleTimeString('ar-SA')}
🏢 نظام نُظم لإدارة الأساطيل`;

    return shareText;
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `workshop-toast ${type === 'error' ? 'workshop-toast-error' : 'workshop-toast-success'}`;
    toast.innerHTML = `<i class="fas ${type === 'error' ? 'fa-exclamation-triangle' : 'fa-check-circle'}"></i>${message}`;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('workshop-toast-hide');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
