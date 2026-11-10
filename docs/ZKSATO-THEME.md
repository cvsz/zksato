# ZKSATO — UNIVERSAL ENTERPRISE DASHBOARD MASTER IMPLEMENTATION PROMPT

## PROJECT IDENTITY

Project: ZKSato  
Repository: https://github.com/cvsz/zksato  
Primary branch: main  
Primary frontend: `frontend/`  
Secondary frontend: `dashboard/`  
Backend: FastAPI / Python 3.11+  
Design reference: https://nextjs-demo.tailadmin.com/

Mission: Independently audit, design, implement, upgrade, test, and complete a professional enterprise trading operations dashboard for ZKSato.

This is a FULL IMPLEMENTATION assignment, not a mockup, wireframe, design proposal, or documentation-only task.

Implement the working application directly in the repository.

---

# PHASE 0 — READ PROJECT GOVERNANCE AND ESTABLISH BASELINE

Before changing anything, read:

- `AGENTS.md`
- `CODEX.md`
- `README.md`
- `ROADMAP.md`
- `docs/INDEX.md`
- `docs/FEATURE-MATRIX.md`
- `docs/DASHBOARD.md`
- `docs/API-SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/RISK.md`
- `docs/AUTHORIZATION.md`
- Relevant files under `agents/` and `skills/`.

Read additional documentation whenever it governs the feature being implemented.

Inspect the complete repository, especially:

- `src/zksato/`
- `src/zksato/api.py`
- `src/zksato/dashboard.py`
- `src/zksato/risk.py`
- `src/zksato/service.py`
- `src/zksato/broker/`
- `src/zksato/portfolio.py`
- `src/zksato/market.py`
- `src/zksato/automation.py`
- `src/zksato/tfex/`
- `frontend/`
- `dashboard/`
- `tests/`
- `migrations/`
- `deploy/`
- `.github/workflows/`

Establish the actual application architecture and existing capabilities.

Identify:
1. Existing functional pages.
2. Incomplete pages.
3. Existing dashboard components.
4. API contracts and authentication mechanisms.
5. Data sources.
6. Existing charts and chart adapters.
7. Existing state management.
8. Existing responsive layout.
9. Existing test coverage.
10. Current implementation gaps.

Do not assume any API, feature, or service exists without verifying its implementation.

Preserve useful existing code.

Do not introduce a replacement architecture simply because it is easier than integrating with the existing one.

## Deliverables

Create or update:

- `docs/DASHBOARD-IMPLEMENTATION-PLAN.md`
- `docs/DASHBOARD-DESIGN-SYSTEM.md`
- `docs/DASHBOARD-ROUTES.md`
- `docs/DASHBOARD-API-MAPPING.md`
- `docs/DASHBOARD-TEST-PLAN.md`
- `docs/DASHBOARD-IMPLEMENTATION-REPORT.md`

Maintain traceability between requirements, implementations, APIs, tests, and completion evidence.

---

# PHASE 1 — DESIGN SYSTEM AND VISUAL IMPLEMENTATION

## 1.1 Reference

Use https://nextjs-demo.tailadmin.com/ as the visual and UX reference.

Create the ZKSato Enterprise Trading Dashboard.

Design characteristics:

- Premium enterprise SaaS appearance.
- Professional financial trading interface.
- High information density without visual clutter.
- Precise alignment and consistent spacing.
- Clear information hierarchy.
- Responsive layouts.
- Fast navigation.
- Light and dark themes.
- Accessible components.

Do not reproduce TailAdmin branding, logos, proprietary content, or assets.

## 1.2 Technology constraints

Use the existing `frontend/` application and its established dependencies.

Existing stack includes:

- Next.js 16
- React 19
- TypeScript
- next-themes
- i18next
- Lightweight Charts
- Playwright

Use existing dependencies whenever possible.

Do not add a large UI dependency merely to reproduce basic dashboard components.

Use strict TypeScript.

Prefer reusable components and clear separation of concerns.

## 1.3 Design tokens

Establish centralized design tokens:

- Color palette
- Typography scale
- Spacing scale
- Border radius
- Elevation
- Shadows
- Z-index
- Breakpoints
- Animation durations
- Chart colors
- Status colors

Support light and dark themes.

Use semantic tokens rather than hardcoded colors distributed throughout components.

## 1.4 Main layout

Implement:

A. Sidebar
- ZKSato branding.
- Dashboard navigation.
- Navigation groups.
- Active page indicators.
- Collapsible desktop sidebar.
- Mobile slide-over sidebar.
- Tooltips for collapsed navigation.
- Permission-aware navigation.
- Keyboard accessibility.

B. Header
- Breadcrumbs.
- Global search.
- Market/session indicator.
- API connection status.
- Notification center.
- Theme switcher.
- User profile.
- Account menu.

C. Content area
- Consistent page headers.
- Contextual descriptions.
- Page actions.
- Filters.
- Loading states.
- Error states.
- Empty states.
- Responsive data grids.

D. Footer
- Application version.
- Environment indicator.
- API health.
- Last synchronization time.

Never use hardcoded operational status as though it were live data.

---

# PHASE 2 — COMPLETE DASHBOARD INFORMATION ARCHITECTURE

Implement the following navigation architecture, adapting routes and capabilities to actual repository APIs.

## 2.1 Overview

Route: `/dashboard`

Main executive trading overview.

Display:

- Net liquidation value.
- Available cash.
- Portfolio exposure.
- Realized P&L.
- Unrealized P&L.
- Today's trading activity.
- Orders by status.
- Positions overview.
- Risk utilization.
- Open alerts.
- Market session.
- Recent executions.
- System health.

KPI cards must display:

- Value.
- Unit.
- Data timestamp.
- Relevant change versus a valid comparison period.
- Loading and error states.
- Data freshness indicator.

Charts:

- Portfolio equity curve.
- P&L history.
- Asset allocation.
- Trading activity.
- Orders and execution statistics.
- Risk utilization.

Do not generate fake financial values in production.

## 2.2 Market Terminal

Route: `/market`

Implement:

- SET market overview.
- TFEX market overview.
- USDT/exchange market overview where supported.
- Instrument search.
- Watchlists.
- Bid/ask.
- Last traded price.
- Volume.
- Turnover.
- Price change.
- Market status.
- Data freshness.
- Market depth where supported.
- Historical price charts.
- Timeframe selector.
- Technical indicators where available.

Use Lightweight Charts.

Separate market adapters and asset-class semantics.

Clearly distinguish:
- Live data.
- Delayed data.
- Historical data.
- Simulated data.
- Unavailable data.

Never label simulated quotes as live market prices.

## 2.3 Portfolio

Route: `/portfolio`

Implement:

- Portfolio summary.
- Account balances.
- Cash balance.
- Positions.
- Asset allocation.
- Exposure.
- Average entry prices.
- Current valuation.
- Unrealized P&L.
- Realized P&L.
- Position history.
- Account snapshots.

Support independent SET, TFEX and supported exchange portfolio views.

Do not combine incompatible currencies or contract units without explicit normalization.

## 2.4 Orders

Route: `/orders`

Implement:

- Order list.
- Order details.
- Order history.
- Order status.
- Order timeline.
- Partial fills.
- Rejected orders.
- Cancelled orders.
- Execution details.
- Broker reference IDs.
- Reconciliation status.
- Search.
- Filtering.
- Pagination.
- CSV export.

Order lifecycle must reflect actual backend state.

Never invent fill prices, statuses, or broker confirmations.

## 2.5 Executions and Fills

Route: `/executions`

Display:

- Execution history.
- Fill quantity.
- Fill price.
- Fees.
- Execution timestamp.
- Partial fill relationships.
- Slippage where reliably measurable.
- Broker references.
- Related order.
- Reconciliation status.

## 2.6 Risk Management

Route: `/risk`

