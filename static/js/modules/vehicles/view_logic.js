/**
 * Vehicle View Logic
 * Handles all interactive functionality for vehicle display page
 */

document.addEventListener("DOMContentLoaded", function () {
    // ============================================================================
    // TAB DEFAULT STATE
    // ============================================================================
    const defaultInfoTab = document.querySelector('#info-tab');
    if (defaultInfoTab) {
        const tabTrigger = new bootstrap.Tab(defaultInfoTab);
        tabTrigger.show();
    }

    const tabLinks = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabLinks.forEach((tabLink) => {
        tabLink.addEventListener("shown.bs.tab", (event) => {
            localStorage.setItem("activeVehicleTab", event.target.getAttribute("data-bs-target"));
        });
    });

    // ============================================================================
    // HANDOVER RECORDS: SELECT ALL & BULK DELETE
    // ============================================================================
    const selectAllCheckbox = document.getElementById("select-all");
    const handoverCheckboxes = document.querySelectorAll(".handover-checkbox");
    const deleteSelectedBtn = document.getElementById("delete-selected-btn");
    const handoverDeleteForm = document.getElementById("handover-delete-form");

    if (selectAllCheckbox && handoverCheckboxes.length > 0 && deleteSelectedBtn) {
        function updateDeleteButtonState() {
            const checkedCount = document.querySelectorAll(".handover-checkbox:checked").length;
            deleteSelectedBtn.disabled = checkedCount === 0;

            if (checkedCount > 0) {
                deleteSelectedBtn.innerHTML = `<i class="fas fa-trash-alt ms-1"></i> حذف المحدد (${checkedCount})`;
                deleteSelectedBtn.classList.remove('btn-secondary');
                deleteSelectedBtn.classList.add('btn-danger');
            } else {
                deleteSelectedBtn.innerHTML = `<i class="fas fa-trash-alt ms-1"></i> حذف المحدد`;
                deleteSelectedBtn.classList.remove('btn-danger');
                deleteSelectedBtn.classList.add('btn-secondary');
            }
        }

        selectAllCheckbox.addEventListener("change", function () {
            handoverCheckboxes.forEach((checkbox) => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateDeleteButtonState();
        });

        handoverCheckboxes.forEach((checkbox) => {
            checkbox.addEventListener("change", function () {
                const allChecked = document.querySelectorAll(".handover-checkbox:checked").length === handoverCheckboxes.length;
                selectAllCheckbox.checked = allChecked;
                updateDeleteButtonState();
            });
        });

        updateDeleteButtonState();
    }

    if (handoverDeleteForm) {
        handoverDeleteForm.addEventListener("submit", function (e) {
            const checkedBoxes = document.querySelectorAll(".handover-checkbox:checked");
            if (checkedBoxes.length === 0) {
                e.preventDefault();
                alert("يرجى تحديد السجلات المراد حذفها");
                return false;
            }

            const confirmMessage = `هل أنت متأكد من حذف ${checkedBoxes.length} سجل من سجلات التسليم والاستلام؟\n\nهذا الإجراء لا يمكن التراجع عنه.`;
            if (!confirm(confirmMessage)) {
                e.preventDefault();
                return false;
            }
        });
    }

    // ============================================================================
    // SAFETY CHECK FORM SHARING
    // ============================================================================
    window.shareSafetyCheckForm = function(vehicleId, plateNumber) {
        const formUrl = window.location.origin + "/external-safety/external-safety-check/" + vehicleId;

        const shareData = {
            title: "نموذج فحص السلامة الخارجي - نُظم",
            text: `مرحباً 👋

يرجى تعبئة نموذج فحص السلامة الخارجي للمركبة التالية:

🚗 رقم اللوحة: ${plateNumber}
📋 نوع النموذج: فحص السلامة الخارجي
🏢 نظام نُظم لإدارة المركبات

يرجى الضغط على الرابط أدناه لتعبئة النموذج:
${formUrl}

⚠️ ملاحظة: يرجى تعبئة النموذج بعناية وإرفاق جميع الصور المطلوبة للفحص.

شكراً لتعاونكم`,
            url: formUrl,
        };

        if (navigator.share) {
            navigator.share(shareData)
                .then(() => {
                    showToast("تم مشاركة الرابط بنجاح!", "success");
                })
                .catch((error) => {
                    console.error("خطأ في المشاركة:", error);
                    fallbackShare(shareData);
                });
        } else {
            fallbackShare(shareData);
        }
    };

    // ============================================================================
    // FALLBACK SHARE FUNCTION
    // ============================================================================
    window.fallbackShare = function(shareData) {
        const textToCopy = shareData.text;

        if (navigator.clipboard) {
            navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    showToast("تم نسخ رابط الفحص للحافظة!", "success");
                })
                .catch(() => {
                    showShareModal(shareData);
                });
        } else {
            showShareModal(shareData);
        }
    };

    // ============================================================================
    // SHARE MODAL
    // ============================================================================
    function showShareModal(shareData) {
        const modal = document.createElement("div");
        modal.className = "modal fade";
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">مشاركة رابط فحص السلامة</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-3">انسخ الرابط والرسالة التالية لمشاركتها:</p>
                        <textarea class="form-control" rows="8" readonly>${shareData.text}</textarea>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="window.copyToClipboard(this, '${shareData.text.replace(/'/g, "\\'")}')">
                            <i class="fas fa-copy ms-1"></i>
                            نسخ النص
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إغلاق</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        modal.addEventListener("hidden.bs.modal", () => {
            document.body.removeChild(modal);
        });
    }

    // ============================================================================
    // COPY TO CLIPBOARD
    // ============================================================================
    window.copyToClipboard = function(button, text) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);

        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check ms-1"></i> تم النسخ!';
        button.className = "btn btn-success";

        setTimeout(() => {
            button.innerHTML = originalText;
            button.className = "btn btn-primary";
        }, 2000);
    };

    // ============================================================================
    // TOAST NOTIFICATIONS
    // ============================================================================
    window.showToast = function(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = "top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 300px;";
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    };

    // ============================================================================
    // IMAGE MODAL VIEWER
    // ============================================================================
    window.openImageModal = function(imageSrc, title = 'صورة') {
        const modal = document.createElement("div");
        modal.className = "modal fade";
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <img src="${imageSrc}" alt="${title}" class="img-fluid">
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        modal.addEventListener("hidden.bs.modal", () => {
            document.body.removeChild(modal);
        });
    };

    // ============================================================================
    // DOCUMENT SHARING (WHATSAPP)
    // ============================================================================
    window.shareVehicleDocuments = function() {
        const plateElem = document.querySelector('[data-plate-number]');
        const plateNumber = plateElem ? plateElem.getAttribute('data-plate-number') : 'السيارة';

        const shareText = `أرسل لك وثائق المركبة رقم ${plateNumber} من نظام نُظم لإدارة المركبات`;
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
        window.open(whatsappUrl, '_blank');
    };
});
