import re
from pathlib import Path

from core.app_factory import create_app


def main() -> None:
    layout = Path("templates/layout.html").read_text(encoding="utf-8")
    endpoints = set(re.findall(r"url_for\('([^']+)'\)", layout))

    app = create_app()
    registered = {rule.endpoint for rule in app.url_map.iter_rules()}

    missing = sorted(endpoint for endpoint in endpoints if endpoint not in registered)

    print("ENDPOINTS_IN_LAYOUT=", len(endpoints))
    print("MISSING=", missing)


if __name__ == "__main__":
    main()
