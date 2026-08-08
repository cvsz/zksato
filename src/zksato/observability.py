from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from uuid import uuid4

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

CORRELATION_ID: ContextVar[str] = ContextVar("zksato_correlation_id", default="")

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
MARKET_FEED_AGE = Gauge(
    "zksato_market_feed_age_seconds",
    "Age of the freshest trusted market quote",
)
OUTBOX_BACKLOG = Gauge(
    "zksato_outbox_backlog",
    "Pending durable outbox messages",
)
BROKER_ERRORS = Counter(
    "zksato_broker_errors_total",
    "Broker/API errors by operation",
    ["operation"],
)
COORDINATION_HEALTH = Gauge(
    "zksato_coordination_healthy",
    "Redis coordination health, 1 healthy or not configured, 0 unhealthy",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": current_correlation_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    if json_logs:
        formatter = JsonFormatter()
        for handler in root.handlers:
            handler.setFormatter(formatter)


def bind_correlation_id(value: str | None = None) -> Token[str]:
    return CORRELATION_ID.set(value or str(uuid4()))


def reset_correlation_id(token: Token[str]) -> None:
    CORRELATION_ID.reset(token)


def current_correlation_id() -> str:
    value = CORRELATION_ID.get()
    return value or ""


def init_tracing(service_name: str, endpoint: str | None) -> bool:
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logging.getLogger(__name__).warning(
            "OpenTelemetry endpoint configured but observability extra is not installed"
        )
        return False
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return True


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
