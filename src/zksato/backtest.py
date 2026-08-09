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
        entry_fee = 0.0
        prices: list[float] = []
        trades: list[BacktestTrade] = []
        equity_curve: list[float] = []
        closed_pnls: list[float] = []
        wins = 0
        closed = 0
        fees_paid = 0.0
        bars_exposed = 0
        commission_rate = request.commission_pct / 100
        slippage_rate = request.slippage_pct / 100

        for candle in request.candles:
            prices.append(candle.close)
            signal = self.strategy.evaluate(request.symbol.upper(), prices, request.strategy)
            if signal.action == SignalAction.BUY and quantity == 0:
                buy_price = candle.close * (1 + slippage_rate)
                max_qty = int(cash / (buy_price * (1 + commission_rate)))
                buy_qty = min(request.order_size, max_qty)
                if buy_qty > 0:
                    cost = buy_price * buy_qty
                    entry_fee = cost * commission_rate
                    fees_paid += entry_fee
                    cash -= cost + entry_fee
                    quantity = buy_qty
                    average_price = buy_price
                    trades.append(
                        BacktestTrade(
                            side=Side.BUY,
                            timestamp=candle.timestamp,
                            price=buy_price,
                            quantity=buy_qty,
                            fee=entry_fee,
                        )
                    )
            elif signal.action == SignalAction.SELL and quantity > 0:
                sell_price = candle.close * (1 - slippage_rate)
                proceeds = sell_price * quantity
                exit_fee = proceeds * commission_rate
                fees_paid += exit_fee
                pnl = (sell_price - average_price) * quantity - entry_fee - exit_fee
                cash += proceeds - exit_fee
                closed += 1
                closed_pnls.append(pnl)
                if pnl > 0:
                    wins += 1
                trades.append(
                    BacktestTrade(
                        side=Side.SELL,
                        timestamp=candle.timestamp,
                        price=sell_price,
                        quantity=quantity,
                        pnl=pnl,
                        fee=exit_fee,
                    )
                )
                quantity = 0
                average_price = 0.0
                entry_fee = 0.0
            if quantity > 0:
                bars_exposed += 1
            equity_curve.append(cash + (quantity * candle.close))

        final_price = request.candles[-1].close
        final_equity = cash + (quantity * final_price)
        total_return = (final_equity - request.initial_cash) / request.initial_cash * 100
        gross_profit = sum(value for value in closed_pnls if value > 0)
        gross_loss = sum(-value for value in closed_pnls if value < 0)
        first_price = request.candles[0].close
        buy_and_hold = ((final_price - first_price) / first_price * 100) if first_price else 0.0
        return BacktestResult(
            symbol=request.symbol.upper(),
            initial_cash=request.initial_cash,
            final_equity=final_equity,
            total_return_pct=total_return,
            max_drawdown_pct=max_drawdown_pct(equity_curve),
            total_trades=len(trades),
            win_rate_pct=(wins / closed * 100) if closed else 0.0,
            closed_trades=closed,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else None,
            average_closed_trade_pnl=(sum(closed_pnls) / closed) if closed else 0.0,
            fees_paid=fees_paid,
            exposure_pct=(bars_exposed / len(request.candles) * 100) if request.candles else 0.0,
            buy_and_hold_return_pct=buy_and_hold,
            trades=trades,
            equity_curve=equity_curve,
        )
