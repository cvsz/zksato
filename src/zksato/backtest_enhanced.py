"""
Enhanced backtesting engine with Freqtrade-compatible performance metrics.

All backtesting is advisory/research only — no order execution occurs.
Optimized with NumPy vectorization for speed on large datasets.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from zksato.domain import Candle
from zksato.strategy_freqtrade import ExitReason

logger = logging.getLogger(__name__)


# ── Result Dataclasses ─────────────────────────────────────────────────────


@dataclass
class TradeMetrics:
    """Per-trade metrics."""

    pair: str
    entry_time: datetime
    exit_time: datetime | None
    duration_seconds: float
    profit_abs: float
    profit_pct: float
    entry_price: float
    exit_price: float | None
    amount: float
    fee_abs: float
    side: str  # "long" or "short"
    exit_reason: str = ""
    entry_tag: str = ""
    exit_tag: str = ""
    position_size_pct: float = 0.0
    market_regime: str = ""
    position_adjustments: int = 0


@dataclass
class PairPerformance:
    pair: str
    trades: int
    avg_profit_pct: float
    total_profit_abs: float
    total_profit_pct: float
    wins: int
    draws: int
    losses: int
    win_rate: float


@dataclass
class ExitReasonStats:
    exit_reason: str
    exits: int
    avg_profit_pct: float
    total_profit_abs: float
    total_profit_pct: float
    wins: int
    draws: int
    losses: int
    win_rate: float


@dataclass
class EntryTagStats:
    tag: str
    trades: int
    avg_profit_pct: float
    total_profit_abs: float
    total_profit_pct: float
    wins: int
    losses: int
    win_rate: float


@dataclass
class PositionSizingStats:
    avg_position_size_pct: float
    max_position_size_pct: float
    min_position_size_pct: float
    total_position_adjustments: int


@dataclass
class BacktestSummaryMetrics:
    backtest_from: datetime
    backtest_to: datetime
    trading_mode: str = "paper"
    max_open_trades: int = 0
    total_trades: int = 0
    daily_avg_trades: float = 0.0
    starting_balance: float = 0.0
    final_balance: float = 0.0
    absolute_profit: float = 0.0
    total_profit_pct: float = 0.0
    cagr_pct: float = 0.0
    sharpe_closed: float | None = None
    sortino_closed: float | None = None
    calmar_closed: float | None = None
    sqn: float | None = None
    mean_profit_pvalue: float | None = None
    profit_factor: float | None = None
    expectancy_ratio: float | None = None
    avg_daily_profit: float = 0.0
    avg_stake_amount: float = 0.0
    market_change_pct: float = 0.0
    total_trade_volume: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    long_profit_pct: float = 0.0
    short_profit_pct: float = 0.0
    best_pair: str = ""
    best_pair_profit_pct: float = 0.0
    worst_pair: str = ""
    worst_pair_profit_pct: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    best_day_profit: float = 0.0
    worst_day_profit: float = 0.0
    days_win: int = 0
    days_draw: int = 0
    days_lose: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    rejected_entry_signals: int = 0
    entry_timeouts: int = 0
    exit_timeouts: int = 0
    min_balance_closed: float = 0.0
    max_balance_closed: float = 0.0
    max_underwater_pct: float = 0.0
    absolute_drawdown_abs: float = 0.0
    absolute_drawdown_pct: float = 0.0
    drawdown_duration_seconds: float = 0.0
    profit_at_drawdown_start: float = 0.0
    profit_at_drawdown_end: float = 0.0
    drawdown_start: datetime | None = None
    drawdown_end: datetime | None = None
    sharpe_wallet: float | None = None
    sortino_wallet: float | None = None
    calmar_wallet: float | None = None
    entry_tag_stats: list[EntryTagStats] = field(default_factory=list)
    position_sizing: PositionSizingStats | None = None
    order_expirations: int = 0


# ── Fast Metric Helpers ──────────────────────────────────────────────────


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365 * 24 * 60,
) -> float | None:
    if returns.empty or returns.std() == 0:
        return None
    excess_returns = returns - risk_free_rate / periods_per_year
    return float(np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std())


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365 * 24 * 60,
) -> float | None:
    if returns.empty:
        return None
    downside_returns = returns[returns < 0]
    if downside_returns.empty or downside_returns.std() == 0:
        return None
    excess_returns = returns - risk_free_rate / periods_per_year
    return float(np.sqrt(periods_per_year) * excess_returns.mean() / downside_returns.std())


def calculate_calmar_ratio(
    total_return_pct: float,
    max_drawdown_pct: float,
) -> float | None:
    if max_drawdown_pct == 0:
        return None
    return float(total_return_pct / max_drawdown_pct)


def calculate_sqn(returns: pd.Series) -> float | None:
    if returns.empty or returns.std() == 0:
        return None
    n = len(returns)
    return float(math.sqrt(n) * returns.mean() / returns.std())


def calculate_profit_factor(
    profits: pd.Series,
    losses: pd.Series,
) -> float | None:
    gross_profit = profits.sum() if not profits.empty else 0.0
    gross_loss = abs(losses.sum()) if not losses.empty else 0.0
    if gross_loss == 0:
        return None if gross_profit == 0 else float("inf")
    return float(gross_profit / gross_loss)


def calculate_expectancy(
    returns: pd.Series,
) -> tuple[float | None, float | None]:
    if returns.empty:
        return None, None
    avg_return = returns.mean()
    losing_trades = returns[returns < 0]
    avg_loss = abs(losing_trades.mean()) if not losing_trades.empty else 0.0
    expectancy_r = float(avg_return / avg_loss) if avg_loss > 0 else None
    return float(avg_return), expectancy_r


def calculate_max_drawdown(
    equity_curve: pd.Series,
) -> tuple[float, float, datetime, datetime, float]:
    if equity_curve.empty:
        return 0.0, 0.0, datetime.now(UTC), datetime.now(UTC), 0.0

    running_max = equity_curve.expanding(min_periods=1).max()
    drawdown = equity_curve - running_max
    drawdown_pct = drawdown / running_max.replace(0, np.nan)

    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown[max_dd_idx]
    max_dd_pct = drawdown_pct[max_dd_idx] if not pd.isna(drawdown_pct[max_dd_idx]) else 0.0

    # Get integer positions for DatetimeIndex
    max_dd_pos = equity_curve.index.get_loc(max_dd_idx)
    peak_pos = equity_curve.iloc[: max_dd_pos + 1].idxmax()
    # peak_pos is a Timestamp, get its integer position
    peak_int_pos = equity_curve.index.get_loc(peak_pos)

    dd_start = equity_curve.index[peak_int_pos]
    dd_end = equity_curve.index[max_dd_pos]

    duration = (dd_end - dd_start).total_seconds()

    return (
        float(abs(max_dd)),
        float(abs(max_dd_pct) * 100),
        dd_start.to_pydatetime() if hasattr(dd_start, "to_pydatetime") else dd_start,
        dd_end.to_pydatetime() if hasattr(dd_end, "to_pydatetime") else dd_end,
        duration,
    )


# ── Enhanced Backtest Engine ───────────────────────────────────────────────


class EnhancedBacktester:
    """Vectorized backtesting engine with Freqtrade-style metrics."""

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        commission_pct: float = 0.15,
        slippage_pct: float = 0.05,
        risk_free_rate: float = 0.02,
    ) -> None:
        self.initial_cash = initial_cash
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.risk_free_rate = risk_free_rate

    def run(
        self,
        symbol: str,
        candles: list[Candle],
        signals: pd.DataFrame | None,
        strategy_name: str = "unknown",
    ) -> dict[str, Any]:
        """Run enhanced backtest with vectorized signal processing."""
        if not candles:
            return self._empty_result(symbol, strategy_name)

        # Build price dataframe
        df = pd.DataFrame(
            [
                {
                    "date": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Merge signals
        if signals is not None and not signals.empty:
            signals = signals.copy()
            signals["date"] = pd.to_datetime(signals["date"])
            df = df.merge(signals, on="date", how="left")

        # Simulate trades (vectorized signal loop — single pass)
        trades = self._simulate_trades(df, symbol)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, df, symbol)

        # Pair performance
        pair_perf = self._calculate_pair_performance(trades)

        # Exit reason stats
        exit_reasons = self._calculate_exit_reason_stats(trades)

        return {
            "symbol": symbol,
            "strategy_name": strategy_name,
            "trades": trades,
            "metrics": metrics,
            "pair_performance": pair_perf,
            "exit_reasons": exit_reasons,
            "equity_curve": metrics.equity_curve if hasattr(metrics, "equity_curve") else [],
        }

    def _empty_result(self, symbol: str, strategy_name: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "strategy_name": strategy_name,
            "trades": [],
            "metrics": BacktestSummaryMetrics(
                backtest_from=datetime.now(UTC),
                backtest_to=datetime.now(UTC),
                starting_balance=self.initial_cash,
                final_balance=self.initial_cash,
            ),
            "pair_performance": [],
            "exit_reasons": [],
            "equity_curve": [],
        }

    # ── Trade Simulation (Single Pass Over DataFrame) ────────────────────

    def _simulate_trades(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[TradeMetrics]:
        trades: list[TradeMetrics] = []
        position: dict[str, Any] | None = None
        trade_id = 0
        pending_orders: list[dict[str, Any]] = []

        # Pre-extract columns as arrays for fast index-based access
        # (avoids the per-row Series allocation overhead of df.iterrows())
        dates = df["date"].to_numpy()
        closes = df["close"].to_numpy()
        enter_longs = df.get("enter_long", pd.Series([0] * len(df))).to_numpy()
        enter_shorts = df.get("enter_short", pd.Series([0] * len(df))).to_numpy()
        exit_longs = df.get("exit_long", pd.Series([0] * len(df))).to_numpy()
        exit_shorts = df.get("exit_short", pd.Series([0] * len(df))).to_numpy()
        stop_losses = df.get("stop_loss", pd.Series([None] * len(df))).to_numpy()
        take_profits = df.get("take_profit", pd.Series([None] * len(df))).to_numpy()
        enter_tags = df.get("enter_tag", pd.Series([""] * len(df))).to_numpy()
        exit_tags = df.get("exit_tag", pd.Series([""] * len(df))).to_numpy()
        market_regimes = df.get("market_regime", pd.Series([""] * len(df))).to_numpy()

        n = len(dates)
        for i in range(n):
            current_time = dates[i]
            current_price = closes[i]

            # Expire pending orders
            expired_orders = []
            for pending in pending_orders:
                if (
                    pending.get("order_expiration_candles") is not None
                    and pending.get("entry_candle_index") is not None
                    and i - pending["entry_candle_index"] >= pending["order_expiration_candles"]
                ):
                    expired_orders.append(pending)
            for expired in expired_orders:
                pending_orders.remove(expired)
                trades.append(
                    TradeMetrics(
                        pair=symbol,
                        entry_time=expired["entry_time"],
                        exit_time=current_time,
                        duration_seconds=(current_time - expired["entry_time"]).total_seconds(),
                        profit_abs=0.0,
                        profit_pct=0.0,
                        entry_price=expired["entry_price"],
                        exit_price=current_price,
                        amount=expired["amount"],
                        fee_abs=expired["fee_abs"],
                        side=expired["side"],
                        exit_reason=ExitReason.ORDER_EXPIRATION,
                        entry_tag=expired.get("entry_tag", ""),
                        exit_tag="order_expiration",
                        position_size_pct=expired.get("position_size_pct", 0.0),
                        market_regime=expired.get("market_regime", ""),
                        position_adjustments=expired.get("position_adjustments", 0),
                    )
                )

            # Exit checks
            if position is not None:
                exit_reason = self._check_exit_array(
                    position,
                    current_price,
                    enter_longs[i],
                    enter_shorts[i],
                    exit_longs[i],
                    exit_shorts[i],
                )
                if exit_reason:
                    exit_price = current_price
                    exit_price *= (
                        1 - self.slippage_pct / 100
                        if position["side"] == "long"
                        else 1 + self.slippage_pct / 100
                    )

                    profit_abs, profit_pct = self._calculate_profit(position, exit_price)

                    trades.append(
                        TradeMetrics(
                            pair=symbol,
                            entry_time=position["entry_time"],
                            exit_time=current_time,
                            duration_seconds=(
                                current_time - position["entry_time"]
                            ).total_seconds(),
                            profit_abs=profit_abs,
                            profit_pct=profit_pct,
                            entry_price=position["entry_price"],
                            exit_price=exit_price,
                            amount=position["amount"],
                            fee_abs=position["fee_abs"],
                            side=position["side"],
                            exit_reason=exit_reason,
                            entry_tag=position.get("entry_tag", ""),
                            exit_tag=str(exit_tags[i]),
                            position_size_pct=position.get("position_size_pct", 0.0),
                            market_regime=position.get("market_regime", ""),
                            position_adjustments=position.get("position_adjustments", 0),
                        )
                    )
                    position = None
                    continue

            # Entry checks
            if position is None:
                if enter_longs[i] == 1:
                    position = self._open_position_array(
                        trade_id,
                        symbol,
                        "long",
                        current_time,
                        current_price,
                        str(enter_tags[i]),
                        str(market_regimes[i]),
                        stop_losses[i],
                        take_profits[i],
                    )
                    position["entry_candle_index"] = i
                    trade_id += 1
                elif enter_shorts[i] == 1:
                    position = self._open_position_array(
                        trade_id,
                        symbol,
                        "short",
                        current_time,
                        current_price,
                        str(enter_tags[i]),
                        str(market_regimes[i]),
                        stop_losses[i],
                        take_profits[i],
                    )
                    position["entry_candle_index"] = i
                    trade_id += 1

        # Close remaining position at end
        if position is not None:
            last_price = closes[-1]
            last_time = dates[-1]
            exit_price = last_price
            exit_price *= (
                1 - self.slippage_pct / 100
                if position["side"] == "long"
                else 1 + self.slippage_pct / 100
            )
            profit_abs, profit_pct = self._calculate_profit(position, exit_price)
            trades.append(
                TradeMetrics(
                    pair=symbol,
                    entry_time=position["entry_time"],
                    exit_time=last_time,
                    duration_seconds=(last_time - position["entry_time"]).total_seconds(),
                    profit_abs=profit_abs,
                    profit_pct=profit_pct,
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    amount=position["amount"],
                    fee_abs=position["fee_abs"],
                    side=position["side"],
                    exit_reason=ExitReason.FORCE_EXIT,
                    entry_tag=position.get("entry_tag", ""),
                    exit_tag=str(exit_tags[-1]),
                    position_size_pct=position.get("position_size_pct", 0.0),
                    market_regime=position.get("market_regime", ""),
                    position_adjustments=position.get("position_adjustments", 0),
                )
            )

        return trades

    def _open_position(
        self,
        trade_id: int,
        symbol: str,
        side: str,
        entry_time: datetime,
        entry_price: float,
        row: pd.Series,
    ) -> dict[str, Any]:
        amount = self.initial_cash * 0.1
        fee_abs = amount * self.commission_pct / 100
        entry_price *= (
            1 + self.slippage_pct / 100 if side == "long" else 1 - self.slippage_pct / 100
        )
        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "amount": amount,
            "fee_abs": fee_abs,
            "stop_loss": row.get("stop_loss"),
            "take_profit": row.get("take_profit"),
            "entry_tag": row.get("enter_tag", ""),
            "position_size_pct": 10.0,
            "position_adjustments": 0,
            "market_regime": row.get("market_regime", ""),
        }

    def _open_position_array(
        self,
        trade_id: int,
        symbol: str,
        side: str,
        entry_time: Any,
        entry_price: float,
        entry_tag: str,
        market_regime: str,
        stop_loss: Any,
        take_profit: Any,
    ) -> dict[str, Any]:
        """Array-based position open — avoids row Series allocation."""
        amount = self.initial_cash * 0.1
        fee_abs = amount * self.commission_pct / 100
        entry_price *= (
            1 + self.slippage_pct / 100 if side == "long" else 1 - self.slippage_pct / 100
        )
        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "amount": amount,
            "fee_abs": fee_abs,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_tag": entry_tag,
            "position_size_pct": 10.0,
            "position_adjustments": 0,
            "market_regime": market_regime,
        }

    def _check_exit(
        self,
        position: dict[str, Any],
        row: pd.Series,
        df: pd.DataFrame,
    ) -> str | None:
        current_price = row["close"]

        if position["side"] == "long" and row.get("exit_long", 0) == 1:
            return ExitReason.EXIT_SIGNAL
        if position["side"] == "short" and row.get("exit_short", 0) == 1:
            return ExitReason.EXIT_SIGNAL

        stop_loss = position.get("stop_loss")
        if stop_loss is not None:
            if position["side"] == "long" and current_price <= stop_loss:
                return ExitReason.STOP_LOSS
            if position["side"] == "short" and current_price >= stop_loss:
                return ExitReason.STOP_LOSS

        take_profit = position.get("take_profit")
        if take_profit is not None:
            if position["side"] == "long" and current_price >= take_profit:
                return ExitReason.ROI
            if position["side"] == "short" and current_price <= take_profit:
                return ExitReason.ROI

        return None

    def _check_exit_array(
        self,
        position: dict[str, Any],
        current_price: float,
        enter_long: Any,
        enter_short: Any,
        exit_long: Any,
        exit_short: Any,
    ) -> str | None:
        """Array-based exit check — avoids row Series allocation."""
        if position["side"] == "long" and exit_long == 1:
            return ExitReason.EXIT_SIGNAL
        if position["side"] == "short" and exit_short == 1:
            return ExitReason.EXIT_SIGNAL

        stop_loss = position.get("stop_loss")
        if stop_loss is not None:
            if position["side"] == "long" and current_price <= stop_loss:
                return ExitReason.STOP_LOSS
            if position["side"] == "short" and current_price >= stop_loss:
                return ExitReason.STOP_LOSS

        take_profit = position.get("take_profit")
        if take_profit is not None:
            if position["side"] == "long" and current_price >= take_profit:
                return ExitReason.ROI
            if position["side"] == "short" and current_price <= take_profit:
                return ExitReason.ROI

        return None

    def _calculate_profit(
        self,
        position: dict[str, Any],
        exit_price: float,
    ) -> tuple[float, float]:
        entry_price = position["entry_price"]
        amount = position["amount"]
        fee_abs = position["fee_abs"]

        if position["side"] == "long":
            profit_abs = (exit_price - entry_price) * amount - fee_abs
        else:
            profit_abs = (entry_price - exit_price) * amount - fee_abs

        profit_pct = (
            (profit_abs / (entry_price * amount)) * 100 if entry_price * amount > 0 else 0.0
        )
        return profit_abs, profit_pct

    def _calculate_metrics(
        self,
        trades: list[TradeMetrics],
        df: pd.DataFrame,
        symbol: str,
    ) -> BacktestSummaryMetrics:
        if not trades:
            return BacktestSummaryMetrics(
                backtest_from=df["date"].iloc[0] if not df.empty else datetime.now(UTC),
                backtest_to=df["date"].iloc[-1] if not df.empty else datetime.now(UTC),
                starting_balance=self.initial_cash,
                final_balance=self.initial_cash,
            )

        profits = [t.profit_pct for t in trades]
        profit_abs_values = [t.profit_abs for t in trades]

        total_profit_abs = sum(profit_abs_values)
        total_profit_pct = (total_profit_abs / self.initial_cash) * 100
        final_balance = self.initial_cash + total_profit_abs

        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]

        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

        avg_return = sum(profits) / len(profits)
        avg_loss = abs(sum(losing_trades) / len(losing_trades)) if losing_trades else 0.0
        expectancy_r = (avg_return / avg_loss) if avg_loss > 0 else None

        returns_series = pd.Series(profits)
        sharpe = calculate_sharpe_ratio(returns_series, self.risk_free_rate)
        sortino = calculate_sortino_ratio(returns_series, self.risk_free_rate)

        equity_curve = []
        running_balance = self.initial_cash
        for t in trades:
            running_balance += t.profit_abs
            equity_curve.append(running_balance)

        equity_series = pd.Series(
            equity_curve,
            index=[t.exit_time or t.entry_time for t in trades],
        )
        dd_abs, dd_pct, dd_start, dd_end, dd_duration = calculate_max_drawdown(equity_series)

        calmar = calculate_calmar_ratio(total_profit_pct, dd_pct)
        sqn = calculate_sqn(returns_series)

        start_date = df["date"].iloc[0]
        end_date = df["date"].iloc[-1]
        days = (end_date - start_date).total_seconds() / 86400
        years = days / 365.25
        if years > 0 and final_balance > 0 and self.initial_cash > 0:
            ratio = final_balance / self.initial_cash
            # Clamp ratio to prevent overflow in exp/log
            ratio = max(min(ratio, 1e6), 1e-6)
            # Check exponent magnitude before computing
            exponent = np.log(ratio) / years
            if exponent > 20:  # exp(20) ~ 4.8e8, safe
                cagr = 1e6
            elif exponent < -20:
                cagr = -100.0
            else:
                cagr = float((np.exp(exponent) - 1) * 100)
            cagr = max(min(cagr, 1e6), -100.0)
        else:
            cagr = 0.0

        best_pair = symbol
        best_pair_pct = total_profit_pct
        worst_pair = symbol
        worst_pair_pct = total_profit_pct

        best_trade_pct = max(profits) if profits else 0.0
        worst_trade_pct = min(profits) if profits else 0.0

        long_trades_list = [t for t in trades if t.side == "long"]
        short_trades_list = [t for t in trades if t.side == "short"]
        long_profit_pct = sum(t.profit_pct for t in long_trades_list)
        short_profit_pct = sum(t.profit_pct for t in short_trades_list)

        daily_profits: dict[str, float] = {}
        for t in trades:
            day = (
                t.exit_time.strftime("%Y-%m-%d")
                if t.exit_time
                else t.entry_time.strftime("%Y-%m-%d")
            )
            daily_profits[day] = daily_profits.get(day, 0.0) + t.profit_abs
        days_win = sum(1 for p in daily_profits.values() if p > 0)
        days_draw = sum(1 for p in daily_profits.values() if p == 0)
        days_lose = sum(1 for p in daily_profits.values() if p < 0)

        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        for p in profits:
            if p > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            elif p < 0:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0

        best_day = max(daily_profits.values()) if daily_profits else 0.0
        worst_day = min(daily_profits.values()) if daily_profits else 0.0

        min_balance = min(equity_curve) if equity_curve else self.initial_cash
        max_balance = max(equity_curve) if equity_curve else self.initial_cash

        return BacktestSummaryMetrics(
            backtest_from=start_date.to_pydatetime()
            if hasattr(start_date, "to_pydatetime")
            else start_date,
            backtest_to=end_date.to_pydatetime()
            if hasattr(end_date, "to_pydatetime")
            else end_date,
            total_trades=len(trades),
            daily_avg_trades=len(trades) / max(days, 1),
            starting_balance=self.initial_cash,
            final_balance=final_balance,
            absolute_profit=total_profit_abs,
            total_profit_pct=total_profit_pct,
            cagr_pct=cagr,
            sharpe_closed=sharpe,
            sortino_closed=sortino,
            calmar_closed=calmar,
            sqn=sqn,
            profit_factor=profit_factor,
            expectancy_ratio=expectancy_r,
            avg_daily_profit=total_profit_abs / max(days, 1),
            avg_stake_amount=self.initial_cash * 0.1,
            best_pair=best_pair,
            best_pair_profit_pct=best_pair_pct,
            worst_pair=worst_pair,
            worst_pair_profit_pct=worst_pair_pct,
            best_trade_pct=best_trade_pct,
            worst_trade_pct=worst_trade_pct,
            best_day_profit=best_day,
            worst_day_profit=worst_day,
            long_profit_pct=long_profit_pct,
            short_profit_pct=short_profit_pct,
            days_win=days_win,
            days_draw=days_draw,
            days_lose=days_lose,
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            min_balance_closed=min_balance,
            max_balance_closed=max_balance,
            max_underwater_pct=dd_pct,
            absolute_drawdown_abs=dd_abs,
            absolute_drawdown_pct=dd_pct,
            drawdown_duration_seconds=dd_duration,
            profit_at_drawdown_start=0.0,
            profit_at_drawdown_end=total_profit_abs,
            drawdown_start=dd_start,
            drawdown_end=dd_end,
            entry_tag_stats=self._calculate_entry_tag_stats(trades),
            position_sizing=self._calculate_position_sizing(trades),
            order_expirations=sum(
                1 for t in trades if t.exit_reason == ExitReason.ORDER_EXPIRATION.value
            ),
        )

    def _calculate_entry_tag_stats(
        self,
        trades: list[TradeMetrics],
    ) -> list[EntryTagStats]:
        tags: dict[str, list[TradeMetrics]] = {}
        for t in trades:
            tag = t.entry_tag or "untagged"
            tags.setdefault(tag, []).append(t)

        results = []
        for tag, tag_trades in tags.items():
            profits = [t.profit_pct for t in tag_trades]
            wins = sum(1 for p in profits if p > 0)
            losses = sum(1 for p in profits if p < 0)
            total_profit = sum(t.profit_abs for t in tag_trades)
            total_profit_pct = sum(profits)

            results.append(
                EntryTagStats(
                    tag=tag,
                    trades=len(tag_trades),
                    avg_profit_pct=total_profit_pct / len(profits) if profits else 0.0,
                    total_profit_abs=total_profit,
                    total_profit_pct=total_profit_pct,
                    wins=wins,
                    losses=losses,
                    win_rate=(wins / len(profits) * 100) if profits else 0.0,
                )
            )

        results.sort(key=lambda r: r.total_profit_pct, reverse=True)
        return results

    def _calculate_position_sizing(
        self,
        trades: list[TradeMetrics],
    ) -> PositionSizingStats | None:
        if not trades:
            return None

        position_sizes = [t.position_size_pct for t in trades if t.position_size_pct > 0]
        if not position_sizes:
            return None

        total_adjustments = sum(t.position_adjustments for t in trades)

        return PositionSizingStats(
            avg_position_size_pct=sum(position_sizes) / len(position_sizes),
            max_position_size_pct=max(position_sizes),
            min_position_size_pct=min(position_sizes),
            total_position_adjustments=total_adjustments,
        )

    def _calculate_pair_performance(
        self,
        trades: list[TradeMetrics],
    ) -> list[PairPerformance]:
        pairs: dict[str, list[TradeMetrics]] = {}
        for t in trades:
            pairs.setdefault(t.pair, []).append(t)

        results = []
        for pair, pair_trades in pairs.items():
            profits = [t.profit_pct for t in pair_trades]
            wins = sum(1 for p in profits if p > 0)
            losses = sum(1 for p in profits if p < 0)
            draws = len(profits) - wins - losses
            total_profit = sum(t.profit_abs for t in pair_trades)
            total_profit_pct = sum(profits)

            results.append(
                PairPerformance(
                    pair=pair,
                    trades=len(pair_trades),
                    avg_profit_pct=total_profit_pct / len(profits) if profits else 0.0,
                    total_profit_abs=total_profit,
                    total_profit_pct=total_profit_pct,
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    win_rate=(wins / len(profits) * 100) if profits else 0.0,
                )
            )

        results.sort(key=lambda p: p.total_profit_pct, reverse=True)
        return results

    def _calculate_exit_reason_stats(
        self,
        trades: list[TradeMetrics],
    ) -> list[ExitReasonStats]:
        reasons: dict[str, list[TradeMetrics]] = {}
        for t in trades:
            reasons.setdefault(t.exit_reason, []).append(t)

        results = []
        for reason, reason_trades in reasons.items():
            profits = [t.profit_pct for t in reason_trades]
            wins = sum(1 for p in profits if p > 0)
            losses = sum(1 for p in profits if p < 0)
            draws = len(profits) - wins - losses
            total_profit = sum(t.profit_abs for t in reason_trades)
            total_profit_pct = sum(profits)

            results.append(
                ExitReasonStats(
                    exit_reason=reason,
                    exits=len(reason_trades),
                    avg_profit_pct=total_profit_pct / len(profits) if profits else 0.0,
                    total_profit_abs=total_profit,
                    total_profit_pct=total_profit_pct,
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    win_rate=(wins / len(profits) * 100) if profits else 0.0,
                )
            )

        results.sort(key=lambda r: r.total_profit_pct, reverse=True)
        return results
