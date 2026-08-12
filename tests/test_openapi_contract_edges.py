from typing import Any, cast

from zksato.openapi_contract import CRITICAL_OPERATIONS, validate_schema


def complete_paths() -> dict[str, dict[str, dict[str, str]]]:
    return {
        path: {method: {"operationId": f"op_{index}_{method}"} for method in methods}
        for index, (path, methods) in enumerate(CRITICAL_OPERATIONS.items())
    }


def test_validator_rejects_non_object_paths() -> None:
    assert validate_schema({"paths": []}) == ["OpenAPI paths must be an object"]


def test_validator_reports_missing_critical_paths_and_methods() -> None:
    errors = validate_schema({"paths": {"/health": {}}})
    assert "/health missing methods: get" in errors
    assert any(error.startswith("missing critical path:") for error in errors)


def test_validator_rejects_forbidden_live_tfex_path_and_duplicate_operation_ids() -> None:
    paths = cast(dict[str, Any], complete_paths())
    paths["/v1/tfex/orders/live"] = {"post": {"operationId": "forbidden_live"}}
    paths["/extra-one"] = {"get": {"operationId": "duplicate"}}
    paths["/extra-two"] = {"get": {"operationId": "duplicate"}}
    errors = validate_schema({"paths": paths})
    assert "forbidden live TFEX mutation path exists: /v1/tfex/orders/live" in errors
    assert "duplicate OpenAPI operationId detected" in errors


def test_validator_rejects_missing_and_invalid_operations() -> None:
    paths = cast(dict[str, Any], complete_paths())
    paths["/no-id"] = {"get": {}}
    paths["/not-object"] = {"post": "invalid"}
    errors = validate_schema({"paths": paths})
    assert "GET /no-id has no operationId" in errors
    assert "POST /not-object is not an OpenAPI operation object" in errors
