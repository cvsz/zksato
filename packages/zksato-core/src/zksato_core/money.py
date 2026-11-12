"""Decimal money handling and currency utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

Numeric = int | float | Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable money value with currency."""

    amount: Decimal
    currency: str = "THB"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.currency != "THB":
            raise ValueError("Only THB currency is supported")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Numeric) -> Money:
        if not isinstance(factor, (int, float, Decimal)):
            return NotImplemented
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __truediv__(self, divisor: Numeric) -> Money:
        if not isinstance(divisor, (int, float, Decimal)):
            return NotImplemented
        if divisor == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Money(self.amount / Decimal(str(divisor)), self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        return self == other or self < other

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        return self == other or self > other

    def abs(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def quantize(self, exp: str = "0.01") -> Money:
        """Quantize to specified decimal places."""
        return Money(
            self.amount.quantize(Decimal(exp), rounding=ROUND_HALF_UP),
            self.currency,
        )

    def to_float(self) -> float:
        return float(self.amount)

    def to_int(self) -> int:
        return int(self.amount)

    @classmethod
    def zero(cls, currency: str = "THB") -> Money:
        return cls(Decimal("0"), currency)

    @classmethod
    def from_float(cls, value: float, currency: str = "THB") -> Money:
        return cls(Decimal(str(value)), currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency!r})"


def thb(amount: Numeric) -> Money:
    """Create Money in THB."""
    return Money(Decimal(str(amount)), "THB")


# Board lot constant for SET
BOARD_LOT = 100


def round_to_board_lot(quantity: int) -> int:
    """Round quantity down to nearest board lot."""
    return (quantity // BOARD_LOT) * BOARD_LOT


def is_board_lot(quantity: int) -> bool:
    """Check if quantity is a valid board lot."""
    return quantity % BOARD_LOT == 0
