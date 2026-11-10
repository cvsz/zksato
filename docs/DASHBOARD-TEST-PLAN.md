# ZKSATO Dashboard Test Plan

## 1. Scope
Automated verification of dashboard components, layouts, API proxy endpoints, and safety mechanisms.

## 2. Test Suites
1. **API Contracts & Safety Tests (`tests/`)**:
   - `tests/test_api_auth.py`: Session issuance, token revocation, header validation.
   - `tests/test_risk_engine.py`: Preflight risk gate assertions, notional limits.
   - `tests/test_portfolio.py`: P&L accounting, position safety.
   - `tests/test_workflow_security.py`: Git workflow and multi-account signature gates.
2. **Frontend Type Checking & Build**:
   - `npm run build`: Strict TypeScript checks, Next.js page generation, standalone output validation.
3. **End-to-End Playwright Scenarios (`frontend/src/tests/` / `frontend/tests/`)**:
   - Navigation across TailAdmin routes (`/dashboard`, `/terminal`, `/tfex`, `/admin`).
   - Authentication flow via API Key modal and session persistence.
   - Kill switch activation and paper trading safety banner visibility.
