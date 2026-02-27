#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import migration script: Update all imports from root locations to src/ locations.
This script finds and replaces imports in all Python files in src/.
Uses absolute imports with src. prefix within the src/ directory.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define import patterns to replace
# These patterns assume sys.path includes src/ directory, so imports become absolute with src. prefix
IMPORT_REPLACEMENTS = [
    # from app import → from src.app import
    (r'from app\.(?!pycache)', 'from src.app.'),
    (r'from app import', 'from src.app import'),
    
    # from modules → from src.modules
    (r'from modules\.(?!pycache)', 'from src.modules.'),
    (r'from modules import', 'from src.modules import'),
    
    # from routes → from src.routes
    (r'from routes\.(?!pycache)', 'from src.routes.'),
    (r'from routes import', 'from src.routes import'),
    
    # from core → from src.core
    (r'from core\.(?!pycache)', 'from src.core.'),
    (r'from core import', 'from src.core import'),
    
    # from services → from src.services
    (r'from services\.(?!pycache)', 'from src.services.'),
    (r'from services import', 'from src.services import'),
    
    # from utils → from src.utils
    (r'from utils\.(?!pycache)', 'from src.utils.'),
    (r'from utils import', 'from src.utils import'),
    
    # from presentation → from src.presentation
    (r'from presentation\.(?!pycache)', 'from src.presentation.'),
    (r'from presentation import', 'from src.presentation import'),
    
    # from application → from src.application
    (r'from application\.(?!pycache)', 'from src.application.'),
    (r'from application import', 'from src.application import'),
    
    # from domain → from src.domain
    (r'from domain\.(?!pycache)', 'from src.domain.'),
    (r'from domain import', 'from src.domain import'),
    
    # from infrastructure → from src.infrastructure
    (r'from infrastructure\.(?!pycache)', 'from src.infrastructure.'),
    (r'from infrastructure import', 'from src.infrastructure import'),
    
    # from shared → from src.shared
    (r'from shared\.(?!pycache)', 'from src.shared.'),
    (r'from shared import', 'from src.shared import'),
    
    # from forms → from src.forms
    (r'from forms\.(?!pycache)', 'from src.forms.'),
    (r'from forms import', 'from src.forms import'),
    
    # from models import → from src.models import
    (r'from models import', 'from src.models import'),
]

class ImportMigrator:
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.replacements_made = 0
        self.files_processed = 0
        
    def get_python_files(self) -> List[Path]:
        """Get all Python files in src/ directory."""
        return list(self.src_dir.rglob('*.py'))
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = ['__pycache__', '.pyc', 'node_modules', '.git']
        return any(skip in str(file_path) for skip in skip_patterns)
    
    def update_imports_in_file(self, file_path: Path) -> Tuple[int, int]:
        """Update imports in a single file. Returns (lines_changed, lines_total)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            lines = content.split('\n')
            updated_lines = []
            changes_in_file = 0
            
            for line in lines:
                stripped = line.lstrip()
                
                # Only process import lines
                if not (stripped.startswith('from ') or stripped.startswith('import ')):
                    updated_lines.append(line)
                    continue
                
                # Skip if already a relative import or already has src. prefix
                if 'from .' in stripped or 'from src.' in stripped or 'import src.':
                    updated_lines.append(line)
                    continue
                
                # Get indentation
                indent = line[:len(line) - len(stripped)]
                
                # Try each replacement pattern on the stripped line
                original_line = stripped
                for pattern, replacement in IMPORT_REPLACEMENTS:
                    new_line = re.sub(pattern, replacement, stripped)
                    if new_line != stripped:
                        stripped = new_line
                        changes_in_file += 1
                        break
                
                # Reconstruct with indentation
                updated_lines.append(indent + stripped)
            
            # Write back if changed
            updated_content = '\n'.join(updated_lines)
            if updated_content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                return changes_in_file, len(lines)
            
            return 0, len(lines)
        
        except Exception as e:
            print(f"[ERROR] Processing {file_path}: {e}")
            return 0, 0
    
    def migrate_all(self) -> None:
        """Migrate all Python files in src/."""
        python_files = [f for f in self.get_python_files() if not self.should_skip_file(f)]
        total_files = len(python_files)
        
        print(f"\n{'='*70}")
        print(f"Import Migration: {total_files} Python files found in src/")
        print(f"{'='*70}\n")
        
        files_with_imports = []
        
        for idx, file_path in enumerate(python_files, 1):
            rel_path = file_path.relative_to(self.src_dir.parent)
            changes, total = self.update_imports_in_file(file_path)
            
            if changes > 0:
                self.files_processed += 1
                self.replacements_made += changes
                status = '✓ UPDATED'
                files_with_imports.append((rel_path, changes))
                print(f"[{idx:3d}/{total_files}] {status} {rel_path} ({changes} changes)")
        
        print(f"\n{'='*70}")
        print(f"Migration Complete!")
        print(f"Files Updated:      {self.files_processed}")
        print(f"Total Replacements: {self.replacements_made}")
        if files_with_imports:
            print(f"\nFirst 10 updated files:")
            for p, c in files_with_imports[:10]:
                print(f"  - {p} ({c} changes)")
        print(f"{'='*70}\n")


if __name__ == '__main__':
    src_dir = Path(__file__).resolve().parent.parent / 'src'
    
    if not src_dir.exists():
        print(f"[ERROR] src/ directory not found at {src_dir}")
        exit(1)
    
    migrator = ImportMigrator(src_dir)
    migrator.migrate_all()
