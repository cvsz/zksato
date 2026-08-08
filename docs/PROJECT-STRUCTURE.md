# Project structure

```text
zksato/
├── AGENTS.md
├── agents/                 specialist contributor playbooks
├── skills/                 reusable engineering procedures
├── src/zksato/
│   ├── api.py              HTTP/control-plane wiring
│   ├── automation.py       bot orchestration
│   ├── strategy.py         deterministic strategy engine
│   ├── indicators.py
│   ├── risk.py             independent risk controls
│   ├── service.py          trusted execution boundary
│   ├── portfolio.py
│   ├── market.py
│   ├── backtest.py
│   ├── store.py            current process-local adapter
│   └── broker/
├── tests/
├── docs/
│   └── adr/
└── .github/
```

## Target additions
`persistence/`, `repositories/`, `market_data/`, `reconciliation/`, `auth/`, `observability/`, `workers/`, and migration tooling should be introduced as vertical slices rather than empty layers.
