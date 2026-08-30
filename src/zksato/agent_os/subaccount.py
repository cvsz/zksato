from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class AgentPermission(StrEnum):
    READ_MARKET = "read_market"
    READ_PORTFOLIO = "read_portfolio"
    SUBMIT_INTENT = "submit_intent"
    CANCEL_ORDER = "cancel_order"
    WITHDRAW = "withdraw"  # Permanently denied to agent sub-accounts


@dataclass
class AgentSubAccount:
    """Isolated, zero-withdrawal sub-account for autonomous trading agents."""

    sub_account_id: str = field(default_factory=lambda: f"agsub-{uuid.uuid4().hex[:8]}")
    agent_name: str = "default_agent"
    allocated_collateral_usd: float = 1000.0
    current_cash_usd: float = 1000.0
    max_drawdown_limit_pct: float = 10.0
    max_position_notional_usd: float = 200.0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    permissions: set[AgentPermission] = field(
        default_factory=lambda: {
            AgentPermission.READ_MARKET,
            AgentPermission.READ_PORTFOLIO,
            AgentPermission.SUBMIT_INTENT,
            AgentPermission.CANCEL_ORDER,
        }
    )

    def can_perform(self, permission: AgentPermission) -> bool:
        if permission == AgentPermission.WITHDRAW:
            return False  # Strict sandbox invariant: never allow agent withdrawals
        return self.is_active and permission in self.permissions

    def debit(self, amount: float) -> bool:
        if amount <= 0 or amount > self.current_cash_usd:
            return False
        self.current_cash_usd -= amount
        return True

    def credit(self, amount: float) -> None:
        if amount > 0:
            self.current_cash_usd += amount


class AgentSubAccountManager:
    """Manages multi-tenant agent sub-account partitions and collateral budgets."""

    def __init__(self) -> None:
        self._accounts: dict[str, AgentSubAccount] = {}

    def create_subaccount(
        self,
        agent_name: str,
        collateral_usd: float = 1000.0,
        max_drawdown_pct: float = 10.0,
    ) -> AgentSubAccount:
        account = AgentSubAccount(
            agent_name=agent_name,
            allocated_collateral_usd=collateral_usd,
            current_cash_usd=collateral_usd,
            max_drawdown_limit_pct=max_drawdown_pct,
        )
        self._accounts[account.sub_account_id] = account
        return account

    def get_subaccount(self, sub_account_id: str) -> AgentSubAccount | None:
        return self._accounts.get(sub_account_id)

    def list_subaccounts(self) -> list[AgentSubAccount]:
        return list(self._accounts.values())

    def freeze_subaccount(self, sub_account_id: str) -> bool:
        acc = self._accounts.get(sub_account_id)
        if acc:
            acc.is_active = False
            return True
        return False
