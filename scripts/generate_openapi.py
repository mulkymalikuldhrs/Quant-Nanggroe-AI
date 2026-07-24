"""Standalone OpenAPI schema export.

Usage:
    uv run python scripts/generate_openapi.py [--output openapi.json]

Exports the FastAPI application's OpenAPI schema to a JSON file.
This allows external tooling (client generation, documentation,
contract testing) to consume the schema without running the server.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from quant_nanggroe.api.app import app
except ImportError:
    print("ERROR: Could not import FastAPI app. Ensure quant_nanggroe is installed.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument(
        "--output",
        default="openapi.json",
        help="Output file path (default: openapi.json)",
    )
    args = parser.parse_args()

    schema = app.openapi()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {output_path.resolve()} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
