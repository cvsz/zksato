from datetime import UTC, datetime, timedelta

import pytest

from zksato.broker.base import BrokerAmbiguousError
from zksato.broker.settrade import SettradeBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderType, Side
from zksato.tfex import (
    SettradeTfexGateway,
    TfexContractMetadata,
    TfexContractRegistry,
    TfexOrderIntent,
    TfexPosition,
    TfexSide,
)


class FakeEquity:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def place_order(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "orderNo": "UAT-1",
            "symbol": kwargs["symbol"],
            "side": kwargs["side"],
            "vol": kwargs["volume"],
            "matched": 0,
            "price": kwargs["price"],
            "priceType": kwargs["price_type"],
            "status": "accepted",
        }


class FakeDerivatives:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_account_info(self):
        return {"equity": 100_000, "marginUsagePct": 4.0}

    def get_portfolios(self):
        return [{"symbol": "S50U26", "actualLongPosition": 2, "actualShortPosition": 1}]

    def place_order(self, **kwargs):
        self.calls.append(kwargs)
        return {"orderNo": "TFEX-UAT-1", "status": "accepted"}


@pytest.mark.asyncio
async def test_settrade_equity_adapter_maps_sandbox_order_without_credentials() -> None:
    broker = object.__new__(SettradeBroker)
    broker.settings = Settings(
        trading_mode="sandbox",
        settrade_pin="not-used-in-test",
    )
    broker._equity = FakeEquity()
    record = await broker.place_order(
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=42.5,
            client_order_id="uat-equity-1",
            source="uat-test",
        )
    )

    assert record.broker_order_id == "UAT-1"
    assert record.status.value == "accepted"
    assert broker._equity.calls[0]["price_type"] == "Limit"
    assert broker._equity.calls[0]["pin"] == "not-used-in-test"


@pytest.mark.asyncio
async def test_settrade_equity_timeout_is_ambiguous_and_never_retried_here() -> None:
    broker = object.__new__(SettradeBroker)
    broker.settings = Settings(trading_mode="sandbox")

    class TimeoutEquity:
        def place_order(self, **_kwargs):
            raise TimeoutError("simulated UAT timeout")

    broker._equity = TimeoutEquity()
    with pytest.raises(BrokerAmbiguousError, match="timed out"):
        await broker.place_order(
            OrderIntent(
                symbol="AOT",
                side=Side.BUY,
                quantity=1,
                order_type=OrderType.LIMIT,
                price=42.5,
            )
        )


@pytest.mark.asyncio
async def test_settrade_tfex_gateway_risk_context_and_uat_mutation_are_dedicated() -> None:
    gateway = object.__new__(SettradeTfexGateway)
    gateway.settings = Settings(
        trading_mode="sandbox",
        max_tfex_contracts=10,
        settrade_pin="not-used-in-test",
    )
    gateway.contracts = TfexContractRegistry()
    gateway.contracts.upsert(
        TfexContractMetadata(
            symbol="S50U26",
            tick_size=0.1,
            expiry=datetime.now(UTC) + timedelta(days=30),
        )
    )
    gateway.derivatives = FakeDerivatives()

    context = await gateway.risk_context(
        symbol="S50U26",
        price=800.1,
        quote_age_seconds=0.2,
        market_data_available=True,
    )
    assert context.current_contracts == 3
    assert context.tick_size_ok is True
    assert context.margin_usage_pct_after_trade == 4.0

    result = await gateway.place_uat_order(
        TfexOrderIntent(
            symbol="S50U26",
            side=TfexSide.LONG,
            position=TfexPosition.OPEN,
            volume=1,
            price=800.1,
        )
    )
    assert result["orderNo"] == "TFEX-UAT-1"
    assert gateway.derivatives.calls[0]["position"] == "OPEN"

    gateway.settings = Settings(trading_mode="paper")
    with pytest.raises(RuntimeError, match="sandbox/UAT"):
        await gateway.place_uat_order(
            TfexOrderIntent(
                symbol="S50U26",
                side=TfexSide.LONG,
                position=TfexPosition.OPEN,
                volume=1,
                price=800.1,
            )
        )
