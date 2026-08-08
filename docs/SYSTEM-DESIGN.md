# System design

## Target logical architecture
```text
Settrade market/broker APIs
        |                     operator browser
        v                           |
Market Data Gateway                 v
  | normalize/freshness        FastAPI/Auth/RBAC
  v                           /       |        \
Event/History Store      strategy ctl |   approvals/admin
  |                               v   v
  +--> Strategy Engine ------> Signal Store
                                  |
                                  v
                              Risk Engine
                                  |
                             Execution Service
                                  |
                           Durable Order Store
                                  |
                             Settrade Adapter
                                  |
                          Reconciliation Worker
                                  |
                        Positions/Portfolio Store
```

## Key principles
- Modular boundaries inside one deployable application first.
- PostgreSQL durable local source of truth; broker external truth for live order/position reconciliation.
- Redis for ephemeral coordination/cache, never sole durable truth.
- Transactional outbox for events that must survive process failure.
- Typed state machines for order lifecycle.
- Market feed freshness is a prerequisite for automation.
- Read-only AI stays outside trusted mutation path.

## Scale model
Begin single-region/single-account-friendly. Scale ingestion, workers, and read APIs independently only after correctness and observability are mature.
