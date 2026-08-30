from unittest import mock

import pytest

from zksato.broker.ccxt import CcxtBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderStatus, OrderType, Side


class FakeCcxtExchange:
    def __init__(self, exchange_id: str) -> None:
        self.exchange_id = exchange_id
        self.calls: list[dict[str, object]] = []

    def create_order(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "id": "ccxt-123",
            "symbol": kwargs["symbol"],
            "side": kwargs["side"],
            "type": kwargs["type"],
            "amount": kwargs["amount"],
            "price": kwargs.get("price"),
            "status": "open",
            "filled": 0,
        }

    def cancel_order(self, order_id: str, **kwargs):
        self.calls.append({"order_id": order_id})
        return {"id": order_id, "symbol": "BTC/USDT", "side": "buy", "amount": 1, "price": 50000, "status": "canceled"}

    def fetch_open_orders(self, symbol: str = ""):
        return []

    def fetch_balance(self):
        return {"total": {"USDT": 1000.0, "BTC": 0.01}, "free": {"USDT": 500.0, "BTC": 0.01}}

    def fetch_tickers(self):
        return {"BTC/USDT": {"last": 50000.0}}

    def market(self, symbol: str):
        return {"symbol": symbol}


def make_fake_ccxt_module():
    class FakeCcxt:
        binance = FakeCcxtExchange
        binanceth = FakeCcxtExchange
        kucoin = FakeCcxtExchange
        okx = FakeCcxtExchange
        bybit = FakeCcxtExchange

        class ExchangeNotAvailable(Exception):
            pass

        class NetworkError(Exception):
            pass

    return FakeCcxt()


@pytest.mark.asyncio
async def test_ccxt_broker_initializes_exchanges() -> None:
    settings = Settings(
        ccxt_enabled=True,
        ccxt_exchanges="binance",
        ccxt_sandbox=True,
    )
    fake_ccxt = make_fake_ccxt_module()
    with mock.patch.dict("sys.modules", {"ccxt": fake_ccxt}):
        broker = CcxtBroker(settings)
        assert "binance" in broker._exchanges


@pytest.mark.asyncio
async def test_ccxt_broker_raises_when_not_configured() -> None:
    settings = Settings(ccxt_enabled=False, ccxt_exchanges="")
    with pytest.raises(RuntimeError, match="not configured"):
        CcxtBroker(settings)


@pytest.mark.asyncio
async def test_ccxt_broker_place_order_maps_response() -> None:
    settings = Settings(
        ccxt_enabled=True,
        ccxt_exchanges="binance",
        ccxt_sandbox=True,
    )
    fake_ccxt = make_fake_ccxt_module()
    with mock.patch.dict("sys.modules", {"ccxt": fake_ccxt}):
        broker = CcxtBroker(settings)
        broker._exchanges = {"binance": FakeCcxtExchange("binance")}
        record = await broker.place_order(
            OrderIntent(
                symbol="BTC/USDT",
                side=Side.BUY,
                quantity=1,
                order_type=OrderType.LIMIT,
                price=50000.0,
                source="test",
            )
        )
        assert record.symbol == "BTC/USDT"
        assert record.side == Side.BUY
        assert record.status == OrderStatus.ACCEPTED
        assert record.broker_order_id.startswith("binance:")


@pytest.mark.asyncio
async def test_ccxt_broker_handles_network_error() -> None:
    settings = Settings(
        ccxt_enabled=True,
        ccxt_exchanges="binance",
        ccxt_sandbox=True,
    )
    fake_ccxt = make_fake_ccxt_module()
    with mock.patch.dict("sys.modules", {"ccxt": fake_ccxt}):
        broker = CcxtBroker(settings)
        exchange = FakeCcxtExchange("binance")

        def raise_network_error(**kwargs):
            raise fake_ccxt.NetworkError("timeout")

        exchange.create_order = raise_network_error
        broker._exchanges = {"binance": exchange}
        with pytest.raises(Exception, match="ambiguous"):
            await broker.place_order(
                OrderIntent(
                    symbol="BTC/USDT",
                    side=Side.BUY,
                    quantity=1,
                    order_type=OrderType.LIMIT,
                    price=50000.0,
                )
            )
