# zksato-core

Core domain types and utilities for the zksato trading platform.

## Contents

- **Types**: Shared enums, type aliases, constants
- **IDs**: ULID, idempotency keys, correlation IDs
- **Money**: Decimal money handling with THB currency support
- **Datetime**: Bangkok timezone, market sessions, calendar
- **Serialization**: JSON/msgpack serialization, Pydantic helpers
- **Exceptions**: Domain exception hierarchy
- **Events**: Event base classes, event store interface
- **Config**: Configuration base classes with TOML support
- **Models**: Core domain models (orders, fills, positions, accounts, etc.)

## Installation

```bash
pip install -e packages/zksato-core
```

## Usage

```python
from zksato_core import (
    Side, OrderType, OrderStatus,
    Money, thb,
    now_bangkok, MarketCalendar,
    OrderIntent, RiskContext, RiskDecision,
    OrderRecord, FillRecord, Position,
    PortfolioSnapshot, StrategyConfig,
)
```