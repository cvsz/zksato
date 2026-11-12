"""Backtesting engine for zksato strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from zksato_core.types import OrderType, SignalAction, Side
from zksato_core.models import Candle, OrderIntent, OrderRecord, OrderStatus, Signal, StrategyConfig
from zksato_strategy.strategies.classic import StrategyEngine


@dataclass
class BacktestTrade:
    """A single trade in backtest."""
    entry_time: datetime
    exit_time: datetime | None
    symbol: str
    side: Side
    entry_price: float
    exit_price: float | None
    quantity: float
    pnl: float | None
    pnl_pct: float | None
    duration_minutes: float | None


@dataclass
class BacktestResult:
    """Backtest results."""
    strategy_name: str
    symbol: str
    start_time: datetime
    end_time: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float | None
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float | None
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)


class PaperPortfolio:
    """Simple paper portfolio for backtesting."""
    
    def __init__(self, initial_cash: float = 500_000.0) -> None:
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: dict[str, dict] = {}
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[float] = [initial_cash]
    
    def get_equity(self, prices: dict[str, float]) -> float:
        """Calculate current equity."""
        equity = self.cash
        for symbol, pos in self.positions.items():
            price = prices.get(symbol, pos.get("avg_price", 0))
            equity += pos["quantity"] * price * (1 if pos["side"] == Side.BUY else -1)
        return equity
    
    def execute_signal(self, signal: Signal, price: float, timestamp: datetime) -> BacktestTrade | None:
        """Execute a signal and return trade if closed."""
        if signal.action == SignalAction.HOLD:
            return None
        
        symbol = signal.symbol
        side = Side.BUY if signal.action == SignalAction.BUY else Side.SELL
        quantity = 100  # Fixed for now
        
        # Check if we have an existing position
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos["side"] == side:
                # Add to position
                total_qty = pos["quantity"] + quantity
                pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + price * quantity) / total_qty
                pos["quantity"] = total_qty
                self.cash -= price * quantity if side == Side.BUY else -price * quantity
                return None
            else:
                # Close or reduce position
                close_qty = min(pos["quantity"], quantity)
                pnl = (price - pos["avg_price"]) * close_qty * (1 if pos["side"] == Side.BUY else -1)
                
                trade = BacktestTrade(
                    entry_time=pos["entry_time"],
                    exit_time=timestamp,
                    symbol=symbol,
                    side=pos["side"],
                    entry_price=pos["avg_price"],
                    exit_price=price,
                    quantity=close_qty,
                    pnl=pnl,
                    pnl_pct=pnl / (pos["avg_price"] * close_qty) * 100,
                    duration_minutes=(timestamp - pos["entry_time"]).total_seconds() / 60,
                )
                self.trades.append(trade)
                self.cash += price * close_qty
                
                if pos["quantity"] <= close_qty:
                    del self.positions[symbol]
                else:
                    pos["quantity"] -= close_qty
                
                return trade
        else:
            # New position
            cost = price * quantity
            if side == Side.BUY and self.cash < cost:
                return None
            if side == Side.SELL:
                # Short selling - check if allowed
                pass
            
            self.positions[symbol] = {
                "side": side,
                "quantity": quantity,
                "avg_price": price,
                "entry_time": timestamp,
            }
            self.cash -= cost if side == Side.BUY else -cost
            return None
    
    def close_all(self, prices: dict[str, float], timestamp: datetime) -> list[BacktestTrade]:
        """Close all positions."""
        closed = []
        for symbol, pos in list(self.positions.items()):
            price = prices.get(symbol, pos["avg_price"])
            pnl = (price - pos["avg_price"]) * pos["quantity"] * (1 if pos["side"] == Side.BUY else -1)
            
            trade = BacktestTrade(
                entry_time=pos["entry_time"],
                exit_time=timestamp,
                symbol=symbol,
                side=pos["side"],
                entry_price=pos["avg_price"],
                exit_price=price,
                quantity=pos["quantity"],
                pnl=pnl,
                pnl_pct=pnl / (pos["avg_price"] * pos["quantity"]) * 100,
                duration_minutes=(timestamp - pos["entry_time"]).total_seconds() / 60,
            )
            closed.append(trade)
            self.cash += price * pos["quantity"]
        
        self.trades.extend(closed)
        self.positions.clear()
        return closed


class BacktestEngine:
    """Backtesting engine for strategy evaluation."""
    
    def __init__(self, initial_cash: float = 500_000.0) -> None:
        self.initial_cash = initial_cash
        self.strategy_engine = StrategyEngine()
    
    def run(
        self,
        candles: list[Candle],
        config: StrategyConfig,
        sentiment_scores: list[float] | None = None,
    ) -> BacktestResult:
        """Run backtest on historical candles."""
        if not candles:
            raise ValueError("No candles provided")
        
        portfolio = PaperPortfolio(self.initial_cash)
        prices = [c.close for c in candles]
        timestamps = [c.timestamp for c in candles]
        
        for i, candle in enumerate(candles):
            # Update equity curve
            current_prices = {candle.symbol: candle.close}
            equity = portfolio.get_equity(current_prices)
            portfolio.equity_curve.append(equity)
            
            # Get sentiment score if available
            sentiment = sentiment_scores[i] if sentiment_scores and i < len(sentiment_scores) else None
            
            # Evaluate strategy
            signal = self.strategy_engine.evaluate(
                symbol=candle.symbol,
                prices=prices[:i+1],
                config=config,
                sentiment_score=sentiment,
                candles=candles[:i+1],
            )
            
            # Execute signal
            if signal.action != SignalAction.HOLD:
                portfolio.execute_signal(signal, candle.close, candle.timestamp)
        
        # Close all positions at end
        final_prices = {candle.symbol: candles[-1].close}
        portfolio.close_all(final_prices, candles[-1].timestamp)
        
        # Calculate results
        return self._calculate_results(config.name, candle.symbol, candles[0].timestamp, candles[-1].timestamp, portfolio)
    
    def _calculate_results(
        self,
        strategy_name: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        portfolio: PaperPortfolio,
    ) -> BacktestResult:
        trades = portfolio.trades
        equity_curve = portfolio.equity_curve
        
        final_capital = equity_curve[-1] if equity_curve else self.initial_cash
        total_return = final_capital - self.initial_cash
        total_return_pct = (total_return / self.initial_cash) * 100
        
        # Max drawdown
        peak = self.initial_cash
        max_drawdown = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            drawdown = peak - eq
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        max_drawdown_pct = (max_drawdown / peak) * 100 if peak > 0 else 0.0
        
        # Trade statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        wins = [t.pnl for t in trades if t.pnl and t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl and t.pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        
        # Sharpe ratio (simplified)
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] for i in range(1, len(equity_curve))]
        sharpe = None
        if returns:
            import numpy as np
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe = mean_return / std_return * (252 ** 0.5)  # Annualized
        
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            initial_capital=self.initial_cash,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_curve,
        )