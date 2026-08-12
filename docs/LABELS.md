# Labels

Use labels to communicate domain, risk, and workflow state; labels do not replace review requirements.

## Provisioned labels

The repository currently has these labels available for issue forms and automation:

- Domains: `api`, `broker`, `dashboard`, `market-data`, `operations`, `persistence`, `risk`, `security`, `strategy`, `tests`, `tfex`
- Standard GitHub types/states: `bug`, `documentation`, `duplicate`, `enhancement`, `good first issue`, `help wanted`, `invalid`, `question`, `wontfix`

Issue forms in `.github/ISSUE_TEMPLATE/` must reference only labels that actually exist in repository settings. If a new label taxonomy is introduced, provision the labels first and update forms in the same change.

## Optional future taxonomy

A richer taxonomy may be introduced later, for example `risk:high`, `status:blocked-external`, or `status:needs-evidence`, but those names are documentation proposals until they are created in GitHub. Do not make templates depend on unprovisioned labels.

The labeler workflow may apply safe path-based labels automatically; humans remain responsible for risk classification. Labels never authorize production/live execution.
