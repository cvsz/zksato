# zTrader Advisory Security Boundary Audit

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Boundary Contract & Security Guarantees

The integration with `zTrader` adheres to strict advisory-only invariants:
1. **Advisories are data, not execution commands**:
   Intake routes (`/v1/integrations/ztrader/advisory-intents`) accept recommendations strictly for risk review and logging.
2. **`execution_allowed` is fixed to `False`**:
   The response explicitly returns:
   ```json
   {
     "accepted": true,
     "execution_allowed": false,
     "risk_review_required": true,
     "canonical_executor": "zksato",
     "mode": "paper"
   }
   ```
3. **Paper-Only Enforced**:
   Submissions with `mode != "paper"` or order type other than `limit` are rejected with HTTP 422 Unprocessable Entity.
   If the server's runtime mode is not `paper`, intake returns HTTP 409 Conflict.

## 2. Multi-Tenant Namespace Hardening

### Defect Identified & Remediated
Previously, `_ztrader_advisory_key(signal_id)` only keyed by `signal_id`, creating potential collision between different tenants using identical signal IDs.

### Remediation
Updated `_ztrader_advisory_key` in `src/zksato/api.py`:
```python
def _ztrader_advisory_key(
    signal_id: str,
    *,
    tenant_id: str | None = None,
    account_ref: str | None = None,
) -> str:
    if tenant_id and account_ref:
        namespaced = f"{tenant_id}:{account_ref}:{signal_id}"
    else:
        namespaced = signal_id
    digest = hashlib.sha256(namespaced.encode("utf-8")).hexdigest()
    return f"ztrader-advisory:{digest}"
```

### Verification Evidence
Added negative and multi-tenant isolation tests in `tests/test_ztrader_integration.py`:
- `test_ztrader_advisory_isolation_across_tenants`: Proves two tenants with identical `signal_id` store independent state entries.
- `test_ztrader_advisory_rejects_missing_tenant_or_account`: Confirms missing tenant/account yields HTTP 422.
- Verified test run: 6 passed in 3.01s.
