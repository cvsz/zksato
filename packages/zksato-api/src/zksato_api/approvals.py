"""Approval manager for live trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from zksato_core.ids import new_ulid


@dataclass
class ApprovalRequest:
    """Approval request for live trading."""

    request_id: UUID = field(default_factory=new_ulid)
    order_id: UUID | None = None
    requested_by: str = ""
    required_approvers: int = 2
    approvers: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, approved, rejected, expired
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalManager:
    """Manages four-eyes approval for live orders."""

    requests: dict[UUID, ApprovalRequest] = field(default_factory=dict)

    def request_approval(
        self,
        order_id: UUID,
        requested_by: str,
        required_approvers: int = 2,
        ttl_seconds: int = 900,
    ) -> ApprovalRequest:
        """Request approval for an order."""
        request = ApprovalRequest(
            order_id=order_id,
            requested_by=requested_by,
            required_approvers=required_approvers,
            expires_at=datetime.now(UTC).replace(second=0, microsecond=0)
            + __import__("datetime").timedelta(seconds=ttl_seconds),
        )
        self.requests[request.request_id] = request
        return request

    def approve(self, request_id: UUID, approver: str) -> ApprovalRequest | None:
        """Approve a request."""
        request = self.requests.get(request_id)
        if not request:
            return None

        if request.status != "pending":
            return request

        if approver in request.approvers:
            return request

        request.approvers.append(approver)

        if len(request.approvers) >= request.required_approvers:
            request.status = "approved"

        return request

    def reject(self, request_id: UUID, approver: str) -> ApprovalRequest | None:
        """Reject a request."""
        request = self.requests.get(request_id)
        if not request or request.status != "pending":
            return request
        request.status = "rejected"
        return request

    def get_request(self, request_id: UUID) -> ApprovalRequest | None:
        """Get approval request."""
        return self.requests.get(request_id)

    def cleanup_expired(self) -> int:
        """Clean up expired requests."""
        now = datetime.now(UTC)
        count = 0
        for req in list(self.requests.values()):
            if req.expires_at and req.expires_at < now and req.status == "pending":
                req.status = "expired"
                count += 1
        return count
