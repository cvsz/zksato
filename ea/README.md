# zksato MQL5 research EA

`ZKSATO_VideoDerived_PA_Grid.mq5` is a **Strategy Tester / demo-account reference implementation** derived from the three supplied videos. It is not the trusted SET/Settrade execution path and deliberately refuses MetaTrader real accounts during `OnInit()`.

## What it reproduces

- PA-zone confirmation using rejection candles / engulfing behavior
- breakout → retest / support-resistance flip bias
- fixed-size stop-order ladder
- optional two-sided symmetric grid for research reproduction
- basket profit close/reset
- basket maximum-loss close/reset
- fixed lot size; no martingale
- maximum positions, pending orders and cycle volume
- spread gate, session gate and cooldown
- symbol volume min/max/step normalization
- trade stops/freeze-level validation
- explicit trade-server `ResultRetcode()` validation
- hedging/netting account detection
- netting mode fails closed when a foreign magic number already owns the symbol
- specified pending-order expiry and duplicate-comment recovery after restart
- Strategy Tester statistics CSV export

Preset files are provided under `ea/presets/` for SET-style PA-filtered research and TFEX/generic symmetric research. They are starting points for Strategy Tester/demo validation, not broker-certified parameters.

The default `InpGridStepPrice=0.30` mirrors the approximately 0.30 XAUUSD ladder spacing visible in the supplied M5 clip. It is **not** a suitable universal value for other symbols.

## Safety boundary

- MetaTrader `ACCOUNT_TRADE_MODE_REAL` is rejected.
- The EA does not contain a switch to bypass that rejection.
- Symmetric grid mode is for reproducing the video behavior in Strategy Tester/demo only.
- zksato SET integration uses `src/zksato/video_ea.py`, which emits **virtual research triggers only**; it never submits a broker order.
- Any future SET order derived from a trigger must be reconstructed server-side and pass `TradingService` + `RiskEngine` and the existing operator authorization boundary.

## Suggested test workflow

1. Compile in MetaEditor.
2. Run MT5 Strategy Tester or a demo account.
3. Start with `ZKSATO_PA_FILTERED`.
4. Use fixed `InpLots` and keep `InpMaxCycleVolume`, `InpMaxPositions`, and `InpMaxPendingOrders` small.
5. Validate spread sensitivity, gap behavior, basket stop, basket TP, reconnect/restart behavior and broker-specific stop-distance constraints.
6. Do not infer profitability from the supplied videos; they show selected outcomes, not a statistically complete backtest.

## Important difference from the extreme stacking clip

One supplied clip visually shows a very large number of 0.01 XAUUSD positions. zksato intentionally does **not** reproduce unlimited duplicate stacking. The reference EA seeds at most one pending order per level per cycle and enforces hard position/order/volume caps.
