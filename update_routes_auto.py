#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AUTO-UPDATE Backend Routes - No prompts"""
import os
import re
from pathlib import Path

BASE_DIR = Path(r'd:\nuzm\modules\vehicles\presentation\web')

TEMPLATE_PATH_MAPPINGS = {
    'vehicles/confirm_delete.html': 'vehicles/modals/confirm_delete.html',
    'vehicles/confirm_delete_handovers.html': 'vehicles/modals/confirm_delete_handovers.html',
    'vehicles/confirm_delete_inspection.html': 'vehicles/modals/confirm_delete_inspection.html',
    'vehicles/confirm_delete_safety_check.html': 'vehicles/modals/confirm_delete_safety_check.html',
    'vehicles/confirm_delete_single_handover.html': 'vehicles/modals/confirm_delete_single_handover.html',
    'vehicles/confirm_delete_workshop.html': 'vehicles/modals/confirm_delete_workshop.html',
    'vehicles/confirm_delete_workshop_image.html': 'vehicles/modals/confirm_delete_workshop_image.html',
    'vehicles/inspection_confirm_delete.html': 'vehicles/modals/inspection_confirm_delete.html',
    'vehicles/safety_check_confirm_delete.html': 'vehicles/modals/safety_check_confirm_delete.html',
    
    'vehicles/handover_create.html': 'vehicles/handovers/handover_create.html',
    'vehicles/handover_form_view.html': 'vehicles/handovers/handover_form_view.html',
    'vehicles/handover_pdf_public.html': 'vehicles/handovers/handover_pdf_public.html',
    'vehicles/handover_view.html': 'vehicles/handovers/handover_view.html',
    'vehicles/handovers_list.html': 'vehicles/handovers/handovers_list.html',
    'vehicles/update_handover_link.html': 'vehicles/handovers/update_handover_link.html',
    'vehicles/edit_handover.html': 'vehicles/handovers/edit_handover.html',
    
    'vehicles/create.html': 'vehicles/forms/create.html',
    'vehicles/edit.html': 'vehicles/forms/edit.html',
    'vehicles/create_accident.html': 'vehicles/forms/create_accident.html',
    'vehicles/edit_accident.html': 'vehicles/forms/edit_accident.html',
    'vehicles/create_external_authorization.html': 'vehicles/forms/create_external_authorization.html',
    'vehicles/edit_external_authorization.html': 'vehicles/forms/edit_external_authorization.html',
    'vehicles/edit_documents.html': 'vehicles/forms/edit_documents.html',
    'vehicles/inspection_create.html': 'vehicles/forms/inspection_create.html',
    'vehicles/inspection_edit.html': 'vehicles/forms/inspection_edit.html',
    'vehicles/project_create.html': 'vehicles/forms/project_create.html',
    'vehicles/project_edit.html': 'vehicles/forms/project_edit.html',
    'vehicles/rental_create.html': 'vehicles/forms/rental_create.html',
    'vehicles/rental_edit.html': 'vehicles/forms/rental_edit.html',
    'vehicles/safety_check_create.html': 'vehicles/forms/safety_check_create.html',
    'vehicles/safety_check_edit.html': 'vehicles/forms/safety_check_edit.html',
    'vehicles/workshop_create.html': 'vehicles/forms/workshop_create.html',
    'vehicles/workshop_edit.html': 'vehicles/forms/workshop_edit.html',
    
    'vehicles/index.html': 'vehicles/views/index.html',
    'vehicles/view.html': 'vehicles/views/view.html',
    'vehicles/view_documents.html': 'vehicles/views/view_documents.html',
    'vehicles/view_external_authorization.html': 'vehicles/views/view_external_authorization.html',
    'vehicles/accident_details.html': 'vehicles/views/accident_details.html',
    'vehicles/workshop_details.html': 'vehicles/views/workshop_details.html',
    'vehicles/workshop_image_view.html': 'vehicles/views/workshop_image_view.html',
    
    'vehicles/dashboard.html': 'vehicles/reports/dashboard.html',
    'vehicles/reports.html': 'vehicles/reports/reports.html',
    'vehicles/detailed_list.html': 'vehicles/reports/detailed_list.html',
    'vehicles/print_workshop.html': 'vehicles/reports/print_workshop.html',
    'vehicles/share_workshop.html': 'vehicles/reports/share_workshop.html',
    
    'vehicles/delete_accident.html': 'vehicles/utilities/delete_accident.html',
    'vehicles/drive_files.html': 'vehicles/utilities/drive_files.html',
    'vehicles/drive_management.html': 'vehicles/utilities/drive_management.html',
    'vehicles/expired_documents.html': 'vehicles/utilities/expired_documents.html',
    'vehicles/valid_documents.html': 'vehicles/utilities/valid_documents.html',
    'vehicles/import_vehicles.html': 'vehicles/utilities/import_vehicles.html',
    'vehicles/inspections.html': 'vehicles/utilities/inspections.html',
    'vehicles/license_image.html': 'vehicles/utilities/license_image.html',
    'vehicles/safety_checks.html': 'vehicles/utilities/safety_checks.html',
}

ROUTE_FILES = [
    'vehicle_routes.py',
    'handover_routes.py',
    'accident_routes.py',
    'workshop_routes.py',
    'vehicle_extra_routes.py',
]

def update_file(file_path):
    if not file_path.exists():
        print(f"SKIP: {file_path.name} (not found)")
        return 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    replacements = 0
    
    for old_path, new_path in TEMPLATE_PATH_MAPPINGS.items():
        # Both single and double quotes
        for quote in ['"', "'"]:
            old_str = f'render_template({quote}{old_path}{quote}'
            new_str = f'render_template({quote}{new_path}{quote}'
            if old_str in content:
                count = content.count(old_str)
                content = content.replace(old_str, new_str)
                replacements += count
                print(f"  {file_path.name}: {old_path} -> {new_path} ({count}x)")
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  SAVED: {file_path.name}")
    
    return replacements

print("="*80)
print("UPDATING BACKEND ROUTES")
print("="*80)

total = 0
for route_file in ROUTE_FILES:
    file_path = BASE_DIR / route_file
    print(f"\n[{route_file}]")
    count = update_file(file_path)
    total += count

print(f"\n{'='*80}")
print(f"TOTAL REPLACEMENTS: {total}")
print(f"{'='*80}")
print("DONE!")
