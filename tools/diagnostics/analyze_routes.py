#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analyze route files for LOC, endpoints, and long functions."""

from __future__ import annotations

import ast
import os
import re
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
}

ROUTE_FILE_PATTERNS = (
    "routes",
    "route",
)

ROUTE_DECORATOR_RE = re.compile(r"^\s*@[^\n]*\.route\(")


def is_route_file(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    lowered = path.as_posix().lower()
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    return "routes" in lowered or "route" in path.name.lower()


def count_endpoints(lines: list[str]) -> int:
    return sum(1 for line in lines if ROUTE_DECORATOR_RE.search(line))


def get_function_lengths(code: str) -> list[tuple[str, int, int, int]]:
    results = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "end_lineno") and node.end_lineno is not None:
                length = node.end_lineno - node.lineno + 1
                results.append((node.name, node.lineno, node.end_lineno, length))
    return results


def infer_responsibility(path: Path) -> str:
    name = path.stem.lower()
    parts = [p.lower() for p in path.parts]

    if "vehicles" in parts:
        if "handover" in name:
            return "Vehicle handovers"
        if "accident" in name:
            return "Vehicle accidents"
        if "workshop" in name:
            return "Vehicle workshop"
        if "vehicle" in name:
            return "Vehicle core routes"
        if "main" in name:
            return "Vehicle main views"
        return "Vehicles (general)"

    if "employees" in parts:
        return "Employees"

    if "api" in parts or "api" in name:
        return "API"

    if "auth" in name:
        return "Authentication"

    if "dashboard" in name:
        return "Dashboard"

    if "reports" in name or "report" in name:
        return "Reports"

    if "analytics" in name:
        return "Analytics"

    if "attendance" in name:
        return "Attendance"

    if "users" in name:
        return "Users"

    return "General"


def main() -> None:
    route_files = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for filename in files:
            path = Path(root) / filename
            if is_route_file(path):
                route_files.append(path)

    summaries = []
    long_functions = []

    for path in sorted(route_files):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        loc = len(lines)
        endpoints = count_endpoints(lines)
        responsibility = infer_responsibility(path)

        summaries.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "loc": loc,
            "endpoints": endpoints,
            "responsibility": responsibility,
        })

        for name, start, end, length in get_function_lengths(content):
            if length > 50:
                long_functions.append({
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "name": name,
                    "start": start,
                    "end": end,
                    "length": length,
                })

    print("ROUTE_SUMMARY_START")
    for row in summaries:
        print(f"{row['path']}\t{row['loc']}\t{row['endpoints']}\t{row['responsibility']}")
    print("ROUTE_SUMMARY_END")

    print("LONG_FUNCTIONS_START")
    for row in sorted(long_functions, key=lambda r: (-r["length"], r["path"], r["name"])):
        print(f"{row['path']}\t{row['name']}\t{row['start']}\t{row['end']}\t{row['length']}")
    print("LONG_FUNCTIONS_END")


if __name__ == "__main__":
    main()
