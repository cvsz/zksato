"""OpenTelemetry observability setup for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.instrument.fastapi import FastAPIInstrumentor
    from opentelemetry.instrument.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrument.redis import RedisInstrumentor
    from opentelemetry.instrument.httpx import HTTPXClientInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


@dataclass
class ObservabilityConfig:
    """Configuration for observability."""
    enabled: bool = True
    otlp_endpoint: str | None = None
    service_name: str = "zksato"
    console_export: bool = False


def setup_observability(config: ObservabilityConfig | None = None) -> None:
    """Set up OpenTelemetry auto-instrumentation."""
    if not OTEL_AVAILABLE:
        return
    
    config = config or ObservabilityConfig()
    if not config.enabled:
        return
    
    # Resource
    resource = Resource.create({"service.name": config.service_name})
    
    # Traces
    trace.set_tracer_provider(TracerProvider(resource=resource))
    
    if config.otlp_endpoint:
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=config.otlp_endpoint))
        )
    
    if config.console_export:
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )
    
    # Metrics
    readers = []
    if config.otlp_endpoint:
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=config.otlp_endpoint)))
    if config.console_export:
        readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
    
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))
    
    # Auto-instrumentation
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()


def get_tracer(name: str = "zksato"):
    """Get a tracer instance."""
    if not OTEL_AVAILABLE:
        return NoOpTracer()
    return trace.get_tracer(name)


def get_meter(name: str = "zksato"):
    """Get a meter instance."""
    if not OTEL_AVAILABLE:
        return NoOpMeter()
    return metrics.get_meter(name)


class NoOpTracer:
    """No-op tracer for when OTel is not available."""
    
    def start_as_current_span(self, name: str, **kwargs):
        return NoOpSpan()
    
    def start_span(self, name: str, **kwargs):
        return NoOpSpan()


class NoOpSpan:
    """No-op span for when OTel is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    
    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass
    
    def record_exception(self, exception: Exception) -> None:
        pass
    
    def end(self) -> None:
        pass


class NoOpMeter:
    """No-op meter for when OTel is not available."""
    
    def create_counter(self, name: str, **kwargs):
        return NoOpCounter()
    
    def create_histogram(self, name: str, **kwargs):
        return NoOpHistogram()
    
    def create_gauge(self, name: str, **kwargs):
        return NoOpGauge()


class NoOpCounter:
    def add(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class NoOpHistogram:
    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class NoOpGauge:
    def set(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass