from __future__ import annotations

import logging
from typing import Any

from zksato.agent_os.skills import AgentSkillHub
from zksato.agent_os.subaccount import AgentPermission, AgentSubAccountManager
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderType, Side
from zksato.service import TradingService

logger = logging.getLogger(__name__)


class AgentExecutionEngine:
    """Core Agent OS execution orchestrator enforcing confirm-before-execute protocols."""

    def __init__(
        self,
        settings: Settings,
        trading_service: TradingService,
        subaccount_manager: AgentSubAccountManager | None = None,
    ) -> None:
        self.settings = settings
        self.trading_service = trading_service
        self.subaccount_manager = subaccount_manager or AgentSubAccountManager()
        self.skills = AgentSkillHub()
        self._bootstrap_core_skills()

    def _bootstrap_core_skills(self) -> None:
        """Register built-in financial intelligence & execution skills."""

        async def get_market_quote(symbol: str) -> dict[str, Any]:
            quote = self.trading_service.store.get_quote(symbol)
            if not quote:
                return {"found": False, "symbol": symbol}
            return {
                "found": True,
                "symbol": symbol,
                "bid": quote.bid,
                "offer": quote.offer,
                "last": quote.last,
                "timestamp": quote.timestamp.isoformat(),
            }

        async def submit_guarded_order(
            sub_account_id: str,
            symbol: str,
            side: str,
            quantity: float,
            price: float | None = None,
            order_type: str = "limit",
            stop_loss: float | None = None,
            take_profit: float | None = None,
        ) -> dict[str, Any]:
            acc = self.subaccount_manager.get_subaccount(sub_account_id)
            if not acc or not acc.can_perform(AgentPermission.SUBMIT_INTENT):
                return {
                    "approved": False,
                    "reason": "Unauthorized agent sub-account or permission denied",
                }

            intent_side = Side.BUY if side.lower() == "buy" else Side.SELL
            intent_type = OrderType.LIMIT if order_type.lower() == "limit" else OrderType.MARKET

            from zksato.domain import OrderSubmission
            from zksato.service import RiskRejectedError

            # If buy order and stop_loss not explicitly supplied, calculate default safety stop
            if intent_side == Side.BUY and stop_loss is None:
                ref_p = price or 1.0
                stop_loss = ref_p * (1.0 - self.settings.default_stop_loss_pct / 100.0)

            intent = OrderIntent(
                symbol=symbol,
                side=intent_side,
                quantity=int(quantity),
                order_type=intent_type,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                source=f"agent_os:{acc.agent_name}",
            )
            submission = OrderSubmission(intent=intent)

            # Route through trusted TradingService with risk evaluation
            try:
                actor_id = f"agent:{acc.agent_name}"
                record = await self.trading_service.submit(submission, actor=actor_id)
                return {
                    "approved": True,
                    "order_id": str(record.id),
                    "status": record.status.value,
                }
            except RiskRejectedError as err:
                return {
                    "approved": False,
                    "reasons": err.decision.reasons,
                    "order_id": None,
                    "status": "rejected",
                }

        self.skills.register(
            name="get_market_quote",
            description="Fetches live market quote for an equity/crypto/derivative symbol.",
            parameters_schema={
                "symbol": {"type": "string", "description": "Trading pair symbol"}
            },
            handler=get_market_quote,
        )

        self.skills.register(
            name="submit_guarded_order",
            description="Submits an order intent from an agent sub-account through RiskEngine.",
            parameters_schema={
                "sub_account_id": {"type": "string"},
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "number"},
                "price": {"type": "number", "nullable": True},
                "order_type": {"type": "string", "enum": ["limit", "market"]},
            },
            handler=submit_guarded_order,
        )
