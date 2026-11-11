"""
Agent-native trading platform models for zksato.

Inspired by AI-Trader (HKUDS/AI-Trader), this module provides:
- Agent registration, authentication, token-based API
- Agent profiles with cash balance, points, reputation score
- Wallet address integration
- Agent roles and permissions

All features are advisory/research only — order execution always routes
through RiskEngine and TradingService, preserving zksato's safety invariants.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class AgentRole(StrEnum):
    """Agent roles in the platform."""

    MEMBER = "member"
    OPERATOR = "operator"
    ADMIN = "admin"


class AgentIdentityStatus(StrEnum):
    """Agent identity verification status."""

    NORMAL = "normal"
    VERIFIED = "verified"


class Agent(BaseModel):
    """Agent sub-account model."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=64)
    email: str | None = Field(default=None, max_length=256)
    password_hash: str | None = Field(default=None)
    token: str | None = Field(default=None, max_length=128)
    wallet_address: str | None = Field(default=None, max_length=128)
    role: AgentRole = AgentRole.MEMBER
    identity_status: AgentIdentityStatus = AgentIdentityStatus.NORMAL
    is_verified: bool = False
    cash: float = Field(default=100000.0, ge=0)
    deposited: float = Field(default=0.0, ge=0)
    points: int = Field(default=0, ge=0)
    reputation_score: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class AgentRegisterRequest(BaseModel):
    """Agent registration request."""

    name: str = Field(min_length=1, max_length=64)
    email: str | None = Field(default=None, max_length=256)
    password: str = Field(min_length=1, max_length=128)
    wallet_address: str | None = Field(default=None, max_length=128)
    initial_balance: float = Field(default=100000.0, ge=0)
    positions: list[dict[str, Any]] | None = Field(default=None)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized or None


class AgentLoginRequest(BaseModel):
    """Agent login request."""

    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AgentTokenRecoveryRequest(BaseModel):
    """Agent token recovery request."""

    agent_id: UUID | None = Field(default=None)
    name: str | None = Field(default=None, max_length=64)


class AgentTokenRecoveryConfirm(BaseModel):
    """Agent token recovery confirmation."""

    agent_id: UUID | None = Field(default=None)
    name: str | None = Field(default=None, max_length=64)
    challenge: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class AgentPasswordResetRequest(BaseModel):
    """Agent password reset request."""

    agent_id: UUID | None = Field(default=None)
    name: str | None = Field(default=None, max_length=64)


class AgentPasswordResetConfirm(BaseModel):
    """Agent password reset confirmation."""

    agent_id: UUID | None = Field(default=None)
    name: str | None = Field(default=None, max_length=64)
    challenge: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class AgentInfo(BaseModel):
    """Agent info response."""

    id: UUID
    name: str
    email: str | None
    identity_status: AgentIdentityStatus
    is_verified: bool
    role: AgentRole
    permissions: list[str]
    wallet_address: str | None
    points: int
    cash: float
    reputation_score: int


class AgentHeartbeatResponse(BaseModel):
    """Agent heartbeat response."""

    agent_id: UUID
    server_time: str
    recommended_poll_interval_seconds: int = 30
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    message_count: int = 0
    task_count: int = 0
    unread_count: int = 0
    remaining_unread_count: int = 0
    remaining_task_count: int = 0
    has_more_messages: bool = False
    has_more_tasks: bool = False
    experiment_context: dict[str, Any] | None = None
