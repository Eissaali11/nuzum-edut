#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AUTO-RUN Reorganization Script - No prompts"""
import os
import shutil
from pathlib import Path

TEMPLATES_BASE = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles')

FILE_MAPPING = {
    'modals': [
        'confirm_delete.html', 'confirm_delete_handovers.html',
        'confirm_delete_inspection.html', 'confirm_delete_safety_check.html',
        'confirm_delete_single_handover.html', 'confirm_delete_workshop.html',
        'confirm_delete_workshop_image.html', 'inspection_confirm_delete.html',
        'safety_check_confirm_delete.html'
    ],
    'handovers': [
        'handover_create.html', 'handover_create_refactored.html',
        'handover_form_view.html', 'handover_pdf_public.html',
        'handover_report.html', 'handover_report1.html',
        'handover_simple_view.html', 'handover_view.html',
        'handover_view_public.html', 'handovers_list.html',
        'edit_handover.html', 'update_handover_link.html'
    ],
    'forms': [
        'create.html', 'edit.html', 'create_accident.html', 'edit_accident.html',
        'create_external_authorization.html', 'edit_external_authorization.html',
        'edit_documents.html', 'inspection_create.html', 'inspection_edit.html',
        'project_create.html', 'project_edit.html', 'rental_create.html',
        'rental_edit.html', 'safety_check_create.html', 'safety_check_edit.html',
        'workshop_create.html', 'workshop_edit.html'
    ],
    'views': [
        'view.html', 'index.html', '1view.html', '3view.html', '4view.html',
        'view_cards.html', 'view_clean.html', 'view_documents.html',
        'view_external_authorization.html', 'view_modern.html', 'view_simple.html',
        'view_with_sidebar.html', 'accident_details.html', 'workshop_details.html',
        'workshop_image_view.html'
    ],
    'reports': [
        'dashboard.html', 'dashboard_stats.html', 'reports.html',
        'detailed_list.html', 'print_workshop.html', 'share_workshop.html'
    ],
    'utilities': [
        'delete_accident.html', 'drive_files.html', 'drive_management.html',
        'expired_documents.html', 'valid_documents.html', 'import_vehicles.html',
        'inspections.html', 'license_image.html', 'safety_checks.html'
    ],
}

print("="*80)
print("STARTING AUTO-REORGANIZATION")
print("="*80)

total_moved = 0
for subdirectory, files in FILE_MAPPING.items():
    print(f"\n[{subdirectory}] Moving {len(files)} files...")
    moved = 0
    for filename in files:
        source_path = TEMPLATES_BASE / filename
        dest_path = TEMPLATES_BASE / subdirectory / filename
        
        if not source_path.exists():
            print(f"  SKIP: {filename} (not found)")
            continue
        
        if dest_path.exists():
            print(f"  SKIP: {filename} (already at destination)")
            continue
        
        try:
            shutil.move(str(source_path), str(dest_path))
            print(f"  OK: {filename}")
            moved += 1
            total_moved += 1
        except Exception as e:
            print(f"  ERROR: {filename} - {e}")
    
    print(f"  [{subdirectory}] Moved {moved}/{len(files)} files")

print(f"\n{'='*80}")
print(f"TOTAL: Moved {total_moved} files")
print(f"{'='*80}")

# Verify
print("\nVERIFYING...")
for subdir in FILE_MAPPING.keys():
    dir_path = TEMPLATES_BASE / subdir
    count = len(list(dir_path.glob('*.html')))
    print(f"  {subdir}: {count} files")

root_count = len(list(TEMPLATES_BASE.glob('*.html')))
print(f"  ROOT: {root_count} files (should be 0)")
print("\nDONE!")
