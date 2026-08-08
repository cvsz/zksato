from __future__ import annotations

import hmac

from zksato.approvals import ApprovalRepository
from zksato.broker.base import Broker, BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import OrderRecord, OrderStatus, OrderSubmission, PortfolioSnapshot, RiskDecision
from zksato.observability import ORDER_SUBMISSIONS, RISK_REJECTIONS
from zksato.risk import RiskEngine
from zksato.store import StateStore


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
        order = await self.broker.cancel_order(order_id)
        self.store.upsert_order(order)
        self.store.add_audit("order.cancelled", f"cancelled order {order_id}")
        return order

    async def list_orders(self) -> list[OrderRecord]:
        return await self.broker.list_orders()

    async def portfolio(self) -> PortfolioSnapshot:
        return await self.broker.portfolio()
