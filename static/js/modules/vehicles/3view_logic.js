/**
 * 3view.html Logic - Vehicle View Alternative Layout
 * Extracted from inline <script> for better performance and maintainability
 */

// Toggle older workshop records visibility
function toggleOlderWorkshopRecords() {
    const olderRecords = document.querySelectorAll('.older-workshop-record');
    const toggleIcon = document.getElementById('toggleWorkshopIcon');
    const toggleText = document.getElementById('toggleWorkshopText');
    
    if (olderRecords[0] && olderRecords[0].classList.contains('d-none')) {
        // Show older records
        olderRecords.forEach(record => {
            record.classList.remove('d-none');
        });
        toggleIcon.className = 'fas fa-chevron-up ms-1';
        toggleText.textContent = 'إخفاء العمليات السابقة';
    } else {
        // Hide older records
        olderRecords.forEach(record => {
            record.classList.add('d-none');
        });
        toggleIcon.className = 'fas fa-chevron-down ms-1';
        toggleText.textContent = 'عرض العمليات السابقة (' + olderRecords.length + ')';
    }
}

// Authorization management functions
function viewAuthDetails(authId) {
    alert('عرض تفاصيل التفويض رقم: ' + authId);
}

function editAuthDetails(authId) {
    alert('تعديل التفويض رقم: ' + authId);
}

function approveAuth(authId) {
    if (confirm('هل أنت متأكد من الموافقة على هذا التفويض؟')) {
        alert('تم الموافقة على التفويض رقم: ' + authId);
    }
}

function rejectAuth(authId) {
    if (confirm('هل أنت متأكد من رفض هذا التفويض؟')) {
        alert('تم رفض التفويض رقم: ' + authId);
    }
}

// Filter employees by department
const departmentSelect = document.getElementById('department_id');
if (departmentSelect) {
    departmentSelect.addEventListener('change', function() {
        const departmentId = this.value;
        const employeeSelect = document.getElementById('employee_id');
        if (!employeeSelect) return;
        
        const options = employeeSelect.querySelectorAll('option');
        
        options.forEach(option => {
            if (option.value === '') {
                option.style.display = 'block';
                return;
            }
            
            const employeeDepartments = option.dataset.departments ? option.dataset.departments.split(',') : [];
            
            if (!departmentId || employeeDepartments.includes(departmentId)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
        
        // Reset selected employee
        employeeSelect.value = '';
    });
}

// Placeholder function for counters
function animateCounters() {
    console.log('animateCounters called');
}

// Handover deletion management
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('select-all');
    const handoverCheckboxes = document.querySelectorAll('.handover-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const handoverDeleteForm = document.getElementById('handover-delete-form');

    // Update delete button state based on selection
    function updateDeleteButtonState() {
        const checkedBoxes = document.querySelectorAll('.handover-checkbox:checked');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.disabled = checkedBoxes.length === 0;
        }
    }

    // Select all functionality
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            handoverCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateDeleteButtonState();
        });
    }

    // Update delete button on checkbox change
    handoverCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateDeleteButtonState();
            
            // Update "select all" state
            if (selectAllCheckbox) {
                const checkedCount = document.querySelectorAll('.handover-checkbox:checked').length;
                selectAllCheckbox.checked = checkedCount === handoverCheckboxes.length;
                selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < handoverCheckboxes.length;
            }
        });
    });

    // Confirm deletion before submit
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

    // Initialize button state
    updateDeleteButtonState();
});

// Show license image modal
function showLicenseModal() {
    const modal = `
        <div class="modal fade" id="licenseModal" tabindex="-1" aria-labelledby="licenseModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="licenseModalLabel">صورة رخصة السيارة</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img src="" class="img-fluid rounded" style="max-height: 70vh; width: auto;" alt="صورة رخصة السيارة">
                    </div>
                    <div class="modal-footer">
                        <a href="#" target="_blank" class="btn btn-success">
                            <i class="fas fa-download ms-1"></i>تحميل الصورة
                        </a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إغلاق</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal
    const existingModal = document.getElementById('licenseModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modal);
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(document.getElementById('licenseModal'));
    bootstrapModal.show();
}

// Copy link to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success toast
        const toast = document.createElement('div');
        toast.className = 'toast show position-fixed top-0 end-0 m-3';
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto text-success">نجح النسخ</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">تم نسخ الرابط إلى الحافظة</div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }).catch(function() {
        alert('تم نسخ الرابط');
    });
}

// Validate Google Drive link
function validateDriveLink(url) {
    const drivePattern = /^https:\/\/(drive\.google\.com|docs\.google\.com)/;
    return drivePattern.test(url);
}

// Handle Google Drive form
document.addEventListener('DOMContentLoaded', function() {
    const driveForm = document.getElementById('driveForm');
    const driveLinkInput = document.getElementById('driveLink');
    const linkPreview = document.getElementById('linkPreview');
    const previewContainer = document.getElementById('previewContainer');
    
    if (driveLinkInput) {
        driveLinkInput.addEventListener('input', function() {
            const url = this.value.trim();
            if (url && validateDriveLink(url)) {
                linkPreview.textContent = url;
                previewContainer.style.display = 'block';
                previewContainer.className = 'alert alert-success';
                previewContainer.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>رابط صحيح:</strong><br>
                    <small>${url}</small>
                `;
            } else if (url) {
                previewContainer.style.display = 'block';
                previewContainer.className = 'alert alert-warning';
                previewContainer.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    يرجى إدخال رابط Google Drive صحيح
                `;
            } else {
                previewContainer.style.display = 'none';
            }
        });
    }
    
    if (driveForm) {
        driveForm.addEventListener('submit', function(e) {
            const url = driveLinkInput.value.trim();
            if (url && !validateDriveLink(url)) {
                e.preventDefault();
                alert('يرجى إدخال رابط Google Drive صحيح');
                return false;
            }
        });
    }
});
