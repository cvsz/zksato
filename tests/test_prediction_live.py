"""Dedicated tests for zksato.prediction.live.

Covers:
- PredictionVenueAdapter cannot be instantiated directly.
- PolymarketClobAdapter is now wired (httpx) with injected fake client — must return
  normalized quotes and order results, validate inputs, require credentials for
  mutation, and surface ambiguous network errors as BrokerAmbiguousError.
- PredictionLiveGate.validate() enforces all five sequential safety checks.
- PredictionLiveGate.validate() passes when given a fully-compliant adapter
  and all safety flags are set.
"""

from __future__ import annotations

from typing import Any

import pytest

from zksato.broker.base import BrokerAmbiguousError
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
# Fake HTTP client helpers for Polymarket adapter
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, data: Any, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code
        self.text = str(data)

    def json(self) -> Any:
        return self._data


class _FakeBookClient:
    """Returns deterministic book/price/order responses for get_market_quote."""

    async def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResp:
        if "/book" in url:
            return _FakeResp({"bids": [{"price": "0.49"}], "asks": [{"price": "0.51"}]})
        if "/price" in url:
            # secondary fallback — not hit when book succeeds, but support it
            return _FakeResp({"price": "0.51"})
        if "/markets/" in url:
            mid = url.rsplit("/", 1)[-1]
            return _FakeResp({"market_id": mid, "up_ask": 0.51, "up_bid": 0.49, "down_ask": 0.49})
        return _FakeResp({}, 200)

    async def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResp:
        payload = json or {}
        return _FakeResp(
            {
                "order_id": "poly-123",
                "id": "poly-123",
                "market_id": payload.get("market_id", payload.get("token_id", "mkt-1")),
                "price": payload.get("price", 0.55),
                "size": payload.get("size", 10),
                "status": "open",
            },
            200,
        )

    async def delete(self, url: str) -> _FakeResp:
        if "notfound" in url:
            return _FakeResp({"success": False}, 404)
        return _FakeResp({"success": True}, 200)

    async def aclose(self) -> None:
        return None


class _NetworkErrorClient:
    async def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResp:  # type: ignore[no-untyped-def]
        raise ConnectionError("network down")

    async def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResp:  # type: ignore[no-untyped-def]
        raise ConnectionError("network down")

    async def delete(self, url: str) -> _FakeResp:  # type: ignore[no-untyped-def]
        raise ConnectionError("network down")

    async def aclose(self) -> None:
        return None


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
# PolymarketClobAdapter — wired invariants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_polymarket_clob_get_market_quote_returns_normalized_quote() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    quote = await adapter.get_market_quote("mkt-abc")
    assert quote["market_id"] == "mkt-abc"
    assert 0.5 < float(quote["up_ask"]) < 1.0  # type: ignore[arg-type]
    assert 0.0 < float(quote["up_bid"]) < 1.0  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_polymarket_clob_place_order_succeeds_with_fake_client() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    result = await adapter.place_order("mkt-abc", Side.UP, 0.55, 10.0)
    assert result["order_id"] == "poly-123"
    assert result["market_id"] == "mkt-abc"
    assert result["status"] == "open"
    assert result["price"] == 0.55


@pytest.mark.asyncio
async def test_polymarket_clob_cancel_order_returns_true() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    ok = await adapter.cancel_order("poly-123")
    assert ok is True


@pytest.mark.asyncio
async def test_polymarket_clob_cancel_order_returns_false_on_404() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    ok = await adapter.cancel_order("notfound-xyz")
    assert ok is False


@pytest.mark.asyncio
async def test_polymarket_clob_place_order_validates_price() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    with pytest.raises(ValueError, match="price must be between 0 and 1"):
        await adapter.place_order("mkt-abc", Side.UP, 0.0, 10.0)
    with pytest.raises(ValueError, match="price must be between 0 and 1"):
        await adapter.place_order("mkt-abc", Side.UP, 1.0, 10.0)


@pytest.mark.asyncio
async def test_polymarket_clob_place_order_requires_credentials() -> None:
    adapter = PolymarketClobAdapter(http_client=_FakeBookClient())
    with pytest.raises(RuntimeError, match="requires api_key"):
        await adapter.place_order("mkt-abc", Side.UP, 0.55, 10.0)


@pytest.mark.asyncio
async def test_polymarket_clob_cancel_requires_credentials() -> None:
    adapter = PolymarketClobAdapter(http_client=_FakeBookClient())
    with pytest.raises(RuntimeError, match="requires api_key"):
        await adapter.cancel_order("poly-123")


@pytest.mark.asyncio
async def test_polymarket_clob_place_order_ambiguous_on_network_error() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_NetworkErrorClient())
    with pytest.raises(BrokerAmbiguousError, match="ambiguous"):
        await adapter.place_order("mkt-abc", Side.UP, 0.55, 10.0)


@pytest.mark.asyncio
async def test_polymarket_clob_cancel_ambiguous_on_network_error() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_NetworkErrorClient())
    with pytest.raises(BrokerAmbiguousError, match="ambiguous"):
        await adapter.cancel_order("poly-123")


@pytest.mark.asyncio
async def test_polymarket_clob_get_market_quote_validates_market_id() -> None:
    adapter = PolymarketClobAdapter(api_key="k", api_secret="s", http_client=_FakeBookClient())
    with pytest.raises(ValueError, match="market_id is required"):
        await adapter.get_market_quote("  ")


@pytest.mark.asyncio
async def test_polymarket_clob_respects_settings_credentials() -> None:
    settings = Settings(
        prediction_enabled=True,
        prediction_clob_api_key="from-settings-k",
        prediction_clob_api_secret="from-settings-s",
        prediction_clob_url="https://clob.example.test",
    )
    adapter = PolymarketClobAdapter(settings=settings, http_client=_FakeBookClient())
    assert adapter.api_key == "from-settings-k"
    assert adapter.base_url == "https://clob.example.test"
    result = await adapter.place_order("mkt-abc", Side.DOWN, 0.45, 5.0)
    assert result["side"] == "down"


# ---------------------------------------------------------------------------
# PredictionLiveGate — sequential safety invariants
# ---------------------------------------------------------------------------


def test_gate_rejects_when_prediction_not_enabled() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=False))
    with pytest.raises(RuntimeError, match="not enabled"):
        gate.validate()


def test_gate_rejects_when_live_disabled_by_policy() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=False))
    with pytest.raises(RuntimeError, match="disabled by server policy"):
        gate.validate()


def test_gate_rejects_when_acknowledge_loss_not_set() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=True))
    with pytest.raises(RuntimeError, match="acknowledge loss is required"):
        gate.validate()


def test_gate_rejects_when_adapter_review_not_set() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=True))
    gate.acknowledge_loss = True
    with pytest.raises(RuntimeError, match="adapter review is required"):
        gate.validate()


def test_gate_rejects_when_kill_switch_not_ready() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=True))
    gate.acknowledge_loss = True
    gate.reviewed_adapter = True
    with pytest.raises(RuntimeError, match="kill switch readiness is required"):
        gate.validate()


def test_gate_rejects_when_no_adapter_attached() -> None:
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=True))
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
