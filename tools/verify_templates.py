r"""Template smoke verifier for url_for endpoint usage.

Usage:
  .venv\Scripts\python tools/verify_templates.py
"""

import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
from routes.accounting.mapping_registry import LEGACY_ENDPOINT_MAPPINGS


URL_FOR_PATTERN = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")


def collect_template_endpoints(templates_root: Path):
    usage = defaultdict(list)
    for html_file in templates_root.rglob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in URL_FOR_PATTERN.finditer(content):
            endpoint = match.group(1)
            usage[endpoint].append(str(html_file.relative_to(templates_root.parent)))
    return usage


def filter_usage_by_scope(usage, scope):
    if scope == "all":
        return usage

    if scope == "accounting":
        filtered = {}
        for endpoint, files in usage.items():
            has_accounting_endpoint = endpoint.startswith("accounting.")
            has_accounting_template = any("templates\\accounting\\" in file_path or "templates/accounting/" in file_path for file_path in files)
            if has_accounting_endpoint or has_accounting_template:
                filtered[endpoint] = files
        return filtered

    return usage


def parse_args():
    parser = argparse.ArgumentParser(description="Verify template url_for endpoint usage against registered routes")
    parser.add_argument(
        "--scope",
        choices=["all", "accounting"],
        default="all",
        help="Limit verification scope. Use 'accounting' for Phase-0 accounting triage.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    templates_root = Path("templates")
    if not templates_root.exists():
        print("[ERROR] templates directory not found")
        return 2

    mapped_legacy = {m.legacy_endpoint: m for m in LEGACY_ENDPOINT_MAPPINGS}
    registered_endpoints = set(app.view_functions.keys())

    usage = collect_template_endpoints(templates_root)
    scoped_usage = filter_usage_by_scope(usage, args.scope)

    missing_unmapped = []
    legacy_mapped = []

    for endpoint, files in sorted(scoped_usage.items()):
        if endpoint in registered_endpoints:
            continue
        if endpoint in mapped_legacy:
            legacy_mapped.append((endpoint, mapped_legacy[endpoint].canonical_endpoint, len(files)))
        else:
            missing_unmapped.append((endpoint, len(files), files[:5]))

    print("=== Template URL Verification ===")
    print(f"Scope: {args.scope}")
    print(f"Total unique url_for endpoints: {len(usage)}")
    if args.scope != "all":
        print(f"Scoped unique url_for endpoints: {len(scoped_usage)}")
    print(f"Registered endpoints: {len(registered_endpoints)}")
    print(f"Legacy mapped-but-missing endpoints: {len(legacy_mapped)}")
    print(f"Unmapped missing endpoints: {len(missing_unmapped)}")

    if legacy_mapped:
        print("\n[LEGACY-MAPPED]")
        for endpoint, canonical, count in legacy_mapped:
            print(f"- {endpoint} -> {canonical} (used in {count} template locations)")

    if missing_unmapped:
        print("\n[UNMAPPED-MISSING]")
        for endpoint, count, files in missing_unmapped:
            print(f"- {endpoint} (used in {count} template locations)")
            for file_path in files:
                print(f"    * {file_path}")
        return 1

    print("\n[OK] No unmapped missing endpoints detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
