#!/usr/bin/env python3
"""Debug import patterns"""
import re
from pathlib import Path

# Read a sample file
sample_file = Path('D:\\nuzm\\src\\modules\\vehicles\\__init__.py')
with open(sample_file) as f:
    lines = f.readlines()

print(f"File: {sample_file}")
print(f"Total lines: {len(lines)}")
print("\n" + "="*70)
print("First 30 lines:")
print("="*70)
for i, line in enumerate(lines[:30], 1):
    stripped = line.lstrip()
    if 'from' in line or 'import' in line:
        print(f"{i:3d}: {repr(line)}")
        if stripped.startswith('from '):
            print(f"      Stripped: {repr(stripped)}")
            # Test patterns
            patterns = [
                (r'from modules\.(?!pycache)', 'from src.modules.'),
                (r'from modules import', 'from src.modules import'),
            ]
            for pat, repl in patterns:
                match = re.search(pat, stripped)
                print(f"      Pattern '{pat}' matches: {bool(match)}")
                result = re.sub(pat, repl, stripped)
                print(f"      After sub: {repr(result)}")
