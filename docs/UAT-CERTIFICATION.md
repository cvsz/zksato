# Settrade UAT certification

Source code cannot self-certify broker behavior. Certification evidence must come from the installed Settrade SDK, the broker-enabled UAT account, and observed broker state.

## Sandbox availability

- Best availability: **Thursday and Friday, 09:00–17:00 Thailand time**
- Supports **Equity (Day Session)** and **Derivatives (Day & Night Session)**
- Does **not** support Offline Order
- No guarantee outside the above hours

## UAT test suite

The repository includes `tests/test_uat.py` for automated UAT integration tests:
- Account lookup
- Portfolio lookup
- Limit buy and cancel
- Order rejection with structured error codes
- Idempotent client order ID retry

Run UAT tests only during sandbox availability hours:
```bash
.venv/bin/python -m pytest tests/test_uat.py -v
```

## SDK configuration

zksato uses `settrade-v2` programmatically. Create `settradesdkv2_config.txt` with:
```
environment=uat
```

## Required cases

Required cases: authentication, realtime reconnect, stale-feed breaker, accepted order, rejected order, partial fill, full fill, cancel, cancel-after-fill, timeout/ambiguous response, restart during open order, idempotent retry, portfolio convergence, and TFEX account/portfolio/order semantics.

Start with the non-mutating probe:

```bash
python scripts/uat_certify.py --base-url http://127.0.0.1:9569 --api-key "$READ_KEY"
```

Aggregate local runtime + live probe + manual evidence for `POST /v1/production/readiness`:

```bash
python scripts/verify_external_gates.py --base-url http://127.0.0.1:9569 --api-key "$READ_KEY" --output readiness-input.json
cat readiness-input.json  # supply as ExternalReadinessEvidence JSON to the readiness endpoint
```

Mutating UAT cases must be executed deliberately through existing authenticated sandbox endpoints. Record request correlation ID, client order ID, broker order/deal IDs, timestamps, expected result, observed result, reconciliation result, SDK version, account, and reviewer. Never place real-money orders as part of certification automation.

## Environment-specific unlock procedure

For complete dev/test/uat/prod unlock and release procedures, see [`docs/UNLOCK-RELEASE.md`](docs/UNLOCK-RELEASE.md).
