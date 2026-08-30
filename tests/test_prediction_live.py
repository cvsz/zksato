"""Dedicated tests for zksato.prediction.live.

Covers:
- PredictionVenueAdapter cannot be instantiated directly.
- PolymarketClobAdapter raises NotImplementedError for all three methods
  (scaffold not wired — must not silently return fake data).
- PredictionLiveGate.validate() enforces all five sequential safety checks.
- PredictionLiveGate.validate() passes when given a fully-compliant adapter
  and all safety flags are set.
"""
from __future__ import annotations

from typing import Any

import pytest

from zksato.config import Settings
from zksato.domain import Side
from zksato.prediction.live import (
    PolymarketClobAdapter,
    PredictionLiveGate,
    PredictionVenueAdapter,
)

# ---------------------------------------------------------------------------
# Minimal compliant adapter used across gate tests
# ---------------------------------------------------------------------------


class _MinimalAdapter(PredictionVenueAdapter):
    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
        return {"market_id": market_id, "up_ask": 0.51, "up_bid": 0.49}

    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        return {"order_id": "stub-ok", "status": "submitted"}

    async def cancel_order(self, order_id: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# PredictionVenueAdapter abstract interface
# ---------------------------------------------------------------------------


def test_prediction_venue_adapter_is_abstract() -> None:
    """PredictionVenueAdapter cannot be instantiated without implementing all methods."""
    with pytest.raises(TypeError):
        PredictionVenueAdapter()  # type: ignore[abstract]


def test_minimal_adapter_satisfies_contract() -> None:
    """A concrete implementation that fulfils the ABC can be instantiated."""
    adapter = _MinimalAdapter()
    assert isinstance(adapter, PredictionVenueAdapter)


# ---------------------------------------------------------------------------
# PolymarketClobAdapter — scaffold invariants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_polymarket_clob_get_market_quote_raises() -> None:
    """get_market_quote must raise NotImplementedError — HTTP not wired."""
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s")
    with pytest.raises(NotImplementedError, match="not yet wired"):
        await adapter.get_market_quote("mkt-abc")


@pytest.mark.asyncio
async def test_polymarket_clob_place_order_raises() -> None:
    """place_order must raise NotImplementedError — must not silently succeed."""
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s")
    with pytest.raises(NotImplementedError, match="not yet wired"):
        await adapter.place_order("mkt-abc", Side.UP, 0.55, 10.0)


@pytest.mark.asyncio
async def test_polymarket_clob_cancel_order_raises() -> None:
    """cancel_order must raise NotImplementedError — must not silently no-op."""
    adapter = PolymarketClobAdapter()
    with pytest.raises(NotImplementedError, match="not yet wired"):
        await adapter.cancel_order("order-xyz")


@pytest.mark.asyncio
async def test_polymarket_clob_raises_without_credentials() -> None:
    """Scaffold raises even when credentials are absent — credentials do not gate the guard."""
    adapter = PolymarketClobAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.get_market_quote("mkt-1")


# ---------------------------------------------------------------------------
# PredictionLiveGate — sequential safety invariants
# ---------------------------------------------------------------------------


def test_gate_rejects_when_prediction_not_enabled() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=False))
    with pytest.raises(RuntimeError, match="not enabled"):
        gate.validate()


def test_gate_rejects_when_live_disabled_by_policy() -> None:
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=False)
    )
    with pytest.raises(RuntimeError, match="disabled by server policy"):
        gate.validate()


def test_gate_rejects_when_acknowledge_loss_not_set() -> None:
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True)
    )
    with pytest.raises(RuntimeError, match="acknowledge loss is required"):
        gate.validate()


def test_gate_rejects_when_adapter_review_not_set() -> None:
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True)
    )
    gate.acknowledge_loss = True
    with pytest.raises(RuntimeError, match="adapter review is required"):
        gate.validate()


def test_gate_rejects_when_kill_switch_not_ready() -> None:
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True)
    )
    gate.acknowledge_loss = True
    gate.reviewed_adapter = True
    with pytest.raises(RuntimeError, match="kill switch readiness is required"):
        gate.validate()


def test_gate_rejects_when_no_adapter_attached() -> None:
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True)
    )
    gate.acknowledge_loss = True
    gate.reviewed_adapter = True
    gate.kill_switch_ready = True
    # adapter is None by default
    with pytest.raises(RuntimeError, match="no reviewed venue adapter attached"):
        gate.validate()


def test_gate_passes_when_all_conditions_met() -> None:
    """validate() must not raise when every safety check passes."""
    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True),
        adapter=_MinimalAdapter(),
    )
    gate.acknowledge_loss = True
    gate.reviewed_adapter = True
    gate.kill_switch_ready = True
    gate.validate()  # must not raise


def test_gate_adapter_stored_on_init() -> None:
    adapter = _MinimalAdapter()
    gate = PredictionLiveGate(Settings(), adapter=adapter)
    assert gate.adapter is adapter


def test_gate_safety_flags_start_false() -> None:
    """All three safety booleans must default to False (fail-closed)."""
    gate = PredictionLiveGate(Settings())
    assert gate.acknowledge_loss is False
    assert gate.reviewed_adapter is False
    assert gate.kill_switch_ready is False
