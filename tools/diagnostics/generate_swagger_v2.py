import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "refactor_reports" / "swagger.json"

API_FILES = [
    ROOT / "routes" / "api_documents_v2.py",
    ROOT / "routes" / "api_employee_requests_v2.py",
    ROOT / "routes" / "api_attendance_v2.py",
    ROOT / "routes" / "api_external_safety_v2.py",
    ROOT / "api" / "v2" / "documents_api.py",
]

BLUEPRINT_PREFIX_RE = re.compile(
    r"Blueprint\([^\)]*url_prefix\s*=\s*['\"]([^'\"]+)['\"]"
)
ROUTE_RE = re.compile(
    r"@\w+\.route\(\s*['\"]([^'\"]+)['\"]\s*,\s*methods\s*=\s*\[([^\]]+)\]\s*\)"
)
DEF_RE = re.compile(r"def\s+(\w+)\s*\(")


def normalize_path(prefix: str, route: str) -> str:
    if not prefix:
        prefix = ""
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not route.startswith("/"):
        route = "/" + route
    path = (prefix + route).replace("//", "/")
    # Flask style to OpenAPI style
    path = re.sub(r"<int:(\w+)>", r"{\1}", path)
    path = re.sub(r"<(\w+)>", r"{\1}", path)
    return path


def extract_methods(methods_raw: str):
    methods = []
    for part in methods_raw.split(","):
        token = part.strip().strip("'\"").upper()
        if token:
            methods.append(token)
    return methods or ["GET"]


paths = {}

for file_path in API_FILES:
    if not file_path.exists():
        continue

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    prefix_match = BLUEPRINT_PREFIX_RE.search(text)
    prefix = prefix_match.group(1) if prefix_match else ""

    lines = text.splitlines()
    for i, line in enumerate(lines):
        route_match = ROUTE_RE.search(line)
        if not route_match:
            continue

        route_path = route_match.group(1)
        methods = extract_methods(route_match.group(2))
        full_path = normalize_path(prefix, route_path)

        operation_id = "unknown_operation"
        for j in range(i + 1, min(i + 8, len(lines))):
            m = DEF_RE.search(lines[j])
            if m:
                operation_id = m.group(1)
                break

        path_item = paths.setdefault(full_path, {})
        for method in methods:
            path_item[method.lower()] = {
                "operationId": operation_id,
                "summary": operation_id.replace("_", " "),
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"},
                    "500": {"description": "Server Error"},
                },
                "security": [{"bearerAuth": []}],
            }

# Mark explicit public endpoints (health + login)
for path, ops in paths.items():
    if path.endswith("/health") or path.endswith("/auth/login"):
        for spec in ops.values():
            spec["security"] = []

swagger = {
    "openapi": "3.0.3",
    "info": {
        "title": "Nuzum API v2",
        "version": "2.0.0",
        "description": "Auto-generated baseline Swagger for v2 endpoints.",
    },
    "servers": [
        {"url": "http://localhost:5000", "description": "Local"}
    ],
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "paths": dict(sorted(paths.items())),
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(swagger, ensure_ascii=False, indent=2), encoding="utf-8")
print(OUT)
print(f"paths={len(paths)}")
