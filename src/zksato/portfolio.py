from __future__ import annotations

from dataclasses import asdict, dataclass

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
        self._restore()

    def _restore(self) -> None:
        state = self.store.get_paper_account()
        if not state:
            self._persist()
            return
        self.initial_cash = float(state.get("initial_cash", self.initial_cash))
        self.cash = float(state.get("cash", self.initial_cash))
        self.realized_pnl = float(state.get("realized_pnl", 0.0))
        self._day_start_equity = float(
            state.get("day_start_equity", self.initial_cash)
        )
        self._peak_equity = float(state.get("peak_equity", self.initial_cash))
        raw_holdings = state.get("holdings", {})
        if isinstance(raw_holdings, dict):
            for symbol, raw in raw_holdings.items():
                if not isinstance(symbol, str) or not isinstance(raw, dict):
                    continue
                quantity = int(raw.get("quantity", 0) or 0)
                average_price = float(raw.get("average_price", 0) or 0)
                self.holdings[symbol] = Holding(
                    quantity=max(quantity, 0),
                    average_price=max(average_price, 0),
                )

    def _persist(self) -> None:
        self.store.save_paper_account(
            {
                "version": 1,
                "initial_cash": self.initial_cash,
                "cash": self.cash,
                "realized_pnl": self.realized_pnl,
                "day_start_equity": self._day_start_equity,
                "peak_equity": self._peak_equity,
                "holdings": {
                    symbol: asdict(holding) for symbol, holding in self.holdings.items()
                },
            }
        )

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
            self._persist()
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
        self._persist()

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
        if equity > self._peak_equity:
            self._peak_equity = equity
            self._persist()
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
