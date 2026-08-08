from __future__ import annotations

import argparse
import json
from pathlib import Path

from zksato.api import app

CRITICAL_OPERATIONS: dict[str, set[str]] = {
    "/health": {"get"},
    "/v1/risk/preflight": {"post"},
    "/v1/live-approvals": {"get", "post"},
    "/v1/orders": {"get", "post"},
    "/v1/reconcile": {"post"},
    "/v1/production/readiness": {"post"},
    "/v1/production/canary-plan": {"post"},
    "/v1/tfex/risk/preflight": {"post"},
    "/v1/tfex/orders/uat": {"post"},
}
FORBIDDEN_LIVE_TFEX_PATHS = {"/v1/tfex/orders/live", "/v1/tfex/live-orders"}


def validate_schema(schema: dict[str, object]) -> list[str]:
    errors: list[str] = []
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return ["OpenAPI paths must be an object"]

    for path, methods in CRITICAL_OPERATIONS.items():
        item = paths.get(path)
        if not isinstance(item, dict):
            errors.append(f"missing critical path: {path}")
            continue
        missing = methods - {str(method).lower() for method in item}
        if missing:
            errors.append(f"{path} missing methods: {', '.join(sorted(missing))}")

    for forbidden in FORBIDDEN_LIVE_TFEX_PATHS:
        if forbidden in paths:
            errors.append(f"forbidden live TFEX mutation path exists: {forbidden}")

    operation_ids: list[str] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                errors.append(f"{method.upper()} {path} is not an OpenAPI operation object")
                continue
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                errors.append(f"{method.upper()} {path} has no operationId")
            else:
                operation_ids.append(operation_id)
    if len(operation_ids) != len(set(operation_ids)):
        errors.append("duplicate OpenAPI operationId detected")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and export zksato OpenAPI contract")
    parser.add_argument("--output", default="openapi.json")
    args = parser.parse_args()
    schema = app.openapi()
    errors = validate_schema(schema)
    Path(args.output).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OpenAPI contract valid; wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
