"""JSON/msgpack serialization and Pydantic helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import orjson
from pydantic_core import to_jsonable_python


def json_dumps(obj: object) -> str:
    """Serialize to JSON string using orjson for performance."""
    return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY, default=default_encoder).decode()


def json_loads(data: str | bytes) -> object:
    """Deserialize from JSON string."""
    return orjson.loads(data)


def pydantic_to_dict(model: object, **kwargs: object) -> dict[str, object]:
    """Convert Pydantic model or dataclass to dict with JSON-serializable values."""
    if hasattr(model, "model_dump"):
        raw = model.model_dump(**kwargs)
        result: dict[str, object] = to_jsonable_python(raw)
        return result
    elif hasattr(model, "__dataclass_fields__"):
        raw = asdict(cast(Any, model))
        result = to_jsonable_python(raw)
        return result
    else:
        raise TypeError(f"Expected Pydantic model or dataclass, got {type(model)}")


def pydantic_to_json(model: object, **kwargs: object) -> str:
    """Convert Pydantic model or dataclass to JSON string."""
    return json_dumps(pydantic_to_dict(model, **kwargs))


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for non-standard types."""

    def default(self, obj: object) -> object:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def default_encoder(obj: object) -> object:
    """Default encoder for non-standard types (for orjson default)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format with UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def deserialize_datetime(value: str) -> datetime:
    """Deserialize ISO format string to datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def serialize_decimal(d: Decimal) -> str:
    """Serialize Decimal to string."""
    return str(d)


def deserialize_decimal(value: str) -> Decimal:
    """Deserialize string to Decimal."""
    return Decimal(value)


def stable_json_dumps(obj: object) -> str:
    """Deterministic JSON serialization for idempotency keys."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_idempotency_key(order: dict[str, object]) -> str:
    """Generate deterministic idempotency key from order data."""
    key_data = {
        "symbol": order.get("symbol"),
        "side": order.get("side"),
        "type": order.get("type"),
        "quantity": str(order.get("quantity", 0)),
        "price": str(order.get("price")) if order.get("price") else None,
        "account_id": order.get("account_id"),
        "strategy_id": order.get("strategy_id"),
        "timestamp": order.get("timestamp"),
    }
    return hashlib.sha256(stable_json_dumps(key_data).encode()).hexdigest()[:32]
