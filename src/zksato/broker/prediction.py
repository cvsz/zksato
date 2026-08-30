from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from zksato.broker.base import BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import (
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderType,
    PortfolioSnapshot,
    Position,
    Side,
)


class PredictionMarketClient(Protocol):
    """Pluggable prediction market venue client."""

    async def create_order(
        self, market_id: str, side: str, amount_usd: float, price: float
    ) -> dict[str, Any]: ...
    async def cancel_order(self, order_id: str) -> dict[str, Any]: ...
    async def fetch_open_orders(self, market_id: str) -> list[dict[str, Any]]: ...
    async def fetch_balance(self) -> dict[str, Any]: ...


class PredictionBroker:
    """Prediction-market broker adapter with complete-set settlement tracking."""

    def __init__(self, settings: Settings, client: PredictionMarketClient | None = None) -> None:
        if not settings.prediction_enabled:
            raise RuntimeError("Prediction market is not enabled")
        self.settings = settings
        self._client = client or self._default_client()
        self._directional_residual: dict[str, float] = {}
        self._complete_set_cost: dict[str, float] = {}

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        if intent.side not in {Side.UP, Side.DOWN}:
            raise ValueError("prediction broker requires UP or DOWN side")
        if intent.price is None or not (0.0 < float(intent.price) < 1.0):
            raise ValueError("prediction order requires price between 0 and 1")
        amount_usd = intent.price * intent.quantity
        if amount_usd > self.settings.prediction_max_order_usd:
            raise ValueError("prediction order exceeds configured per-order USD limit")
        market_id = intent.symbol
        side_str = "UP" if intent.side == Side.UP else "DOWN"
        try:
            response = await self._client.create_order(
                market_id, side_str, amount_usd, float(intent.price)
            )
        except (TimeoutError, ConnectionError, OSError) as exc:
            raise BrokerAmbiguousError("prediction market order response ambiguous") from exc
        record = self._map_fill(response, intent=intent)
        self._update_residual_and_cost(market_id, intent.side, intent.quantity, amount_usd)
        return record

    async def cancel_order(self, order_id: str) -> OrderRecord:
        try:
            response = await self._client.cancel_order(order_id)
        except (TimeoutError, ConnectionError, OSError) as exc:
            raise BrokerAmbiguousError("prediction market cancel response ambiguous") from exc
        intent = OrderIntent(
            symbol=str(response.get("market_id", "UNKNOWN")),
            side=Side.UP if str(response.get("side", "UP")).upper() == "UP" else Side.DOWN,
            quantity=int(float(response.get("amount", 1)) or 1),
            order_type=OrderType.LIMIT,
            price=float(response.get("price", 0) or 0),
            source="prediction.cancel",
        )
        record = self._map_fill(response, intent=intent)
        record.status = OrderStatus.CANCELLED
        return record

    async def list_orders(self) -> list[OrderRecord]:
        records: list[OrderRecord] = []
        for market_id in self._directional_residual:
            try:
                orders = await self._client.fetch_open_orders(market_id)
            except (TimeoutError, ConnectionError, OSError):
                continue
            for order in orders or []:
                records.append(self._map_fill(order))
        return records

    async def portfolio(self) -> PortfolioSnapshot:
        try:
            balance = await self._client.fetch_balance()
        except (TimeoutError, ConnectionError, OSError):
            balance = {}
        cash = float(balance.get("cash", 0) or 0)
        positions: list[Position] = []
        for market_id, residual in self._directional_residual.items():
            if residual <= 0:
                continue
            positions.append(
                Position(
                    symbol=market_id,
                    quantity=int(residual),
                    average_price=0.0,
                    market_price=0.0,
                    market_value=0.0,
                    cost_value=self._complete_set_cost.get(market_id, 0.0),
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                )
            )
        return PortfolioSnapshot(
            cash=cash,
            market_value=0.0,
            equity=cash,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            daily_pnl=0.0,
            positions=positions,
        )

    def _update_residual_and_cost(
        self, market_id: str, side: Side, shares: float, cost: float
    ) -> None:
        current_residual = self._directional_residual.get(market_id, 0.0)
        self._directional_residual[market_id] = current_residual + shares
        current_cost = self._complete_set_cost.get(market_id, 0.0)
        self._complete_set_cost[market_id] = current_cost + cost

    def directional_residual(self, market_id: str) -> float:
        return abs(self._directional_residual.get(market_id, 0.0))

    def complete_set_cost(self, market_id: str) -> float:
        return self._complete_set_cost.get(market_id, 0.0)

    def _default_client(self) -> PredictionMarketClient:
        from zksato.prediction.broker import PaperPredictionBroker

        return PaperPredictionBroker(self.settings)

    def _map_fill(self, payload: dict[str, Any], intent: OrderIntent | None = None) -> OrderRecord:
        side = Side.UP if str(payload.get("side", "UP")).upper() == "UP" else Side.DOWN
        quantity = float(payload.get("amount", intent.quantity if intent else 0) or 0)
        price = float(payload.get("price", intent.price if intent else 0) or 0)
        raw_status = str(payload.get("status", "open")).lower()
        status = OrderStatus.ACCEPTED
        if "fill" in raw_status:
            status = OrderStatus.FILLED
        elif "cancel" in raw_status:
            status = OrderStatus.CANCELLED
        elif "reject" in raw_status:
            status = OrderStatus.REJECTED
        now = datetime.now(UTC)
        return OrderRecord(
            broker_order_id=str(payload.get("id", payload.get("order_id", ""))) or None,
            client_order_id=intent.client_order_id if intent else None,
            symbol=str(
                payload.get("market_id", payload.get("symbol", intent.symbol if intent else ""))
            ),
            side=side,
            quantity=quantity,
            filled_quantity=quantity if status == OrderStatus.FILLED else 0,
            order_type=OrderType.LIMIT,
            price=price,
            average_fill_price=price if status == OrderStatus.FILLED else None,
            stop_loss=intent.stop_loss if intent else None,
            take_profit=intent.take_profit if intent else None,
            status=status,
            source=intent.source if intent else "prediction",
            message=str(payload.get("error", "")) or None,
            created_at=now,
            updated_at=now,
        )
