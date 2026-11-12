"""Tests for zksato-core serialization module."""

import pytest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from zksato_core.serialization import (
    json_dumps,
    json_loads,
    pydantic_to_dict,
    pydantic_to_json,
    serialize_datetime,
    deserialize_datetime,
    serialize_decimal,
    deserialize_decimal,
)
from zksato_core.models import OrderIntent, Side, OrderType
from zksato_core.money import thb


def test_json_dumps_loads():
    data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    json_str = json_dumps(data)
    loaded = json_loads(json_str)
    assert loaded == data


def test_json_dumps_datetime():
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    data = {"timestamp": dt}
    json_str = json_dumps(data)
    loaded = json_loads(json_str)
    assert loaded["timestamp"] == "2026-01-01T12:00:00+00:00"


def test_json_dumps_decimal():
    data = {"price": Decimal("100.50")}
    json_str = json_dumps(data)
    loaded = json_loads(json_str)
    assert loaded["price"] == "100.50"


def test_json_dumps_uuid():
    uid = uuid4()
    data = {"id": uid}
    json_str = json_dumps(data)
    loaded = json_loads(json_str)
    assert loaded["id"] == str(uid)


def test_pydantic_to_dict():
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
    )
    d = pydantic_to_dict(intent)
    assert d["symbol"] == "AOT"
    assert d["side"] == "buy"
    assert d["quantity"] == 100


def test_pydantic_to_json():
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
    )
    json_str = pydantic_to_json(intent)
    assert "AOT" in json_str
    assert "buy" in json_str


def test_serialize_datetime():
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    s = serialize_datetime(dt)
    assert s == "2026-01-01T12:00:00+00:00"


def test_deserialize_datetime():
    dt = deserialize_datetime("2026-01-01T12:00:00+00:00")
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.tzinfo is not None


def test_serialize_decimal():
    d = Decimal("100.50")
    s = serialize_decimal(d)
    assert s == "100.50"


def test_deserialize_decimal():
    d = deserialize_decimal("100.50")
    assert d == Decimal("100.50")


def test_json_dumps_bytes():
    data = {"key": "value"}
    json_bytes = json_dumps(data).encode()
    loaded = json_loads(json_bytes)
    assert loaded == data