This page is mission-critical.

Display:

- Risk utilization.
- Maximum position exposure.
- Maximum order size.
- Daily loss limits.
- Position limits.
- Trading restrictions.
- Available margin.
- Margin utilization.
- Concentration risk.
- Risk evaluation history.
- Rejected order reasons.
- Kill-switch status.

Risk policy configuration must be governed by server-side authorization.

Dashboard code must never calculate or override authoritative risk decisions.

Do not introduce client-side risk bypasses.

Every risk decision must be traceable to backend evidence.

## 2.7 Trading Bot Operations

Route: `/bots`

Display:

- Bot inventory.
- Bot state.
- Active strategies.
- Last execution.
- Last heartbeat.
- Trading mode.
- Start/pause/resume/stop status.
- Error history.
- Signal history.
- Runtime statistics.

Operational control buttons must use existing authorized API contracts.

Require server-side validation for all state transitions.

The UI must reflect the server-confirmed result rather than optimistically claiming that an action succeeded.

## 2.8 AI Research and Signals

Routes:

- `/research`
- `/signals`
- `/backtesting`

Implement:

- Strategy research.
- Signal history.
- Technical analysis.
- Backtest results.
- Historical performance.
- Strategy comparison.
- Confidence information where available.
- Model metadata.
- Evidence timestamps.
- Out-of-sample metrics.
- Experiment history.

All AI output is advisory.

AI must never directly authorize orders or bypass risk controls.

Display model-generated recommendations separately from authoritative backend decisions.

## 2.9 TFEX

Route: `/tfex`

Implement dedicated:

- Contract browser.
- Contract specifications.
- Expiry dates.
- Margin information.
- Position exposure.
- Contract multipliers.
- Settlement information.
- TFEX order history.
- Risk calculations sourced from backend.
- Reconciliation.

Do not reuse SET equity calculations for derivatives.

## 2.10 Alerts and Notifications

Route: `/alerts`

Implement:

- Active alerts.
- Alert severity.
- Alert category.
- Alert lifecycle.
- Creation timestamp.
- Acknowledgement.
- Resolution.
- Related service or instrument.
- Alert search.
- Filtering.
- Notification preferences.

Only show actionable alerts backed by actual events.

## 2.11 Audit and Evidence

Route: `/audit`

Implement:

- Audit event timeline.
- Actor.
- Action.
- Resource.
- Timestamp.
- Request ID.
- Correlation ID.
- Result.
- Evidence references.
- Immutable event history.

Support search and filtering.

Do not allow modification or deletion of audit records through the dashboard.

## 2.12 Account and Settings

Routes:

- `/settings`
- `/settings/profile`
- `/settings/security`
- `/settings/preferences`
- `/settings/api`
- `/settings/notifications`

Implement permission-aware settings and session management.

Never render secret API keys or broker credentials in the browser.

---

# PHASE 3 — API INTEGRATION

Use the real FastAPI backend.

The running revision's `/openapi.json` is authoritative.

Inspect the following API groups and map each dashboard feature:

Platform:
- `/health`
- `/livez`
- `/readyz`
- `/metrics`
- `/v1/config`
- `/v1/dashboard`

Authentication:
- `/v1/auth/*`

Markets:
- `/v1/market/*`
- `/v1/market-terminal`
- `/v1/reference/instruments`
- `/v1/scanner`

Automation:
- `/v1/bot/*`

Risk and trading:
- `/v1/risk/*`
- `/v1/orders*`
- `/v1/reconcile`
- `/v1/portfolio`

Other integrations:
- `/v1/agent-os/*`
- `/v1/prediction/*`
- `/v1/ccxt/*`
- `/v1/tfex/*`
- `/v1/webhooks/*`
- `/v1/notifications/*`

Evidence:
- `/v1/order-events`
- `/v1/fills`
- `/v1/risk/evaluations`
- `/v1/account-snapshots`
- `/v1/audit/*`

