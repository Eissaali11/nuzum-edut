#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Print top 20 largest files by LOC (HTML+Python)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(r"d:\nuzm")
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", "migrations", "instance"}

HTML_EXTS = {".html", ".htm"}
PY_EXT = ".py"


def iter_files():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() in HTML_EXTS or path.suffix.lower() == PY_EXT:
                yield path


def count_loc(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return len(text.splitlines())


def main() -> None:
    rows = []
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        rows.append((rel, count_loc(path)))

    for rel, loc in sorted(rows, key=lambda r: -r[1])[:20]:
        print(f"{rel}\t{loc}")


if __name__ == "__main__":
    main()
