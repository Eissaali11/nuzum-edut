#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete Vehicle Templates Reorganization Script
- Creates subdirectories
- Moves files to logical locations
- Updates all template paths (includes/extends)
"""
import os
import shutil
import re
from pathlib import Path

BASE_PATH = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles')

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
        'import_vehicles.html',
        'inspections.html',
        'inspection_confirm_delete.html',
        'inspection_create.html',
        'inspection_edit.html',
        'license_image.html',
        'safety_checks.html',
        'safety_check_confirm_delete.html',
        'valid_documents.html',
    ],
}

def create_directories():
    """Create all subdirectories"""
    print("\n" + "="*70)
    print("STEP 1: CREATING DIRECTORIES")
    print("="*70)
    
    for folder in FILE_MAPPING.keys():
        folder_path = BASE_PATH / folder
        folder_path.mkdir(exist_ok=True)
        print(f"✓ Created: {folder}/")
    
    # Partials already exists
    print(f"✓ Using existing: partials/")

def move_files():
    """Move files to their designated subdirectories"""
    print("\n" + "="*70)
    print("STEP 2: MOVING FILES")
    print("="*70)
    
    stats = {'moved': 0, 'not_found': 0, 'errors': 0}
    
    for folder, files in FILE_MAPPING.items():
        print(f"\n→ Processing {folder}/")
        folder_path = BASE_PATH / folder
        
        for filename in files:
            src = BASE_PATH / filename
            dst = folder_path / filename
            
            try:
                if src.exists() and src.is_file():
                    shutil.move(str(src), str(dst))
                    print(f"  ✓ {filename}")
                    stats['moved'] += 1
                else:
                    print(f"  ✗ Not found: {filename}")
                    stats['not_found'] += 1
            except Exception as e:
                print(f"  ✗ Error moving {filename}: {e}")
                stats['errors'] += 1
    
    return stats

def update_template_paths():
    """Update {% include %} and {% extends %} paths in all templates"""
    print("\n" + "="*70)
    print("STEP 3: UPDATING TEMPLATE PATHS")
    print("="*70)
    
    # Path mappings for updates
    path_updates = {
        # Partials - already in partials folder
        r"{% include 'vehicles/_": r"{% include 'vehicles/partials/_",
        r"{% include \"vehicles/_": r"{% include \"vehicles/partials/_",
        
        # New subdirectories
        r"{% include 'vehicles/handover": r"{% include 'vehicles/handovers/handover",
        r"{% include \"vehicles/handover": r"{% include \"vehicles/handovers/handover",
        
        r"{% include 'vehicles/confirm_delete": r"{% include 'vehicles/modals/confirm_delete",
        r"{% include \"vehicles/confirm_delete": r"{% include \"vehicles/modals/confirm_delete",
        
        r"{% include 'vehicles/view": r"{% include 'vehicles/views/view",
        r"{% include \"vehicles/view": r"{% include \"vehicles/views/view",
        
        r"{% include 'vehicles/dashboard": r"{% include 'vehicles/reports/dashboard",
        r"{% include \"vehicles/dashboard": r"{% include \"vehicles/reports/dashboard",
    }
    
    updated_files = []
    
    # Process all HTML files in all subdirectories
    for root, dirs, files in os.walk(BASE_PATH):
        for filename in files:
            if filename.endswith('.html'):
                filepath = Path(root) / filename
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Apply all path updates
                    for old_pattern, new_pattern in path_updates.items():
                        content = re.sub(old_pattern, new_pattern, content)
                    
                    # Write back if changed
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        rel_path = filepath.relative_to(BASE_PATH)
                        updated_files.append(str(rel_path))
                        print(f"  ✓ Updated: {rel_path}")
                
                except Exception as e:
                    print(f"  ✗ Error processing {filename}: {e}")
    
    return updated_files

def list_remaining_files():
    """List files remaining in root directory"""
    print("\n" + "="*70)
    print("REMAINING FILES IN ROOT")
    print("="*70)
    
    root_files = [f for f in os.listdir(BASE_PATH) 
                  if (BASE_PATH / f).is_file() and f.endswith('.html')]
    
    if root_files:
        for f in sorted(root_files):
            print(f"  - {f}")
        print(f"\n⚠️  Total remaining: {len(root_files)}")
    else:
        print("  ✓ No HTML files in root (perfect!)")
    
    return root_files

def generate_summary(stats, updated_files, remaining):
    """Generate final summary"""
    print("\n" + "="*70)
    print("REORGANIZATION SUMMARY")
    print("="*70)
    print(f"✓ Files moved: {stats['moved']}")
    print(f"✗ Files not found: {stats['not_found']}")
    print(f"✗ Errors: {stats['errors']}")
    print(f"✓ Templates with updated paths: {len(updated_files)}")
    print(f"⚠️  Files remaining in root: {len(remaining)}")
    print(f"✓ Directories created: {len(FILE_MAPPING)}")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Update backend routes (render_template calls)")
    print("2. Test all template rendering")
    print("3. Verify all includes/extends work correctly")
    print("\n✅ Template reorganization complete!\n")

def main():
    print("\n" + "="*70)
    print("VEHICLE TEMPLATES COMPREHENSIVE REORGANIZATION")
    print("="*70)
    print(f"Base path: {BASE_PATH}\n")
    
    # Execute reorganization steps
    create_directories()
    stats = move_files()
    updated_files = update_template_paths()
    remaining = list_remaining_files()
    generate_summary(stats, updated_files, remaining)

if __name__ == '__main__':
    main()
