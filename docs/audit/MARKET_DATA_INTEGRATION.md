# Market Data Integration Audit

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Provider Inventory

The platform integrates with several market data adapters:
1. **Demo Feed (`DemoMarketFeed`)**:
   Deterministic simulated quote and candle generation used for automated integration tests and UI demonstration.
2. **Settrade Open API (`SettradeBroker` / Market Data)**:
   Integration for Thailand SET equity and TFEX futures real-time quotes, level-2 depth, and historical bars.
3. **CCXT Feed (`CcxtMarketFeed`)**:
   Standardized cryptocurrency exchange feeds for research and paper-trading benchmarks.
4. **Prediction Feed (`PredictionMarketFeed`)**:
   Machine learning inference pipeline generating price observations and signal confidence for research.

## 2. Invariants & Freshness
- Stale quotes are tracked with `store.quote_age_seconds(symbol)`.
- Prometheus metrics (`MARKET_FEED_AGE`) export minimum quote freshness across symbols.
- Feed disconnections trigger closed failsafe states in `AutomationEngine`.
