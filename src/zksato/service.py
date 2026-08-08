from __future__ import annotations

import hmac
from datetime import UTC, datetime

from zksato.approvals import ApprovalRepository
from zksato.broker.base import Broker, BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import (
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderSubmission,
    PortfolioSnapshot,
    RiskContext,
    RiskDecision,
    Side,
)
from zksato.observability import ORDER_SUBMISSIONS, RISK_REJECTIONS
from zksato.risk import RiskEngine
from zksato.store import StateStore

OPEN_ORDER_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.NEEDS_RECONCILIATION,
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

    def check_risk(self, submission: OrderSubmission) -> RiskDecision:
        return self.risk_engine.evaluate(submission.intent, submission.risk)

    async def risk_context_for(self, intent: OrderIntent) -> RiskContext:
        portfolio = await self.portfolio()
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
        holding_qty = int(existing.quantity) if existing else 0
        gross_value = sum(float(position.market_value) for position in portfolio.positions)
        if intent.side == Side.BUY:
            symbol_after = existing_value + notional
            gross_after = gross_value + notional
        else:
            reduction = min(existing_value, notional)
            symbol_after = max(0.0, existing_value - reduction)
            gross_after = max(0.0, gross_value - reduction)
        position_pct = (symbol_after / equity * 100) if equity else 100.0
        gross_pct = (gross_after / equity * 100) if equity else 100.0
        symbol_pct = (symbol_after / equity * 100) if equity else 100.0
        daily_pnl_pct = (portfolio.daily_pnl / equity * 100) if equity else 0.0
        drawdown = 0.0
        account = getattr(self.broker, "account", None)
        if account is not None and hasattr(account, "drawdown_pct"):
            drawdown = float(account.drawdown_pct())
        orders = self.store.list_orders()
        today = datetime.now(UTC).date()
        orders_today = sum(item.created_at.date() == today for item in orders)
        open_orders = sum(item.status in OPEN_ORDER_STATUSES for item in orders)
        spread_pct: float | None = None
        if quote and quote.bid and quote.offer and quote.last:
            spread_pct = (quote.offer - quote.bid) / quote.last * 100
        return RiskContext(
            current_positions=len(portfolio.positions),
            daily_pnl_pct=daily_pnl_pct,
            drawdown_pct=drawdown,
            position_pct_after_trade=min(max(position_pct, 0.0), 100.0),
            line_available=max(float(portfolio.cash), 0.0),
            available_quantity=holding_qty,
            reference_price=reference_price,
            orders_today=orders_today,
            open_orders=open_orders,
            portfolio_value=equity if equity > 0 else None,
            gross_exposure_pct=max(gross_pct, 0.0),
            symbol_exposure_pct=max(symbol_pct, 0.0),
            quote_age_seconds=self.store.quote_age_seconds(intent.symbol),
            spread_pct=spread_pct,
            market_session_known=True,
            market_data_available=quote is not None,
            opens_new_position=intent.side == Side.BUY and holding_qty <= 0,
            reduces_exposure=(
                intent.side == Side.SELL and holding_qty > 0 and intent.quantity <= holding_qty
            ),
        )

    async def submit(
        self,
        submission: OrderSubmission,
        *,
        automated: bool = False,
        actor: str = "system",
        approval_id: str | None = None,
    ) -> OrderRecord:
        decision = self.check_risk(submission)
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
        if (
            self.settings.reconciliation_enabled
            and not self.store.broker_reconciliation_ready()
        ):
            raise TradingModeError("broker reconciliation has not completed successfully")
        if self.settings.trading_mode == "sandbox":
            return
        if automated:
            message = "autonomous live execution is disabled; live orders require approval"
            raise TradingModeError(message)
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
        if self.settings.legacy_live_token_enabled:
            expected = self.settings.live_confirmation_token
            supplied = submission.confirmation_token
            if expected and supplied and hmac.compare_digest(expected, supplied):
                return
        raise TradingModeError("one-time intent-bound live approval is required")

    async def cancel_order(self, order_id: str) -> OrderRecord:
        target = self.store.find_order(order_id)
        if target is None:
            raise ValueError("order not found")
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

        merged = remote.model_copy(
            update={
                "id": target.id,
                "client_order_id": target.client_order_id or remote.client_order_id,
                "stop_loss": target.stop_loss,
                "take_profit": target.take_profit,
                "source": target.source,
                "created_at": target.created_at,
            }
        )
        self.store.upsert_order(merged)
        self.store.add_audit(
            "order.cancelled",
            f"cancelled order {target.id}",
            {"broker_order_id": merged.broker_order_id or ""},
        )
        return merged

    async def list_orders(self) -> list[OrderRecord]:
        return self.store.list_orders()

    async def portfolio(self) -> PortfolioSnapshot:
        return await self.broker.portfolio()
