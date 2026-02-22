#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project bloat audit: top files by LOC, long functions, inline script/style blocks, flat folders, duplicated patterns."""

from __future__ import annotations

import ast
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"d:\nuzm")

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "migrations",
    "instance",
}

HTML_EXTS = {".html", ".htm"}
PY_EXT = ".py"

SCRIPT_OPEN_RE = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
SCRIPT_CLOSE_RE = re.compile(r"</script>", re.IGNORECASE)
STYLE_OPEN_RE = re.compile(r"<style\b[^>]*>", re.IGNORECASE)
STYLE_CLOSE_RE = re.compile(r"</style>", re.IGNORECASE)


def iter_files():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() in HTML_EXTS or path.suffix.lower() == PY_EXT:
                yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def count_loc(text: str) -> int:
    return len(text.splitlines())


def python_long_functions(text: str, min_len: int = 100):
    results = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "end_lineno") and node.end_lineno:
                length = node.end_lineno - node.lineno + 1
                if length >= min_len:
                    results.append((node.name, node.lineno, node.end_lineno, length))
    return results


def html_block_lengths(text: str):
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if SCRIPT_OPEN_RE.search(line):
            start = i
            i += 1
            while i < len(lines) and not SCRIPT_CLOSE_RE.search(lines[i]):
                i += 1
            end = i if i < len(lines) else len(lines) - 1
            blocks.append(("script", start + 1, end + 1, end - start - 1))
        if STYLE_OPEN_RE.search(line):
            start = i
            i += 1
            while i < len(lines) and not STYLE_CLOSE_RE.search(lines[i]):
                i += 1
            end = i if i < len(lines) else len(lines) - 1
            blocks.append(("style", start + 1, end + 1, end - start - 1))
        i += 1
    return blocks


def scan_flat_folders(min_files: int = 15):
    flat = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        if not dirs and len(files) >= min_files:
            rel = Path(root).relative_to(ROOT).as_posix()
            flat.append((rel, len(files)))
    return sorted(flat, key=lambda x: -x[1])


def find_repeated_snippets(texts: dict[str, str], min_count: int = 3):
    # Naive signature: top repeated line fragments (trim whitespace)
    line_counts = Counter()
    for text in texts.values():
        for line in text.splitlines():
            trimmed = line.strip()
            if len(trimmed) < 20:
                continue
            if trimmed.startswith("<!--"):
                continue
            line_counts[trimmed] += 1
    return [line for line, count in line_counts.most_common(30) if count >= min_count]


def main():
    file_data = []
    py_long_funcs = []
    html_big_blocks = []

    html_texts = {}

    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        text = read_text(path)
        loc = count_loc(text)
        file_data.append((rel, loc, path.suffix.lower()))

        if path.suffix.lower() == PY_EXT:
            for name, start, end, length in python_long_functions(text, 100):
                py_long_funcs.append((rel, name, start, end, length))
        if path.suffix.lower() in HTML_EXTS:
            html_texts[rel] = text
            for kind, start, end, length in html_block_lengths(text):
                if length >= 50:
                    html_big_blocks.append((rel, kind, start, end, length))

    top20 = sorted(file_data, key=lambda x: -x[1])[:20]
    flat_folders = scan_flat_folders(15)
    repeated_lines = find_repeated_snippets(html_texts, 3)

    print("TOP20_START")
    for rel, loc, ext in top20:
        print(f"{rel}\t{loc}\t{ext}")
    print("TOP20_END")

    print("PY_LONG_FUNCS_START")
    for rel, name, start, end, length in sorted(py_long_funcs, key=lambda r: -r[4]):
        print(f"{rel}\t{name}\t{start}\t{end}\t{length}")
    print("PY_LONG_FUNCS_END")

    print("HTML_BIG_BLOCKS_START")
    for rel, kind, start, end, length in sorted(html_big_blocks, key=lambda r: -r[4]):
        print(f"{rel}\t{kind}\t{start}\t{end}\t{length}")
    print("HTML_BIG_BLOCKS_END")

    print("FLAT_FOLDERS_START")
    for rel, count in flat_folders:
        print(f"{rel}\t{count}")
    print("FLAT_FOLDERS_END")

    print("REPEATED_LINES_START")
    for line in repeated_lines:
        print(line)
    print("REPEATED_LINES_END")


if __name__ == "__main__":
    main()
