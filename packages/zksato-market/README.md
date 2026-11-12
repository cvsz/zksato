# zksato-market

Market data, feeds, and adapters for the zksato trading platform.

## Contents

- **Types**: Market data types (Quote, Trade, Bar, Instrument, FeedEvent)
- **Feeds**: Real-time feeds (Settrade, CCXT), composite feeds, replay feed
- **Adapters**: REST adapters for Settrade and CCXT exchanges
- **Reference**: Instrument reference data with tick sizes, price bands
- **Calendar**: Market calendar with sessions and holidays
- **Scanner**: Market screening and filtering

## Installation

```bash
pip install -e packages/zksato-market
# With Settrade support
pip install -e 'packages/zksato-market[settrade]'
# With CCXT support
pip install -e 'packages/zksato-market[ccxt]'
```

## Usage

```python
from zksato_market import (
    SettradeAdapter,
    CCXTAdapter,
    MarketScanner,
    TradingCalendar,
)

# Settrade adapter
adapter = SettradeAdapter(app_id="...", app_secret="...", broker_id="...", app_code="...")
quote = await adapter.get_quote("AOT")

# CCXT adapter for Binance
binance = CCXTAdapter("binance", api_key="...", secret="...", sandbox=True)
quote = await binance.get_quote("BTC/USDT")

# Market scanner
scanner = MarketScanner(adapter)
results = await scanner.scan(["AOT", "PTT", "CPALL"])

# Trading calendar
calendar = TradingCalendar.create_default()
is_open = calendar.is_session_open(datetime.now())
```