Research:
- `/v1/backtest`
- `/v1/research/*`
- `/v1/signals`

Operations:
- `/v1/alerts`
- `/v1/production/*`

## API engineering requirements

Implement:

1. Typed API client.
2. Shared response types.
3. Request validation.
4. Response validation where appropriate.
5. Request timeout.
6. Retry policy for safe idempotent reads only.
7. Authentication lifecycle.
8. CSRF protection.
9. Structured error handling.
10. Correlation IDs.
11. Request cancellation.
12. Pagination.
13. Filtering.
14. Data normalization.
15. Cache invalidation.
16. API health tracking.

Do not retry financial mutations blindly.

Use server-side adapters for credentials and sensitive integrations.

Do not expose broker API credentials to browser JavaScript.

Never place private credentials in NEXT_PUBLIC variables.

Implement suitable loading, stale, unavailable and failure states.

---

# PHASE 4 — REAL-TIME DATA ARCHITECTURE

Implement real-time updates using the existing supported backend transport.

Inspect whether WebSocket, SSE, or polling is already implemented before selecting a mechanism.

Requirements:

- Connection lifecycle.
- Automatic reconnection with bounded exponential backoff.
- Heartbeats.
- Stale-data detection.
- Duplicate event handling.
- Event ordering.
- Subscription lifecycle.
- Resource cleanup.
- Connection visibility.
- Graceful degradation.

Never assume WebSocket support exists without verifying the API.

Do not use aggressive polling.

Financial tables and charts must distinguish historical snapshots from streaming updates.

Every displayed financial metric must have an identifiable source and timestamp.

---

# PHASE 5 — SECURITY AND AUTHORIZATION

Apply the repository security architecture.

Implement:

- Secure session handling.
- HttpOnly cookies where applicable.
- Secure and SameSite cookie policy.
- CSRF verification.
- Server-side role checks.
- Permission-aware routes.
- Restricted operations.
- Safe logout.
- Session expiration handling.
- Access-denied pages.
- Input sanitization.
- Output encoding.
- Security event logging.

Suggested permission domains:

- dashboard:read
- portfolio:read
- orders:read
- orders:create
- orders:cancel
- risk:read
- risk:configure
- bots:read
- bots:control
- research:read
- audit:read
- settings:manage

Use actual backend roles and permissions as the source of truth.

Suggested presentation roles must not become a second, conflicting authorization system.

## Critical financial safety boundary

The following are absolutely prohibited:

1. Defaulting to live trading.
2. Automatically enabling live trading.
3. Allowing AI agents to execute live trades independently.
4. Bypassing RiskEngine.
5. Bypassing TradingService.
6. Bypassing broker-side authorization.
7. Disabling or weakening kill switches.
8. Treating stale data as valid for automated execution.
9. Exposing broker credentials.
10. Claiming a trade succeeded before the backend confirms it.

Paper mode must remain the mandatory default.

The dashboard is an operator interface, not an alternative trading execution engine.

Any live-trading authorization must remain subject to trusted server-side authorization, independent approval and audit policy.

---

# PHASE 6 — COMPONENT FACTORY

Build reusable, tested components.

## Layout

- AppSidebar
- AppHeader
- AppBreadcrumbs
- DashboardShell
- MobileNavigation
- PageHeader
- PageContainer

## Analytics

- MetricCard
- MetricTrend
- PortfolioChart
- EquityCurve
- AllocationChart
- TradingVolumeChart
- RiskGauge
- PerformanceChart

## Data

- DataTable
- TableToolbar
- TablePagination
- ColumnVisibility
- DateRangeFilter
- SearchInput
- StatusFilter
- ExportMenu

## Trading

- MarketTicker
- InstrumentSelector
- OrderStatusBadge
- OrderTimeline
- ExecutionTable
- PositionTable
- RiskIndicator
- TradingModeIndicator

## System

- SystemHealthCard
- ApiConnectionStatus
- MarketSessionIndicator
- AlertCenter
- NotificationDrawer
- ErrorBoundary
- LoadingSkeleton
- EmptyState
- ErrorState
- ConfirmationDialog

