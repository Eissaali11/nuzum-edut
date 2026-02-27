#!/usr/bin/env python
"""Clean pytest runner with file output."""
import subprocess
import sys
from pathlib import Path

# Run pytest and capture output
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_attendance_late.py', '-v', '--tb=short'],
    cwd=Path(__file__).parent.parent,
    capture_output=True,
    text=True
)

# Write to file
output_file = Path(__file__).parent.parent / 'artifacts' / 'pytest_results.txt'
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn Code: {result.returncode}\n")

# Print to console
print(f"Test output written to: {output_file}")
print("\n" + "="*70)
print("TEST RESULTS")
print("="*70)
print(result.stdout)
if result.stderr:
    print("\nERROR OUTPUT:")
    print(result.stderr)

sys.exit(result.returncode)
