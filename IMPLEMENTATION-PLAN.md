# zksato Phase 5 — Full Independent Implementation Plan

## Overview
This plan implements all features from anglerfish-fable5 adapted for zksato, with performance optimization, full documentation, and GitHub governance compliance.

## Safety Invariants (AGENTS.md)
All implementations must preserve the 10 non-negotiable safety invariants:
1. `paper` is the default mode
2. Autonomous live-money execution is forbidden
3. No LLM/agent may bypass `RiskEngine` or `TradingService`
4. Broker credentials stay server-side, never committed/logged/returned by APIs
5. Broker state is the external source of truth; local state must converge to it
6. Order creation must be idempotent across retries
7. Stale/unknown market feed must fail closed for automated execution
8. Risk controls must have independent kill paths and failure-path tests
9. SET and TFEX semantics must not be conflated
10. Money-moving behavior must be deterministic, auditable, versioned, and testable

## Phase 5 Implementation Tasks

### Task 1: LLM-Driven Decision Engine (adapted from anglerfish autotrade.py)
**File**: `packages/zksato-strategy/src/zksato_strategy/llm_decision.py`
- Implement `call_openrouter()` — adapted from anglerfish autotrade.py
- Implement `parse_decision()` — adapted from anglerfish autotrade.py  
- Implement `build_market_features()` — adapted from anglerfish autotrade.py
- Integrate with zksato `RiskEngine` for pre-trade validation
- Fail-closed: HOLD default on any parse/error/network failure

**Performance**: NumPy-vectorized indicators from `packages/zksato-indicators` (already exists in `src/zksato/indicators.py`)

### Task 2: Market Features & Technical Indicators
**File**: `packages/zksato-market/src/zksato_market/features.py`
- Implement `build_market_features()` — OHLCV + ticker → feature dict for LLM
- Implement indicator functions (SMA, EMA, RSI, MACD, Bollinger, VWAP, ATR, ADX, Stochastic, Williams %R)
- Vectorized NumPy implementations (already partially in `src/zksato/indicators.py`)
- Add series-based indicators for dashboard rendering

**Performance**: Target ~134,000 risk eval/sec benchmark (already achieved in risk engine)

### Task 3: Dashboard UI Modules (adapted from anglerfish index.html)
**File**: `src/zksato/dashboard.py` — enhance existing dashboard
- Add Probability Lattice module (Galton board / quincunx with biased coins)
- Add Tail Probability Ridge 3D landscape module
- Add Relationship Graph force-directed network module
- Add PNL dot-matrix hero count-up
- Enhance existing equity curve and order panel

**Design tokens**: Binance light theme (#FCD535, #0ecb81, #f6465d) adapted to zksato dark theme

### Task 4: Autotrade Bot CLI (adapted from anglerfish autotrade.py)
**File**: `packages/zksato-automation/src/zksato_automation/bot.py`
- Implement `run_cycle()` — main bot loop: fetch OHLCV → features → LLM → risk → execute
- Implement `main_loop()` — with DRY_RUN gate, confirmation phrase, daily-loss halt
- Implement `resolve_execution_mode()` — golden rule: single decision point
- CLI entrypoint with `--live`, `--dry-run`, `--symbol` flags
- Safety gate: DRY_RUN by default, --live + confirmation + I_UNDERSTAND_REAL_MONEY for mainnet

### Task 5: Performance Optimization
**File**: `packages/zksato-core/src/zksato_core/utils/async_utils.py`
- Optimize market data feed processing
- Batch OHLCV fetching and feature computation
- Reduce GC pressure in main loop
- Target: main loop throughput > 50 cycles/sec

**Benchmark**: Already ~134k risk eval/sec, ~120k check_risk/sec, ~15k place_order/sec

### Task 6: Documentation & GitHub Governance
**Files to update**:
- `docs/INDEX.md` — add Phase 5 features
- `docs/FEATURE-MATRIX.md` — update feature status
- `AGENTS.md` — verify invariants preserved
- `SECURITY.md` — review for new code paths
- `ROADMAP.md` — mark Phase 5 complete
- `CHANGELOG.md` — add v2.1.0 entry
- `.github/` — ensure workflow rules are correct

### Task 7: Git Governance Compliance
- All commits must be GPG-signed under `cvsz` account
- PR must be created under `cvsz`, reviewed by `policedbc`, merged by `cvsz`
- Use `/home/cvsz/.config/gh/.git-credentials` for `gh auth switch`
- Never commit credentials, never bypass GPG signing

## Success Criteria
- [ ] All features from anglerfish-fable5 adapted for zksato
- [ ] Performance: main loop throughput competitive with benchmarks
- [ ] All 10 safety invariants preserved
- [ ] Documentation complete and up to date
- [ ] Git governance workflow compliant
- [ ] pytest passes with no new failures
- [ ] ruff check/format passes
- [ ] mypy passes with no new errors