/**
 * Handover Form Interactions
 * Handles all form behavior, validation, and dynamic interactions
 */

// ===== SIGNATURE PADS SYSTEM =====

const signaturePads = {}; // Store initialized signature pads

function initializeSignaturePad(canvasId) {
    const canvasEl = document.getElementById(canvasId);
    if (!canvasEl) return;

    if (signaturePads[canvasId]) {
        const container = canvasEl.parentElement;
        const pad = signaturePads[canvasId];
        if (pad.width !== container.offsetWidth || pad.height !== container.offsetHeight) {
            pad.setWidth(container.offsetWidth - 2);
            pad.setHeight(container.offsetHeight - 2);
            pad.renderAll();
        }
        return;
    }

    const container = canvasEl.parentElement;
    canvasEl.width = container.offsetWidth - 2;
    canvasEl.height = container.offsetHeight - 2;

    const signaturePad = new fabric.Canvas(canvasEl, {
        isDrawingMode: true,
        backgroundColor: '#ffffff'
    });

    signaturePad.freeDrawingBrush.color = '#000000';
    signaturePad.freeDrawingBrush.width = 2;

    signaturePads[canvasId] = signaturePad;
}

function clearSignature(canvasId) {
    if (signaturePads[canvasId]) {
        signaturePads[canvasId].clear();
    }
}

function saveSignatureData(canvasId, inputId) {
    const input = document.getElementById(inputId);
    if (signaturePads[canvasId] && input) {
        input.value = signaturePads[canvasId].toDataURL('image/png');
    }
}

// ===== SIGNATURE IMAGE UPLOAD =====

function setupSignatureUpload(uploadSelector, targetInputId) {
    document.querySelectorAll(uploadSelector).forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(event) {
                const imgData = event.target.result;
                document.getElementById(targetInputId).value = imgData;

                // Show preview
                const previewContainer = input.parentElement.querySelector('.signature-preview');
                if (previewContainer) {
                    const img = document.createElement('img');
                    img.src = imgData;
                    img.style.maxWidth = '100%';
                    img.style.maxHeight = '150px';
                    previewContainer.innerHTML = '';
                    previewContainer.appendChild(img);
                    previewContainer.style.display = 'block';
                }
            };
            reader.readAsDataURL(file);
        });
    });
}

// ===== EMPLOYEE SEARCH & FILTER =====

function setupEmployeeSearch() {
    const departmentSelect = document.getElementById('departmentSelect');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchBtn = document.getElementById('searchEmployeeBtn');
    const tableBody = document.getElementById('employeesTableBody');

    function filterEmployees() {
        const department = departmentSelect?.value || '';
        const searchText = searchInput?.value.toLowerCase() || '';

        if (!tableBody) return;

        tableBody.querySelectorAll('tr').forEach(row => {
            const dept = row.dataset.departmentId || '';
            const name = (row.dataset.name || '').toLowerCase();
            const empId = (row.dataset.employeeId || '').toLowerCase();

            const matchDept = !department || dept.includes(department);
            const matchSearch = !searchText || name.includes(searchText) || empId.includes(searchText);

            row.style.display = (matchDept && matchSearch) ? '' : 'none';
        });
    }

    departmentSelect?.addEventListener('change', filterEmployees);
    searchInput?.addEventListener('input', filterEmployees);
    searchBtn?.addEventListener('click', filterEmployees);

    // Handle employee selection
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('select-employee-btn')) {
            const row = e.target.closest('tr');
            const name = row.dataset.name;
            const employeeId = row.dataset.employeeId;

            document.getElementById('person_name').value = name;
            document.getElementById('employee_id').value = employeeId;

            // Close accordion
            const accordion = document.getElementById('employeeSearchAccordion');
            if (accordion) {
                accordion.querySelector('.accordion-button')?.classList.add('collapsed');
                accordion.querySelector('.collapse')?.classList.remove('show');
            }
        }
    });
}

// ===== SUPERVISOR SEARCH & FILTER =====

