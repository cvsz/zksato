# Binance Agent OS & Binance TH Architecture Specification

## 1. Executive Summary

This document specifies the integration architecture for **Binance Agent OS** (agentic MCP servers, sub-account sandboxing, least-privilege toolkits) and **Binance TH** (licensed Thai regulated entity, THB spot pairs, localized endpoints) within `zksato`.

---

## 2. Binance Agent OS Integration Model

Binance Agent OS provides an open, agent-friendly developer infrastructure consisting of:
- **Model Context Protocol (MCP) Server**: Standardized tool interface exposing market data, portfolio telemetry, and trade intent submissions to AI assistants and autonomous workflows.
- **Agentic Sub-Accounts**: Dedicated sub-accounts with zero-withdrawal permissions and isolated collateral budgets.
- **Confirm-Before-Execute Protocol**: Strict multi-party confirmation boundary for money-moving transactions.

```text
+-------------------------------------------------------------------------------+
|                             BINANCE AGENT OS                                  |
+-------------------------------------------------------------------------------+
|  AI Strategy / LLM Agent     --->  MCP Tool Definition (`zksato` Tool Group)  |
|                                                     |                         |
|                                                     v                         |
|  Pre-Trade Risk Boundary     <---  `RiskEngine` Pre-Trade Constraints         |
|  (Server-derived limits)                            |                         |
|                                                     v                         |
|  Execution Plane             --->  Isolated Agentic Sub-Account (No-Withdraw) |
+-------------------------------------------------------------------------------+
```

### Safety Invariants
1. **No Direct Execution**: AI agents cannot directly sign transactions or execute live orders without passing through `RiskEngine` pre-trade evaluation.
2. **Sub-Account Boundary**: All agent-directed execution is isolated to designated agent sub-accounts with strict collateral caps.
3. **Fail-Closed on Latency/Staleness**: Stale order-book ticks (`> 5.0s`) immediately reject agent trade proposals.

---

## 3. Binance TH (Thailand) Integration Model

Binance TH is a regulated digital asset exchange in Thailand supporting Thai Baht (THB) fiat pairs.

### Supported Currency Pairs
- `BTC/THB`, `USDT/THB`, `ETH/THB`, `BNB/THB`
- Spot cross pairs: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`

### Network & Authentication Architecture
- **Header**: `X-MBX-APIKEY`
- **Signature**: HMAC-SHA256 signature with UTC millisecond timestamps
- **Endpoint**: Localized endpoints configured via `ccxt.binanceth`
- **Mode**: Paper simulation and sandbox execution by default; live trading strictly gated by server authorization tokens.

---

## 4. Implementation Reference in `zksato`

- **CCXT Multi-Venue Spot Broker**: `src/zksato/broker/ccxt.py`
- **Real-Time WebSocket Streamer**: `src/zksato/market/ccxt_feed.py`
- **Configuration & Secret Handling**: `src/zksato/config.py`
- **Deterministic Risk Engine**: `src/zksato/risk.py`
