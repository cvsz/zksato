# zTrader Advisory Intent Contract v1

This document defines the planned contract boundary from zTrader intelligence into deterministic execution. The v1 schema is contract-only until a zksato API/adapter explicitly validates and accepts it; clients must not assume a submission endpoint or execution path exists solely because this contract is present.

## Identity invariants

Every intent is tenant-scoped and account-scoped:
- `tenant_id` is required.
- `account_ref` is required.
- `portfolio_ref` may further scope portfolio policy.
- `signal_id` is unique only within the authenticated tenant/account boundary.

Every crypto instrument is unambiguous:
- `symbol`, `chain`, and `address` are all required.
- Receivers must not resolve an instrument by ticker alone.

## Safety invariants

- The payload is advisory only.
- `mode` is fixed to `paper` in v1.
- `side` is explicit and limited to `buy` or `sell`; receivers must never infer trade direction from narrative or whale evidence.
- zTrader cannot enable live execution.
- zksato remains authoritative for risk, sizing, approvals, kill switches, broker state and reconciliation.
- Missing/stale evidence lowers confidence; it is never treated as safe evidence.
- Every request should carry a trace identifier when available.

## Planned flow

```text
cvsz/zworkforce/packages/ztrader
  -> tenant/account-scoped advisory intent
  -> cvsz/zksato deterministic validation/risk
  -> paper execution or deny
```

The flow above becomes supported only after the receiving zksato route/adapter, validation, risk handoff and regression coverage are implemented and verified. Live execution requires a separately governed policy after backtest, OOS, paper and forward-validation evidence.

## Canonical dependencies

- execution/risk: external repository `cvsz/zksato`
- on-chain/wallet evidence: external standalone repository `cvsz/zwallet` through its read-only evidence contract
- AI model gateway: external repository `cvsz/zaiman`
- dashboard: external repository `cvsz/zdash`

The `cvsz/zwallet` reference above does **not** mean a local `apps/zwallet` billing adapter in another monorepo.
