# ZKSATO Dashboard Implementation Plan & Architecture Specification

## 1. Overview & Strategy
This plan executes the Universal Enterprise Dashboard specification defined in `docs/ZKSATO-THEME.md` referencing the TailAdmin design system (`https://nextjs-demo.tailadmin.com/`). It upgrades the `frontend/` Next.js 16 application into a high-density, accessible, type-safe trading control plane for SET & TFEX.

## 2. Phase Breakdown & Execution Sequence
1. **Design System & Tokens**:
   - Centralized CSS variable tokens in `global.css` (color scales, typography, elevation, spacing, status dots, metric cards).
   - Light and dark themes via `next-themes` and `ThemeContext`.
2. **Application Shell (`src/components/layout/`)**:
   - Collapsible desktop and responsive mobile `Sidebar` with group-based navigation (Trading Control, Derivatives/TFEX, AI Research, Infrastructure & Admin).
   - Sticky `Header` with system connectivity indicators, trading mode badge (`PAPER` / `LIVE`), language selector, theme toggle, and operator profile.
   - Sticky/footer telemetry with API health, persistence status, and reconciliation indicators.
3. **Information Architecture & Route Mapping**:
   - `/[lng]/dashboard`: Real-time PnL, active bots, risk preflight status, 4-column metric KPI grid, lightweight-charts candlestick view, orders table, fills table, signals, and alerts.
   - `/[lng]/terminal`: Full order submission terminal with TradingView charting and risk validation.
   - `/[lng]/tfex`: Dedicated TFEX derivatives control with margin utilization and contract breakdown.
   - `/[lng]/research`: AI Video EA and backtest research lab.
   - `/[lng]/reconciliation`: Trade reconciliation and mismatch resolver.
   - `/[lng]/admin`: Multi-account governance, `.env` parameter controls, and system logs.
   - `/[lng]/settings`: User credentials, risk thresholds, API keys.
4. **Security & State Safety Invariants**:
   - Live trading safety gates (never autonomously enable live execution).
   - Client-side token storage in `sessionStorage['zksato_api_key']` passing `X-API-Key`.
   - All polling endpoints authenticated via `getAuthHeaders()`.
5. **Testing & Validation**:
   - Full Python test suite (`pytest`).
   - Linting with `ruff check .`.
   - Production Next.js build compilation (`next build --webpack`).
