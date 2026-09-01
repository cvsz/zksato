from __future__ import annotations

from datetime import UTC, datetime

from zksato.approvals import ApprovalRepository
from zksato.broker.base import Broker, BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import (
    AccountSnapshot,
    OrderEvent,
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderSubmission,
    PortfolioSnapshot,
    RiskContext,
    RiskDecision,
    RiskEvaluation,
    Side,
)
from zksato.market_rules import InstrumentRegistry, MarketSessionPolicy
from zksato.observability import ORDER_SUBMISSIONS, RISK_REJECTIONS
from zksato.risk import RiskEngine
from zksato.store import StateStore

OPEN_ORDER_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.NEEDS_RECONCILIATION,
}
CANCELLABLE_ORDER_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
}


class RiskRejectedError(Exception):
    def __init__(self, decision: RiskDecision) -> None:
        super().__init__("order rejected by risk engine")
        self.decision = decision


class TradingModeError(Exception):
    pass


class TradingService:
    def __init__(
        self,
        settings: Settings,
        broker: Broker,
        store: StateStore,
        approvals: ApprovalRepository | None = None,
    ) -> None:
        self.settings = settings
        self.broker = broker
        self.store = store
        self.approvals = approvals
        self.risk_engine = RiskEngine(settings)
        self.instruments = InstrumentRegistry(settings.instrument_metadata_json)
        self.market_sessions = MarketSessionPolicy(
            settings.market_timezone,
            settings.equity_sessions,
            settings.equity_holidays,
            settings.equity_special_sessions_json,
        )

    def check_risk(self, submission: OrderSubmission) -> RiskDecision:
        return self.risk_engine.evaluate(submission.intent, submission.risk)

    async def risk_context_for(self, intent: OrderIntent) -> RiskContext:
        portfolio = await self.portfolio(record_snapshot=False)
        quote = self.store.get_quote(intent.symbol)
        reference_price = quote.last if quote is not None else None
        estimate_price = intent.price or reference_price or 0.0
        notional = estimate_price * intent.quantity
        equity = float(portfolio.equity or 0)
        existing = next(
            (position for position in portfolio.positions if position.symbol == intent.symbol),
            None,
        )
        existing_value = float(existing.market_value) if existing else 0.0
        holding_qty = float(existing.quantity) if existing else 0
        gross_value = sum(abs(float(position.market_value)) for position in portfolio.positions)
        net_value = sum(float(position.market_value) for position in portfolio.positions)
        if intent.side == Side.BUY:
            symbol_after = existing_value + notional
            gross_after = gross_value + notional
            net_after = net_value + notional
        else:
            reduction = min(existing_value, notional)
            symbol_after = max(0.0, existing_value - reduction)
            gross_after = max(0.0, gross_value - reduction)
            net_after = net_value - reduction
        position_pct = (symbol_after / equity * 100) if equity else 100.0
        gross_pct = (gross_after / equity * 100) if equity else 100.0
        net_pct = (net_after / equity * 100) if equity else 100.0
        symbol_pct = (symbol_after / equity * 100) if equity else 100.0
        sector_pct = self._sector_exposure_after_trade(intent, portfolio, notional, equity)
        daily_pnl_pct = (portfolio.daily_pnl / equity * 100) if equity else 0.0
        drawdown = 0.0
        account = getattr(self.broker, "account", None)
        if account is not None:
            drawdown_fn = getattr(account, "drawdown_pct", None)
            if callable(drawdown_fn):
                try:
                    drawdown = float(drawdown_fn())
                except (TypeError, ValueError):
                    drawdown = 0.0
        orders = self.store.list_orders()
        today = datetime.now(UTC).date()
        orders_today = sum(item.created_at.date() == today for item in orders)
        open_orders = sum(item.status in OPEN_ORDER_STATUSES for item in orders)
        spread_pct: float | None = None
        if quote and quote.bid and quote.offer and quote.last:
            spread_pct = (quote.offer - quote.bid) / quote.last * 100

        if self.settings.enforce_market_sessions:
            market_session_known, market_session_open = self.market_sessions.state()
        else:
            market_session_known, market_session_open = True, True
        metadata_known, price_band_ok, tick_size_ok = self.instruments.validate_price(
            intent.symbol,
            intent.price,
        )
        market_data_available = quote is not None
        if self.settings.strict_reference_data and not metadata_known:
            market_data_available = False

        return RiskContext(
            current_positions=len(portfolio.positions),
            daily_pnl_pct=daily_pnl_pct,
            drawdown_pct=drawdown,
            position_pct_after_trade=min(max(position_pct, 0.0), 100.0),
            line_available=max(float(portfolio.cash), 0.0),
            available_quantity=int(holding_qty) if holding_qty > 0 else 0,
            reference_price=reference_price,
            orders_today=orders_today,
            open_orders=open_orders,
            portfolio_value=equity if equity > 0 else None,
            gross_exposure_pct=max(gross_pct, 0.0),
            net_exposure_pct=net_pct,
            symbol_exposure_pct=max(symbol_pct, 0.0),
            sector_exposure_pct=max(sector_pct, 0.0),
            quote_age_seconds=self.store.quote_age_seconds(intent.symbol),
            spread_pct=spread_pct,
            market_session_known=market_session_known,
            market_session_open=market_session_open,
            market_data_available=market_data_available,
            price_band_ok=price_band_ok,
            tick_size_ok=tick_size_ok,
            account_allowed=self.settings.account_allowed,
            opens_new_position=intent.side == Side.BUY and holding_qty <= 0,
            reduces_exposure=(
                intent.side == Side.SELL and holding_qty > 0 and intent.quantity <= holding_qty
            ),
        )

    def _sector_exposure_after_trade(
        self,
        intent: OrderIntent,
        portfolio: PortfolioSnapshot,
        notional: float,
        equity: float,
    ) -> float:
        if equity <= 0:
            return 100.0
        target_sector = self.instruments.sector_for(intent.symbol)
        if not target_sector:
            return 0.0
        sector_value = sum(
            float(position.market_value)
            for position in portfolio.positions
            if self.instruments.sector_for(position.symbol) == target_sector
        )
        existing = next(
            (position for position in portfolio.positions if position.symbol == intent.symbol),
            None,
        )
        existing_value = float(existing.market_value) if existing else 0.0
        if intent.side == Side.BUY:
            sector_after = sector_value + notional
        else:
            sector_after = max(0.0, sector_value - min(existing_value, notional))
        return sector_after / equity * 100

    async def submit(
        self,
        submission: OrderSubmission,
        *,
        automated: bool = False,
        actor: str = "system",
        approval_id: str | None = None,
    ) -> OrderRecord:
        decision = self.check_risk(submission)
        self._record_risk_evaluation(submission, decision, actor=actor)
        if not decision.approved:
            RISK_REJECTIONS.inc()
            self.store.add_audit(
                "risk.rejected",
                f"rejected {submission.intent.side.value} {submission.intent.symbol}",
                {"reasons": decision.reasons, "source": submission.intent.source},
            )
            raise RiskRejectedError(decision)

        self._enforce_execution_policy(
            submission,
            automated=automated,
            actor=actor,
            approval_id=approval_id,
        )
        client_order_id = submission.intent.client_order_id
        claimed = False
        if client_order_id:
            claimed = self.store.claim_client_order_id(client_order_id)
            if not claimed:
                existing = self.store.find_order_by_client_order_id(client_order_id)
                if existing is not None:
                    return existing
                raise ValueError("duplicate client_order_id")

        self.store.add_audit(
            "risk.approved",
            f"approved {submission.intent.side.value} {submission.intent.symbol}",
            {
                "estimated_notional": decision.estimated_notional,
                "estimated_risk_pct": decision.estimated_risk_pct or 0.0,
                "source": submission.intent.source,
                "actor": actor,
            },
        )
        # TOCTOU re-check: only if quote exists and is stale; resting limits
        # without quote are allowed
        fresh_age = self.store.quote_age_seconds(submission.intent.symbol)
        if fresh_age is not None and fresh_age > self.settings.market_data_stale_seconds:
            if client_order_id and claimed:
                self.store.release_client_order_id(client_order_id)
            self.store.add_audit(
                "risk.rejected",
                f"stale market data at execution for {submission.intent.symbol}",
                {
                    "quote_age_seconds": fresh_age,
                    "threshold": self.settings.market_data_stale_seconds,
                },
            )
            raise RiskRejectedError(
                RiskDecision(
                    approved=False,
                    reasons=["stale market data at execution"],
                    estimated_notional=decision.estimated_notional,
                )
            )
        ref_price = submission.risk.reference_price
        if submission.intent.price is not None and ref_price not in (None, 0):
            ref = float(ref_price)
            deviation = abs(float(submission.intent.price) - ref) / ref * 100
            if deviation > self.settings.max_price_deviation_pct:
                if client_order_id and claimed:
                    self.store.release_client_order_id(client_order_id)
                self.store.add_audit(
                    "risk.rejected",
                    f"price deviation {deviation:.2f}% exceeds limit at execution",
                    {"deviation": deviation, "limit": self.settings.max_price_deviation_pct},
                )
                raise RiskRejectedError(
                    RiskDecision(
                        approved=False,
                        reasons=[f"price deviation {deviation:.2f}% exceeds limit"],
                        estimated_notional=decision.estimated_notional,
                    )
                )
        try:
            order = await self.broker.place_order(submission.intent)
        except BrokerAmbiguousError as exc:
            order = OrderRecord(
                client_order_id=client_order_id,
                symbol=submission.intent.symbol,
                side=submission.intent.side,
                quantity=submission.intent.quantity,
                order_type=submission.intent.order_type,
                price=submission.intent.price,
                stop_loss=submission.intent.stop_loss,
                take_profit=submission.intent.take_profit,
                status=OrderStatus.NEEDS_RECONCILIATION,
                source=submission.intent.source,
                message=str(exc),
            )
            self.store.upsert_order(order)
            self.store.add_order_event(
                OrderEvent(
                    order_id=order.id,
                    event_type="broker_outcome_ambiguous",
                    status=order.status,
                    data={"client_order_id": client_order_id or ""},
                )
            )
            self.store.set_broker_reconciliation_ready(False)
            self.store.add_audit(
                "order.ambiguous",
                f"broker outcome unknown for {submission.intent.symbol}",
                {"order_id": str(order.id), "client_order_id": client_order_id or ""},
            )
            ORDER_SUBMISSIONS.labels(status="needs_reconciliation").inc()
            return order
        except (RuntimeError, ValueError, OSError):
            if client_order_id and claimed:
                self.store.release_client_order_id(client_order_id)
            raise

        self.store.upsert_order(order)
        self.store.add_order_event(
            OrderEvent(
                order_id=order.id,
                event_type="broker_order_recorded",
                status=order.status,
                data={
                    "broker_order_id": order.broker_order_id or "",
                    "filled_quantity": order.filled_quantity,
                },
            )
        )
        self.store.record_order_fill(order, source="submission")
        self.store.add_audit(
            "order.submitted",
            f"submitted {submission.intent.side.value} {submission.intent.symbol}",
            {
                "order_id": str(order.id),
                "broker_order_id": order.broker_order_id or "",
                "source": submission.intent.source,
                "actor": actor,
            },
        )
        ORDER_SUBMISSIONS.labels(status=order.status.value).inc()
        return order

    def _record_risk_evaluation(
        self,
        submission: OrderSubmission,
        decision: RiskDecision,
        *,
        actor: str,
    ) -> None:
        self.store.add_risk_evaluation(
            RiskEvaluation(
                client_order_id=submission.intent.client_order_id,
                symbol=submission.intent.symbol,
                approved=decision.approved,
                reasons=decision.reasons,
                inputs=submission.risk.model_dump(mode="json"),
                estimated_notional=decision.estimated_notional,
                estimated_risk_pct=decision.estimated_risk_pct,
                policy_version="v1",
                actor=actor,
            )
        )

    def _enforce_execution_policy(
        self,
        submission: OrderSubmission,
        *,
        automated: bool,
        actor: str,
        approval_id: str | None,
    ) -> None:
        if self.settings.trading_mode == "paper":
            return
        if not self.settings.settrade_configured:
            raise TradingModeError("Settrade credentials are not configured")
        if self.settings.trading_mode == "live" and automated:
            message = "autonomous live execution is disabled; live orders require approval"
            raise TradingModeError(message)
        if self.settings.reconciliation_enabled and not self.store.broker_reconciliation_ready():
            raise TradingModeError("broker reconciliation has not completed successfully")
        if self.settings.trading_mode == "sandbox":
            return
        if not self.settings.live_trading_enabled:
            raise TradingModeError("live trading is disabled by server policy")
        if not self.settings.live_requires_confirmation:
            return
        if approval_id and self.approvals is not None:
            try:
                self.approvals.consume(
                    approval_id,
                    submission.intent,
                    consumed_by=actor,
                    require_distinct_approver=self.settings.require_distinct_approver,
                )
            except ValueError as exc:
                raise TradingModeError(str(exc)) from exc
            return
        # Legacy reusable live token has been removed; intent-bound approval is mandatory
        # even when ZKSATO_LEGACY_LIVE_TOKEN_ENABLED is set (fails closed per invariant #2).
        raise TradingModeError("one-time intent-bound live approval is required")

    async def get_order(self, order_id: str) -> OrderRecord:
        order = self.store.find_order(order_id)
        if order is None:
            raise ValueError("order not found")
        return order

    async def cancel_order(self, order_id: str) -> OrderRecord:
        target = await self.get_order(order_id)
        broker_order_id = order_id
        if self.settings.trading_mode != "paper":
            if not target.broker_order_id:
                raise ValueError("order has no broker order id; reconcile before cancellation")
            broker_order_id = target.broker_order_id
        try:
            remote = await self.broker.cancel_order(broker_order_id)
        except BrokerAmbiguousError as exc:
            target.status = OrderStatus.NEEDS_RECONCILIATION
            target.message = str(exc)
            target.updated_at = datetime.now(UTC)
            self.store.upsert_order(target)
            self.store.add_order_event(
                OrderEvent(
                    order_id=target.id,
                    event_type="cancel_outcome_ambiguous",
                    status=target.status,
                    data={"broker_order_id": target.broker_order_id or ""},
                )
            )
            self.store.set_broker_reconciliation_ready(False)
            self.store.add_audit(
                "order.cancel_ambiguous",
                f"cancel outcome unknown for {target.symbol}",
                {
                    "order_id": str(target.id),
                    "broker_order_id": target.broker_order_id or "",
                },
            )
            return target

        # Preserve broker truth for economic fields; only keep local identity
        # per invariant #5: broker is source of truth for live reconciliation
        merged = remote.model_copy(
            update={
                "id": target.id,
                "broker_order_id": remote.broker_order_id or target.broker_order_id,
                "client_order_id": target.client_order_id or remote.client_order_id,
                "source": target.source,
                "correlation_id": target.correlation_id or remote.correlation_id,
                "created_at": target.created_at,
            }
        )
        if (
            remote.symbol != target.symbol
            or remote.side != target.side
            or float(remote.quantity) != float(target.quantity)
            or remote.price != target.price
        ):
            self.store.add_audit(
                "reconciliation.divergence",
                f"broker cancel divergence for {target.symbol} vs {remote.symbol}",
                {
                    "order_id": str(target.id),
                    "local": {
                        "symbol": target.symbol,
                        "side": target.side.value,
                        "quantity": float(target.quantity),
                        "price": target.price,
                    },
                    "remote": {
                        "symbol": remote.symbol,
                        "side": remote.side.value,
                        "quantity": float(remote.quantity),
                        "price": remote.price,
                    },
                },
            )
        self.store.upsert_order(merged)
        self.store.record_order_fill(merged, source="cancel")
        self.store.add_order_event(
            OrderEvent(
                order_id=merged.id,
                event_type="cancel_recorded",
                status=merged.status,
                data={"broker_order_id": merged.broker_order_id or ""},
            )
        )
        self.store.add_audit(
            "order.cancelled",
            f"cancelled order {target.id}",
            {"broker_order_id": merged.broker_order_id or ""},
        )
        return merged

    async def cancel_open_orders(self, symbol: str | None = None) -> list[OrderRecord]:
        normalized = symbol.upper() if symbol else None
        targets = [
            item
            for item in self.store.list_orders()
            if item.status in CANCELLABLE_ORDER_STATUSES
            and (normalized is None or item.symbol == normalized)
        ]
        cancelled: list[OrderRecord] = []
        for target in targets:
            cancelled.append(await self.cancel_order(str(target.id)))
        return cancelled

    async def list_orders(
        self,
        *,
        symbol: str | None = None,
        status: OrderStatus | None = None,
        side: Side | None = None,
        limit: int | None = None,
    ) -> list[OrderRecord]:
        rows = self.store.list_orders()
        if symbol:
            normalized = symbol.upper()
            rows = [item for item in rows if item.symbol == normalized]
        if status is not None:
            rows = [item for item in rows if item.status == status]
        if side is not None:
            rows = [item for item in rows if item.side == side]
        if limit is not None:
            rows = rows[: max(0, limit)]
        return rows

    async def portfolio(self, *, record_snapshot: bool = True) -> PortfolioSnapshot:
        snapshot = await self.broker.portfolio()
        if record_snapshot:
            self.store.add_account_snapshot(
                AccountSnapshot(
                    cash=snapshot.cash,
                    market_value=snapshot.market_value,
                    equity=snapshot.equity,
                    realized_pnl=snapshot.realized_pnl,
                    unrealized_pnl=snapshot.unrealized_pnl,
                    daily_pnl=snapshot.daily_pnl,
                    source=self.settings.trading_mode,
                    timestamp=snapshot.timestamp,
                )
            )
        return snapshot