function setupSupervisorSearch() {
    const departmentSelect = document.getElementById('supervisorDepartmentSelect');
    const searchInput = document.getElementById('supervisorSearchInput');
    const searchBtn = document.getElementById('searchSupervisorBtn');
    const tableBody = document.getElementById('supervisorsTableBody');

    function filterSupervisors() {
        const department = departmentSelect?.value || '';
        const searchText = searchInput?.value.toLowerCase() || '';

        if (!tableBody) return;

        tableBody.querySelectorAll('tr').forEach(row => {
            const dept = row.dataset.departmentId || '';
            const name = (row.dataset.name || '').toLowerCase();
            const empId = (row.dataset.employeeId || '').toLowerCase();

            const matchDept = !department || dept.includes(department);
            const matchSearch = !searchText || name.includes(searchText) || empId.includes(searchText);

            row.style.display = (matchDept && matchSearch) ? '' : 'none';
        });
    }

    departmentSelect?.addEventListener('change', filterSupervisors);
    searchInput?.addEventListener('input', filterSupervisors);
    searchBtn?.addEventListener('click', filterSupervisors);

    // Handle supervisor selection
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('select-supervisor-btn')) {
            const row = e.target.closest('tr');
            const name = row.dataset.name;
            const employeeId = row.dataset.employeeId;

            document.getElementById('supervisor_name').value = name;
            document.getElementById('supervisor_employee_id').value = employeeId;
        }
    });
}

// ===== FILE UPLOAD MANAGEMENT =====

function setupFileUpload() {
    const triggerBtn = document.getElementById('trigger-file-select');
    const fileInput = document.getElementById('files');
    const previewContainer = document.getElementById('file-previews');

    if (!triggerBtn || !fileInput) return;

    triggerBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', function() {
        updateFilePreview(fileInput, previewContainer);
    });
}

function updateFilePreview(fileInput, container) {
    if (!fileInput || !container) return;

    const files = fileInput.files;
    container.innerHTML = '';

    for (let file of files) {
        const isImage = file.type.startsWith('image/');
        const isPdf = file.type === 'application/pdf';

        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';

        let previewHtml = `
            <div class="card file-preview-card">
                <div class="card-body">
                    <div class="mb-3">
        `;

        if (isImage) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'file-preview-image mb-3';
                col.querySelector('.file-preview-area').appendChild(img);
            };
            reader.readAsDataURL(file);
            previewHtml += '<div class="file-preview-area"></div>';
        } else if (isPdf) {
            previewHtml += '<div class="text-center mb-2"><i class="fas fa-file-pdf file-preview-pdf"></i></div>';
            previewHtml += `<small class="text-muted">${file.name}</small>`;
        } else {
            previewHtml += `<small class="text-muted">${file.name}</small>`;
        }

        previewHtml += `
                    </div>
                    <input type="text" class="form-control form-control-sm mb-2" placeholder="وصف الملف" data-file-index="${Array.from(files).indexOf(file)}">
                    <button type="button" class="btn btn-sm btn-danger remove-file-btn" data-file-index="${Array.from(files).indexOf(file)}">
                        <i class="fas fa-trash"></i> حذف
                    </button>
                </div>
            </div>
        `;

        col.innerHTML = previewHtml;
        container.appendChild(col);
    }

    // Handle remove buttons
    container.querySelectorAll('.remove-file-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const index = parseInt(this.dataset.fileIndex);
            removeFileByIndex(fileInput, index);
        });
    });
}

function removeFileByIndex(fileInput, index) {
    const dt = new DataTransfer();
    const files = fileInput.files;

    for (let i = 0; i < files.length; i++) {
        if (i !== index) {
            dt.items.add(files[i]);
        }
    }

    fileInput.files = dt.files;
    updateFilePreview(fileInput, document.getElementById('file-previews'));
}

// ===== EXISTING IMAGES MANAGEMENT =====

function setupExistingImagesManagement() {
    const selectAllCheckbox = document.getElementById('selectAllImages');
    const deleteBtn = document.getElementById('deleteSelectedImages');
    const selectedCountSpan = document.getElementById('selectedCount');

    if (!selectAllCheckbox) return;

    selectAllCheckbox.addEventListener('change', function() {
        document.querySelectorAll('.image-checkbox').forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        updateDeleteButton();
    });

    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('image-checkbox')) {
            updateDeleteButton();
        }
    });

    deleteBtn?.addEventListener('click', function() {
        const selectedImages = document.querySelectorAll('.image-checkbox:checked');
        if (selectedImages.length === 0) {
            alert('الرجاء اختيار صور للحذف');
            return;
        }

        if (!confirm(`هل أنت متأكد من حذف ${selectedImages.length} صورة؟`)) {
            return;
        }

        selectedImages.forEach(checkbox => {
            const imageId = checkbox.dataset.imageId;
            deleteImage(imageId);
        });
    });

    // Individual delete buttons
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-existing-image')) {
            const imageId = e.target.dataset.imageId;
            if (confirm('هل أنت متأكد من حذف هذه الصورة؟')) {
                deleteImage(imageId);
            }
        }
    });

    function updateDeleteButton() {
        const selected = document.querySelectorAll('.image-checkbox:checked').length;
        if (selectedCountSpan) {
            selectedCountSpan.textContent = selected;
        }
        if (deleteBtn) {
            deleteBtn.disabled = selected === 0;
        }
    }
}

function deleteImage(imageId) {
    fetch(`/vehicles/handover/image/${imageId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const container = document.getElementById(`existing-image-${imageId}`);
            if (container) {
                container.style.display = 'none';
            }

            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-dismissible fade show alert-success custom-alert';
            alertDiv.innerHTML = `
                تم حذف الصورة بنجاح
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container-fluid').insertBefore(alertDiv, document.querySelector('.card'));
            setTimeout(() => alertDiv.remove(), 3000);
        } else {
            alert('خطأ: ' + (data.message || 'فشل حذف الصورة'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('حدث خطأ أثناء حذف الصورة');
    });
}

// ===== FORM INITIALIZATION =====

function initializeForm() {
    // Set handover date to today if not in edit mode
    const handoverDateInput = document.getElementById('handover_date');
    if (handoverDateInput && !handoverDateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        handoverDateInput.value = today;
    }

    // Update form title based on handover type
    const typeSelect = document.getElementById('handover_type');
    if (typeSelect) {
        typeSelect.addEventListener('change', updateFormTitle);
    }
}

function updateFormTitle() {
    const typeSelect = document.getElementById('handover_type');
    const titleEl = document.getElementById('form-main-title');
    const plate = document.querySelector('.vehicle-plate')?.textContent || '';

    if (typeSelect && titleEl) {
        const type = typeSelect.value;
        const typeText = type === 'delivery' ? 'نموذج تسليم' : 'نموذج استلام';
        titleEl.innerHTML = `<i class="fas fa-file-alt me-2 text-primary"></i> ${typeText}: <span class="text-dark">${plate}</span>`;
    }
}

// ===== FORM SUBMISSION PREPARATION =====

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('main-handover-form');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        // Save all signature canvases before submit
        ['supervisor', 'driver', 'movement-officer'].forEach(type => {
            const canvasId = `${type}-signature-canvas`;
            const inputId = `${type}-signature-data`;
            if (document.getElementById(canvasId)) {
                saveSignatureData(canvasId, inputId);
            }
        });
    });

    // Initialize all components
    initializeForm();
    setupEmployeeSearch();
    setupSupervisorSearch();
    setupFileUpload();
    setupExistingImagesManagement();

    // Initialize signature pads in tabs
    document.querySelectorAll('[role="tabpanel"]').forEach(panel => {
        panel.addEventListener('shown.bs.tab', function() {
            const canvas = this.querySelector('canvas');
            if (canvas) {
                initializeSignaturePad(canvas.id);
            }
        });
    });

    // Initial signature pad initialization
    ['supervisor-signature-canvas', 'driver-signature-canvas', 'movement-officer-signature-canvas'].forEach(canvasId => {
        if (document.getElementById(canvasId)) {
            setTimeout(() => initializeSignaturePad(canvasId), 100);
        }
    });

    // Clear signature buttons
    document.querySelectorAll('.clear-signature').forEach(btn => {
        btn.addEventListener('click', function() {
            const canvasId = this.dataset.canvasId;
            clearSignature(canvasId);
        });
    });

    // Setup upload-based signatures
    setupSignatureUpload('.signature-upload', function(inputId) {
        return inputId;
    });

    ['supervisor', 'driver', 'movement-officer'].forEach(type => {
        const uploadInput = document.querySelector(`[data-target-input-id="${type}-signature-data"]`);
        if (uploadInput) {
            uploadInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(event) {
                        document.getElementById(`${type}-signature-data`).value = event.target.result;
                        const preview = uploadInput.parentElement.querySelector('.signature-preview');
                        if (preview) {
                            const img = document.createElement('img');
                            img.src = event.target.result;
                            img.style.maxWidth = '100%';
                            img.style.maxHeight = '150px';
                            preview.innerHTML = '';
                            preview.appendChild(img);
                            preview.style.display = 'block';
                        }
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });
});
