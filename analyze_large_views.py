#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Large View Files Refactor Script
Identifies and reports on view files > 300 lines needing refactoring
"""

import os
from pathlib import Path

VIEWS_DIR = Path(r'd:\nuzm\modules\vehicles\presentation\templates\vehicles\views')

# Files to analyze
large_files = [
    '3view.html',
    '4view.html',
    '1view.html',
    'workshop_details.html',
    'view_clean.html',
    'view_modern.html',
    'view_cards.html',
    'index.html',
    'accident_details.html'
]

print("="*80)
print("LARGE VIEW FILES ANALYSIS")
print("="*80)

for filename in large_files:
    file_path = VIEWS_DIR / filename
    
    if not file_path.exists():
        print(f"\nSKIP: {filename} (not found)")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    line_count = len(lines)
    
    # Quick analysis
    has_inline_script = any('<script>' in line for line in lines)
    has_inline_style = any('<style>' in line for line in lines)
    include_count = sum(1 for line in lines if '{% include' in line)
    extends = any('{% extends' in line for line in lines)
    
    print(f"\n📄 {filename}")
    print(f"   Lines: {line_count}")
    print(f"   Inline <script>: {'⚠️ YES' if has_inline_script else '✓ NO'}")
    print(f"   Inline <style>: {'⚠️ YES' if has_inline_style else '✓ NO'}")
    print(f"   {{% include %}} count: {include_count}")
    print(f"   Extends layout: {'✓ YES' if extends else '❌ NO'}")
    
    # Priority classification
    if line_count > 1000:
        priority = "🔴 CRITICAL"
    elif line_count > 700:
        priority = "🟠 HIGH"
    elif line_count > 300:
        priority = "🟡 MEDIUM"
    else:
        priority = "🟢 LOW"
    
    print(f"   Refactor Priority: {priority}")

print(f"\n{'='*80}")
print("RECOMMENDATIONS:")
print("="*80)
print("1. Extract all inline <script> to static/js/modules/vehicles/")
print("2. Extract all inline <style> to static/css/modules/vehicles/")
print("3. Break HTML into partials (< 100 lines each)")
print("4. Keep main files as orchestrators (< 150 lines)")
print("="*80)
