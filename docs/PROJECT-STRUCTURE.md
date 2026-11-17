# Project structure

```text
zksato/
├── AGENTS.md, CLAUDE.md, …   agent operating contracts (tool-specific files stay at root)
├── README.md, ROADMAP.md, CHANGELOG.md, SECURITY.md, governance/community files
├── pyproject.toml, uv.lock   root package `zksato` + uv workspace definition
├── Dockerfile, docker-compose.yml, Makefile
│
├── src/zksato/               RUNTIME — legacy single package served by `uvicorn zksato.api:app`
│   ├── api.py                HTTP/control-plane wiring
│   ├── service.py            trusted execution boundary (TradingService)
│   ├── risk.py               independent risk controls (RiskEngine)
│   ├── broker/               paper / Settrade / CCXT adapters
│   ├── market/, market*.py   market data, sessions, rules
│   ├── strategy.py, indicators.py, backtest*.py, research.py
│   ├── portfolio.py, reconcile.py, persistence.py, store.py
│   ├── tfex.py, prediction/, agent_os/, notifications/, llm_clients/
│   └── config.py             settings (env + TOML, see config/README.md)
│
├── packages/zksato-*/        MONOREPO — uv workspace packages (core, risk, market, broker,
│                             strategy, portfolio, automation, api, cli, test-utils)
├── apps/                     deployable entry points for packages/* (placeholders)
│
├── tests/                    main test suite (targets src/zksato)
├── frontend/                 Next.js operator UI (:3016)
├── dashboard/                Vite lite dashboard (:5174)
├── config/                   TOML settings, environments, policies
├── contracts/                versioned JSON Schemas for external data
├── migrations/               database migrations
├── deploy/                   compose overlays, NGINX, cloudflared, monitoring, terraform
├── scripts/                  CI / operator scripts
├── agents/, skills/          contributor playbooks and reusable procedures
├── ea/, examples/            MQL5 EA material, sample requests
└── docs/
    ├── *.md                  requirements, architecture, operations (see INDEX.md)
    ├── adr/                  architecture decision records
    ├── audit/                domain audit reports
    ├── integrations/         third-party integration specs
    ├── plans/                forward-looking plans and specs
    ├── reports/              point-in-time validation reports and checklists
    ├── superpowers/          agent execution plans
    ├── templates/            evidence templates
    └── video-evidence/
```

## Two implementations (migration in progress)

`src/zksato/` and `packages/*` are independent: they do not import each other and
each defines its own `RiskEngine`, `TradingService`, and `PaperBroker`. Only
`src/zksato/` is deployed. Until the migration in `plans/PHASE-1-SPEC.md` completes,
a runtime behaviour change must land in `src/zksato/` (and be mirrored in
`packages/*` if that package is meant to stay in sync).

## Generated artifacts (not committed)

`openapi.json` (`make openapi`), `coverage.xml`, `.coverage`, `htmlcov/`,
`test_zksato.db`, `.zksato/` — see `.gitignore`.
