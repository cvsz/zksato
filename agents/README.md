# zksato specialist agents

These are role playbooks for human or AI contributors. They do not grant runtime permissions. The root `AGENTS.md` is authoritative.

## Coordination model
`orchestrator-agent` decomposes work and routes it to specialists. Specialists return evidence, tests, docs, and explicit risks. No specialist may bypass the execution trust boundary.

## Roster
- `orchestrator-agent.md` — system-level planning and integration
- `architecture-agent.md` — boundaries, ADRs, system design
- `market-data-agent.md` — realtime/historical data quality
- `strategy-agent.md` — deterministic strategy logic
- `risk-agent.md` — pre-trade/portfolio risk controls
- `execution-agent.md` — order lifecycle/idempotency
- `broker-integration-agent.md` — Settrade adapters/UAT mapping
- `tfex-agent.md` — derivatives contracts/margin/position semantics
- `portfolio-agent.md` — positions, cash, P&L accounting
- `persistence-agent.md` — PostgreSQL/Redis/outbox/recovery
- `dashboard-agent.md` — operator UX and APIs
- `security-agent.md` — auth, secrets, threat model
- `testing-agent.md` — unit/integration/property/UAT validation
- `devops-agent.md` — CI/CD/container/deployment
- `observability-agent.md` — metrics/logs/traces/alerts
- `incident-agent.md` — incident containment and postmortems
- `docs-agent.md` — documentation consistency
- `release-agent.md` — release gates and rollback
- `ai-research-agent.md` — read-only AI assistance boundary
