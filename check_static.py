# Check static files location
from pathlib import Path

BASE_DIR = Path('D:/nuzm')
static_dir = BASE_DIR / 'presentation' / 'web' / 'static'

print(f"Checking static folder: {static_dir}")
print(f"Exists: {static_dir.exists()}")
print(f"Is directory: {static_dir.is_dir()}")

if static_dir.exists():
    # List CSS files
    css_files = list(static_dir.glob("**/*.css"))
    print(f"\nCSS files found: {len(css_files)}")
    for f in css_files[:3]:
        print(f"  - {f.relative_to(static_dir)}")
    
    # Check subdirectories
    subdirs = [d.name for d in static_dir.iterdir() if d.is_dir()]
    print(f"\nSubdirectories: {subdirs}")
else:
    print("Static folder does NOT exist!")
