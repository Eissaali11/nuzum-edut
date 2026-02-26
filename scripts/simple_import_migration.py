#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple import migration script - Update imports from root to src namespace.
"""

import re
from pathlib import Path

# Patterns to replace
PATTERNS = [
    ('from modules.', 'from src.modules.'),
    ('from modules import', 'from src.modules import'),
    ('from routes.', 'from src.routes.'),
    ('from routes import', 'from src.routes import'),
    ('from core.', 'from src.core.'),
    ('from core import', 'from src.core import'),
    ('from app.', 'from src.app.'),
    ('from app import', 'from src.app import'),
    ('from services.', 'from src.services.'),
    ('from services import', 'from src.services import'),
    ('from utils.', 'from src.utils.'),
    ('from utils import', 'from src.utils import'),
    ('from presentation.', 'from src.presentation.'),
    ('from application.', 'from src.application.'),
    ('from domain.', 'from src.domain.'),
    ('from infrastructure.', 'from src.infrastructure.'),
    ('from forms.', 'from src.forms.'),
]

def update_file(file_path):
    """Update imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Apply replacements
        for old, new in PATTERNS:
            content = content.replace(old, new)
        
        # Write back if changed
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    src_dir = Path('D:/nuzm/src')
    if not src_dir.exists():
        print(f"Error: {src_dir} not found")
        return
    
    # Get all Python files
    py_files = list(src_dir.rglob('*.py'))
    py_files = [f for f in py_files if '__pycache__' not in str(f)]
    
    print(f"\nFound {len(py_files)} Python files in src/\n")
    
    updated_count = 0
    for idx, file_path in enumerate(py_files, 1):
        if idx % 50 == 0:
            print(f"Processing {idx}/{len(py_files)}...")
        
        if update_file(file_path):
            updated_count += 1
            rel_path = file_path.relative_to(src_dir.parent)
            print(f"✓ {rel_path}")
    
    print(f"\n{'='*70}")
    print(f"Migration Complete!")
    print(f"Files updated: {updated_count}/{len(py_files)}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
