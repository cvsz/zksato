"""CCXT multi-exchange adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from zksato_core.types import Side, OrderType, OrderStatus
from zksato_core.models import OrderIntent, OrderRecord, PortfolioSnapshot, Position
from zksato_core.config import Settings
from zksato_broker.base import BaseBroker, BrokerConfig, BrokerCapabilities, BrokerAmbiguousError
from zksato_broker.errors import classify_error


class CCXTBroker(BaseBroker):
    """CCXT multi-exchange adapter with ambiguous-outcome normalization."""
    
    def __init__(self, config: BrokerConfig, settings: Settings) -> None:
        super().__init__(config)
        self.settings = settings
        self._exchanges: dict[str, Any] = {}
        self._exchange_not_available = Exception
        self._network_error = Exception
    
    @property
    def capabilities(self) -> set[BrokerCapabilities]:
        caps = {
            BrokerCapabilities.CRYPTO_SPOT,
            BrokerCapabilities.CRYPTO_FUTURES,
            BrokerCapabilities.MARKET_ORDERS,
            BrokerCapabilities.LIMIT_ORDERS,
            BrokerCapabilities.STOP_ORDERS,
            BrokerCapabilities.POSITION_TRACKING,
            BrokerCapabilities.ACCOUNT_BALANCE,
            BrokerCapabilities.ORDER_HISTORY,
            BrokerCapabilities.REALTIME_QUOTES,
            BrokerCapabilities.WEBSOCKET_STREAMS,
        }
        if self.config.sandbox:
            caps.add(BrokerCapabilities.SANDBOX_MODE)
        return caps
    
    async def _do_connect(self) -> None:
        if not self.settings.ccxt_configured:
            raise RuntimeError("CCXT is not configured")
        
        try:
            import ccxt
        except ImportError as exc:
            raise RuntimeError("ccxt is required for CCXTBroker") from exc
        
        self._exchange_not_available = getattr(ccxt, "ExchangeNotAvailable", Exception)
        self._network_error = getattr(ccxt, "NetworkError", Exception)
        
        for exchange_id in self.settings.ccxt_exchange_list:
            cls = getattr(ccxt, exchange_id, None)
            if cls is None:
                continue
            api_key, secret, passphrase = self.settings.ccxt_credentials_for(exchange_id)
            config: dict[str, Any] = {
                "apiKey": api_key,
                "secret": secret,
                "enableRateLimit": True,
            }
            if passphrase:
                config["password"] = passphrase
            if self.settings.ccxt_sandbox:
                config["options"] = {"defaultType": "spot", "adjustForTimeDifference": True}
                if hasattr(cls, "set_sandbox_mode"):
                    instance = cls(config)
                    instance.set_sandbox_mode(True)
                else:
                    instance = cls(config)
                self._exchanges[exchange_id] = instance
            else:
                self._exchanges[exchange_id] = cls(config)
    
    async def _do_disconnect(self) -> None:
        for exchange in self._exchanges.values():
            if hasattr(exchange, "close"):
                await exchange.close()
        self._exchanges.clear()
    
    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        if intent.side not in {Side.BUY, Side.SELL}:
            raise ValueError(f"CCXTBroker requires BUY/SELL side, got {intent.side.value}")
        exchange_id = self._resolve_exchange(intent.symbol)
        exchange = self._exchanges.get(exchange_id)
        if exchange is None:
            raise RuntimeError(f"No CCXT exchange configured for {intent.symbol}")
        ccxt_side = "buy" if intent.side == Side.BUY else "sell"
        order_type = "limit" if intent.order_type == OrderType.LIMIT else "market"
        params: dict[str, Any] = {}
        if intent.client_order_id:
            params["clientOrderId"] = intent.client_order_id
        try:
            raw = exchange.create_order(
                symbol=intent.symbol,
                type=order_type,
                side=ccxt_side,
                amount=intent.quantity,
                price=intent.price if order_type == "limit" else None,
                params=params,
            )
        except self._exchange_not_available as exc:
            raise RuntimeError(f"exchange unavailable: {exc}") from exc
        except self._network_error as exc:
            raise BrokerAmbiguousError(f"CCXT {exchange_id} order response ambiguous: {exc}") from exc
        except Exception as exc:
            classified = classify_error(exc, f"ccxt.{exchange_id}")
            if classified.category in ("transient", "rate_limited"):
                raise BrokerAmbiguousError(f"CCXT {exchange_id} order placement outcome ambiguous: {exc}") from exc
            raise
        
        return self._map_order(raw, intent=intent, exchange_id=exchange_id)
    
    async def cancel_order(self, order_id: str) -> OrderRecord:
        exchange_id, native_order_id = self._parse_order_id(order_id)
        exchange = self._exchanges.get(exchange_id)
        if exchange is None:
            raise RuntimeError(f"No CCXT exchange found for {exchange_id}")
        try:
            raw = exchange.cancel_order(native_order_id)
        except (self._network_error, self._exchange_not_available) as exc:
            raise BrokerAmbiguousError(f"ambiguous cancel for order {order_id}: {exc}") from exc
        except Exception as exc:
            classified = classify_error(exc, f"ccxt.{exchange_id}")
            if classified.category in ("transient", "rate_limited"):
                raise BrokerAmbiguousError(f"ambiguous cancel for order {order_id}: {exc}") from exc
            raise RuntimeError(f"CCXT cancel failed for {order_id}: {exc}") from exc
        return self._map_order(raw, exchange_id=exchange_id)
    
    async def list_orders(self, status: OrderStatus | None = None) -> list[OrderRecord]:
        records: list[OrderRecord] = []
        for exchange_id, exchange in self._exchanges.items():
            try:
                orders = exchange.fetch_open_orders()
            except (self._network_error, self._exchange_not_available):
                continue
            for raw in orders or []:
                records.append(self._map_order(raw, exchange_id=exchange_id))
        if status:
            records = [r for r in records if r.status == status]
        return records
    
    async def get_positions(self) -> list[Position]:
        snap = await self.get_portfolio()
        return snap.positions
    
    async def get_account(self) -> dict[str, Any]:
        total_cash = 0.0
        for exchange in self._exchanges.values():
            try:
                balance = exchange.fetch_balance()
                currency_balances = balance.get("total", {}) if isinstance(balance, dict) else {}
                for currency, amount in currency_balances.items():
                    if currency in ("USDT", "BUSD", "USD", "USDC"):
                        total_cash += float(amount or 0)
            except (self._network_error, self._exchange_not_available):
                continue
        return {"cash": total_cash}
    
    async def get_portfolio(self) -> PortfolioSnapshot:
        total_cash = 0.0
        total_market_value = 0.0
        positions: list[Position] = []
        
        for exchange_id, exchange in self._exchanges.items():
            try:
                balance = exchange.fetch_balance()
                tickers = exchange.fetch_tickers()
            except (self._network_error, self._exchange_not_available):
                continue
            
            currency_balances = balance.get("total", {}) if isinstance(balance, dict) else {}
            for currency, amount in currency_balances.items():
                if currency in ("USDT", "BUSD", "USD", "USDC"):
                    total_cash += float(amount or 0)
            
            for symbol, ticker in (tickers or {}).items():
                if "/" not in symbol:
                    continue
                base = symbol.split("/")[0]
                free = float(balance.get("free", {}).get(base, 0) or 0)
                if free <= 0:
                    continue
                last = float(ticker.get("last", 0) or 0)
                value = free * last
                total_market_value += value
                positions.append(
                    Position(
                        symbol=symbol,
                        quantity=float(free),
                        average_price=last,
                        market_price=last,
                        market_value=value,
                        cost_value=value,
                        unrealized_pnl=0.0,
                        unrealized_pnl_pct=0.0,
                    )
                )
        
        equity = total_cash + total_market_value
        return PortfolioSnapshot(
            cash=total_cash,
            market_value=total_market_value,
            equity=equity,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            daily_pnl=0.0,
            positions=positions,
        )
    
    def _resolve_exchange(self, symbol: str) -> str:
        for exchange_id in self.settings.ccxt_exchange_list:
            try:
                market = self._exchanges[exchange_id].market(symbol)
                if market:
                    return exchange_id
            except (Exception, AttributeError):
                continue
        return self.settings.ccxt_exchange_list[0]
    
    @staticmethod
    def _parse_order_id(order_id: str) -> tuple[str, str]:
        if ":" in order_id:
            exchange_id, client_order_id = order_id.split(":", 1)
            return exchange_id, client_order_id
        return "binance", order_id
    
    def _map_order(
        self,
        payload: dict[str, Any],
        intent: OrderIntent | None = None,
        *,
        exchange_id: str,
    ) -> OrderRecord:
        raw_side = str(payload.get("side", intent.side.value if intent else "buy")).lower()
        side = Side.BUY if raw_side == "buy" else Side.SELL
        raw_type = str(payload.get("type", "limit")).lower()
        order_type = OrderType.LIMIT if raw_type == "limit" else OrderType.MARKET
        quantity = float(payload.get("amount", intent.quantity if intent else 0) or 0)
        filled = float(payload.get("filled", payload.get("cost", 0)) or 0)
        raw_status = str(payload.get("status", "open")).lower()
        status = self._status(raw_status, quantity, filled)
        now = datetime.now(UTC)
        return OrderRecord(
            broker_order_id=f"{exchange_id}:{payload.get('id', '')}",
            client_order_id=intent.client_order_id if intent else None,
            symbol=str(payload.get("symbol", intent.symbol if intent else "")),
            side=side,
            quantity=quantity,
            filled_quantity=filled,
            order_type=order_type,
            price=float(payload.get("price", intent.price if intent else 0) or 0) or None,
            average_fill_price=float(payload.get("average", 0) or 0) or None,
            stop_loss=intent.stop_loss if intent else None,
            take_profit=intent.take_profit if intent else None,
            status=status,
            source=intent.source if intent else f"ccxt.{exchange_id}",
            message=str(payload.get("info", "")) or None,
            created_at=now,
            updated_at=now,
        )
    
    @staticmethod
    def _status(raw: str, quantity: float, filled: float) -> OrderStatus:
        if "cancel" in raw or raw == "canceled":
            return OrderStatus.CANCELLED
        if "reject" in raw or raw == "rejected":
            return OrderStatus.REJECTED
        if filled and filled >= quantity:
            return OrderStatus.FILLED
        if filled:
            return OrderStatus.PARTIALLY_FILLED
        return OrderStatus.ACCEPTED