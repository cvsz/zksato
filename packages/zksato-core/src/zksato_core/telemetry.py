"""Trading telemetry events for zksato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from zksato_core.ids import new_ulid


class TradingEventType(str, Enum):
    """Types of trading events."""
    
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_REJECTED = "order.rejected"
    ORDER_CANCELLED = "order.cancelled"
    RISK_CHECK = "risk.check"
    RISK_OVERRIDE = "risk.override"
    RECONCILIATION_DRIFT = "reconciliation.drift"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    PNL_REALIZED = "pnl.realized"
    KILL_SWITCH_ACTIVATED = "kill_switch.activated"
    MARKET_DATA_STALE = "market_data.stale"
    BROKER_CONNECTED = "broker.connected"
    BROKER_DISCONNECTED = "broker.disconnected"


@dataclass
class TradingEvent:
    """Trading event for telemetry and audit."""
    
    event_id: UUID = field(default_factory=new_ulid)
    event_type: TradingEventType = TradingEventType.ORDER_PLACED
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    account_id: str = ""
    correlation_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/export."""
        data = {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "account_id": self.account_id,
            "payload": self.payload,
        }
        if self.correlation_id:
            data["correlation_id"] = str(self.correlation_id)
        return data


class TelemetryExporter(Protocol):
    """Protocol for telemetry exporters."""
    
    async def export(self, event: TradingEvent) -> None: ...


class LoggingTelemetryExporter:
    """Exports telemetry events to structured logging."""
    
    def __init__(self, logger: Any = None) -> None:
        import logging
        self.logger = logger or logging.getLogger("zksato.telemetry")
    
    async def export(self, event: TradingEvent) -> None:
        self.logger.info("trading_event", extra=event.to_dict())


class TelemetryLogger:
    """Logs trading events with OpenTelemetry integration."""
    
    def __init__(self, exporter: TelemetryExporter | None = None) -> None:
        self.exporter = exporter or LoggingTelemetryExporter()
        try:
            from opentelemetry import trace
            self.tracer = trace.get_tracer("zksato.telemetry")
            self._otel_available = True
        except ImportError:
            self.tracer = None
            self._otel_available = False
    
    async def log(self, event: TradingEvent) -> None:
        """Log a trading event."""
        # Structured logging
        await self.exporter.export(event)
        
        # OpenTelemetry span
        if self._otel_available and self.tracer:
            with self.tracer.start_as_current_span(f"trading.{event.event_type.value}") as span:
                span.set_attribute("account_id", event.account_id)
                span.set_attribute("event_type", event.event_type.value)
                if event.correlation_id:
                    span.set_attribute("correlation_id", str(event.correlation_id))
                for k, v in event.payload.items():
                    span.set_attribute(f"payload.{k}", str(v))
    
    async def log_order_placed(self, order: Any, result: Any) -> None:
        """Log order placed event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.ORDER_PLACED,
            account_id=getattr(order, "account_id", ""),
            correlation_id=getattr(order, "correlation_id", None),
            payload={
                "order_id": str(getattr(result, "order_id", "")),
                "symbol": getattr(order, "symbol", ""),
                "side": getattr(order, "side", "").value if hasattr(getattr(order, "side", ""), "value") else str(getattr(order, "side", "")),
                "quantity": getattr(order, "quantity", 0),
                "price": getattr(order, "price", 0),
            },
        ))
    
    async def log_order_filled(self, order: Any, fill: Any) -> None:
        """Log order filled event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.ORDER_FILLED,
            account_id=getattr(order, "account_id", ""),
            correlation_id=getattr(order, "correlation_id", None),
            payload={
                "order_id": str(getattr(order, "id", "")),
                "fill_id": str(getattr(fill, "id", "")),
                "symbol": getattr(order, "symbol", ""),
                "side": getattr(order, "side", "").value if hasattr(getattr(order, "side", ""), "value") else str(getattr(order, "side", "")),
                "quantity": getattr(fill, "quantity", 0),
                "price": getattr(fill, "price", 0),
            },
        ))
    
    async def log_order_rejected(self, order: Any, reason: str) -> None:
        """Log order rejected event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.ORDER_REJECTED,
            account_id=getattr(order, "account_id", ""),
            correlation_id=getattr(order, "correlation_id", None),
            payload={
                "order_id": str(getattr(order, "id", "")),
                "symbol": getattr(order, "symbol", ""),
                "reason": reason,
            },
        ))
    
    async def log_risk_check(self, context: Any, result: Any) -> None:
        """Log risk check event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.RISK_CHECK,
            account_id=getattr(context, "account_id", ""),
            correlation_id=getattr(context, "correlation_id", None),
            payload={
                "allowed": getattr(result, "allowed", False),
                "reason": getattr(result, "reason", ""),
                "checks": [str(c) for c in getattr(result, "checks", [])],
            },
        ))
    
    async def log_approval_requested(self, order: Any, request: Any) -> None:
        """Log approval requested event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.APPROVAL_REQUESTED,
            account_id=getattr(order, "account_id", ""),
            correlation_id=getattr(order, "correlation_id", None),
            payload={
                "order_id": str(getattr(order, "id", "")),
                "request_id": str(getattr(request, "id", "")),
            },
        ))
    
    async def log_approval_granted(self, request: Any) -> None:
        """Log approval granted event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.APPROVAL_GRANTED,
            account_id="",
            payload={
                "request_id": str(getattr(request, "id", "")),
                "approver": getattr(request, "approver", ""),
            },
        ))
    
    async def log_approval_denied(self, request: Any, reason: str) -> None:
        """Log approval denied event."""
        await self.log(TradingEvent(
            event_type=TradingEventType.APPROVAL_DENIED,
            account_id="",
            payload={
                "request_id": str(getattr(request, "id", "")),
                "reason": reason,
            },
        ))