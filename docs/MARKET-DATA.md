# Market data architecture

## Sources
Synthetic demo feed is implemented for paper mode. Native Settrade realtime/historical integration is the production target.

## Canonical quote
Instrument, last, bid, offer, open/high/low/previous close, volume/value, exchange/source timestamp, received timestamp, source, sequence if available.

## Quality controls
Deduplicate, reject/flag impossible values, track out-of-order events, monitor source latency and feed age, detect gaps/reconnects, preserve provenance.

## Freshness policy
Automated execution requires a quote younger than a configured threshold and a healthy subscription state. If freshness is unknown, reject automated orders that depend on market reference price.

## Replay
Persist normalized bars/events so strategy/backtest incidents can be reproduced deterministically.
