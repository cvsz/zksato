# GitHub repository settings target

Repository YAML cannot prove account/repository settings. Audit these through GitHub UI/API.

## Recommended
- default branch `main`;
- squash merge enabled; decide whether merge/rebase methods remain necessary;
- automatic branch deletion after merge where operationally appropriate;
- vulnerability alerts/dependency graph enabled where supported;
- secret scanning/push protection/code scanning/dependency review enabled when plan/capability permits;
- Actions restricted to trusted/pinned actions with least privilege;
- protected `uat` and `production` environments with reviewers/secrets;
- branch protection/ruleset for `main` requiring PR and key checks where plan permits.

## Evidence
Use Repository Health workflow/API snapshots and record plan-gated gaps. Do not claim a setting enabled solely because documentation recommends it.
