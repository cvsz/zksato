"""JSON/msgpack serialization and Pydantic helpers."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel
from pydantic_core import to_jsonable_python


def json_dumps(obj: Any) -> str:
    """Serialize to JSON string using orjson for performance."""
    return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY, default=default_encoder).decode()


def json_loads(data: str | bytes) -> Any:
    """Deserialize from JSON string."""
    return orjson.loads(data)


def pydantic_to_dict(model: Any, **kwargs: Any) -> dict[str, Any]:
    """Convert Pydantic model or dataclass to dict with JSON-serializable values."""
    if hasattr(model, "model_dump"):
        return to_jsonable_python(model.model_dump(**kwargs))
    elif hasattr(model, "__dataclass_fields__"):
        from dataclasses import asdict
        return to_jsonable_python(asdict(model))
    else:
        raise TypeError(f"Expected Pydantic model or dataclass, got {type(model)}")


def pydantic_to_json(model: Any, **kwargs: Any) -> str:
    """Convert Pydantic model or dataclass to JSON string."""
    return json_dumps(pydantic_to_dict(model, **kwargs))


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for non-standard types."""

    def default(self, obj: Any) -> Any:
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


def default_encoder(obj: Any) -> Any:
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