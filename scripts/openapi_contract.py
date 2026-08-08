from __future__ import annotations

import argparse
import json
from pathlib import Path

from zksato.api import app
from zksato.openapi_contract import validate_schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and export zksato OpenAPI contract")
    parser.add_argument("--output", default="openapi.json")
    args = parser.parse_args()
    schema = app.openapi()
    errors = validate_schema(schema)
    Path(args.output).write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OpenAPI contract valid; wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
