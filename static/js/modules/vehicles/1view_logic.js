document.addEventListener('DOMContentLoaded', function() {
    const configEl = document.getElementById('vehicle-config');

    if (configEl) {
        try {
            window.vehicleConfig = JSON.parse(configEl.textContent);
        } catch (error) {
            window.vehicleConfig = {};
        }
    } else {
        window.vehicleConfig = window.vehicleConfig || {};
    }

    const vehicleConfig = window.vehicleConfig || {};
    const colorBadge = document.querySelector('.vehicle-color-badge');

    if (colorBadge && vehicleConfig.color) {
        colorBadge.style.backgroundColor = vehicleConfig.color;
        if (vehicleConfig.colorText) {
            colorBadge.style.color = vehicleConfig.colorText;
        }
    }

    const sidebarLinks = document.querySelectorAll('.sidebar-nav .nav-link');
    const contentSections = document.querySelectorAll('.main-content .content-section');

    function showSection(targetId) {
        contentSections.forEach(section => {
            section.classList.remove('active');
        });
        sidebarLinks.forEach(link => {
            link.classList.remove('active');
        });

        const targetSection = document.querySelector(targetId);
        const activeLink = document.querySelector(`.nav-link[href="${targetId}"]`);

        if (targetSection) {
            targetSection.classList.add('active');
        }
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const targetId = this.getAttribute('href');
            showSection(targetId);
            if (window.innerWidth < 992) {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    const firstSection = document.querySelector('.main-content .content-section');
    if (firstSection) {
        showSection('#' + firstSection.id);
    }

    const selectAllCheckbox = document.getElementById('select-all');
    const handoverCheckboxes = document.querySelectorAll('.handover-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const handoverDeleteForm = document.getElementById('handover-delete-form');

    function updateDeleteButtonState() {
        const checkedBoxes = document.querySelectorAll('.handover-checkbox:checked');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.disabled = checkedBoxes.length === 0;
        }
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            handoverCheckboxes.forEach(checkbox => { checkbox.checked = this.checked; });
            updateDeleteButtonState();
        });
    }

    handoverCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateDeleteButtonState();
            if (selectAllCheckbox) {
                const checkedCount = document.querySelectorAll('.handover-checkbox:checked').length;
                selectAllCheckbox.checked = checkedCount === handoverCheckboxes.length;
                selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < handoverCheckboxes.length;
            }
        });
    });

    if (handoverDeleteForm) {
        handoverDeleteForm.addEventListener('submit', function(e) {
            const checkedBoxes = document.querySelectorAll('.handover-checkbox:checked');
            if (checkedBoxes.length === 0) {
                e.preventDefault();
                alert('يرجى تحديد السجلات المراد حذفها');
                return false;
            }
            const confirmMessage = `هل أنت متأكد من حذف ${checkedBoxes.length} سجل من سجلات التسليم والاستلام؟\n\nهذا الإجراء لا يمكن التراجع عنه.`;
            if (!confirm(confirmMessage)) {
                e.preventDefault();
                return false;
            }
        });
    }

    updateDeleteButtonState();
});

function toggleOlderWorkshopRecords() {
    const olderRecords = document.querySelectorAll('.older-workshop-record');
    const toggleIcon = document.getElementById('toggleWorkshopIcon');
    const toggleText = document.getElementById('toggleWorkshopText');

    if (olderRecords[0] && olderRecords[0].classList.contains('d-none')) {
        olderRecords.forEach(record => { record.classList.remove('d-none'); });
        if (toggleIcon) {
            toggleIcon.className = 'fas fa-chevron-up ms-1';
        }
        if (toggleText) {
            toggleText.textContent = 'إخفاء العمليات السابقة';
        }
    } else {
        olderRecords.forEach(record => { record.classList.add('d-none'); });
        if (toggleIcon) {
            toggleIcon.className = 'fas fa-chevron-down ms-1';
        }
        if (toggleText) {
            toggleText.textContent = 'عرض العمليات السابقة (' + olderRecords.length + ')';
        }
    }
}

function showLicenseModal() {
    const vehicleConfig = window.vehicleConfig || {};

    if (!vehicleConfig.licenseImageUrl) {
        return;
    }

    const existingModal = document.getElementById('licenseModalInstance');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHtml = `
        <div class="modal fade" id="licenseModalInstance" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">صورة رخصة السيارة - ${vehicleConfig.plateNumber || ''}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body text-center bg-light">
                        <img src="${vehicleConfig.licenseImageUrl}" class="img-fluid rounded license-modal-image" alt="صورة رخصة السيارة">
                    </div>
                    <div class="modal-footer">
                        <a href="${vehicleConfig.licenseImageDownloadUrl || vehicleConfig.licenseImageUrl}" target="_blank" class="btn btn-success"><i class="fas fa-download ms-1"></i> تحميل الصورة</a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إغلاق</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modalElement = document.getElementById('licenseModalInstance');
    const bootstrapModal = new bootstrap.Modal(modalElement);
    bootstrapModal.show();

    modalElement.addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}
