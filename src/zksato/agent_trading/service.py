"""
Agent-native trading service layer for zksato.

Inspired by AI-Trader (HKUDS/AI-Trader), this module provides:
- Agent registration, authentication, token management
- Agent profiles with cash balance, points, reputation score
- Wallet address integration
- Agent roles and permissions

All features are advisory/research only — order execution always routes
through RiskEngine and TradingService, preserving zksato's safety invariants.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from zksato.agent_trading.models import (
    AgentHeartbeatResponse,
    AgentIdentityStatus,
    AgentInfo,
    AgentLoginRequest,
    AgentRegisterRequest,
    AgentRole,
)
from zksato.store import StateStore

logger = logging.getLogger(__name__)

# Reward constants (mirroring AI-Trader)
SIGNAL_PUBLISH_REWARD = 10  # Points for publishing a signal
SIGNAL_ADOPT_REWARD = 1  # Points per follower who receives signal
DISCUSSION_PUBLISH_REWARD = 4  # Points for publishing a discussion
REPLY_PUBLISH_REWARD = 2  # Points for replying to a strategy/discussion
ACCEPT_REPLY_REWARD = 3  # Points for accepting a reply

INITIAL_CAPITAL = 100000.0


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""

    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against stored hash."""
    try:
        salt, pwd_hash = stored.split(":", 1)
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except ValueError:
        return False


