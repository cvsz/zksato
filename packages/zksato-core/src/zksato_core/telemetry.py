"""Trading telemetry events for zksato."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

try:
    from opentelemetry import trace
except ImportError:
    trace = None  # type: ignore[assignment]

from zksato_core.ids import new_ulid


class TradingEventType(StrEnum):
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

    event_id: str = field(default_factory=lambda: str(new_ulid()))
    event_type: TradingEventType = TradingEventType.ORDER_PLACED
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    account_id: str = ""
    correlation_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for logging/export."""
        data: dict[str, object] = {
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


def _safe_side(value: object) -> str:
    """Safely extract side value from an enum or string."""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


class LoggingTelemetryExporter:
    """Exports telemetry events to structured logging."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("zksato.telemetry")

    async def export(self, event: TradingEvent) -> None:
        self.logger.info("trading_event", extra=event.to_dict())


class TelemetryLogger:
    """Logs trading events with OpenTelemetry integration."""

    def __init__(self, exporter: TelemetryExporter | None = None) -> None:
        self.exporter = exporter or LoggingTelemetryExporter()
        self._otel_available = False
        self.tracer: Any = None
        if trace is not None:
            self.tracer = trace.get_tracer("zksato.telemetry")
            self._otel_available = True

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

    async def log_order_placed(self, order: object, result: object) -> None:
        """Log order placed event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.ORDER_PLACED,
                account_id=getattr(order, "account_id", ""),
                correlation_id=getattr(order, "correlation_id", None),
                payload={
                    "order_id": str(getattr(result, "order_id", "")),
                    "symbol": getattr(order, "symbol", ""),
                    "side": _safe_side(getattr(order, "side", "")),
                    "quantity": getattr(order, "quantity", 0),
                    "price": getattr(order, "price", 0),
                },
            )
        )

    async def log_order_filled(self, order: object, fill: object) -> None:
        """Log order filled event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.ORDER_FILLED,
                account_id=getattr(order, "account_id", ""),
                correlation_id=getattr(order, "correlation_id", None),
                payload={
                    "order_id": str(getattr(order, "id", "")),
                    "fill_id": str(getattr(fill, "id", "")),
                    "symbol": getattr(order, "symbol", ""),
                    "side": _safe_side(getattr(order, "side", "")),
                    "quantity": getattr(fill, "quantity", 0),
                    "price": getattr(fill, "price", 0),
                },
            )
        )

    async def log_order_rejected(self, order: object, reason: str) -> None:
        """Log order rejected event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.ORDER_REJECTED,
                account_id=getattr(order, "account_id", ""),
                correlation_id=getattr(order, "correlation_id", None),
                payload={
                    "order_id": str(getattr(order, "id", "")),
                    "symbol": getattr(order, "symbol", ""),
                    "reason": reason,
                },
            )
        )

    async def log_risk_check(self, context: object, result: object) -> None:
        """Log risk check event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.RISK_CHECK,
                account_id=getattr(context, "account_id", ""),
                correlation_id=getattr(context, "correlation_id", None),
                payload={
                    "allowed": getattr(result, "allowed", False),
                    "reason": getattr(result, "reason", ""),
                    "checks": [str(c) for c in getattr(result, "checks", [])],
                },
            )
        )

    async def log_approval_requested(self, order: object, request: object) -> None:
        """Log approval requested event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.APPROVAL_REQUESTED,
                account_id=getattr(order, "account_id", ""),
                correlation_id=getattr(order, "correlation_id", None),
                payload={
                    "order_id": str(getattr(order, "id", "")),
                    "symbol": getattr(order, "symbol", ""),
                    "request_id": str(getattr(request, "id", "")),
                },
            )
        )

    async def log_approval_granted(self, request: object) -> None:
        """Log approval granted event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.APPROVAL_GRANTED,
                account_id="",
                payload={
                    "request_id": str(getattr(request, "id", "")),
                    "approver": getattr(request, "approver", ""),
                },
            )
        )

    async def log_approval_denied(self, request: object, reason: str) -> None:
        """Log approval denied event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.APPROVAL_DENIED,
                account_id="",
                payload={
                    "request_id": str(getattr(request, "id", "")),
                    "reason": reason,
                },
            )
        )

    async def log_position_opened(self, position: object) -> None:
        """Log position opened event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.POSITION_OPENED,
                account_id=getattr(position, "account_id", ""),
                payload={
                    "symbol": getattr(position, "symbol", ""),
                    "quantity": getattr(position, "quantity", 0),
                    "side": _safe_side(getattr(position, "side", "")),
                },
            )
        )

    async def log_position_closed(self, position: object, pnl: float) -> None:
        """Log position closed event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.POSITION_CLOSED,
                account_id=getattr(position, "account_id", ""),
                payload={
                    "symbol": getattr(position, "symbol", ""),
                    "pnl": pnl,
                },
            )
        )

    async def log_pnl_realized(self, account_id: str, symbol: str, pnl: float) -> None:
        """Log realized P&L event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.PNL_REALIZED,
                account_id=account_id,
                payload={"symbol": symbol, "pnl": pnl},
            )
        )

    async def log_kill_switch_activated(self, account_id: str, reason: str) -> None:
        """Log kill switch activated event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.KILL_SWITCH_ACTIVATED,
                account_id=account_id,
                payload={"reason": reason},
            )
        )

    async def log_market_data_stale(self, symbol: str, last_update: datetime) -> None:
        """Log market data stale event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.MARKET_DATA_STALE,
                payload={"symbol": symbol, "last_update": last_update.isoformat()},
            )
        )

    async def log_broker_connected(self, broker: str) -> None:
        """Log broker connected event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.BROKER_CONNECTED,
                payload={"broker": broker},
            )
        )

    async def log_broker_disconnected(self, broker: str, reason: str) -> None:
        """Log broker disconnected event."""
        await self.log(
            TradingEvent(
                event_type=TradingEventType.BROKER_DISCONNECTED,
                payload={"broker": broker, "reason": reason},
            )
        )
