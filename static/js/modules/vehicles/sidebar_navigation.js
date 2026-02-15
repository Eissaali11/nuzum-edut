/**
 * Vehicle Detail View - Sidebar Navigation Module
 * Extracted from: modules/vehicles/presentation/templates/vehicles/view_with_sidebar.html
 * 
 * Handles:
 * - Sidebar navigation between content sections
 * - Dynamic content loading for various vehicle sections
 * - Global vehicle data management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Setup sidebar navigation
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    const contentSections = document.querySelectorAll('.content-section');
    
    // Hide all sections except the first
    contentSections.forEach((section, index) => {
        if (index === 0) {
            section.classList.remove('d-none');
        } else {
            section.classList.add('d-none');
        }
    });
    
    // Add event listeners to sidebar items
    sidebarItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all items
            sidebarItems.forEach(si => si.classList.remove('active'));
            
            // Add active class to selected item
            this.classList.add('active');
            
            // Hide all sections
            contentSections.forEach(section => section.classList.add('d-none'));
            
            // Show selected section
            const sectionName = this.getAttribute('data-section');
            const targetSection = document.getElementById('content-' + sectionName);
            
            if (targetSection) {
                targetSection.classList.remove('d-none');
                
                // Load content if not already loaded
                loadSectionContent(sectionName, targetSection);
            }
        });
    });
    
    // Set vehicle color badge text color based on background color
    const colorBadge = document.getElementById('vehicleColorBadge');
    if (colorBadge) {
        const bgColor = window.getComputedStyle(colorBadge).backgroundColor;
        const lightColors = ['white', 'yellow', 'silver', 'rgb(255, 255, 255)', 'rgb(255, 255, 0)', 'rgb(192, 192, 192)'];
        const textColor = lightColors.some(lc => bgColor.includes(lc) || colorBadge.style.backgroundColor === lc) ? '#000' : '#fff';
        colorBadge.style.color = textColor;
    }
});

/**
 * Load content for a specific section
 * @param {string} sectionName - Name of the section to load
 * @param {HTMLElement} targetSection - Target element to populate
 */
function loadSectionContent(sectionName, targetSection) {
    // Check if already loaded
    if (targetSection.getAttribute('data-loaded') === 'true') {
        return;
    }
    
    // Load content based on section type
    switch(sectionName) {
        case 'documents':
            loadDocumentsContent(targetSection);
            break;
        case 'periodic-inspection':
            loadPeriodicInspectionContent(targetSection);
            break;
        case 'safety-checks':
            loadSafetyChecksContent(targetSection);
            break;
        case 'projects':
            loadProjectsContent(targetSection);
            break;
        case 'handovers':
            loadHandoversContent(targetSection);
            break;
        case 'workshop':
            loadWorkshopContent(targetSection);
            break;
        case 'external-authorizations':
            loadExternalAuthorizationsContent(targetSection);
            break;
        case 'accidents':
            loadAccidentsContent(targetSection);
            break;
        case 'driver-stats':
            loadDriverStatsContent(targetSection);
            break;
        case 'attachments':
            loadAttachmentsContent(targetSection);
            break;
    }
}

/**
 * Load documents content
 */
function loadDocumentsContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>وثائق المركبة</h5>
                <p class="text-muted">سيتم تحميل محتوى الوثائق هنا</p>
                <a href="${window.vehicleData.urls.viewDocuments}" class="btn btn-primary">
                    <i class="fas fa-eye ms-1"></i>
                    عرض جميع الوثائق
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load periodic inspection content
 */
function loadPeriodicInspectionContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>الفحص الدوري</h5>
                <p class="text-muted">سيتم تحميل محتوى الفحص الدوري هنا</p>
                <a href="${window.vehicleData.urls.vehicleInspections}" class="btn btn-primary">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة فحص دوري
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load safety checks content
 */
function loadSafetyChecksContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>فحوصات السلامة</h5>
                <p class="text-muted">سيتم تحميل محتوى فحوصات السلامة هنا</p>
                <a href="${window.vehicleData.urls.vehicleSafetyChecks}" class="btn btn-success">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة فحص سلامة
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load projects content
 */
function loadProjectsContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>المشاريع</h5>
                <p class="text-muted">سيتم تحميل محتوى المشاريع هنا</p>
                <button class="btn btn-warning">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة مشروع
                </button>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load handovers content
 */
function loadHandoversContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>سجلات التسليم والاستلام</h5>
                <p class="text-muted">سيتم تحميل محتوى سجلات التسليم والاستلام هنا</p>
                <a href="javascript:window.open('/mobile/vehicles/' + ${window.vehicleData.vehicle_id} + '/handover/create', '_blank')" class="btn btn-info">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة سجل تسليم
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load workshop content with detailed table
 */
function loadWorkshopContent(targetSection) {
    const workshopData = window.vehicleData.workshop_records;
    const totalCost = window.vehicleData.total_maintenance_cost;
    const daysInWorkshop = window.vehicleData.days_in_workshop;
    const vehicleId = window.vehicleData.vehicle_id;
    
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        
        let content = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">
                    <i class="fas fa-tools ms-2"></i>
                    سجلات الورشة
                    <span class="badge bg-secondary">${workshopData.length}</span>
                </h5>
                <a href="/mobile/vehicles/${vehicleId}/workshop/create" target="_blank" class="btn btn-sm btn-primary">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة سجل ورشة
                </a>
            </div>
        `;
        
        if (workshopData.length > 0) {
            content += `
                <div class="table-responsive">
                    <table class="table table-sm table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>تاريخ الدخول</th>
                                <th>سبب الدخول</th>
                                <th>حالة الإصلاح</th>
                                <th>التكلفة</th>
                                <th>الإجراءات</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            workshopData.forEach(record => {
                // Format reason badge
                let reasonBadge = getReasonBadge(record.reason);
                
                // Format status badge
                let statusBadge = getStatusBadge(record.repair_status);
                
                // Format cost
                let costDisplay = record.cost ? 
                    new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(record.cost) :
                    '<span class="text-muted">غير محدد</span>';
                
                content += `
                    <tr>
                        <td>${record.formatted_entry_date}</td>
                        <td>${reasonBadge}</td>
                        <td>${statusBadge}</td>
                        <td>${costDisplay}</td>
                        <td>
                            <div class="btn-group" role="group">
                                <a href="/vehicles/workshop-details/${record.id}" class="btn btn-sm btn-outline-primary" title="عرض التفاصيل">
                                    <i class="fas fa-eye"></i>
                                </a>
                                <button class="btn btn-sm btn-outline-success" onclick="shareWorkshopRecord(${record.id})" title="مشاركة">
                                    <i class="fas fa-share-alt"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            content += `
                        </tbody>
                    </table>
                </div>
                
                <!-- Statistics -->
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="small text-center p-2 bg-light rounded">
                            <div class="fw-bold text-primary">${workshopData.length}</div>
                            <small class="text-muted">إجمالي السجلات</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="small text-center p-2 bg-light rounded">
                            <div class="fw-bold text-success">${totalCost.toFixed(2)}</div>
                            <small class="text-muted">إجمالي التكلفة (ريال)</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="small text-center p-2 bg-light rounded">
                            <div class="fw-bold text-warning">${daysInWorkshop}</div>
                            <small class="text-muted">أيام في الورشة</small>
                        </div>
                    </div>
                </div>
            `;
        } else {
            content += `
                <div class="text-center py-4">
                    <div class="mb-3">
                        <i class="fas fa-tools fa-3x text-muted"></i>
                    </div>
                    <h6 class="text-muted">لا توجد سجلات ورشة للسيارة</h6>
                    <p class="text-muted small">سيتم عرض سجلات الورشة والصيانة هنا عند إضافتها</p>
                    <a href="/mobile/vehicles/${vehicleId}/workshop/create" target="_blank" class="btn btn-primary">
                        <i class="fas fa-plus ms-1"></i>
                        إضافة أول سجل ورشة
                    </a>
                </div>
            `;
        }
        
        cardBody.innerHTML = content;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load reports content
 */
function loadReportsContent(targetSection) {
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>التقارير</h5>
                <p class="text-muted">سيتم تحميل محتوى التقارير هنا</p>
                <div class="d-flex gap-2 justify-content-center flex-wrap">
                    <a href="${window.vehicleData.urls.generateReport}" class="btn btn-secondary" target="_blank">
                        <i class="fas fa-file-excel ms-1"></i>
                        تقرير Excel
                    </a>
                    <a href="${window.vehicleData.urls.viewDocuments}" class="btn btn-secondary">
                        <i class="fas fa-file-pdf ms-1"></i>
                        تقرير PDF
                    </a>
                </div>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load external authorizations content
 */
function loadExternalAuthorizationsContent(targetSection) {
    const stats = window.vehicleData.external_authorizations;
    
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>التفويضات الخارجية</h5>
                <div class="row mb-3">
                    <div class="col-4 text-center">
                        <div class="fw-bold text-warning h5">${stats.pending}</div>
                        <small class="text-muted">في الانتظار</small>
                    </div>
                    <div class="col-4 text-center">
                        <div class="fw-bold text-success h5">${stats.approved}</div>
                        <small class="text-muted">مُوافق عليه</small>
                    </div>
                    <div class="col-4 text-center">
                        <div class="fw-bold text-danger h5">${stats.rejected}</div>
                        <small class="text-muted">مرفوض</small>
                    </div>
                </div>
                <p class="text-muted">إجمالي التفويضات: ${stats.total}</p>
                <a href="${window.vehicleData.urls.createExternalAuth}" class="btn btn-primary">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة تفويض جديد
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load accidents content
 */
function loadAccidentsContent(targetSection) {
    const stats = window.vehicleData.accidents;
    
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        
        cardBody.innerHTML = `
            <div class="text-center py-4">
                <h5>الحوادث المرورية</h5>
                <div class="row mb-3">
                    <div class="col-6 text-center">
                        <div class="fw-bold text-warning h5">${stats.processing}</div>
                        <small class="text-muted">قيد المعالجة</small>
                    </div>
                    <div class="col-6 text-center">
                        <div class="fw-bold text-success h5">${stats.closed}</div>
                        <small class="text-muted">مغلق</small>
                    </div>
                </div>
                <p class="text-muted">إجمالي الحوادث: ${stats.total}</p>
                <a href="${window.vehicleData.urls.createAccident}" class="btn btn-danger">
                    <i class="fas fa-plus ms-1"></i>
                    إضافة حادث جديد
                </a>
            </div>
        `;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load driver stats content
 */
function loadDriverStatsContent(targetSection) {
    const currentDriver = window.vehicleData.current_driver;
    
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        let content = `<div class="text-center py-4"><h5>إحصائيات السائق الحالي</h5>`;
        
        if (currentDriver) {
            content += `
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h6 class="card-title">${currentDriver.name}</h6>
                        <p class="card-text">
                            <i class="fas fa-calendar ms-1"></i>
                            تسليم السيارة: ${currentDriver.formatted_date}
                        </p>
                        ${currentDriver.mobile ? `
                        <p class="card-text">
                            <i class="fas fa-phone ms-1"></i>
                            ${currentDriver.mobile}
                        </p>
                        ` : ''}
                        <div class="btn-group">
                            <a href="/mobile/vehicles/handover/${currentDriver.handover_id}" class="btn btn-outline-primary btn-sm">
                                <i class="fas fa-eye ms-1"></i>
                                عرض التفاصيل
                            </a>
                            <a href="/mobile/vehicles/handover/edit/${currentDriver.handover_id}" class="btn btn-outline-success btn-sm">
                                <i class="fas fa-edit ms-1"></i>
                                تعديل
                            </a>
                        </div>
                    </div>
                </div>
            `;
        } else {
            content += `
                <p class="text-muted">لا توجد معلومات سائق حالي</p>
                <a href="javascript:window.open('/mobile/vehicles/${window.vehicleData.vehicle_id}/handover/create', '_blank')" class="btn btn-primary">
                    <i class="fas fa-user-plus ms-1"></i>
                    تسليم لسائق
                </a>
            `;
        }
        
        content += '</div>';
        cardBody.innerHTML = content;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Load attachments content
 */
function loadAttachmentsContent(targetSection) {
    const attachmentsCount = window.vehicleData.attachments_count;
    const workshopRecordsCount = window.vehicleData.workshop_records.length;
    const driveLink = window.vehicleData.drive_folder_link;
    const licenseImage = window.vehicleData.license_image;
    const vehicleId = window.vehicleData.vehicle_id;
    
    setTimeout(() => {
        const cardBody = targetSection.querySelector('.card-body');
        
        let content = `
            <div class="text-center py-4">
                <h5>الملفات والمرفقات</h5>
                <div class="row mb-3">
                    <div class="col-6 text-center">
                        <div class="fw-bold text-info h5">${attachmentsCount}</div>
                        <small class="text-muted">الملفات المرفقة</small>
                    </div>
                    <div class="col-6 text-center">
                        <div class="fw-bold text-success h5">${workshopRecordsCount}</div>
                        <small class="text-muted">سجلات الورشة</small>
                    </div>
                </div>
                <div class="d-flex gap-2 justify-content-center flex-wrap">
        `;
        
        if (driveLink) {
            content += `
                    <a href="${driveLink}" target="_blank" class="btn btn-success btn-sm">
                        <i class="fab fa-google-drive ms-1"></i>
                        مجلد Google Drive
                    </a>
            `;
        }
        
        if (licenseImage) {
            content += `
                    <a href="/static/uploads/vehicles/${licenseImage}" target="_blank" class="btn btn-info btn-sm">
                        <i class="fas fa-image ms-1"></i>
                        صورة الرخصة
                    </a>
            `;
        }
        
        content += `
                    <a href="javascript:window.open('/mobile/vehicles/${vehicleId}/workshop/create', '_blank')" class="btn btn-primary btn-sm">
                        <i class="fas fa-upload ms-1"></i>
                        رفع ملف جديد
                    </a>
                </div>
            </div>
        `;
        
        cardBody.innerHTML = content;
        targetSection.setAttribute('data-loaded', 'true');
    }, 500);
}

/**
 * Show license modal
 */
function showLicenseModal() {
    const modal = new bootstrap.Modal(document.getElementById('licenseModal'));
    modal.show();
}

/**
 * Share workshop record
 * @param {number} recordId - Workshop record ID
 */
function shareWorkshopRecord(recordId) {
    // Implementation for sharing workshop record
    console.log('Sharing workshop record:', recordId);
}

/**
 * Helper function to get reason badge
 * @param {string} reason - Repair reason
 * @returns {string} HTML badge
 */
function getReasonBadge(reason) {
    const badges = {
        'maintenance': '<span class="badge bg-info">صيانة دورية</span>',
        'repair': '<span class="badge bg-warning">إصلاح</span>',
        'accident': '<span class="badge bg-danger">حادث</span>'
    };
    return badges[reason] || `<span class="badge bg-secondary">${reason}</span>`;
}

/**
 * Helper function to get status badge
 * @param {string} status - Repair status
 * @returns {string} HTML badge
 */
function getStatusBadge(status) {
    const badges = {
        'completed': '<span class="badge bg-success">مكتمل</span>',
        'in_progress': '<span class="badge bg-warning">قيد التنفيذ</span>',
        'pending': '<span class="badge bg-secondary">في الانتظار</span>'
    };
    return badges[status] || `<span class="badge bg-primary">${status}</span>`;
}
