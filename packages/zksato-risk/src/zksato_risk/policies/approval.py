"""Approval modes and four-eyes policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from zksato_core.models import OrderIntent, RiskContext
from zksato_risk.policies.base import Policy, PolicyDecision, PolicyResult


class ApprovalMode(Enum):
    """Approval mode for order execution."""

    PAPER = "paper"  # No approval needed, simulated
    SANDBOX = "sandbox"  # Broker sandbox, no real money
    UAT = "uat"  # User acceptance testing
    LIVE = "live"  # Live trading, requires explicit approval


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """Request for order approval."""

    id: UUID = field(default_factory=uuid4)
    order_intent: OrderIntent = field(default_factory=lambda: OrderIntent(symbol="", side=Side.BUY, quantity=0))
    risk_context: RiskContext = field(default_factory=RiskContext)
    requested_by: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    approval_token: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FourEyesPolicy(Policy):
    """Four-eyes approval policy for live execution."""

    require_distinct_approver: bool = True
    approval_ttl_seconds: int = 120

    @property
    def name(self) -> str:
        return "four_eyes_approval"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        # This policy is evaluated at execution time, not pre-trade
        # It checks if the order has a valid approval token
        if context.confirmation_token:
            # Token validation would happen here
            return PolicyResult(decision=PolicyDecision.APPROVE)

        return PolicyResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reasons=["live execution requires explicit operator approval"],
        )


@dataclass(frozen=True, slots=True)
class ApprovalManager:
    """Manages approval requests."""

    requests: dict[UUID, ApprovalRequest] = field(default_factory=dict)
    approval_ttl_seconds: int = 120
    require_distinct_approver: bool = True

    def create_request(
        self,
        order_intent: OrderIntent,
        risk_context: RiskContext,
        requested_by: str,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        import secrets

        request = ApprovalRequest(
            order_intent=order_intent,
            risk_context=risk_context,
            requested_by=requested_by,
            approval_token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC).replace(second=datetime.now(UTC).second + self.approval_ttl_seconds),
        )
        self.requests[request.id] = request
        return request

    def approve(self, request_id: UUID, approver: str, token: str) -> bool:
        """Approve a request."""
        request = self.requests.get(request_id)
        if not request:
            return False

        if request.approval_token != token:
            return False

        if request.expires_at and datetime.now(UTC) > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            return False

        if self.require_distinct_approver and request.requested_by == approver:
            return False

        request.status = ApprovalStatus.APPROVED
        request.approver = approver
        request.approved_at = datetime.now(UTC)
        return True

    def reject(self, request_id: UUID, approver: str, reason: str) -> bool:
        """Reject a request."""
        request = self.requests.get(request_id)
        if not request:
            return False

        request.status = ApprovalStatus.REJECTED
        request.approver = approver
        request.rejection_reason = reason
        return True

    def get_request(self, request_id: UUID) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        return self.requests.get(request_id)

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Get all pending requests."""
        return [r for r in self.requests.values() if r.status == ApprovalStatus.PENDING]

    def cleanup_expired(self) -> int:
        """Remove expired requests."""
        now = datetime.now(UTC)
        expired = [
            rid for rid, req in self.requests.items()
            if req.expires_at and now > req.expires_at and req.status == ApprovalStatus.PENDING
        ]
        for rid in expired:
            self.requests[rid] = ApprovalRequest(
                **{**self.requests[rid].__dict__, "status": ApprovalStatus.EXPIRED}
            )
        return len(expired)