# Skill: Settrade Open API integration

## Use when
Changing account, portfolio, order, deal, or market-data integration.

## Workflow
- Confirm installed SDK/API version and UAT environment.
- Validate exact method signatures against current SDK/docs.
- Normalize broker payloads at adapter boundary.
- Keep credentials/PIN server-side and redacted.
- Model ambiguous timeouts separately from confirmed rejection.
- Test place/query/change/cancel/reconcile in UAT before production claims.

## Output
Adapter change, mapping tests, normalized error behavior, compatibility/UAT notes.
