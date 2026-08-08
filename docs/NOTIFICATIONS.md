# Notifications

## Channels
Generic webhook is implemented. Target adapters may include LINE, Telegram, Discord, email, and on-call systems.

## Event classes
Signal information, order accepted/rejected/filled/cancelled, risk rejection, kill switch, stale feed, broker outage, reconciliation drift, drawdown threshold, incident/recovery.

## Rules
Notifications are not authoritative state. Redact confidential/secret data. Deduplicate noisy events and include correlation ID, mode, account alias, instrument, severity, and operator action when appropriate.
