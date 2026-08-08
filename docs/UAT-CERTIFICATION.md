# Settrade UAT certification

Source code cannot self-certify broker behavior. Certification evidence must come from the installed Settrade SDK, the broker-enabled UAT account, and observed broker state.

Required cases: authentication, realtime reconnect, stale-feed breaker, accepted order, rejected order, partial fill, full fill, cancel, cancel-after-fill, timeout/ambiguous response, restart during open order, idempotent retry, portfolio convergence, and TFEX account/portfolio/order semantics.

Start with the non-mutating probe:

```bash
python scripts/uat_certify.py --base-url http://127.0.0.1:9569 --api-key "$READ_KEY"
```

Mutating UAT cases must be executed deliberately through existing authenticated sandbox endpoints. Record request correlation ID, client order ID, broker order/deal IDs, timestamps, expected result, observed result, reconciliation result, SDK version, account, and reviewer. Never place real-money orders as part of certification automation.
