from __future__ import annotations

from zksato.broker.base import Broker
from zksato.config import Settings
from zksato.domain import OrderRecord, OrderSubmission, RiskDecision
from zksato.risk import RiskEngine


class RiskRejectedError(Exception):
    def __init__(self, decision: RiskDecision) -> None:
        super().__init__("order rejected by risk engine")
        self.decision = decision


class TradingModeError(Exception):
    pass


class TradingService:
    def __init__(self, settings: Settings, broker: Broker) -> None:
        self.settings = settings
        self.broker = broker
        self.risk_engine = RiskEngine(settings)

    def check_risk(self, submission: OrderSubmission) -> RiskDecision:
        return self.risk_engine.evaluate(submission.intent, submission.risk)

    async def submit(self, submission: OrderSubmission) -> OrderRecord:
        decision = self.check_risk(submission)
        if not decision.approved:
            raise RiskRejectedError(decision)

        if self.settings.trading_mode == "live" and not self.settings.live_trading_enabled:
            raise TradingModeError("live trading is disabled by server policy")

        if self.settings.trading_mode != "paper":
            raise TradingModeError(
                "sandbox/live broker adapter is not wired yet; refusing to fall back to paper silently"
            )

        return await self.broker.place_order(submission.intent)

    async def list_orders(self) -> list[OrderRecord]:
        return await self.broker.list_orders()
