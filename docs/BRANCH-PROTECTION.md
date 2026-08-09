# Branch protection and rulesets

## Target policy for `main`
Require pull request, required status checks, conversation resolution, restricted force push/deletion, and review of high-risk CODEOWNERS paths. Prefer linear/squash history if compatible with repository workflow.

When merge queue is enabled, workflows that are required for queue evaluation must support `merge_group`.

## High-risk paths
Risk/execution/broker/portfolio/auth/TFEX/migrations/workflows/security and architecture decision paths should require explicit owner review.

## Capability note
Rulesets/merge queue/private-repo security features vary by GitHub plan. Record unavailable controls as external gaps; do not weaken in-repo governance to pretend equivalence.
