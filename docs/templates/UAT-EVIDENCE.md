# UAT evidence: <broker/account/revision>

## Scope
- Broker environment: sandbox/UAT only; never production
- Account type/reference (sanitized):
- Revision:
- SDK version:
- Date/operator:
- Sandbox schedule: Thu/Fri 09:00-17:00 Thailand time; Equity Day + Derivatives Day/Night; no Offline Order

## Automated test evidence
Run `tests/test_uaa t.py` during sandbox availability and attach results:
- [ ] `test_uat_account_lookup` — account info retrieved
- [ ] `test_uat_portfolio_lookup` — portfolio positions retrieved
- [ ] `test_uat_limit_buy_and_cancel` — order accepted and cancelled
- [ ] `test_uat_order_rejection_returns_understandable_error` — structured error code returned
- [ ] `test_uat_duplicate_client_order_id_is_idempotent` — duplicate client order ID handled

## Required cases
- [ ] authentication/read portfolio
- [ ] realtime reconnect/freshness/gap/out-of-order diagnostics
- [ ] stale-feed breaker: automation fails closed when feed age exceeds `market_data_stale_seconds`
- [ ] accepted order: deterministic risk passes, one-time approval obtained, order accepted by broker
- [ ] rejected order: deterministic risk rejects, broker rejects, or approval not obtained
- [ ] partial fill: incremental fill delta recorded, portfolio P&L updates, no double counting
- [ ] full fill: cumulative fill converges to broker snapshot, reconciliation passes
- [ ] cancel: open order cancelled, remainder not filled, audit event recorded
- [ ] cancel-after-fill: partial fill recorded, remainder cancelled
- [ ] timeout/ambiguous outcome: `BrokerAmbiguousError` raised, reconciliation required, execution gate closed
- [ ] restart during open order: local state recovered, client order idempotency preserved, broker state reconciled
- [ ] idempotent retry: duplicate `client_order_id` rejected, no duplicate broker order
- [ ] portfolio convergence: local cash/holdings/P&L matches broker account snapshot after reconciliation
- [ ] TFEX-specific: LONG/SHORT, OPEN/CLOSE/AUTO semantics, contract metadata, margin usage, expiry restriction

## Evidence format
For each case record:
- Request correlation ID (`X-Request-ID`)
- Client order ID
- Broker order/deal IDs
- Timestamps (request, broker ack, fill, cancel)
- Expected result
- Observed result
- Reconciliation result
- SDK version
- Account reference
- Operator/reviewer initials

## TFEX certification
- [ ] installed SDK exposes `Derivatives.get_account_info`, `get_portfolios`, `get_orders`, `place_order`
- [ ] contract registry loaded with verified metadata
- [ ] margin usage and dynamic multiplier tested under stressed scenarios
- [ ] expiry restriction blocks orders inside configured window
- [ ] tick-size alignment validated against contract metadata

## Limitations
UAT does not imply production permission. Live equity mutation requires separate broker/legal authorization and a manually authorized canary.

## SDK configuration
- `settradesdkv2_config.txt` must set `environment=uat`
- zksato reads credentials from `.env` / `/run/secrets` and passes them directly to `settrade_v2.Investor`
