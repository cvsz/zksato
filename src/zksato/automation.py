from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from zksato.config import Settings
from zksato.domain import (
    BotConfig,
    BotState,
    BotStatus,
    OrderIntent,
    OrderStatus,
    OrderSubmission,
    OrderType,
    Quote,
    RiskContext,
    Side,
    SignalAction,
)
from zksato.service import RiskRejectedError, TradingModeError, TradingService
from zksato.store import StateStore
from zksato.strategy import StrategyEngine


class AutomationEngine:
    def __init__(
        self,
        settings: Settings,
        store: StateStore,
        service: TradingService,
    ) -> None:
        self.settings = settings
        self.store = store
        self.service = service
        self.strategy = StrategyEngine()
        self.status = BotStatus()
        self._last_action: dict[str, datetime] = {}

    def start(self, config: BotConfig) -> BotStatus:
        if not config.symbols:
            config.symbols = self.settings.watchlist
        self.status = BotStatus(state=BotState.RUNNING, config=config)
        self.store.add_audit(
            "bot.started",
            f"automation started for {', '.join(config.symbols)}",
            {"strategy": config.strategy.name, "auto_execute": config.auto_execute},
        )
        return self.status

    def stop(self) -> BotStatus:
        self.status.state = BotState.STOPPED
        self.store.add_audit("bot.stopped", "automation stopped")
        return self.status

    async def on_quote(self, quote: Quote) -> None:
        stored = self.store.update_quote(quote)
        if stored.timestamp != quote.timestamp:
            self.store.add_audit(
                "market.out_of_order",
                f"ignored out-of-order quote for {quote.symbol}",
            )
            return
        await self._check_alerts(quote)
        await self._check_protective_exits(quote)
        if self.status.state != BotState.RUNNING or not self.status.config:
            return
        if quote.symbol not in self.status.config.symbols:
            return
        await self._evaluate_symbol(quote.symbol)

    async def tick(self) -> BotStatus:
        self.status.last_tick_at = datetime.now(UTC)
        if self.status.state != BotState.RUNNING or not self.status.config:
            return self.status
        for symbol in self.status.config.symbols:
            if self.store.get_quote(symbol):
                await self._evaluate_symbol(symbol)
        return self.status

    async def _evaluate_symbol(self, symbol: str) -> None:
        config = self.status.config
        if config is None:
            return
        prices = self.store.get_prices(symbol)
        if not prices:
            return
        signal = self.strategy.evaluate(symbol, prices, config.strategy)
        if signal.action == SignalAction.HOLD:
            return
        if self._in_cooldown(symbol, config.cooldown_seconds):
            return
        self.store.add_signal(signal)
        self.status.signals_generated += 1
        self._last_action[symbol] = datetime.now(UTC)
        self.store.add_audit(
            "signal.generated",
            f"{signal.action.value.upper()} {symbol}: {signal.reason}",
            {"strategy": signal.strategy, "confidence": signal.confidence},
        )
        if not config.auto_execute:
            message = (
                f"zksato signal: {signal.action.value.upper()} "
                f"{symbol} {signal.price:.2f}"
            )
            await self._notify(message)
            return
        await self._execute_signal(signal.action, symbol, signal.price)

    async def _execute_signal(self, action: SignalAction, symbol: str, price: float) -> None:
        config = self.status.config
        if config is None:
            return
        portfolio = await self.service.portfolio()
        existing = next(
            (position for position in portfolio.positions if position.symbol == symbol),
            None,
        )
        if action == SignalAction.SELL:
            if not existing or existing.quantity <= 0:
                return
            side = Side.SELL
            quantity = min(config.order_size, existing.quantity)
            stop_loss = None
            take_profit = None
        else:
            if existing and existing.quantity > 0:
                return
            side = Side.BUY
            quantity = config.order_size
            stop_loss = price * (1 - config.stop_loss_pct / 100)
            take_profit = price * (1 + config.take_profit_pct / 100)

        context = self._risk_context(portfolio, symbol, price, quantity)
        submission = OrderSubmission(
            intent=OrderIntent(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                price=None,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_order_id=f"bot-{uuid4()}",
                source=f"bot:{config.strategy.name}",
            ),
            risk=context,
        )
        try:
            order = await self.service.submit(submission, automated=True)
        except (RiskRejectedError, TradingModeError, ValueError) as exc:
            self.status.last_error = str(exc)
            self.store.add_audit("bot.execution_blocked", str(exc), {"symbol": symbol})
            return
        self.status.orders_submitted += 1
        await self._notify(
            f"zksato {self.settings.trading_mode}: {side.value.upper()} "
            f"{quantity} {symbol} status={order.status.value}"
        )

    def _risk_context(
        self,
        portfolio: object,
        symbol: str,
        price: float,
        quantity: int,
    ) -> RiskContext:
        positions = getattr(portfolio, "positions", [])
        equity = float(getattr(portfolio, "equity", 0) or 0)
        cash = float(getattr(portfolio, "cash", 0) or 0)
        notional = price * quantity
        existing_value = sum(
            float(getattr(position, "market_value", 0) or 0)
            for position in positions
            if getattr(position, "symbol", "") == symbol
        )
        gross_value = sum(float(getattr(item, "market_value", 0) or 0) for item in positions)
        position_pct = ((existing_value + notional) / equity * 100) if equity else 100.0
        gross_pct = ((gross_value + notional) / equity * 100) if equity else 100.0
        symbol_pct = ((existing_value + notional) / equity * 100) if equity else 100.0
        daily_pnl = float(getattr(portfolio, "daily_pnl", 0) or 0)
        daily_pnl_pct = (daily_pnl / equity * 100) if equity else 0.0
        drawdown = 0.0
        account = getattr(self.service.broker, "account", None)
        if account is not None and hasattr(account, "drawdown_pct"):
            drawdown = float(account.drawdown_pct())
        orders = self.store.list_orders()
        open_statuses = {
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.NEEDS_RECONCILIATION,
        }
        today = datetime.now(UTC).date()
        orders_today = sum(item.created_at.date() == today for item in orders)
        open_orders = sum(item.status in open_statuses for item in orders)
        quote = self.store.get_quote(symbol)
        spread_pct: float | None = None
        if quote and quote.bid and quote.offer and quote.last:
            spread_pct = (quote.offer - quote.bid) / quote.last * 100
        return RiskContext(
            current_positions=len(positions),
            daily_pnl_pct=daily_pnl_pct,
            drawdown_pct=drawdown,
            position_pct_after_trade=min(position_pct, 100),
            line_available=cash,
            reference_price=price,
            orders_today=orders_today,
            open_orders=open_orders,
            portfolio_value=equity if equity > 0 else None,
            gross_exposure_pct=max(gross_pct, 0),
            symbol_exposure_pct=max(symbol_pct, 0),
            quote_age_seconds=self.store.quote_age_seconds(symbol),
            spread_pct=spread_pct,
        )

    async def _check_protective_exits(self, quote: Quote) -> None:
        if self.settings.trading_mode != "paper":
            return
        for order in list(self.store.orders):
            if order.side != Side.BUY or order.filled_quantity <= 0:
                continue
            account = getattr(self.service.broker, "account", None)
            if account is None or not account.can_sell(order.symbol, order.filled_quantity):
                continue
            exit_reason: str | None = None
            if order.stop_loss and quote.last <= order.stop_loss:
                exit_reason = "stop_loss"
            elif order.take_profit and quote.last >= order.take_profit:
                exit_reason = "take_profit"
            if not exit_reason:
                continue
            submission = OrderSubmission(
                intent=OrderIntent(
                    symbol=order.symbol,
                    side=Side.SELL,
                    quantity=order.filled_quantity,
                    order_type=OrderType.MARKET,
                    source=f"protective:{exit_reason}",
                    client_order_id=f"exit-{order.id}-{exit_reason}",
                ),
                risk=RiskContext(
                    reference_price=quote.last,
                    quote_age_seconds=self.store.quote_age_seconds(order.symbol),
                ),
            )
            try:
                await self.service.submit(submission, automated=True)
            except (RiskRejectedError, TradingModeError, ValueError) as exc:
                self.store.add_audit(
                    "protective_exit.failed",
                    str(exc),
                    {"symbol": order.symbol},
                )
                continue
            self.store.add_audit(
                "protective_exit.executed",
                f"{exit_reason} closed {order.symbol} at {quote.last:.2f}",
            )

    async def _check_alerts(self, quote: Quote) -> None:
        for alert in self.store.list_alerts():
            if not alert.enabled or alert.symbol != quote.symbol:
                continue
            triggered = alert.operator == "gte" and quote.last >= alert.price
            triggered = triggered or (alert.operator == "lte" and quote.last <= alert.price)
            if triggered:
                alert.enabled = False
                self.store.add_alert(alert)
                message = f"price alert {quote.symbol} {alert.operator} {alert.price:.2f}"
                self.store.add_audit("alert.triggered", message, {"last": quote.last})
                await self._notify(message)

    def _in_cooldown(self, symbol: str, seconds: int) -> bool:
        previous = self._last_action.get(symbol)
        if not previous or seconds <= 0:
            return False
        return datetime.now(UTC) - previous < timedelta(seconds=seconds)

    async def _notify(self, message: str) -> None:
        if not self.settings.notification_webhook_url:
            return
        self.store.enqueue_outbox(
            "notification.webhook",
            {"text": message, "source": "zksato"},
        )
