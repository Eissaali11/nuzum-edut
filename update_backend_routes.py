#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automatic Backend Routes Updater for Vehicle Templates Reorganization
This script updates all render_template() calls to reflect the new subdirectory structure
"""

import os
import re
from pathlib import Path

# Base directory
BASE_DIR = Path(r'd:\nuzm\modules\vehicles\presentation\web')

# Mapping of old template paths to new paths
TEMPLATE_PATH_MAPPINGS = {
    # Modals
    'vehicles/confirm_delete.html': 'vehicles/modals/confirm_delete.html',
    'vehicles/confirm_delete_handovers.html': 'vehicles/modals/confirm_delete_handovers.html',
    'vehicles/confirm_delete_inspection.html': 'vehicles/modals/confirm_delete_inspection.html',
    'vehicles/confirm_delete_safety_check.html': 'vehicles/modals/confirm_delete_safety_check.html',
    'vehicles/confirm_delete_single_handover.html': 'vehicles/modals/confirm_delete_single_handover.html',
    'vehicles/confirm_delete_workshop.html': 'vehicles/modals/confirm_delete_workshop.html',
    'vehicles/confirm_delete_workshop_image.html': 'vehicles/modals/confirm_delete_workshop_image.html',
    
    # Handovers
    'vehicles/handover_create.html': 'vehicles/handovers/handover_create.html',
    'vehicles/handover_form_view.html': 'vehicles/handovers/handover_form_view.html',
    'vehicles/handover_pdf_public.html': 'vehicles/handovers/handover_pdf_public.html',
    'vehicles/handover_view.html': 'vehicles/handovers/handover_view.html',
    'vehicles/handovers_list.html': 'vehicles/handovers/handovers_list.html',
    'vehicles/update_handover_link.html': 'vehicles/handovers/update_handover_link.html',
    
    # Forms
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
    
    # Views
    'vehicles/index.html': 'vehicles/views/index.html',
    'vehicles/view.html': 'vehicles/views/view.html',
    'vehicles/view_documents.html': 'vehicles/views/view_documents.html',
    'vehicles/view_external_authorization.html': 'vehicles/views/view_external_authorization.html',
    'vehicles/accident_details.html': 'vehicles/views/accident_details.html',
    'vehicles/workshop_details.html': 'vehicles/views/workshop_details.html',
    'vehicles/workshop_image_view.html': 'vehicles/views/workshop_image_view.html',
    
    # Reports
    'vehicles/dashboard.html': 'vehicles/reports/dashboard.html',
    'vehicles/reports.html': 'vehicles/reports/reports.html',
    'vehicles/detailed_list.html': 'vehicles/reports/detailed_list.html',
    'vehicles/print_workshop.html': 'vehicles/reports/print_workshop.html',
    'vehicles/share_workshop.html': 'vehicles/reports/share_workshop.html',
    
    # Utilities
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

# Python files to update
ROUTE_FILES = [
    'vehicle_routes.py',
    'handover_routes.py',
    'accident_routes.py',
    'workshop_routes.py',
    'vehicle_extra_routes.py',
]


def update_render_template_calls(file_path, dry_run=False):
    """
    Update render_template() calls in a Python file
    
    Args:
        file_path: Path to the Python file
        dry_run: If True, only show what would be changed without modifying files
    
    Returns:
        Number of replacements made
    """
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Update each template path
    for old_path, new_path in TEMPLATE_PATH_MAPPINGS.items():
        # Match both single and double quotes
        patterns = [
            (f'render_template("{old_path}"', f'render_template("{new_path}"'),
            (f"render_template('{old_path}'", f"render_template('{new_path}'"),
            (f'render_template\(\s*"{old_path}"', f'render_template("{new_path}"'),
            (f"render_template\(\s*'{old_path}'", f"render_template('{new_path}'"),
        ]
        
        for pattern, replacement in patterns:
            if pattern in content or re.search(pattern, content):
                count = content.count(pattern.replace('\\(', '(').replace('\\s*', ' ').strip())
                if count > 0:
                    content = content.replace(
                        pattern.replace('\\(', '(').replace('\\s*', ' ').strip(),
                        replacement.replace('\\(', '(').strip()
                    )
                    replacements += count
                    print(f"  ✓ Replaced '{old_path}' → '{new_path}' ({count}x)")
    
    # Write updated content if changes were made
    if content != original_content:
        if dry_run:
            print(f"  [DRY RUN] Would update {file_path}")
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  💾 Saved {file_path}")
    
    return replacements


def main():
    """Main execution function"""
    print("=" * 80)
    print("🔧 Vehicle Templates Backend Routes Updater")
    print("=" * 80)
    print(f"Base directory: {BASE_DIR}")
    print(f"Template mappings: {len(TEMPLATE_PATH_MAPPINGS)}")
    print(f"Files to update: {len(ROUTE_FILES)}")
    print("=" * 80)
    
    # Ask for dry run
    dry_run_input = input("\nDry run mode? (Y/n): ").strip().lower()
    dry_run = dry_run_input != 'n'
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")
    else:
        print("\n⚠️  LIVE MODE - Files will be modified!\n")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Aborted.")
            return
    
    print()
    
    total_replacements = 0
    files_updated = 0
    
    for route_file in ROUTE_FILES:
        file_path = BASE_DIR / route_file
        print(f"\n📄 Processing: {route_file}")
        print("-" * 80)
        
        count = update_render_template_calls(file_path, dry_run=dry_run)
        
        if count > 0:
            total_replacements += count
            files_updated += 1
        else:
            print("  ℹ️  No changes needed")
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Files processed: {len(ROUTE_FILES)}")
    print(f"Files updated: {files_updated}")
    print(f"Total replacements: {total_replacements}")
    
    if dry_run:
        print("\n✅ Dry run completed. Run again with live mode to apply changes.")
    else:
        print("\n✅ All route files updated successfully!")
        print("\n⚠️  Next steps:")
        print("   1. Update template {% include %} paths")
        print("   2. Test the application thoroughly")
        print("   3. Check for any broken templates")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
