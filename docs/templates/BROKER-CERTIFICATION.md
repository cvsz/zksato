# Broker integration certification

## Automated test evidence
- `tests/test_settrade_adapters.py` — adapter mapping and error handling
- `tests/test_uat.py` — live UAT integration tests (run during sandbox availability)

## SDK configuration
- `settradesdkv2_config.txt` must set `environment=uat` for sandbox or `environment=prod` for production
- zksato reads credentials from `.env` / `/run/secrets` and passes them directly to `settrade_v2.Investor`

- Broker/member:
- Environment: UAT / production-readiness only
- SDK/API version:
- Account permissions confirmed by:
- Revision:

## Certified operations
List exact read/mutation operations and observed signatures/response shapes.

## Lifecycle evidence
Accepted/rejected/partial/full/cancel/timeout/reconciliation/reconnect.

## Known unsupported/uncertified operations

## Credential handling review

## Approval/evidence references
Certification is environment/account/version-specific and does not authorize autonomous execution.
