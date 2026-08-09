from __future__ import annotations

CRITICAL_OPERATIONS: dict[str, set[str]] = {
    "/health": {"get"},
    "/v1/market/session": {"get"},
    "/v1/risk/preflight": {"post"},
    "/v1/live-approvals": {"get", "post"},
    "/v1/orders": {"get", "post"},
    "/v1/orders/cancel-open": {"post"},
    "/v1/reconcile": {"post"},
    "/v1/research/strategies": {"get"},
    "/v1/research/drift": {"post"},
    "/v1/production/readiness": {"post"},
    "/v1/production/canary-plan": {"post"},
    "/v1/tfex/risk/preflight": {"post"},
    "/v1/tfex/orders/uat": {"post"},
}
FORBIDDEN_LIVE_TFEX_PATHS = {"/v1/tfex/orders/live", "/v1/tfex/live-orders"}


def validate_schema(schema: dict[str, object]) -> list[str]:
    """Validate stable API safety boundaries without making any network call."""

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
            if str(method).lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                errors.append(f"{str(method).upper()} {path} is not an OpenAPI operation object")
                continue
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                errors.append(f"{str(method).upper()} {path} has no operationId")
            else:
                operation_ids.append(operation_id)
    if len(operation_ids) != len(set(operation_ids)):
        errors.append("duplicate OpenAPI operationId detected")
    return errors
