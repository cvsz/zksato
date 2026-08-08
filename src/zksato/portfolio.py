from __future__ import annotations

from dataclasses import dataclass

from zksato.domain import PortfolioSnapshot, Position, Side
from zksato.store import StateStore


@dataclass
class Holding:
    quantity: int = 0
    average_price: float = 0.0


class PaperPortfolio:
    def __init__(self, store: StateStore, initial_cash: float) -> None:
        self.store = store
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.realized_pnl = 0.0
        self.holdings: dict[str, Holding] = {}
        self._day_start_equity = initial_cash
        self._peak_equity = initial_cash

    def can_sell(self, symbol: str, quantity: int) -> bool:
        return self.holdings.get(symbol, Holding()).quantity >= quantity

    def apply_fill(self, symbol: str, side: Side, quantity: int, price: float) -> None:
        holding = self.holdings.setdefault(symbol, Holding())
        if side == Side.BUY:
            cost = quantity * price
            if cost > self.cash:
                raise ValueError("insufficient paper cash")
            new_quantity = holding.quantity + quantity
            weighted_cost = (holding.quantity * holding.average_price) + cost
            holding.quantity = new_quantity
            holding.average_price = weighted_cost / new_quantity
            self.cash -= cost
            return

        if quantity > holding.quantity:
            raise ValueError("cannot sell more than paper position")
        proceeds = quantity * price
        pnl = (price - holding.average_price) * quantity
        holding.quantity -= quantity
        self.cash += proceeds
        self.realized_pnl += pnl
        if holding.quantity == 0:
            holding.average_price = 0.0

    def snapshot(self) -> PortfolioSnapshot:
        positions: list[Position] = []
        market_value = 0.0
        unrealized_pnl = 0.0
        for symbol, holding in sorted(self.holdings.items()):
            if holding.quantity <= 0:
                continue
            quote = self.store.get_quote(symbol)
            market_price = quote.last if quote else holding.average_price
            value = market_price * holding.quantity
            cost = holding.average_price * holding.quantity
            pnl = value - cost
            pnl_pct = (pnl / cost * 100) if cost else 0.0
            market_value += value
            unrealized_pnl += pnl
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=holding.quantity,
                    average_price=holding.average_price,
                    market_price=market_price,
                    market_value=value,
                    cost_value=cost,
                    unrealized_pnl=pnl,
                    unrealized_pnl_pct=pnl_pct,
                )
            )
        equity = self.cash + market_value
        self._peak_equity = max(self._peak_equity, equity)
        daily_pnl = equity - self._day_start_equity
        return PortfolioSnapshot(
            cash=self.cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized_pnl,
            daily_pnl=daily_pnl,
            positions=positions,
        )

    def drawdown_pct(self) -> float:
        equity = self.snapshot().equity
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - equity) / self._peak_equity * 100)

    def daily_pnl_pct(self) -> float:
        if self._day_start_equity <= 0:
            return 0.0
        return self.snapshot().daily_pnl / self._day_start_equity * 100
