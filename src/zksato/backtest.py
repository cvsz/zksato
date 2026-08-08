from __future__ import annotations

from zksato.domain import BacktestRequest, BacktestResult, BacktestTrade, Side, SignalAction
from zksato.indicators import max_drawdown_pct
from zksato.strategy import StrategyEngine


class Backtester:
    def __init__(self) -> None:
        self.strategy = StrategyEngine()

    def run(self, request: BacktestRequest) -> BacktestResult:
        cash = request.initial_cash
        quantity = 0
        average_price = 0.0
        prices: list[float] = []
        trades: list[BacktestTrade] = []
        equity_curve: list[float] = []
        wins = 0
        closed = 0
        commission_rate = request.commission_pct / 100

        for candle in request.candles:
            prices.append(candle.close)
            signal = self.strategy.evaluate(request.symbol.upper(), prices, request.strategy)
            if signal.action == SignalAction.BUY and quantity == 0:
                max_qty = int(cash / (candle.close * (1 + commission_rate)))
                buy_qty = min(request.order_size, max_qty)
                if buy_qty > 0:
                    cost = candle.close * buy_qty
                    fee = cost * commission_rate
                    cash -= cost + fee
                    quantity = buy_qty
                    average_price = candle.close
                    trades.append(
                        BacktestTrade(
                            side=Side.BUY,
                            timestamp=candle.timestamp,
                            price=candle.close,
                            quantity=buy_qty,
                        )
                    )
            elif signal.action == SignalAction.SELL and quantity > 0:
                proceeds = candle.close * quantity
                fee = proceeds * commission_rate
                pnl = (candle.close - average_price) * quantity - fee
                cash += proceeds - fee
                closed += 1
                if pnl > 0:
                    wins += 1
                trades.append(
                    BacktestTrade(
                        side=Side.SELL,
                        timestamp=candle.timestamp,
                        price=candle.close,
                        quantity=quantity,
                        pnl=pnl,
                    )
                )
                quantity = 0
                average_price = 0.0
            equity_curve.append(cash + (quantity * candle.close))

        final_price = request.candles[-1].close
        final_equity = cash + (quantity * final_price)
        total_return = (final_equity - request.initial_cash) / request.initial_cash * 100
        return BacktestResult(
            symbol=request.symbol.upper(),
            initial_cash=request.initial_cash,
            final_equity=final_equity,
            total_return_pct=total_return,
            max_drawdown_pct=max_drawdown_pct(equity_curve),
            total_trades=len(trades),
            win_rate_pct=(wins / closed * 100) if closed else 0.0,
            trades=trades,
            equity_curve=equity_curve,
        )