## Form infrastructure

- ValidatedInput
- NumericInput
- SelectField
- DateTimeField
- SearchableSelect
- FormSection
- FormErrorSummary
- SubmitActions

Use shared components with strict types.

Avoid redundant components and excessive abstraction.

---

# PHASE 7 — FORM AND INTERACTION ENGINEERING

Build functional forms rather than decorative forms.

Each form must provide:

- Schema validation.
- Field-level errors.
- Clear labels.
- Keyboard accessibility.
- Loading state.
- Disabled state.
- Server validation.
- Error summary.
- Success confirmation.
- Cancellation.
- Confirmation for consequential actions.

Forms must be mapped to actual backend API contracts.

Implement:

1. Instrument search.
2. Watchlist management.
3. Dashboard filter configuration.
4. Alert acknowledgement.
5. Bot control confirmations.
6. Strategy research filters.
7. Backtest configuration.
8. Profile preferences.
9. Notification preferences.
10. Administrative settings where supported.

Financial action forms must never derive authority from client input.

Any operation affecting orders, risk, or account state must be verified by the server.

---

# PHASE 8 — DATA TABLES AND CHARTS

## Data tables

Support:

- Server-side pagination.
- Server-side filtering.
- Sorting.
- Column visibility.
- Responsive behavior.
- Empty data.
- Loading.
- Error handling.
- CSV export with permission enforcement.

Use stable record IDs.

Do not use array indices as financial entity identifiers.

## Charts

Use Lightweight Charts for financial price/time-series visualizations.

Implement:

- Candlesticks where supported.
- Line series.
- Volume.
- Crosshair.
- Timeframe selection.
- Zoom.
- Historical range.
- Market timezone handling.
- Empty and unavailable states.

Other statistical charts can use lightweight React/SVG implementations or existing libraries.

Charts must:

- Use real backend data.
- Include units.
- Handle missing points.
- Respect market timezones.
- Avoid misleading axes.
- Avoid silently interpolating missing prices.
- Expose accessible summaries.

---

# PHASE 9 — PERFORMANCE AND RESPONSIVENESS

Requirements:

- Responsive desktop/tablet/mobile.
- Route-level code splitting.
- Dynamic imports for expensive components where appropriate.
- Efficient rendering.
- Memoization only where beneficial.
- Optimized table rendering.
- Controlled chart updates.
- Request cancellation.
- No memory leaks.
- No duplicated subscriptions.
- No redundant API fetching.
- Optimized production builds.
- Appropriate caching.

Measure performance rather than assuming an optimization helped.

Target:

- Good Core Web Vitals.
- No horizontal overflow at supported viewports.
- Fast initial navigation.
- Stable chart rendering.
- No unnecessary full-page re-rendering from streaming events.

---

# PHASE 10 — TESTING

Implement unit, integration and end-to-end coverage.

## Unit testing

Test:

- Formatting.
- Financial precision.
- Timezones.
- Data normalization.
- Risk status presentation.
- Permission checks.
- Form validation.
- API error mapping.
- Pagination.
- Connection state transitions.

## Integration testing

Test:

- Authentication.
- Session expiration.
- Dashboard API integration.
- Portfolio API integration.
- Order status integration.
- Risk status integration.
- Alert integration.
- Audit event integration.
- Real-time connection lifecycle.

## Playwright E2E

Test:

1. Application loads.
2. Authentication works.
3. Dashboard renders.
4. Sidebar navigation works.
5. Mobile navigation works.
6. Theme switching works.
7. Filters work.
8. Pagination works.
9. Charts render.
10. API failures render correctly.
11. Unauthorized routes are denied.
12. Session expiration is handled.
13. Paper-mode indicator is visible.
14. Financial actions require authorized confirmation.
15. Sensitive data is never rendered.
16. Keyboard navigation works.

