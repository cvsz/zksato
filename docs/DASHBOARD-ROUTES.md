# ZKSATO Dashboard Routes Specification

| Route | Role | Component Path | Data Dependencies |
|---|---|---|---|
| `/[lng]/dashboard` | Executive Trading Operations & P&L Overview | `frontend/src/app/[lng]/dashboard/page.tsx` | `/v1/portfolio`, `/v1/orders`, `/v1/fills`, `/v1/signals`, `/v1/alerts`, `/v1/risk/evaluations` |
| `/[lng]/terminal` | Order Execution & TradingView Charting | `frontend/src/app/[lng]/terminal/page.tsx` | `/v1/market/quotes`, `/v1/orders`, `/v1/risk/check` |
| `/[lng]/tfex` | TFEX Derivatives, Margin & Position Control | `frontend/src/app/[lng]/tfex/page.tsx` | `/v1/tfex/positions`, `/v1/tfex/orders`, `/v1/tfex/risk/preflight` |
| `/[lng]/research` | AI Video EA Analysis & Backtesting | `frontend/src/app/[lng]/research/page.tsx` | `/v1/backtest`, `/v1/signals`, EA models |
| `/[lng]/reconciliation` | Local-to-Broker Position & Fill Reconciler | `frontend/src/app/[lng]/reconciliation/page.tsx` | `/v1/reconcile`, `/v1/portfolio` |
| `/[lng]/admin` | Multi-Account Git Governance & Config Panel | `frontend/src/app/[lng]/admin/page.tsx` | `/v1/admin/env`, `/v1/audit` |
| `/[lng]/settings` | Operator Credentials & Risk Thresholds | `frontend/src/app/[lng]/settings/page.tsx` | `/v1/auth/me`, `/v1/risk/evaluations` |
| `/[lng]/login` | API Key & Operator Authentication | `frontend/src/app/[lng]/login/page.tsx` | `/v1/auth/session` |
