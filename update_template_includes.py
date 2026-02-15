#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automatic Template Include Paths Updater for Vehicle Templates Reorganization
This script updates all {% include %} and {% extends %} paths in HTML templates
"""

import os
import re
from pathlib import Path

# Base directory for templates
TEMPLATES_DIR = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles')

# Path update patterns
PATH_UPDATES = [
    # Partials - update paths to use partials/ subdirectory
    (
        r"{%\s*include\s+['\"]vehicles/_",
        r"{% include 'vehicles/partials/_",
        "Partials references"
    ),
    
    # Handover templates
    (
        r"{%\s*include\s+['\"]vehicles/handover_",
        r"{% include 'vehicles/handovers/handover_",
        "Handover includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/edit_handover",
        r"{% include 'vehicles/handovers/edit_handover",
        "Edit handover includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/update_handover",
        r"{% include 'vehicles/handovers/update_handover",
        "Update handover includes"
    ),
    
    # Modal templates
    (
        r"{%\s*include\s+['\"]vehicles/confirm_delete",
        r"{% include 'vehicles/modals/confirm_delete",
        "Confirm delete modal includes"
    ),
    
    # View templates
    (
        r"{%\s*include\s+['\"]vehicles/view_",
        r"{% include 'vehicles/views/view_",
        "View includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/accident_details",
        r"{% include 'vehicles/views/accident_details",
        "Accident details includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/workshop_details",
        r"{% include 'vehicles/views/workshop_details",
        "Workshop details includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/workshop_image_view",
        r"{% include 'vehicles/views/workshop_image_view",
        "Workshop image view includes"
    ),
    
    # Report templates
    (
        r"{%\s*include\s+['\"]vehicles/dashboard",
        r"{% include 'vehicles/reports/dashboard",
        "Dashboard includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/reports\.html",
        r"{% include 'vehicles/reports/reports.html",
        "Reports page includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/detailed_list",
        r"{% include 'vehicles/reports/detailed_list",
        "Detailed list includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/print_workshop",
        r"{% include 'vehicles/reports/print_workshop",
        "Print workshop includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/share_workshop",
        r"{% include 'vehicles/reports/share_workshop",
        "Share workshop includes"
    ),
    
    # Form templates
    (
        r"{%\s*include\s+['\"]vehicles/create\.html",
        r"{% include 'vehicles/forms/create.html",
        "Create form includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/edit\.html",
        r"{% include 'vehicles/forms/edit.html",
        "Edit form includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/create_",
        r"{% include 'vehicles/forms/create_",
        "Create forms includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/edit_",
        r"{% include 'vehicles/forms/edit_",
        "Edit forms includes (excluding handover)"
    ),
    
    # Utility templates
    (
        r"{%\s*include\s+['\"]vehicles/inspections",
        r"{% include 'vehicles/utilities/inspections",
        "Inspections includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/safety_checks",
        r"{% include 'vehicles/utilities/safety_checks",
        "Safety checks includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/drive_",
        r"{% include 'vehicles/utilities/drive_",
        "Drive management includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/license_image",
        r"{% include 'vehicles/utilities/license_image",
        "License image includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/expired_documents",
        r"{% include 'vehicles/utilities/expired_documents",
        "Expired documents includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/valid_documents",
        r"{% include 'vehicles/utilities/valid_documents",
        "Valid documents includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/import_vehicles",
        r"{% include 'vehicles/utilities/import_vehicles",
        "Import vehicles includes"
    ),
    (
        r"{%\s*include\s+['\"]vehicles/delete_accident",
        r"{% include 'vehicles/utilities/delete_accident",
        "Delete accident includes"
    ),
]


def find_all_html_files(base_dir):
    """Find all HTML files in the directory and subdirectories"""
    html_files = []
    for root, dirs, files in os.walk(base_dir):
        # Skip backup directory
        if 'backup' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                html_files.append(Path(root) / file)
    return html_files


def update_template_includes(file_path, dry_run=False):
    """
    Update {% include %} and {% extends %} paths in an HTML template
    
    Args:
        file_path: Path to the HTML file
        dry_run: If True, only show what would be changed
    
    Returns:
        Number of replacements made
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️  Error reading file: {e}")
        return 0
    
    original_content = content
    total_replacements = 0
    replacements_detail = []
    
    # Apply each path update pattern
    for pattern, replacement, description in PATH_UPDATES:
        matches = re.findall(pattern, content)
        if matches:
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                total_replacements += count
                replacements_detail.append(f"    • {description}: {count}x")
    
    # Show details if replacements were made
    if replacements_detail:
        print(f"  ✓ {file_path.name} ({total_replacements} replacements)")
        for detail in replacements_detail:
            print(detail)
    
    # Write updated content if changes were made
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"    💾 Saved")
            except Exception as e:
                print(f"    ⚠️  Error saving file: {e}")
                return 0
        else:
            print(f"    [DRY RUN] Would save changes")
    
    return total_replacements


def main():
    """Main execution function"""
    print("=" * 80)
    print("🔧 Vehicle Templates Include Paths Updater")
    print("=" * 80)
    print(f"Templates directory: {TEMPLATES_DIR}")
    print(f"Path update patterns: {len(PATH_UPDATES)}")
    print("=" * 80)
    
    # Check if directory exists
    if not TEMPLATES_DIR.exists():
        print(f"\n❌ Error: Templates directory not found: {TEMPLATES_DIR}")
        return
    
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
    
    print("\n🔍 Scanning for HTML files...")
    html_files = find_all_html_files(TEMPLATES_DIR)
    print(f"Found {len(html_files)} HTML files\n")
    
    if not html_files:
        print("❌ No HTML files found!")
        return
    
    print("-" * 80)
    
    total_replacements = 0
    files_updated = 0
    
    for html_file in html_files:
        count = update_template_includes(html_file, dry_run=dry_run)
        
        if count > 0:
            total_replacements += count
            files_updated += 1
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Files scanned: {len(html_files)}")
    print(f"Files updated: {files_updated}")
    print(f"Total replacements: {total_replacements}")
    
    if dry_run:
        print("\n✅ Dry run completed. Run again with live mode to apply changes.")
    else:
        print("\n✅ All template files updated successfully!")
        print("\n⚠️  Next steps:")
        print("   1. Test the application thoroughly")
        print("   2. Check for any broken template includes")
        print("   3. Verify all pages render correctly")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
