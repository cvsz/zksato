from zksato.api import app
from zksato.openapi_contract import validate_schema


def test_openapi_contract_preserves_critical_control_boundaries() -> None:
    errors = validate_schema(app.openapi())
    assert errors == []


def test_openapi_has_no_autonomous_live_tfex_mutation_endpoint() -> None:
    paths = app.openapi()["paths"]
    assert "/v1/tfex/orders/live" not in paths
    assert "/v1/tfex/live-orders" not in paths