Use mocked API fixtures only for isolated UI tests.

Integration and staging tests must separately validate the real backend.

Never claim live-market or broker UAT validation from mocked tests.

---

# PHASE 11 — ACCESSIBILITY

Target WCAG 2.2 AA.

Implement:

- Semantic HTML.
- ARIA where necessary.
- Keyboard navigation.
- Visible focus.
- Accessible dialogs.
- Screen-reader labels.
- Adequate contrast.
- Accessible status indicators.
- Reduced-motion support.
- Accessible chart descriptions.
- Form field associations.

Color must never be the only way to communicate trading or risk status.

---

# PHASE 12 — OBSERVABILITY

Implement frontend observability consistent with backend conventions.

Track:

- Application startup.
- API latency.
- API failures.
- Route errors.
- Session failures.
- WebSocket/SSE connection health.
- Dashboard data freshness.
- Client-side rendering failures.

Include request and correlation IDs where available.

Avoid sending credentials, tokens, financial secrets, or sensitive personal information to telemetry systems.

---

# PHASE 13 — DEPLOYMENT

Preserve the existing primary deployment strategy.

Repository Docker Compose deployment must remain supported.

Inspect the actual current Docker and reverse-proxy configuration.

Requirements:

- Multi-stage frontend build.
- Minimal production runtime.
- Non-root execution.
- Secure headers.
- Correct proxy configuration.
- Health checks.
- Environment validation.
- No development server in production.
- No embedded secrets.
- Correct API base URL.
- Graceful shutdown.

Verify:

- Dashboard build.
- Dashboard container.
- API connectivity.
- Reverse-proxy routing.
- Static asset loading.
- Authentication cookie behavior.
- Health endpoints.

Do not change the existing production routing without reviewing its operational effects.

---

# PHASE 14 — INDEPENDENT AUDIT AND SECURITY GATES

Perform a dedicated audit of:

- Authentication bypasses.
- Authorization bypasses.
- CSRF.
- XSS.
- SSRF.
- Open redirects.
- Sensitive information disclosure.
- Insecure cookies.
- Unsafe caching.
- Financial precision defects.
- Incorrect timezones.
- Race conditions.
- Stale market state.
- Duplicate events.
- Memory leaks.
- Broken navigation.
- Inaccessible controls.
- API contract mismatches.
- Incorrect market calculations.
- False success notifications.
- Unhandled API failures.

Also inspect existing repository issues.

Resolve dashboard-relevant defects with tests.

IMPORTANT: Independently investigate the open repository security and CI issues.

Known issues to investigate include:

- Issue #42: P0 PR-controlled reviewer credential workflow and automated reviewer approval.
- Issue #41: P1 performance probe dependency and CLI contract mismatch.
- Issue #30: advisory-intent execution boundary.

Do not treat these issues as fixed without verifying current main, the relevant commits, and their regression tests.

Do not expose reviewer credentials or execute untrusted PR-controlled code with privileged secrets.

Do not automate independent reviewer approval.

Preserve signed commits and the repository's multi-account review and merge governance.

---

# PHASE 15 — MULTI-AGENT ENGINEERING WORKFLOW

Use parallel agents only for independent workstreams.

Suggested roles:

1. Architecture Agent
   - Repository audit.
   - Architecture and integration contracts.

2. UI/UX Agent
   - Dashboard design system.
   - Responsive layouts.
   - Visual QA.

3. Frontend Agent
   - Pages.
   - Components.
   - Navigation.
   - Forms.

4. Backend Integration Agent
   - API mapping.
   - Typed client.
   - Authentication.
   - Streaming.

5. Financial Domain Agent
   - Portfolio.
   - Orders.
   - Market data.
   - Risk semantics.

6. Security Agent
   - Authorization.
   - Browser security.
   - Sensitive information handling.

7. Testing Agent
   - Unit tests.
   - Integration tests.
   - Playwright E2E.

8. DevOps Agent
   - Docker.
   - Reverse proxy.
   - Build and deployment.

