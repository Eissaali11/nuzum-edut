#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت تقسيم ملف attendance.py إلى 8 ملفات منفصلة
Split attendance.py into 8 modular files

هذا السكريبت:
1. يقرأ الملف الأصلي
2. يحدد الدوال والمسارات
3. يوزعها على الملفات المناسبة
4. يحافظ على جميع الواردات والإعدادات
"""

import re
import os
from pathlib import Path

# نطاقات الأسطر لكل وحدة (من grep_search سابقاً)
ROUTE_RANGES = {
    'views': [
        (62, 232),      # index
        (227, 283),     # departmentلا... انتظر! هناك مشكلة هنا. /department هو في السطر 227 لكن /bulk-record في 284
        # سأحتاج إلى قراءة الملف بعناية لتحديد النهايات الصحيحة
    ],
    'recording': [
        # /record, /bulk-record, /all-departments, circle_mark
    ],
    'export': [
        # جميع وظائف الـexport
    ],
    'statistics': [
        # /stats, /dashboard, /department-stats
    ],
    'crud': [
        # /delete, /bulk_delete, /edit, /update
    ],
    'circles': [
        # عمليات الدوائر
    ]
}

def read_file(filepath):
    """Read the entire file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()

def find_function_ranges(lines):
    """Find all function definitions and their ending line numbers"""
    function_ranges = {}
    current_func = None
    
    for i, line in enumerate(lines):
        # Check for @attendance_bp.route decorators
        if '@attendance_bp.route' in line:
            # Next line should be function definition
            if i + 1 < len(lines):
                func_line = lines[i + 1]
                match = re.search(r'def\s+(\w+)\s*\(', func_line)
                if match:
                    func_name = match.group(1)
                    current_func = func_name
                    function_ranges[func_name] = {'start': i, 'decorator_start': i}
        
        # Check for function definitions without decorator
        elif line.startswith('def ') and not line.strip().startswith('#'):
            match = re.search(r'def\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                current_func = func_name
                if func_name not in function_ranges:
                    function_ranges[func_name] = {'start': i, 'decorator_start': i}
    
    # Now find end of each function (next function or decorator)
    sorted_functions = sorted(function_ranges.items(), key=lambda x: x[1]['start'])
    for i, (func_name, info) in enumerate(sorted_functions):
        if i + 1 < len(sorted_functions):
            next_start = sorted_functions[i + 1][1]['decorator_start']
            info['end'] = next_start - 1
        else:
            info['end'] = len(lines) - 1
    
    return sorted_functions

def classify_route(func_name, route_decorator):
    """Classify which module this route belongs to"""
    if 'delete' in route_decorator or func_name == 'delete_attendance' or func_name == 'bulk_delete_attendance':
        return 'crud'
    elif 'export' in route_decorator or 'export' in func_name:
        return 'export'
    elif 'stats' in route_decorator or 'dashboard' in route_decorator or 'stats' in func_name:
        return 'statistics'
    elif 'bulk-record' in route_decorator or 'department' in route_decorator and 'bulk' in route_decorator:
        return 'recording'
    elif 'record' in route_decorator or 'record' in func_name:
        return 'recording'
    elif 'circle' in route_decorator or 'circle' in func_name:
        return 'circles'
    elif 'department' in route_decorator and 'export' not in route_decorator:
        return 'views'
    elif 'employee' in route_decorator:
        return 'views'
    elif route_decorator == '/' or func_name == 'index':
        return 'views'
    else:
        return 'views'

def main():
    """Main refactoring process"""
    input_file = r'd:\nuzm\routes\attendance.py'
    output_dir = r'd:\nuzm\routes\attendance'
    
    print(f"📖 Reading {input_file}...")
    lines = read_file(input_file)
    
    print(f"🔍 Finding function ranges...")
    functions = find_function_ranges(lines)
    
    print(f"✅ Found {len(functions)} functions/routes")
    
    # Print all functions found (for verification)
    for func_name, info in functions:
        start_line = info['start'] + 1  # Convert to 1-indexed
        end_line = info['end'] + 1
        # Find the route decorator
        decorator_line = lines[info['decorator_start']] if info['decorator_start'] >= 0 else ''
        route_match = re.search(r"route\('([^']+)'", decorator_line)
        route_path = route_match.group(1) if route_match else '?'
        
        print(f"  • {func_name:30} Lines {start_line:4d}-{end_line:4d}  Route: {route_path}")

if __name__ == '__main__':
    main()
