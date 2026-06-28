"""Dump the FastAPI OpenAPI schema to docs/openapi.json.

Run from the api/ directory:
    .venv/bin/python scripts/export_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402

OUT = API_DIR.parent / "docs" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n")
    paths = sorted(schema.get("paths", {}))
    print(f"Wrote {OUT} ({len(paths)} paths, "
          f"{len(schema.get('components', {}).get('schemas', {}))} schemas)")
    for p in paths:
        print(" ", p)


if __name__ == "__main__":
    main()
