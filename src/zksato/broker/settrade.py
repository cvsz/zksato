from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

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


class SettradeBroker:
    """Settrade Open API v2 equity adapter with ambiguous-outcome normalization."""

    def __init__(self, settings: Settings) -> None:
        if not settings.settrade_configured:
            raise RuntimeError("Settrade credentials are incomplete")
        self.settings = settings
        try:
            from settrade_v2 import Investor  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("install zksato[settrade] to use Settrade mode") from exc

        self._investor = Investor(
            app_id=settings.settrade_app_id,
            app_secret=settings.settrade_app_secret,
            broker_id=settings.settrade_broker_id,
            app_code=settings.settrade_app_code,
            is_auto_queue=False,
        )
        self._equity = self._investor.Equity(account_no=settings.settrade_account_no)

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        price_type = "Limit" if intent.order_type == OrderType.LIMIT else "MP-MKT"
        price = float(intent.price or 0)
        try:
            payload = await asyncio.to_thread(
                self._equity.place_order,
                pin=self.settings.settrade_pin,
                side="Buy" if intent.side == Side.BUY else "Sell",
                symbol=intent.symbol,
                trustee_id_type="Local",
                volume=intent.quantity,
                qty_open=0,
                price=price,
                price_type=price_type,
                validity_type="Day",
                bypass_warning=False,
                valid_till_date="",
            )
        except (TimeoutError, ConnectionError) as exc:
            raise BrokerAmbiguousError("Settrade order response timed out") from exc
        return self._map_order(payload, intent=intent)

    async def cancel_order(self, order_id: str) -> OrderRecord:
        cancel = getattr(self._equity, "cancel_order", None)
        if cancel is None:
            raise RuntimeError("installed Settrade SDK does not expose cancel_order")
        try:
            payload = await asyncio.to_thread(
                cancel,
                order_no=order_id,
                pin=self.settings.settrade_pin,
            )
        except (TimeoutError, ConnectionError) as exc:
            raise BrokerAmbiguousError("Settrade cancel response timed out") from exc
        intent = OrderIntent(
            symbol=str(payload.get("symbol", "UNKNOWN")),
            side=Side.BUY if str(payload.get("side", "Buy")).lower() == "buy" else Side.SELL,
            quantity=int(payload.get("vol", payload.get("volume", 1)) or 1),
            order_type=OrderType.LIMIT,
            price=float(payload.get("price", 0) or 1),
            source="settrade.cancel",
        )
        record = self._map_order(payload, intent=intent)
        record.status = OrderStatus.CANCELLED
        return record

    async def list_orders(self) -> list[OrderRecord]:
        rows = await asyncio.to_thread(self._equity.get_orders)
        return [self._map_order(row) for row in rows or []]

    async def portfolio(self) -> PortfolioSnapshot:
        account = await asyncio.to_thread(self._equity.get_account_info)
        get_portfolios = getattr(self._equity, "get_portfolios", None)
        rows = await asyncio.to_thread(get_portfolios) if get_portfolios else []
        positions: list[Position] = []
        market_value = 0.0
        unrealized = 0.0
        for row in rows or []:
            quantity = int(row.get("currentVolume", row.get("actualVolume", 0)) or 0)
            if quantity <= 0:
                continue
            average = float(row.get("averagePrice", 0) or 0)
            market_price = float(row.get("marketPrice", average) or average)
            value = float(row.get("marketValue", market_price * quantity) or 0)
            cost = average * quantity
            pnl = float(row.get("profit", value - cost) or 0)
            market_value += value
            unrealized += pnl
            positions.append(
                Position(
                    symbol=str(row.get("symbol", "")),
                    quantity=quantity,
                    average_price=average,
                    market_price=market_price,
                    market_value=value,
                    cost_value=cost,
                    unrealized_pnl=pnl,
                    unrealized_pnl_pct=(pnl / cost * 100) if cost else 0.0,
                )
            )
        cash = float(account.get("cashBalance", account.get("cash_balance", 0)) or 0)
        equity = float(account.get("equity", cash + market_value) or (cash + market_value))
        return PortfolioSnapshot(
            cash=cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=0.0,
            unrealized_pnl=unrealized,
            daily_pnl=0.0,
            positions=positions,
        )

    def _map_order(
        self,
        payload: dict[str, Any],
        intent: OrderIntent | None = None,
    ) -> OrderRecord:
        raw_side = str(payload.get("side", intent.side.value if intent else "Buy")).lower()
        side = Side.BUY if raw_side == "buy" else Side.SELL
        raw_type = str(payload.get("priceType", "Limit")).lower()
        order_type = OrderType.LIMIT if raw_type == "limit" else OrderType.MARKET
        quantity = int(
            payload.get(
                "vol",
                payload.get("volume", intent.quantity if intent else 0),
            )
            or 0
        )
        matched = int(payload.get("matched", payload.get("matchedQty", 0)) or 0)
        raw_status = str(payload.get("status", payload.get("showOrderStatus", ""))).lower()
        status = self._status(raw_status, quantity, matched)
        now = datetime.now(UTC)
        return OrderRecord(
            broker_order_id=str(payload.get("orderNo", payload.get("setOrderNo", ""))) or None,
            client_order_id=intent.client_order_id if intent else None,
            symbol=str(payload.get("symbol", intent.symbol if intent else "")),
            side=side,
            quantity=quantity,
            filled_quantity=matched,
            order_type=order_type,
            price=float(payload.get("price", intent.price if intent else 0) or 0) or None,
            average_fill_price=None,
            stop_loss=intent.stop_loss if intent else None,
            take_profit=intent.take_profit if intent else None,
            status=status,
            source=intent.source if intent else "settrade",
            message=str(payload.get("rejectReason", "")) or None,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _status(raw: str, quantity: int, matched: int) -> OrderStatus:
        if "cancel" in raw or raw in {"c", "e"}:
            return OrderStatus.CANCELLED
        if "reject" in raw or raw == "r":
            return OrderStatus.REJECTED
        if matched and matched >= quantity:
            return OrderStatus.FILLED
        if matched:
            return OrderStatus.PARTIALLY_FILLED
        return OrderStatus.ACCEPTED
