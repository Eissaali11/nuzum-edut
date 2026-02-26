"""
Pytest configuration - sets up sys.path for src/ imports
"""
import sys
from pathlib import Path

# Add src/ directory to Python path so imports work correctly
src_dir = Path(__file__).resolve().parent.parent / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Also ensure base directory is in path for backward compatibility
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))
