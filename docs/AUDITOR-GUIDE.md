# Auditor guide

## Evidence surfaces
Review order records/events, fill deltas, risk evaluations, account snapshots, strategy versions/runs, audit chain, reconciliation reports, release/DR/UAT/readiness evidence, and GitHub workflow/review history.

## Questions
- Was the final merged revision validated?
- Was live authority explicit and bounded?
- Did risk use trusted server-side inputs?
- Was reconciliation fresh after restart?
- Are broker lifecycle claims backed by UAT evidence?
- Are external production claims backed by environment evidence?
- Were migrations/rollbacks/audit records retained?

## Access
Use auditor/read-only privileges. Auditing should not require mutation or exposure of secret values.
