"""Instrument reference data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zksato_market.types import Instrument, MarketType
from zksato_core.money import Money
from zksato_core.exceptions import MarketDataError


@dataclass
class ReferenceData:
    """Reference data store."""

    instruments: dict[str, Instrument] = field(default_factory=dict)
    tick_sizes: dict[str, Money] = field(default_factory=dict)
    price_bands: dict[str, float] = field(default_factory=dict)
    sectors: dict[str, str] = field(default_factory=dict)

    def add_instrument(self, instrument: Instrument) -> None:
        """Add an instrument."""
        self.instruments[instrument.symbol] = instrument
        self.tick_sizes[instrument.symbol] = instrument.tick_size
        if instrument.price_band_pct:
            self.price_bands[instrument.symbol] = instrument.price_band_pct
        if instrument.sector:
            self.sectors[instrument.symbol] = instrument.sector

    def get_instrument(self, symbol: str) -> Instrument | None:
        """Get instrument by symbol."""
        return self.instruments.get(symbol)

    def get_tick_size(self, symbol: str) -> Money | None:
        """Get tick size for symbol."""
        return self.tick_sizes.get(symbol)

    def get_price_band(self, symbol: str) -> float | None:
        """Get price band percentage for symbol."""
        return self.price_bands.get(symbol)

    def get_sector(self, symbol: str) -> str | None:
        """Get sector for symbol."""
        return self.sectors.get(symbol)

    def is_tradable(self, symbol: str) -> bool:
        """Check if symbol is tradable."""
        inst = self.instruments.get(symbol)
        return inst.is_tradable if inst else False

    def validate_price(self, symbol: str, price: Money) -> bool:
        """Validate price against tick size."""
        tick_size = self.get_tick_size(symbol)
        if not tick_size:
            return True
        # Check if price is multiple of tick size
        return (price.amount / tick_size.amount) == int(price.amount / tick_size.amount)

    def validate_quantity(self, symbol: str, quantity: int) -> bool:
        """Validate quantity against board lot."""
        inst = self.instruments.get(symbol)
        if not inst:
            return True
        return quantity % inst.board_lot == 0

    def validate_price_band(self, symbol: str, price: Money, reference_price: Money) -> bool:
        """Validate price against price band."""
        band = self.get_price_band(symbol)
        if not band:
            return True
        if reference_price.amount == 0:
            return True
        deviation = abs(price.amount - reference_price.amount) / reference_price.amount * 100
        return deviation <= band


# Global reference data instance
_reference_data = ReferenceData()


def get_reference_data() -> ReferenceData:
    """Get global reference data instance."""
    return _reference_data


def load_reference_data(data: dict[str, Any]) -> None:
    """Load reference data from dict."""
    for symbol, info in data.items():
        instrument = Instrument(
            symbol=symbol,
            name=info.get("name", symbol),
            market_type=MarketType(info.get("market_type", "equity")),
            tick_size=Money(str(info.get("tick_size", "0.01"))),
            board_lot=info.get("board_lot", 100),
            price_band_pct=info.get("price_band_pct"),
            sector=info.get("sector"),
            is_tradable=info.get("is_tradable", True),
            metadata=info.get("metadata", {}),
        )
        _reference_data.add_instrument(instrument)