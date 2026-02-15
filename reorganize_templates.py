#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reorganize vehicles templates into logical subdirectories
"""
import os
import shutil

BASE_PATH = r'd:\nuzm\modules\vehicles\presentation\templates\vehicles'

# Define directory structure and file mappings
DIRECTORIES = {
    'modals': [
        'confirm_delete.html',
        'confirm_delete_handovers.html',
        'confirm_delete_inspection.html',
        'confirm_delete_safety_check.html',
        'confirm_delete_single_handover.html',
        'confirm_delete_workshop.html',
        'confirm_delete_workshop_image.html'
    ],
    'handovers': [
        'handovers_list.html',
        'handover_create.html',
        'handover_create_refactored.html',
        'handover_form_view.html',
        'handover_pdf_public.html',
        'handover_report.html',
        'handover_report1.html',
        'handover_simple_view.html',
        'handover_view.html',
        'handover_view_public.html',
        'edit_handover.html',
        'update_handover_link.html'
    ],
    'inspections': [
        'inspections.html',
        'inspection_confirm_delete.html',
        'inspection_create.html',
        'inspection_edit.html'
    ],
    'forms': [
        'create_accident.html',
        'create_external_authorization.html',
        'edit_accident.html',
        'edit_documents.html',
        'edit_external_authorization.html',
        'project_create.html',
        'project_edit.html',
        'rental_create.html',
       'rental_edit.html',
        'safety_check_create.html',
        'safety_check_edit.html',
        'safety_check_confirm_delete.html',
        'workshop_create.html',
        'workshop_edit.html'
    ],
    'views': [
        '1view.html',
        '3view.html',
        '4view.html',
        'view_cards.html',
        'view_clean.html',
        'view_documents.html',
        'view_external_authorization.html',
        'view_modern.html',
        'view_simple.html',
        'view_with_sidebar.html'
    ],
    'accidents': [
        'accident_details.html',
        'delete_accident.html'
    ],
    'workshops': [
        'workshop_details.html',
        'workshop_image_view.html',
        'print_workshop.html',
        'share_workshop.html'
    ],
    'utilities': [
        'dashboard_stats.html',
        'detailed_list.html',
        'drive_files.html',
        'drive_management.html',
        'expired_documents.html',
        'import_vehicles.html',
        'license_image.html',
        'reports.html',
        'safety_checks.html',
        'valid_documents.html'
    ]
}

def main():
    print("=" * 60)
    print("TEMPLATE REORGANIZATION SCRIPT")
    print("=" * 60)
    print(f"Base path: {BASE_PATH}\n")
    
    # Create directories and move files
    total_moved = 0
    total_not_found = 0
    
    for folder, files in DIRECTORIES.items():
        folder_path = os.path.join(BASE_PATH, folder)
        
        # Create directory
        os.makedirs(folder_path, exist_ok=True)
        print(f"\n✓ Created/verified folder: {folder}/")
        print("-" * 60)
        
        # Move files
        for file in files:
            src = os.path.join(BASE_PATH, file)
            dst = os.path.join(folder_path, file)
            
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                    print(f"  ✓ Moved: {file}")
                    total_moved += 1
                except Exception as e:
                    print(f"  ✗ Error moving {file}: {e}")
            else:
                print(f"  ✗ Not found: {file}")
                total_not_found += 1
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Files moved: {total_moved}")
    print(f"✗ Files not found: {total_not_found}")
    print(f"✓ Directories created: {len(DIRECTORIES)}")
    print("\n✅ Reorganization complete!")
    
    # List remaining files in root
    print("\n" + "=" * 60)
    print("REMAINING FILES IN ROOT:")
    print("=" * 60)
    remaining = [f for f in os.listdir(BASE_PATH) 
                 if os.path.isfile(os.path.join(BASE_PATH, f)) and f.endswith('.html')]
    for f in sorted(remaining):
        print(f"  - {f}")
    print(f"\nTotal remaining: {len(remaining)}")

if __name__ == '__main__':
    main()