9. Independent Review Agent
   - Review implementation.
   - Identify defects.
   - Verify test evidence.

Rules:

- Assign explicit file ownership to parallel agents.
- Avoid simultaneous modifications to shared files.
- Establish API contracts before dependent implementation.
- Use isolated branches or worktrees where appropriate.
- Require test evidence from each workstream.
- Review integration conflicts before merging work.

If model/provider access fails, use available alternative agents or models.

A free model is acceptable for implementation and review only when it has sufficient technical capability.

Never treat model agreement as independent security approval.

---

# PHASE 16 — IMPLEMENTATION EXECUTION

Work in dependency order:

1. Audit and baseline.
2. Establish design tokens.
3. Implement application shell.
4. Implement API client.
5. Implement authentication.
6. Implement dashboard overview.
7. Implement market terminal.
8. Implement portfolio.
9. Implement orders and executions.
10. Implement risk.
11. Implement bots.
12. Implement research and signals.
13. Implement TFEX.
14. Implement alerts and audit.
15. Implement settings.
16. Implement real-time updates.
17. Implement responsive and accessibility improvements.
18. Implement observability.
19. Complete security review.
20. Complete automated testing.
21. Complete deployment validation.
22. Update documentation and feature matrix.

Do not leave pages as empty placeholders.

Do not create buttons that have no functional action.

Do not fabricate backend capabilities.

Where a backend feature is genuinely absent, either implement the necessary safe vertical slice or show a truthful capability-unavailable state and document the gap.

Prioritize usable, end-to-end features over superficial page count.

---

# PHASE 17 — VALIDATION COMMANDS

Run the appropriate existing repository commands.

Backend:

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run build
npm run test:e2e
```

Secondary dashboard, when changed:

```bash
cd dashboard
npm ci
npm run build
npm run lint
```

Infrastructure:

```bash
docker compose config
docker compose build
```

Also run available type checks, security scans, API contract tests, and relevant frontend lint commands.

Do not silently skip failures.

Do not weaken a test, threshold, permission, or security policy merely to achieve green CI.

Distinguish:

- Passed.
- Failed.
- Blocked.
- Not applicable.
- Not executed.

Record the exact command and evidence for every result.

---

# PHASE 18 — COMPLETION CRITERIA

The task is complete only when:

- The main dashboard is implemented.
- The application shell is responsive.
- All required routes work.
- Design components are reusable.
- Real API integrations are operational.
- Authentication and authorization are enforced.
- Paper mode is visible and remains the default.
- Financial data is correctly formatted.
- Risk information is authoritative.
- All operational actions have proper server confirmation.
- Loading/error/empty states are implemented.
- Tables and charts work.
- Tests are passing.
- Accessibility is reviewed.
- Security review is complete.
- Deployment configuration is validated.
- Documentation is updated.
- Known defects are recorded and resolved or explicitly blocked.
- No fake production data or misleading status indicators remain.

Do not claim 100% completion without evidence.

External dependencies such as broker UAT, production credentials, authorized live trading, production infrastructure and independent sign-off must be reported separately.

---

# FINAL OUTPUT

Produce a final implementation report containing:

1. Executive summary.
2. Original architecture discovered.
3. Implemented dashboard routes.
4. Implemented components.
5. API integrations.
6. Design system.
7. Security improvements.
8. Test results.
9. Build results.
10. Deployment results.
11. Performance and accessibility results.
12. Remaining defects.
13. External dependencies.
14. Files changed.
15. Commit hashes and PR URL.
16. Rollout and rollback instructions.
17. Completion matrix with evidence.

Implementation standard:

ENTERPRISE-GRADE  
PRODUCTION-ORIENTED  
TYPE-SAFE  
SECURE-BY-DESIGN  
RESPONSIVE  
TESTED  
OBSERVABLE  
MAINTAINABLE

Execute the work independently, make reasonable engineering decisions, and continue through implementation and validation without stopping after the audit or plan.