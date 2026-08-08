from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "zksato_http_requests_total",
    "HTTP requests handled by zksato",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "zksato_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
)
ORDER_SUBMISSIONS = Counter(
    "zksato_order_submissions_total",
    "Trading submissions by resulting status",
    ["status"],
)
RISK_REJECTIONS = Counter(
    "zksato_risk_rejections_total",
    "Orders rejected by deterministic risk controls",
)
RECONCILIATION_RUNS = Counter(
    "zksato_reconciliation_runs_total",
    "Broker reconciliation runs",
    ["result"],
)
RECONCILIATION_UNRESOLVED = Gauge(
    "zksato_reconciliation_unresolved_orders",
    "Orders currently requiring reconciliation",
)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
