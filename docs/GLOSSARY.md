# Glossary

- **Approval** — bounded operator authorization tied to a specific live intent and expiry.
- **Audit chain** — hash-linked audit records used to detect tampering in retained application history.
- **Broker reconciliation** — comparison/convergence of local durable state with broker-observed orders/positions.
- **Dead letter** — notification outbox item removed from normal retry after bounded failures pending operator action.
- **Economic order identity** — the stable business identity/intent of an order independent of mutable broker status snapshots.
- **Fill delta** — newly observed executed quantity derived from a cumulative order snapshot without double counting prior fills.
- **Live** — broker environment where mutation can move real money; heavily gated.
- **Paper** — deterministic local simulator; not a representation of real exchange queue/liquidity.
- **Reference data** — trusted instrument metadata such as tick size, price band, sector, multiplier, series, expiry.
- **Risk context** — server-derived state used by deterministic pre-trade policy.
- **Sandbox/UAT** — broker-provided non-production environment used for integration certification.
- **Strategy version** — immutable `(name, version)` plus configuration/code identity used for reproducibility.
- **TFEX** — Thailand Futures Exchange domain; handled separately from equity semantics.
- **Readiness** — service or production prerequisites satisfied; production readiness does not itself execute a trade.
