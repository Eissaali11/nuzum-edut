#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MASTER REORGANIZATION SCRIPT
Complete automation of vehicle templates reorganization
Executes all steps: create directories, move files, update paths
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
TEMPLATES_BASE = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles')
BACKUP_DIR = Path(r'd:\nuzm\template_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

# File categorization
FILE_MAPPING = {
    'modals': [
        'confirm_delete.html',
        'confirm_delete_handovers.html',
        'confirm_delete_inspection.html',
        'confirm_delete_safety_check.html',
        'confirm_delete_single_handover.html',
        'confirm_delete_workshop.html',
        'confirm_delete_workshop_image.html',
    ],
    'handovers': [
        'handover_create.html',
        'handover_create_refactored.html',
        'handover_form_view.html',
        'handover_pdf_public.html',
        'handover_report.html',
        'handover_report1.html',
        'handover_simple_view.html',
        'handover_view.html',
        'handover_view_public.html',
        'handovers_list.html',
        'edit_handover.html',
        'update_handover_link.html',
    ],
    'forms': [
        'create.html',
        'edit.html',
        'create_accident.html',
        'edit_accident.html',
        'create_external_authorization.html',
        'edit_external_authorization.html',
        'edit_documents.html',
        'inspection_create.html',
        'inspection_edit.html',
        'project_create.html',
        'project_edit.html',
        'rental_create.html',
        'rental_edit.html',
        'safety_check_create.html',
        'safety_check_edit.html',
        'workshop_create.html',
        'workshop_edit.html',
    ],
    'views': [
        'view.html',
        'index.html',
        '1view.html',
        '3view.html',
        '4view.html',
        'view_cards.html',
        'view_clean.html',
        'view_documents.html',
        'view_external_authorization.html',
        'view_modern.html',
        'view_simple.html',
        'view_with_sidebar.html',
        'accident_details.html',
        'workshop_details.html',
        'workshop_image_view.html',
    ],
    'reports': [
        'dashboard.html',
        'dashboard_stats.html',
        'reports.html',
        'detailed_list.html',
        'print_workshop.html',
        'share_workshop.html',
    ],
    'utilities': [
        'delete_accident.html',
        'drive_files.html',
        'drive_management.html',
        'expired_documents.html',
        'valid_documents.html',
        'import_vehicles.html',
        'inspections.html',
        'license_image.html',
        'safety_checks.html',
    ],
}


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(step_num, text):
    """Print formatted step"""
    print(f"\n{'▶' * 3} STEP {step_num}: {text}")
    print("-" * 80)


def create_backup():
    """Create a full backup of the templates directory"""
    print_step(1, "CREATING BACKUP")
    
    if BACKUP_DIR.exists():
        print(f"⚠️  Backup directory already exists: {BACKUP_DIR}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Backup skipped.")
            return False
        shutil.rmtree(BACKUP_DIR)
    
    print(f"📦 Backing up to: {BACKUP_DIR}")
    try:
        shutil.copytree(TEMPLATES_BASE, BACKUP_DIR)
        print(f"✅ Backup created successfully!")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def create_directories():
    """Create all subdirectories"""
    print_step(2, "CREATING SUBDIRECTORIES")
    
    directories = list(FILE_MAPPING.keys())
    created = 0
    
    for directory in directories:
        dir_path = TEMPLATES_BASE / directory
        if dir_path.exists():
            print(f"  ℹ️  Already exists: {directory}/")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ Created: {directory}/")
                created += 1
            except Exception as e:
                print(f"  ❌ Failed to create {directory}/: {e}")
                return False
    
    print(f"\n✅ Created {created} new directories")
    return True


def move_files():
    """Move files to their designated subdirectories"""
    print_step(3, "MOVING FILES")
    
    total_moved = 0
    total_files = sum(len(files) for files in FILE_MAPPING.values())
    
    for subdirectory, files in FILE_MAPPING.items():
        print(f"\n  📂 {subdirectory}/ ({len(files)} files)")
        moved = 0
        
        for filename in files:
            source_path = TEMPLATES_BASE / filename
            dest_path = TEMPLATES_BASE / subdirectory / filename
            
            if not source_path.exists():
                print(f"    ⚠️  Not found: {filename}")
                continue
            
            if dest_path.exists():
                print(f"    ⚠️  Already exists at destination: {filename}")
                continue
            
            try:
                shutil.move(str(source_path), str(dest_path))
                print(f"    ✓ {filename}")
                moved += 1
                total_moved += 1
            except Exception as e:
                print(f"    ❌ Failed to move {filename}: {e}")
    
    print(f"\n✅ Moved {total_moved}/{total_files} files")
    return total_moved == total_files


def verify_structure():
    """Verify the reorganized structure"""
    print_step(4, "VERIFYING STRUCTURE")
    
    # Count files in root (should be 0 HTML files)
    root_html_files = list(TEMPLATES_BASE.glob('*.html'))
    root_count = len(root_html_files)
    
    print(f"\n  HTML files in root: {root_count}")
    if root_count > 0:
        print("  ⚠️  Remaining files:")
        for file in root_html_files:
            print(f"    • {file.name}")
    
    # Count files in each subdirectory
    print(f"\n  Subdirectory file counts:")
    all_good = True
    
    for subdirectory, expected_files in FILE_MAPPING.items():
        dir_path = TEMPLATES_BASE / subdirectory
        if not dir_path.exists():
            print(f"    ❌ {subdirectory}/: Directory not found!")
            all_good = False
            continue
        
        actual_files = list(dir_path.glob('*.html'))
        expected_count = len(expected_files)
        actual_count = len(actual_files)
        
        status = "✅" if actual_count == expected_count else "⚠️"
        print(f"    {status} {subdirectory}/: {actual_count}/{expected_count} files")
        
        if actual_count != expected_count:
            all_good = False
    
    if root_count == 0 and all_good:
        print("\n✅ Structure verification PASSED")
        return True
    else:
        print("\n⚠️  Structure verification has warnings")
        return False


def list_remaining_files():
    """List any HTML files remaining in root"""
    remaining = list(TEMPLATES_BASE.glob('*.html'))
    
    if remaining:
        print(f"\n⚠️  {len(remaining)} HTML files remain in root:")
        for file in remaining:
            print(f"  • {file.name}")
    else:
        print("\n✅ No HTML files remain in root directory!")
    
    return len(remaining)


def generate_summary():
    """Generate reorganization summary"""
    print_header("📊 REORGANIZATION SUMMARY")
    
    total_files = 0
    print("\n  Directory breakdown:")
    
    for subdirectory, expected_files in FILE_MAPPING.items():
        dir_path = TEMPLATES_BASE / subdirectory
        if dir_path.exists():
            actual_files = list(dir_path.glob('*.html'))
            count = len(actual_files)
            total_files += count
            print(f"    • {subdirectory:.<30} {count:>3} files")
        else:
            print(f"    • {subdirectory:.<30} NOT FOUND")
    
    print(f"\n  {'Total files organized':.<30} {total_files:>3}")
    
    # Check for files in root
    root_count = len(list(TEMPLATES_BASE.glob('*.html')))
    if root_count > 0:
        print(f"  {'Files remaining in root':.<30} {root_count:>3} ⚠️")
    else:
        print(f"  {'Files remaining in root':.<30} {root_count:>3} ✅")
    
    print(f"\n  Backup location: {BACKUP_DIR}")
    print("\n" + "=" * 80)


def main():
    """Main execution"""
    print_header("🚀 VEHICLE TEMPLATES MASTER REORGANIZATION SCRIPT")
    
    print(f"""
  This script will:
    1. Create a full backup of current templates
    2. Create 6 subdirectories (modals, handovers, forms, views, reports, utilities)
    3. Move 68 HTML files to appropriate subdirectories
    4. Verify the new structure
  
  Base directory: {TEMPLATES_BASE}
  Backup location: {BACKUP_DIR}
  
  ⚠️  This will modify your file system!
    """)
    
    response = input("  Proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n  ❌ Operation cancelled.")
        return
    
    # Execute steps
    success = True
    
    # Step 1: Backup
    if not create_backup():
        print("\n❌ Backup failed. Aborting.")
        return
    
    # Step 2: Create directories
    if not create_directories():
        print("\n❌ Failed to create directories. Aborting.")
        return
    
    # Step 3: Move files
    if not move_files():
        print("\n⚠️  Not all files were moved successfully.")
        success = False
    
    # Step 4: Verify
    verify_structure()
    list_remaining_files()
    
    # Summary
    generate_summary()
    
    if success:
        print("\n✅ FILE REORGANIZATION COMPLETED SUCCESSFULLY!")
        print("\n⚠️  NEXT STEPS:")
        print("  1. Run: python update_backend_routes.py")
        print("  2. Run: python update_template_includes.py")
        print("  3. Test your application thoroughly")
        print("  4. If successful, you can delete the backup")
    else:
        print("\n⚠️  REORGANIZATION COMPLETED WITH WARNINGS")
        print(f"\n  Check the backup at: {BACKUP_DIR}")
        print("  You can restore from backup if needed")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
