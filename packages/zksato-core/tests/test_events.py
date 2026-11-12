"""Tests for zksato-core events module."""

import pytest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from zksato_core.events import Event, DomainEvent, EventType


def test_event_creation():
    event = Event(event_type="test.event", payload={"key": "value"})
    assert event.event_type == "test.event"
    assert event.payload == {"key": "value"}
    assert event.id is not None
    assert event.correlation_id is not None
    assert event.timestamp is not None


def test_event_to_json():
    event = Event(event_type="test.event", payload={"key": "value"})
    json_str = event.to_json()
    assert "test.event" in json_str
    assert "key" in json_str
    assert "value" in json_str


def test_event_from_json():
    event = Event(event_type="test.event", payload={"key": "value"})
    json_str = event.to_json()
    loaded = Event.from_json(json_str)
    assert loaded.event_type == event.event_type
    assert loaded.payload == event.payload
    assert loaded.id == event.id
    assert loaded.correlation_id == event.correlation_id


def test_domain_event():
    agg_id = uuid4()
    event = DomainEvent(
        event_type="order.created",
        aggregate_id=agg_id,
        aggregate_type="Order",
        version=1,
        payload={"symbol": "AOT"},
    )
    assert event.aggregate_id == agg_id
    assert event.aggregate_type == "Order"
    assert event.version == 1


def test_event_types():
    assert EventType.ORDER_CREATED == "order.created"
    assert EventType.ORDER_FILLED == "order.filled"
    assert EventType.RISK_EVALUATED == "risk.evaluated"
    assert EventType.KILL_SWITCH_ACTIVATED == "risk.kill_switch_activated"
    assert EventType.POSITION_OPENED == "position.opened"
    assert EventType.BOT_STARTED == "bot.started"
    assert EventType.AGENT_SESSION_STARTED == "agent.session_started"