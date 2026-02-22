#!/usr/bin/env python3
# Cleanup script for view.html - removes orphaned code

Clean_template = '''{% extends 'layout.html' %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/modules/vehicles/view.css') }}">
{% endblock %}

{% block title %}تفاصيل السيارة: {{ vehicle.plate_number }}{% endblock %}

{% block content %}
<div class="container-fluid">
    <!-- Header -->
    {% include 'vehicles/partials/_view_header.html' %}

    <!-- Tab Navigation -->
    {% include 'vehicles/partials/_view_tabs.html' %}

    <!-- Tab Content -->
    <div class="tab-content" id="vehicleTabsContent">
        <!-- Accidents Tab -->
        {% include 'vehicles/partials/_tab_accidents.html' %}
        
        <!-- Information Tab -->
        {% include 'vehicles/partials/_tab_information.html' %}

        <!-- Documents Tab -->
        <div class="tab-pane fade" id="documents" role="tabpanel" aria-labelledby="documents-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-file-alt me-2"></i>
                    انتقل إلى صفحة إدارة الوثائق
                </h5>
                <p class="text-muted">يرجى استخدام النموذج المخصص لإدارة وثائق المركبة.</p>
                <a href="{{ url_for('vehicles.view_documents', id=vehicle.id) }}" class="btn btn-primary">
                    <i class="fas fa-folder-open me-2"></i>
                    إدارة الوثائق
                </a>
            </div>
        </div>

        <!-- Inspections Tab -->
        <div class="tab-pane fade" id="inspections" role="tabpanel" aria-labelledby="inspections-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-clipboard-check me-2"></i>
                    الفحوصات الدورية والسلامة
                </h5>
                <p class="text-muted">تم تحويل هذا التبويب إلى صفحة مخصصة لعرض الفحوصات.</p>
                <a href="{{ url_for('vehicles.vehicle_inspections', id=vehicle.id) }}" class="btn btn-info me-2">
                    <i class="fas fa-clipboard me-2"></i>
                    الفحوصات الدورية
                </a>
                <a href="{{ url_for('vehicles.vehicle_safety_checks', id=vehicle.id) }}" class="btn btn-warning">
                    <i class="fas fa-shield-alt me-2"></i>
                    فحوصات السلامة
                </a>
            </div>
        </div>

        <!-- Workshop Tab -->
        <div class="tab-pane fade" id="workshop" role="tabpanel" aria-labelledby="workshop-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-tools me-2"></i>
                    سجلات الورشة
                </h5>
                <p class="text-muted">قائمة سجلات الورشة والصيانة للسيارة.</p>
                <a href="{{ url_for('vehicles.vehicle_workshop_records', id=vehicle.id) }}" class="btn btn-primary">
                    <i class="fas fa-list me-2"></i>
                    عرض سجلات الورشة
                </a>
            </div>
        </div>

        <!-- Drivers Tab -->
        <div class="tab-pane fade" id="drivers" role="tabpanel" aria-labelledby="drivers-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-user-tie me-2"></i>
                    السائقين والتسليم والاستلام
                </h5>
                <p class="text-muted">معلومات السائقين الحاليين والسابقين وسجلات التسليم والاستلام.</p>
                <a href="{{ url_for('vehicles.vehicle_drivers', id=vehicle.id) }}" class="btn btn-primary">
                    <i class="fas fa-drivers me-2"></i>
                    إدارة السائقين
                </a>
            </div>
        </div>

        <!-- Projects Tab -->
        <div class="tab-pane fade" id="projects" role="tabpanel" aria-labelledby="projects-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-building me-2"></i>
                    تخصيصات المشاريع
                </h5>
                <p class="text-muted">المشاريع المخصصة لهذه السيارة.</p>
                <a href="{{ url_for('vehicles.create_project', id=vehicle.id) }}" class="btn btn-success">
                    <i class="fas fa-plus me-2"></i>
                    تخصيص لمشروع جديد
                </a>
            </div>
        </div>

        <!-- Authorizations Tab -->
        <div class="tab-pane fade" id="authorizations" role="tabpanel" aria-labelledby="authorizations-tab">
            <div style="padding: 2rem; background: #f8f9fa; border-radius: 12px; margin: 2rem 0;">
                <h5 class="mb-3">
                    <i class="fas fa-file-signature me-2"></i>
                    التفويضات الخارجية
                </h5>
                <p class="text-muted">التفويضات والصلاحيات الخارجية للسيارة.</p>
                <a href="{{ url_for('vehicles.list_external_authorizations', vehicle_id=vehicle.id) }}" class="btn btn-primary">
                    <i class="fas fa-list me-2"></i>
                    التفويضات
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
{{ super() }}
<script>
document.addEventListener("DOMContentLoaded", function () {
    // حفظ التبويب النشط عند التحديث
    const activeTab = localStorage.getItem("activeVehicleTab");
    if (activeTab) {
        const tabTrigger = new bootstrap.Tab(document.querySelector(activeTab));
        tabTrigger.show();
    }

    // تحديث التبويب النشط عند التغيير
    const tabLinks = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabLinks.forEach((tabLink) => {
        tabLink.addEventListener("shown.bs.tab", (event) => {
            localStorage.setItem(
                "activeVehicleTab",
                event.target.getAttribute("data-bs-target")
            );
        });
    });
});
</script>
{% endblock %}'''

# Write the clean template
with open(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles\view.html', 'w', encoding='utf-8') as f:
    f.write(Clean_template)

print("✅ view.html successfully cleaned and refactored!")
print(f"📊 New file size: {len(Clean_template.splitlines())} lines")
print("✨ Orphaned code removed. File is now modular and maintainable.")
