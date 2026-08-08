# Event catalog

Events are domain/audit facts, not commands. Target envelope: `event_id`, `event_type`, `schema_version`, `occurred_at`, `correlation_id`, `causation_id`, `actor`, `payload`.

## Market
`market.quote.received`, `market.feed.stale`, `market.feed.recovered`, `market.subscription.failed`.

## Strategy
`strategy.run.started`, `signal.generated`, `signal.expired`, `signal.rejected_by_policy`.

## Risk
`risk.approved`, `risk.rejected`, `kill_switch.enabled`, `kill_switch.disabled`.

## Orders
`order.intent.created`, `order.submit.started`, `order.accepted`, `order.unknown`, `order.partially_filled`, `order.filled`, `order.cancel_requested`, `order.cancelled`, `order.rejected`, `order.reconciled`.

## Portfolio
`position.changed`, `account.snapshot.recorded`, `drawdown.threshold_reached`.

## Security/ops
`auth.login`, `auth.denied`, `approval.created`, `approval.used`, `config.changed`, `release.deployed`, `incident.declared`.

Persist important events through an outbox before publishing externally.
