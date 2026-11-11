🚀 WHAT I CAN DO NEXT
1. Frontend Integration
- Build Next.js frontend components for agent dashboard, signal feed, copy trading, challenge competitions
- Connect frontend to /v1/freqtrade/* and /api/claw/* endpoints
- Add TradingView-style charts for strategy backtest results
2. Broker Adapters
- Implement full Settrade equity adapter (currently stub)
- Implement full CCXT broker adapter (currently stub)
- Add more exchanges (Binance, KuCoin, OKX, Bybit, Binance TH)
3. Strategy Library Expansion
- Add more strategies beyond ema_cross and rsi_reversion (MACD cross, Bollinger breakout, VWAP, stochastic, Williams %R, ATR channel, statistical arbitrage, TFEX basis spread)
- Add strategy templates and examples
4. Backtesting UI
- Build interactive backtest results visualization
- Add equity curve charts, drawdown charts, monthly/yearly breakdowns
- Add parameter sweep visualization
5. Hyperopt UI
- Build hyperopt parameter sweep interface
- Add loss function selection and comparison
- Add hyperopt result visualization and export
6. Prediction Markets
- Implement prediction market broker (Polymarket integration)
- Add complete-set cost calculations and directional residual limits
- Add guarded live execution gate
7. Native Agent OS Enhancements
- Add more Agent Skills (beyond quotes, indicators, account telemetry, order cancellation)
- Add more Agent SubAccount types
- Add financial intelligence skill hub enhancements
8. Documentation
- Update docs/API-SPEC.md with new endpoints
- Update docs/DOMAIN-MODEL.md with new domain models
- Add ADRs for major architectural decisions
- Create operator runbooks for new features
9. Testing
- Add unit tests for new modules
- Add integration tests for API endpoints
- Add property-based tests for risk engine
- Add security tests (pen test scenarios)
10. Infrastructure & DevOps
- Add Docker Compose production configuration
- Add Kubernetes deployment manifests
- Add monitoring/alerting (Prometheus metrics already in place)
- Add backup/restore automation
🛡️ SAFETY INVARIANTS (NEVER COMPROMISED)
All 10 AGENTS.md invariants remain fully enforced across all integrations:
 1. paper is the default mode
 2. Autonomous live-money execution is forbidden
 3. No LLM/agent/dashboard may bypass RiskEngine or TradingService
 4. Broker credentials stay server-side
 5. Broker state is the external source of truth
 6. Order creation is idempotent across retries and restarts
 7. Stale/unknown market feed fails closed
 8. Risk controls have independent kill paths
 9. SET and TFEX semantics not conflated
10. Money-moving behavior is deterministic, auditable, versioned, testable
What would you like me to work on next? Pick any area above, or describe a new feature you'd like added to zksato.
Build · Nemotron 3.5 Super VL 120B A12B · 1m 11s · 43.0 tok/s
list all we can do next
+1 thought
Here is a comprehensive, prioritized list of everything that can be done next with the zksato repository, organized by domain with specific implementation details.
1. IMMEDIATE NEXT STEPS (Ready to Implement)
These are low-risk, high-impact tasks that build directly on the code already merged:
#	Task	Files to Modify	Effort
1.1	Add more example strategies	src/zksato/strategy_freqtrade.py	2-4 hours
1.2	Add more hyperopt loss functions	src/zksato/hyperopt.py	1-2 hours
1.3	Add more protection types	src/zksato/protections.py	2-3 hours
1.4	Add more pairlist types	src/zksato/pairlist.py	1-2 hours
1.5	Add more LLM providers	src/zksato/llm_clients/	2-4 hours
1.6	Add API rate limiting per agent	src/zksato/api_freqtrade.py, src/zksato/security.py	2-3 hours
1.7	Add agent session management	src/zksato/agent_trading/service.py	2-3 hours
1.8	Add API rate limiting per agent	src/zksato/api_freqtrade.py	2-3 hours
2. FRONTEND & UI (Next.js Dashboard)
The frontend directory exists at /home/cvsz/zksato/frontend/. The API endpoints are already built at /v1/freqtrade/* and /api/claw/*.
#	Task	Details
2.1	Agent Dashboard	Build React/Next.js pages for agent registration, login, profile, heartbeat monitoring
2.2	Strategy Builder UI	Visual strategy builder with drag-and-drop indicators, EMA cross, RSI reversion config
2.3	Backtest Results Visualization	Equity curve charts, drawdown charts, monthly/yearly breakdown tables using Lightweight Charts or Recharts
2.3	Hyperopt Results UI	Parameter sweep visualization, loss function comparison, best parameters export
2.4	Signal Feed	Real-time signal feed with entry/exit tags, market regime indicators
2.5	Copy Trading UI	Follow/unfollow traders, view copied positions, PnL tracking
2.6	Challenge Competition UI	Join challenges, team formation, team leaderboard, team portfolio
2.7	Risk Dashboard	Kill switch toggle, position limits, drawdown alerts, session risk metrics
2.8	Environment Control Panel	Already built at frontend/src/components/admin/EnvControlPanel.tsx — connect to /v1/admin/env endpoints
3. STRATEGY & RESEARCH
3.1 Additional Strategies to Implement
Strategy	File	Logic
MACD Cross	src/zksato/strategy_freqtrade.py	MACD line crosses signal line
Bollinger Band Reversion	src/zksato/strategy_freqtrade.py	Price touches lower/upper band
Stochastic Oscillator	src/zksato/strategy_freqtrade.py	%K crosses %D in oversold/overbought
Williams %R	src/zksato/strategy_freqtrade.py	%R below -80 (buy), above -20 (sell)
ATR Channel	src/zksato/strategy_freqtrade.py	Price breaks EMA ± ATR×multiplier
Statistical Arbitrage	src/zksato/strategy_freqtrade.py	Z-score dispersion mean-reversion
TFEX Basis Spread	src/zksato/strategy_freqtrade.py	Futures prompt contract deviation
3.2 Backtesting Enhancements
- Multi-symbol backtesting — Run backtests across multiple symbols simultaneously
- Walk-forward analysis — Already partially implemented in research.py, extend to full OOS testing
- Parameter sensitivity heatmap — Already in video_ea_research.py, expose via API
- Monte Carlo trade stress — Already implemented, add to API
- Cost sensitivity matrix — Already implemented, add to API
3.3 Hyperopt Enhancements
- Optuna study persistence — Save/load studies to SQLite/PostgreSQL
- Parallel hyperopt — Multi-process optuna studies
- Early stopping — Stop trials that are clearly underperforming
- Hyperopt result export — Export best parameters to JSON/strategy config
4. EXECUTION & BROKER (CCXT, Settrade, Paper)
4.1 Broker Adapters to Complete
Broker	File	Status	What's Needed
CCXT Multi-exchange	src/zksato/broker/ccxt.py	Partial	Full order management, cancel, portfolio sync
Settrade Equity	src/zksato/broker/settrade.py	Partial	SDK integration, order mapping, error handling
Paper Broker	src/zksato/broker/paper.py	Complete	Done
Prediction Broker	src/zksato/broker/prediction.py	Partial	CLOB integration, complete-set settlement
4.2 Order Management
- Order lifecycle management — Create, update, cancel, reject, fill tracking
- Order idempotency — Already implemented via claim_client_order_id
- Order archival — Already implemented via max_orders in StateStore
- Order filtering — Already implemented in service.py
4.3 Execution Modes
- Paper mode — Default, fully implemented
- Sandbox mode — Settrade UAT sandbox, partially implemented
- Live mode — Requires explicit operator approval, kill switch, fail-closed
5. RISK & COMPLIANCE
5.1 Risk Engine Enhancements
- Portfolio VaR/CVaR — Already implemented in PortfolioRiskManager
- Concentration limits — Already implemented
- Position limits — Already implemented
- Drawdown limits — Already implemented
- Daily loss limits — Already implemented
- Notional limits — Already implemented
- Spread limits — Already implemented
- Tick size validation — Already implemented via market_rules.py
5.2 Kill Switch
- Global kill switch — Already implemented via settings.kill_switch
- Independent kill paths — Required by AGENTS.md invariant #8
- Failure-path tests — Required by AGENTS.md invariant #8
5.3 Compliance & Audit
- Hash-linked audit chain — Already implemented in store.py
- Audit event redaction — Already implemented in security.py
- Order archival — Already implemented
- Reconciliation readiness — Already implemented
6. AGENT OS & NATIVE AGENTS
6.1 Existing Agent OS (Already Implemented)
Component	File	Status
AgentSubAccount	src/zksato/agent_os/subaccount.py	Complete — WITHDRAW=False invariant
AgentSkillHub	src/zksato/agent_os/skills.py	Complete — Skill registration/execution
AgentExecutionEngine	src/zksato/agent_os/engine.py	Complete — confirm-before-execute
AppProviders	frontend/src/app/providers.tsx	Complete — Theme, Sidebar, i18n
6.2 Additional Skills to Add
Skill	Description
market_sentiment	Sentiment analysis from news/social
technical_analysis	RSI, EMA, MACD calculation
risk_assessment	Pre-trade risk check
portfolio_optimization	Mean-variance optimization
news_aggregation	News feed aggregation and filtering
6.3 Agent Communication
- Agent-to-agent messaging — Already partially implemented via AgentMessageCreate
- Heartbeat protocol — Already implemented
- Task queue — Already implemented via AgentTaskCreate
7. MARKET DATA & FEEDS
7.1 Market Data Adapters
Adapter	File	Status
CCXT Market Feed	src/zksato/market/ccxt_feed.py	Partial
Settrade Realtime	src/zksato/market_settrade.py	Partial
Demo Market Feed	src/zksato/market/demo.py	Complete
Prediction Market Feed	src/zksato/market/prediction_feed.py	Partial
7.2 Data Vendors (from AI-Trader research)
Vendor	Use Case
Yahoo Finance	Equity spot prices
Alpha Vantage	Equity fundamentals
FRED	Macro economic data
SEC EDGAR	SEC filings
Polygon.io	Spot/crypto prices
CoinGecko	Crypto prices
Telegram	Signal ingestion
7.3 Market Rules & Calendar
- SET equity sessions — 09:30-12:30, 14:00-16:30 Asia/Bangkok
- TFEX derivatives sessions — Day/Night sessions
- Holiday/special sessions — Configurable overrides
- Price bands — Trusted reference metadata
- Tick sizes — Board lot 100 enforcement
8. PORTFOLIO & ACCOUNTING
8.1 Paper Portfolio (Already Implemented)
- PaperPortfolio class in src/zksato/portfolio.py
- Cash, holdings, realized P&L, unrealized P&L
- Restart-safe persistence via StateStore
- Idempotent fill application
8.2 Portfolio Enhancements
- Multi-currency support — THB, USD, USDT
- Position grouping — By symbol, by strategy, by agent
- P&L attribution — By strategy, by symbol, by time period
- Performance analytics — Sharpe, Sortino, Calmar, SQN (already in backtest_enhanced.py)
9. SECURITY & OPERATIONS
9.1 Security Enhancements
- Session encryption — Already implemented (HMAC-SHA256 signed)
- CSRF protection — Already implemented
- CORS/Trusted hosts — Already implemented
- Secret redaction — Already implemented in security.py
- Admin .env control panel — Already implemented with secret masking
9.2 Observability
- Prometheus metrics — Already implemented in observability.py
- JSON logging — Already implemented
- OpenTelemetry — Optional, configured in config.py
- Correlation IDs — Already implemented via X-Request-ID
9.3 Health Checks
- /health — Database, coordination, reconciliation, audit chain
- /livez — Liveness
- /readyz — Readiness (fail-closed if not ready)
- /metrics — Prometheus metrics
10. DOCUMENTATION & COMPLIANCE
10.1 Documentation to Update
Doc	Status	What's Needed
AGENTS.md	✅ Complete	Operating contract
README.md	✅ Updated	Product overview
Final-Report.md	✅ Updated	Master audit report
docs/API-SPEC.md	❌ Missing	OpenAPI contract
docs/DATABASE.md	❌ Missing	Database schema
docs/DOMAIN-MODEL.md	❌ Missing	Domain model
docs/RISK.md	⚠️ Partial	Risk engine docs
docs/ORDER-LIFECYCLE.md	❌ Missing	Order lifecycle
docs/PORTFOLIO-ACCOUNTING.md	❌ Missing	P&L accounting
10.2 ADRs to Create
- docs/adr/001-agent-native-platform.md
- docs/adr/002-freqtrade-integration.md
- docs/adr/003-risk-engine-design.md
- docs/adr/004-reconciliation-design.md
10.3 Runbooks to Create
- docs/DR-RUNBOOK.md — Disaster recovery
- docs/INCIDENT-RESPONSE.md — Incident response
- docs/OPERATIONS.md — Daily operations
- docs/ONCALL.md — On-call procedures
11. TESTING & QUALITY ASSURANCE
11.1 Test Coverage Gaps
Area	Current	Needed
Risk engine	✅ Good	Fail-closed path tests
Execution	⚠️ Partial	Broker adapter tests
Portfolio	⚠️ Partial	Double-counting tests
Reconciliation	⚠️ Partial	Divergence detection tests
Agent OS	❌ Missing	Agent lifecycle tests
Security	⚠️ Partial	Secrets handling tests
11.2 Penetration Testing
- Authentication bypass — Test session fixation, token reuse
- Input validation — Test SQL injection, XSS in API inputs
- Rate limiting — Test bypass of rate limits
- Secret exposure — Test that secrets are never returned
- IDOR — Test direct object reference attacks
12. INFRASTRUCTURE & DEVOPS
12.1 Docker & Containerization
- Multi-stage Dockerfile — Already exists
- Non-root container — Already implemented
- Health checks — Already implemented
- Secret management — Docker secrets (/run/secrets/)
12.2 CI/CD
- GitHub Actions — Already configured
- Security scanning — Bandit, Gitleaks, Trivy already configured
- Release verification — SBOM, digest verification already configured
12.3 Monitoring & Alerting
- Prometheus metrics — Already implemented
- Grafana dashboards — To be created
- Alert rules — To be configured
- SLO/SLI definitions — To be documented
13. PREDICTION MARKETS
13.1 Prediction Broker (Partially Implemented)
- src/zksato/broker/prediction.py — Partial implementation
- CPMM dynamic liquidity depth — Already implemented
- Complete-set cost calculations — Already implemented
- Directional residual limits — Already implemented
- Guarded live execution gate — Already implemented
13.2 Prediction Markets to Add
- Polymarket integration — Already referenced
- Synthetic probability feeds — Already implemented
- Directional residual engine — Already implemented
14. TFEX DERIVATIVES
14.1 TFEX Domain (Already Implemented)
- src/zksato/tfex.py — Complete TFEX domain
- Dedicated LONG/SHORT, OPEN/CLOSE/AUTO domains
- TFEX account/portfolio/order reads
- Contract registry and deterministic risk
- Sandbox/UAT-only mutation boundary
14.2 TFEX Enhancements
- Contract rollover — Already documented in roadmap
- Dynamic margin management — Already documented
- SET/TFEX separation — Already enforced
15. INTEGRATIONS
15.1 TradingView Webhook
- HMAC-SHA256 signature verification — Already implemented
- Automated alert/signal dispatching — Already implemented
- Symbol-specific webhook secrets — Already implemented
15.2 Telegram Notifications
- Asynchronous alert delivery — Already implemented
- Trade notifications — Already implemented
- Kill switch alerts — Already implemented
- Risk rejection alerts — Already implemented
- P&L summaries — Already implemented
- VaR alerts — Already implemented
- TradingView signal alerts — Already implemented
- Reconciliation alerts — Already implemented
15.3 CCXT Multi-Exchange
- Binance, Binance TH, KuCoin, OKX, Bybit — Already configured
- Paper/sandbox execution — Already implemented
- CCXT dynamic liquidity depth — Already implemented