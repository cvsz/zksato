from __future__ import annotations

import hmac

from zksato.broker.base import Broker
from zksato.config import Settings
from zksato.domain import OrderRecord, OrderSubmission, PortfolioSnapshot, RiskDecision
from zksato.risk import RiskEngine
from zksato.store import StateStore


class RiskRejectedError(Exception):
    def __init__(self, decision: RiskDecision) -> None:
        super().__init__("order rejected by risk engine")
        self.decision = decision


class TradingModeError(Exception):
    pass


class TradingService:
    def __init__(self, settings: Settings, broker: Broker, store: StateStore) -> None:
        self.settings = settings
        self.broker = broker
        self.store = store
        self.risk_engine = RiskEngine(settings)

    def check_risk(self, submission: OrderSubmission) -> RiskDecision:
        return self.risk_engine.evaluate(submission.intent, submission.risk)

    async def submit(self, submission: OrderSubmission, *, automated: bool = False) -> OrderRecord:
        decision = self.check_risk(submission)
        if not decision.approved:
            self.store.add_audit(
                "risk.rejected",
                f"rejected {submission.intent.side.value} {submission.intent.symbol}",
                {"reasons": decision.reasons, "source": submission.intent.source},
            )
            raise RiskRejectedError(decision)

        self._enforce_execution_policy(submission, automated=automated)
        order = await self.broker.place_order(submission.intent)
        self.store.add_audit(
            "order.submitted",
            f"submitted {submission.intent.side.value} {submission.intent.symbol}",
            {
                "order_id": str(order.id),
                "broker_order_id": order.broker_order_id or "",
                "source": submission.intent.source,
            },
        )
        return order

    def _enforce_execution_policy(
        self,
        submission: OrderSubmission,
        *,
        automated: bool,
    ) -> None:
        if self.settings.trading_mode == "paper":
            return
        if not self.settings.settrade_configured:
            raise TradingModeError("Settrade credentials are not configured")
        if self.settings.trading_mode == "sandbox":
            return
        if automated:
            raise TradingModeError("autonomous live execution is disabled; live orders require confirmation")
        if not self.settings.live_trading_enabled:
            raise TradingModeError("live trading is disabled by server policy")
        if self.settings.live_requires_confirmation:
            expected = self.settings.live_confirmation_token
            supplied = submission.confirmation_token
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                raise TradingModeError("valid live confirmation token is required")

    async def cancel_order(self, order_id: str) -> OrderRecord:
        return await self.broker.cancel_order(order_id)

    async def list_orders(self) -> list[OrderRecord]:
        return await self.broker.list_orders()

    async def portfolio(self) -> PortfolioSnapshot:
        return await self.broker.portfolio()
