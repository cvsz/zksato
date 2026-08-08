# Production completion execution plan

## Completed source-code foundation

The v0.3 implementation closes the major source-code gaps identified by the earlier P0-P3 plan:

1. SQL-backed durable operational state and restart-safe idempotency.
2. Persistent paper account state.
3. Broker ambiguity classification and reconciliation worker.
4. Durable notification outbox.
5. Versioned PostgreSQL migration baseline and PostgreSQL CI integration test.
6. Native Settrade realtime subscription bridge with stale-feed execution guard.
7. Expanded deterministic exposure/spread/open-order risk controls.
8. API-key RBAC, configurable CORS/trusted hosts, rate limiting and security headers.
9. One-time intent-bound live approval with optional four-eyes separation.
10. Prometheus metrics.
11. Dedicated TFEX domain/risk/read APIs and sandbox-only order gateway.
12. Expanded indicators/scanner and cost-aware backtesting.

## Next execution gate — broker UAT evidence

Source code cannot prove behavior of a broker account or installed SDK. Use Settrade UAT to validate:

1. Equity account and portfolio response mappings.
2. Accepted/rejected/cancelled/partial-filled order mappings.
3. Timeout/unknown-outcome reconciliation without duplicate submission.
4. Realtime subscription stability and reconnect behavior.
5. TFEX account, portfolio, order and margin semantics.
6. TFEX order signature for the installed SDK release.

Do not promote a behavior to production until the UAT evidence is recorded.

## Deployment gate

1. Apply `migrations/` before application rollout.
2. Use managed PostgreSQL with backup/restore procedures.
3. Enable `ZKSATO_AUTH_REQUIRED=true` and separate risk-admin/order-approver credentials.
4. Keep credentials and PINs in a managed secret facility.
5. Terminate TLS at a trusted ingress/reverse proxy.
6. Configure host/origin allow-lists.
7. Scrape `/metrics` and define alerts for availability, risk rejection and reconciliation backlog.
8. Centralize logs/traces and preserve audit evidence.
9. Exercise database restore, broker outage and kill-switch procedures.

## Controlled live canary

1. Start signal-only.
2. Create a one-time approval for one exact order intent.
3. Have a distinct order approver submit that same intent.
4. Start with deliberately small server-side limits.
5. Compare local order/portfolio state against broker/Streaming state.
6. Stop on any unexplained divergence.
7. Increase limits only after reviewed evidence.

Autonomous live-money execution remains out of scope by design.
