"""ULID, idempotency keys, and correlation IDs."""

from __future__ import annotations

import secrets
import time
from uuid import UUID, uuid4

import ulid
from ulid import ULID


def new_ulid() -> ULID:
    """Generate a new ULID with current timestamp."""
    return ulid.new()


def new_uuid() -> UUID:
    """Generate a new UUID v4."""
    return uuid4()


def new_idempotency_key(prefix: str = "idem") -> str:
    """Generate a new idempotency key."""
    return f"{prefix}_{secrets.token_urlsafe(16)}"


def new_correlation_id(prefix: str = "corr") -> str:
    """Generate a new correlation ID."""
    return f"{prefix}_{int(time.time() * 1000)}_{secrets.token_hex(4)}"


def parse_ulid(value: str) -> ULID:
    """Parse a ULID from string."""
    return ulid.parse(value)


def ulid_to_str(ulid_obj: ULID) -> str:
    """Convert ULID to string."""
    return str(ulid_obj)


def uuid_to_str(uuid: UUID) -> str:
    """Convert UUID to string."""
    return str(uuid)