class AgentService:
    """Agent-native trading service layer."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    # ── Agent Registration ──────────────────────────────────────────

    def register_agent(self, request: AgentRegisterRequest) -> dict[str, Any]:
        """Register a new agent sub-account.

        Mirrors AI-Trader's /api/claw/agents/selfRegister endpoint.
        """
        agent_name = request.name.strip()
        if not agent_name:
            raise ValueError("Agent name is required")

        # Check for existing agent with same name
        existing = self.store.find_agent_by_name(agent_name)
        if existing is not None:
            raise ValueError("Agent name already exists")

        password_hash = _hash_password(request.password)
        wallet = request.wallet_address or ""
        email = str(request.email).strip().lower() if request.email else None

        try:
            initial_cash = float(request.initial_balance)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid initial balance") from exc

        if not isinstance(initial_cash, float) or initial_cash < 0:
            raise ValueError("Invalid initial balance")

        # Create agent
        uid = uuid4()
        new_agent = {
            "id": uid,
            "name": agent_name,
            "email": email,
            "password_hash": password_hash,
            "wallet_address": wallet,
            "cash": initial_cash,
            "deposited": 0.0,
            "points": 0,
            "reputation_score": 0,
            "identity_status": AgentIdentityStatus.NORMAL.value,
            "is_verified": False,
            "role": AgentRole.MEMBER.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        self.store.create_agent(new_agent)

        # Generate token
        token = self.store.generate_agent_token(uid)

        # Handle initial positions
        initial_position_value = 0.0
        if request.positions:
            for pos in request.positions:
                market = str(pos.get("market", "us-stock")).strip().lower()
                symbol = str(pos.get("symbol") or "").strip()
                if not symbol:
                    raise ValueError("Position symbol is required")
                if market != "polymarket":
                    symbol = symbol.upper()

                side = str(pos.get("side") or "long").strip().lower()
                if side not in {"long", "short"}:
                    raise ValueError("Position side must be long or short")

                try:
                    quantity = float(pos.get("quantity", 0))
                except (TypeError, ValueError) as exc:
                    raise ValueError("Invalid position quantity") from exc
                if quantity <= 0:
                    raise ValueError("Invalid position quantity")

                entry_price = float(pos.get("entry_price", 0))
                if not isinstance(entry_price, (int, float)) or entry_price <= 0:
                    raise ValueError("Invalid position entry price")

                initial_position_value += entry_price * abs(quantity)
                self.store.create_position(
                    agent_id=uid,
                    symbol=symbol,
                    market=market,
                    side=side,
                    quantity=quantity,
                    entry_price=entry_price,
                )

            self.store.add_audit(
                event_type="agent_registered",
                message=f"agent registered: {agent_name}",
                data={
                    "agent_id": str(uid),
                    "name": agent_name,
                    "email": email,
                    "wallet_address": wallet,
                    "initial_cash": initial_cash,
                    "position_count": len(request.positions),
                },
            )

        deposited = max(0.0, initial_cash + initial_position_value - INITIAL_CAPITAL)
        self.store.update_agent_cash(uid, initial_cash, deposited)

        return {
            "token": token,
            "agent_id": str(uid),
            "name": agent_name,
            "email": email,
            "identity_status": "normal",
            "is_verified": False,
            "initial_balance": initial_cash,
            "deposited": deposited,
        }

    # ── Agent Authentication ────────────────────────────────────────

    def login_agent(self, request: AgentLoginRequest) -> dict[str, Any]:
        """Agent login.

        Mirrors AI-Trader's /api/claw/agents/login endpoint.
        """
        row = self.store.find_agent_by_name(request.name)
        if not row or not _verify_password(request.password, row.get("password_hash", "")):
            raise ValueError("Invalid credentials")

        token = self.store.get_or_issue_agent_token(row["id"])

        return {
            "token": token,
            "agent_id": str(row["id"]),
            "name": row["name"],
            "identity_status": row.get("identity_status", "normal"),
            "is_verified": bool(row.get("is_verified", False)),
        }

    def get_agent_info(self, agent_id: str) -> AgentInfo | None:
        """Get agent info.

        Mirrors AI-Trader's /api/claw/agents/me endpoint.
        """
        uid = UUID(agent_id)
        agent = self.store.get_agent_by_id(uid)
        if agent is None:
            return None

        return AgentInfo(
            id=UUID(str(agent.get("id"))),
            name=str(agent.get("name") or ""),
            email=str(agent.get("email") or ""),
            identity_status=AgentIdentityStatus(
                str(agent.get("identity_status", AgentIdentityStatus.NORMAL.value))
            ),
            is_verified=bool(agent.get("is_verified", False)),
            role=AgentRole(str(agent.get("role", AgentRole.MEMBER.value))),
            permissions=self._get_agent_permissions(agent),
            wallet_address=str(agent.get("wallet_address") or ""),
            points=int(agent.get("points", 0)),
            cash=float(agent.get("cash", 0.0)),
            reputation_score=int(agent.get("reputation_score", 0)),
        )

    def get_agent_points(self, agent_id: str) -> int:
        """Get agent's points balance."""
        uid = UUID(agent_id)
        return self.store.get_agent_points(uid)

    # ── Agent Heartbeat ─────────────────────────────────────────────

    def agent_heartbeat(self, agent_id: str) -> AgentHeartbeatResponse:
        """Agent heartbeat endpoint.

        Mirrors AI-Trader's /api/claw/agents/heartbeat endpoint.
        Returns pending messages and tasks for the agent.
        """
        uid = UUID(agent_id)
        agent = self.store.get_agent_by_id(uid)
        if agent is None:
            raise ValueError("Invalid agent")

        # Get unread messages
        messages = self.store.get_unread_agent_messages(uid, limit=50)
        message_ids = [str(m["id"]) for m in messages]

        # Mark messages as read
        if message_ids:
            self.store.mark_agent_messages_read(uid, message_ids)

        # Get pending tasks
        tasks = self.store.get_pending_agent_tasks(uid, limit=10)

        now = datetime.now(UTC)
        unread_count = len(messages)
        pending_task_count = len(tasks)

        return AgentHeartbeatResponse(
            agent_id=UUID(str(agent.get("id"))),
            server_time=now.isoformat().replace("+00:00", "Z"),
            recommended_poll_interval_seconds=30,
            messages=messages,
            tasks=tasks,
            message_count=len(messages),
            task_count=len(tasks),
            unread_count=unread_count,
            remaining_unread_count=max(0, unread_count - len(messages)),
            remaining_task_count=max(0, pending_task_count - len(tasks)),
            has_more_messages=unread_count > len(messages),
            has_more_tasks=pending_task_count > len(tasks),
        )

    # ── Points/Rewards ──────────────────────────────────────────────

    def add_agent_points(
        self,
        agent_id: str,
        points: int,
        reason: str = "reward",
        *,
        source_type: str | None = None,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add points to an agent's account.

        Mirrors AI-Trader's reward ledger system.
        """
        if points <= 0:
            return {"success": False, "skipped": True, "reason": "zero_amount"}

        uid = UUID(agent_id)
        self.store.add_agent_points(
            agent_id=uid,
            points=points,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
        )

        return {"success": True, "points": points, "reason": reason}

    def exchange_points_for_cash(self, agent_id: str, points_amount: int) -> dict[str, Any]:
        """Exchange points for cash (1 point = 1,000 USD).

        Mirrors AI-Trader's points exchange system.
        """
        if points_amount <= 0:
            raise ValueError("Points amount must be positive")

        uid = UUID(agent_id)
        agent = self.store.get_agent_by_id(uid)
        if agent is None:
            raise ValueError("Agent not found")

        if int(agent.get("points", 0)) < points_amount:
            raise ValueError("Insufficient points")

        cash_added = points_amount * 1000  # 1 point = 1,000 USD

        self.store.add_agent_points(
            agent_id=uid,
            points=-points_amount,
            reason="points_exchange",
            source_type="points_exchange",
            metadata={"cash_added": cash_added},
        )
        self.store.update_agent_cash(uid, float(agent.get("cash", 0.0)) + cash_added, 0)

        return {
            "success": True,
            "points_exchanged": points_amount,
            "cash_added": cash_added,
            "remaining_points": int(agent.get("points", 0)) - points_amount,
            "total_cash": float(agent.get("cash", 0.0)) + cash_added,
        }

    # ── Helper Methods ──────────────────────────────────────────────

    def _get_agent_permissions(self, agent: dict[str, Any]) -> list[str]:
        """Get permissions for an agent based on role."""
        base_permissions = ["read_market", "read_portfolio", "submit_intent", "cancel_order"]
        role = str(agent.get("role", AgentRole.MEMBER.value))
        if role == AgentRole.OPERATOR.value:
            base_permissions.extend(["approve_orders", "manage_risk"])
        if role == AgentRole.ADMIN.value:
            base_permissions.extend(["manage_agents", "manage_system"])
        return base_permissions
