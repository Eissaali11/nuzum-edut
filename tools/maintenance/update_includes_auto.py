#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AUTO-UPDATE Template Includes - No prompts"""
import os
import re
from pathlib import Path

TEMPLATES_DIR = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles')

# Pattern-based replacements for {% include %} and {% extends %}
PATH_UPDATES = [
    # Partials - already in partials/ but need to ensure correct references
    (r"{%\s*include\s+['\"]vehicles/_", r"{% include 'vehicles/partials/_"),
    
    # Handovers
    (r"{%\s*include\s+['\"]vehicles/handover_", r"{% include 'vehicles/handovers/handover_"),
    (r"{%\s*include\s+['\"]vehicles/handovers_list", r"{% include 'vehicles/handovers/handovers_list"),
    (r"{%\s*include\s+['\"]vehicles/edit_handover", r"{% include 'vehicles/handovers/edit_handover"),
    (r"{%\s*include\s+['\"]vehicles/update_handover", r"{% include 'vehicles/handovers/update_handover"),
    
    # Modals - confirm_delete
    (r"{%\s*include\s+['\"]vehicles/confirm_delete", r"{% include 'vehicles/modals/confirm_delete"),
    (r"{%\s*include\s+['\"]vehicles/inspection_confirm_delete", r"{% include 'vehicles/modals/inspection_confirm_delete"),
    (r"{%\s*include\s+['\"]vehicles/safety_check_confirm_delete", r"{% include 'vehicles/modals/safety_check_confirm_delete"),
    
    # Views
    (r"{%\s*include\s+['\"]vehicles/view_", r"{% include 'vehicles/views/view_"),
    (r"{%\s*include\s+['\"]vehicles/view\.html", r"{% include 'vehicles/views/view.html"),
    (r"{%\s*include\s+['\"]vehicles/index\.html", r"{% include 'vehicles/views/index.html"),
    (r"{%\s*include\s+['\"]vehicles/accident_details", r"{% include 'vehicles/views/accident_details"),
    (r"{%\s*include\s+['\"]vehicles/workshop_details", r"{% include 'vehicles/views/workshop_details"),
    (r"{%\s*include\s+['\"]vehicles/workshop_image_view", r"{% include 'vehicles/views/workshop_image_view"),
    
    # Reports
    (r"{%\s*include\s+['\"]vehicles/dashboard", r"{% include 'vehicles/reports/dashboard"),
    (r"{%\s*include\s+['\"]vehicles/reports\.html", r"{% include 'vehicles/reports/reports.html"),
    (r"{%\s*include\s+['\"]vehicles/detailed_list", r"{% include 'vehicles/reports/detailed_list"),
    (r"{%\s*include\s+['\"]vehicles/print_workshop", r"{% include 'vehicles/reports/print_workshop"),
    (r"{%\s*include\s+['\"]vehicles/share_workshop", r"{% include 'vehicles/reports/share_workshop"),
    
    # Forms - be careful with edit_ (don't catch edit_handover)
    (r"{%\s*include\s+['\"]vehicles/create\.html", r"{% include 'vehicles/forms/create.html"),
    (r"{%\s*include\s+['\"]vehicles/edit\.html", r"{% include 'vehicles/forms/edit.html"),
    (r"{%\s*include\s+['\"]vehicles/create_", r"{% include 'vehicles/forms/create_"),
    (r"{%\s*include\s+['\"]vehicles/edit_accident", r"{% include 'vehicles/forms/edit_accident"),
    (r"{%\s*include\s+['\"]vehicles/edit_documents", r"{% include 'vehicles/forms/edit_documents"),
    (r"{%\s*include\s+['\"]vehicles/edit_external_authorization", r"{% include 'vehicles/forms/edit_external_authorization"),
    (r"{%\s*include\s+['\"]vehicles/inspection_create", r"{% include 'vehicles/forms/inspection_create"),
    (r"{%\s*include\s+['\"]vehicles/inspection_edit", r"{% include 'vehicles/forms/inspection_edit"),
    (r"{%\s*include\s+['\"]vehicles/project_", r"{% include 'vehicles/forms/project_"),
    (r"{%\s*include\s+['\"]vehicles/rental_", r"{% include 'vehicles/forms/rental_"),
    (r"{%\s*include\s+['\"]vehicles/safety_check_create", r"{% include 'vehicles/forms/safety_check_create"),
    (r"{%\s*include\s+['\"]vehicles/safety_check_edit", r"{% include 'vehicles/forms/safety_check_edit"),
    (r"{%\s*include\s+['\"]vehicles/workshop_create", r"{% include 'vehicles/forms/workshop_create"),
    (r"{%\s*include\s+['\"]vehicles/workshop_edit", r"{% include 'vehicles/forms/workshop_edit"),
    
    # Utilities
    (r"{%\s*include\s+['\"]vehicles/inspections", r"{% include 'vehicles/utilities/inspections"),
    (r"{%\s*include\s+['\"]vehicles/safety_checks", r"{% include 'vehicles/utilities/safety_checks"),
    (r"{%\s*include\s+['\"]vehicles/drive_", r"{% include 'vehicles/utilities/drive_"),
    (r"{%\s*include\s+['\"]vehicles/license_image", r"{% include 'vehicles/utilities/license_image"),
    (r"{%\s*include\s+['\"]vehicles/expired_documents", r"{% include 'vehicles/utilities/expired_documents"),
    (r"{%\s*include\s+['\"]vehicles/valid_documents", r"{% include 'vehicles/utilities/valid_documents"),
    (r"{%\s*include\s+['\"]vehicles/import_vehicles", r"{% include 'vehicles/utilities/import_vehicles"),
    (r"{%\s*include\s+['\"]vehicles/delete_accident", r"{% include 'vehicles/utilities/delete_accident"),
]

def find_html_files(base_dir):
    html_files = []
    for root, dirs, files in os.walk(base_dir):
        if 'backup' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                html_files.append(Path(root) / file)
    return html_files

def update_template(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return 0
    
    original = content
    total_replacements = 0
    
    for pattern, replacement in PATH_UPDATES:
        content, count = re.subn(pattern, replacement, content)
        total_replacements += count
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        rel_path = file_path.relative_to(TEMPLATES_DIR)
        print(f"  UPDATED: {rel_path} ({total_replacements} changes)")
        return total_replacements
    return 0

print("="*80)
print("UPDATING TEMPLATE INCLUDES")
print("="*80)

html_files = find_html_files(TEMPLATES_DIR)
print(f"\nFound {len(html_files)} HTML files\n")

total = 0
updated_count = 0
for html_file in html_files:
    count = update_template(html_file)
    if count > 0:
        total += count
        updated_count += 1

print(f"\n{'='*80}")
print(f"FILES UPDATED: {updated_count}/{len(html_files)}")
print(f"TOTAL REPLACEMENTS: {total}")
print(f"{'='*80}")
print("DONE!")
