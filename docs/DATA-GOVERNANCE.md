# Data governance

## Data classes
- Public/market: quotes, bars, instrument metadata subject to provider terms.
- Confidential: account balances, positions, orders, fills, strategy parameters.
- Secret: broker app secrets, PINs, auth/session tokens, live approval credentials.

## Rules
Collect the minimum needed; preserve provenance and UTC timestamps; encrypt confidential/secret data in transit and at rest; never place secrets in logs, analytics, traces, browser storage, fixtures, screenshots, or Git.

## Retention
Define retention separately for market history, audit/order records, operational logs, and security logs based on operational/legal/provider requirements. Deletion must not destroy records required for reconciliation or audit.

## Export
Exports require authorization, redaction, and an audit event. Market/broker data use must comply with applicable provider/broker terms.
