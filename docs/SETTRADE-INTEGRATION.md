# Settrade integration

## Current
`src/zksato/broker/settrade.py` provides an optional equity adapter using `settrade-v2`. It requires UAT certification before production claims.

## Target capabilities
Account info, equity portfolio, TFEX portfolio, quotes/realtime feed, order place/change/cancel, order query, deals/fills, broker error mapping, rate-limit/backoff, session/environment separation.

## Environment policy
- `paper`: no Settrade credentials required.
- `sandbox`: UAT/simulated Settrade configuration only.
- `live`: production credentials plus server policy, authenticated operator authorization, and explicit confirmation. Autonomous live execution remains blocked.

## UAT certification matrix
For each SDK version record: environment, account type, method signatures, order types, place/cancel/change, partial fills, reject mapping, query consistency, portfolio mapping, reconnect behavior, known limitations.

## Ambiguous outcomes
Network timeout after submission is `unknown`, not `failed`. Reconcile by idempotency/business identifiers and broker order/deal queries before retrying.
