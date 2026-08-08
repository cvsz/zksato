# zksato Operations Runbook

## 1. Default safe startup

The repository starts in paper mode. Do not add broker credentials until the paper workflow is healthy.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:9569/health
```

Open `http://127.0.0.1:9569/` and use **Start demo feed** to exercise market watch, portfolio, bot, alerts, orders and audit history without external market access.

## 2. Preflight checklist

Before starting automation:

- [ ] `/health` returns `status=ok`
- [ ] dashboard shows expected mode
- [ ] kill switch is not unexpectedly active
- [ ] account/cash state is expected
- [ ] strategy and symbols are reviewed
- [ ] order size and stop/take-profit percentages are reviewed
- [ ] maximum notional and position limits are appropriate
- [ ] daily loss and drawdown limits are appropriate
- [ ] webhook alerts are tested if configured
- [ ] system clock/timezone is correct

## 3. Paper validation

Minimum paper test sequence:

1. Start the synthetic feed.
2. Submit one manual paper order.
3. Confirm order, cash, position and P/L update together.
4. Create a price alert and verify it transitions to triggered.
5. Start the bot in signal-only mode.
6. Confirm generated signals appear in the audit trail.
7. Enable paper auto-execution.
8. Confirm each automated order has a source and audit event.
9. Exercise stop-loss and take-profit exits.
10. Stop the bot and verify no new automated orders are generated.
11. Run a backtest using representative historical candles.

## 4. Settrade UAT promotion

Install the optional SDK dependency:

```bash
pip install -e '.[settrade]'
```

Configure the official SDK for its UAT/simulated environment and set only UAT credentials in `.env`:

```dotenv
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=...
ZKSATO_SETTRADE_APP_SECRET=...
ZKSATO_SETTRADE_BROKER_ID=...
ZKSATO_SETTRADE_APP_CODE=ALGO_EQ
ZKSATO_SETTRADE_ACCOUNT_NO=...
ZKSATO_SETTRADE_PIN=...
```

UAT exit checklist:

- [ ] account lookup succeeds
- [ ] portfolio lookup agrees with Settrade/Streaming
- [ ] one limit buy can be submitted
- [ ] one open order can be cancelled
- [ ] filled orders appear in local response mapping
- [ ] broker order numbers are captured
- [ ] rejected orders return understandable errors
- [ ] repeated client requests do not create unexpected duplicate business actions
- [ ] risk rejection occurs before broker submission
- [ ] bot start/stop is repeatable
- [ ] no production credentials are present in the UAT environment

Broker method signatures can differ by SDK release. Validate cancel/change/reconciliation behavior against the installed Settrade SDK in UAT before any production promotion.

## 5. Live-mode controls

Live mode is not an autonomous mode. The automation engine is deliberately blocked from live broker mutation.

Required server settings for explicit live orders:

```dotenv
ZKSATO_TRADING_MODE=live
ZKSATO_LIVE_TRADING_ENABLED=true
ZKSATO_LIVE_REQUIRES_CONFIRMATION=true
ZKSATO_LIVE_CONFIRMATION_TOKEN=<long-random-secret>
```

The confirmation token is an execution control secret. Do not embed it in frontend source, logs, CI variables visible to untrusted jobs or version control.

Before live use, also require deployment-level authentication/RBAC and durable order reconciliation; these remain production-hardening roadmap items.

## 6. Emergency stop

Immediate application-level stop sequence:

1. Stop the bot from the dashboard or call `POST /v1/bot/stop`.
2. Set `ZKSATO_KILL_SWITCH=true` and restart the API if an environment-level hard stop is needed.
3. Review open broker orders directly in Settrade/Streaming.
4. Cancel or manage broker-side orders using the broker's approved interface if required.
5. Preserve logs/audit evidence before changing configuration.

The application kill switch blocks new risk-approved submissions; it does not claim to cancel an order that has already reached the broker.

## 7. Observability checks

Current single-node checks:

```bash
curl -fsS http://127.0.0.1:9569/health
curl -fsS http://127.0.0.1:9569/v1/config
curl -fsS http://127.0.0.1:9569/v1/portfolio
curl -fsS http://127.0.0.1:9569/v1/audit
```

Docker checks:

```bash
docker compose ps
docker compose logs --tail=200 api
```

## 8. Backup and recovery status

The current v0.2 application state store is process-local, so a process restart resets local paper session state. PostgreSQL/Redis services are present in Compose for the next durable-state phase but are not yet the order-system-of-record.

Do not represent v0.2 in-memory state as restart-safe production reconciliation. Before production-scale operation, implement the durable-state phase in `ROADMAP.md` and test backup/restore and broker-state recovery.

## 9. Configuration-change discipline

Treat changes to strategy parameters, risk limits, broker mode and account configuration as controlled changes:

- record the previous values
- test the new values in paper/UAT
- review resulting backtests and paper behavior
- deploy during an agreed maintenance window
- verify `/v1/config` after restart
- retain an immediate rollback path

## 10. Release verification

For every release:

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

CI must be green before merging into `main`.
