# Strategy operator guide

## Research workflow
1. ingest/verify bars;
2. register immutable strategy version;
3. replay/backtest with explicit fees/slippage;
4. run walk-forward/OOS analysis;
5. inspect drawdown, trade count, profit factor, exposure, benchmark, and drift;
6. record limitations/bias;
7. promote only through documented research → paper → UAT → manual-live-readiness evidence.

## Paper automation
Use paper mode for bot start/pause/resume/stop/tick testing and order simulation. Paper fills do not prove real liquidity or queue position.

## Authority boundary
Strategy output is advisory input to deterministic risk/execution. Strategy operators cannot grant themselves unrestricted live broker authority and no strategy version can autonomously promote to live execution.
