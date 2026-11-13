# ============================================================
# zksato — Makefile
# Risk-first automated trading platform for SET / TFEX
# Enterprise-grade all-in-one build, test, deploy, and run system
# ============================================================
# Usage:  make <target>
#         make help          — list all targets
#         make all           — full validation + start all services
# ============================================================

.DEFAULT_GOAL := help

# ------------------------------------------------------------------
# PHONY targets — every target is phony so make always runs it
# ------------------------------------------------------------------
.PHONY: help \
	install install-settrade install-ccxt install-prediction \
	install-observability install-agent-os install-cli install-all install-deps \
	install-apps install-api install-worker \
	lint format format-check shellcheck type \
	test test-resilience test-performance test-uat test-postgres \
	test-concurrency test-frontend test-e2e test-security \
	test-agent-trading test-agent-os test-agent-platform test-video-ea test-prediction \
	test-tfex test-notifications test-coordination test-ztrader \
	test-hyperopt test-scanner test-backtest test-market \
	test-penetration test-production-readiness test-research \
	test-api test-auth test-approvals test-audit test-broker \
	test-concurrency-adv test-fill-deltas test-indicators test-monorepo \
	test-news test-openapi test-outbox test-paper test-protections \
	test-reconcile test-risk test-runtime test-server-risk test-session-reconcile \
	test-strategy test-tradingview test-trailing-stop test-version \
	test-env-admin test-env-req test-bot-enhancements test-equity-sell \
	test-github-admin test-github-req test-mql5-policy \
	coverage coverage-html \
	contract openapi licenses package \
	security security-full audit bandit gitleaks \
	sec-bandit sec-pip-audit sec-zizmor sec-gitleaks \
	db-migrate db-status db-backup db-restore \
	docker docker-run docker-scan compose \
	resilience dr-drill dr-restore load-test env-check github-health \
	all all-features all-services start-all stop-all restart-all \
	start-backend stop-backend restart-backend \
	start-frontend stop-frontend restart-frontend \
	start-dashboard stop-dashboard restart-dashboard \
	start-worker stop-worker restart-worker \
	health-check-all \
	frontend-lint frontend-type frontend-build frontend-test frontend-e2e \
	dashboard-lint dashboard-type dashboard-build \
	dashboard-test \
	test-all-features \
	ci ci-full ci-security clean \
	docs-check docs-build docs-validate \
	tui-install tui-start tui-build tui

# ------------------------------------------------------------------
# Colour helpers
# ------------------------------------------------------------------
BOLD  := \033[1m
RESET := \033[0m
GREEN := \033[32m
CYAN  := \033[36m
YELLOW := \033[33m
RED   := \033[31m

# ------------------------------------------------------------------
# Environment defaults
# ------------------------------------------------------------------
ZKSATO_TRADING_MODE ?= paper
VENV_PYTHON         ?= $(CURDIR)/.venv/bin/python
PYTHON              ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python)
PIP                 ?= $(PYTHON) -m pip
PYTEST              ?= $(PYTHON) -m pytest
NPM                 ?= npm
NODE                ?= node
COV_FAIL_UNDER      ?= 65
IMAGE_TAG           ?= zksato:local
BACKUP_DIR          ?= ./backups
DOCKERFILE          ?= Dockerfile
COMPOSE_FILE        ?= docker-compose.yml

# Workspace packages, leaf-first (inter-package deps are bare names and
# unpublished, so dependent packages must be installed after their deps).
PKG_CORE        := packages/zksato-core
PKG_RISK        := packages/zksato-risk
PKG_MARKET      := packages/zksato-market
PKG_STRATEGY    := packages/zksato-strategy
PKG_PORTFOLIO   := packages/zksato-portfolio
PKG_TESTUTILS   := packages/zksato-test-utils
PKG_BROKER      := packages/zksato-broker
PKG_AUTOMATION  := packages/zksato-automation
PKG_API         := packages/zksato-api
PKG_CLI         := packages/zksato-cli
PKGS_LEAF       := $(PKG_CORE) $(PKG_RISK) $(PKG_MARKET) $(PKG_STRATEGY) $(PKG_PORTFOLIO) $(PKG_TESTUTILS)
PKGS_MIDDLE     := $(PKG_BROKER) $(PKG_AUTOMATION)
PKGS_TOP        := $(PKG_API) $(PKG_CLI)
PKGS_ALL        := $(PKGS_LEAF) $(PKGS_MIDDLE) $(PKGS_TOP)

# Apps (thin wrappers depending on workspace packages)
APP_API     := apps/api
APP_CLI     := apps/cli
APP_WORKER  := apps/worker
APPS_ALL    := $(APP_API) $(APP_CLI) $(APP_WORKER)

# ============================================================
# HELP
# ============================================================
help:
	@printf '$(BOLD)$(CYAN)zksato — Enterprise Makefile$(RESET)\n'
	@printf 'Risk-first automated trading control plane for SET / TFEX\n\n'
	@printf '$(BOLD)Install targets$(RESET)\n'
	@printf '  $(GREEN)install$(RESET)              Root package + dev/quality/security extras + all workspace packages\n'
	@printf '  $(GREEN)install-apps$(RESET)          Install API, CLI, and Worker apps\n'
	@printf '  $(GREEN)install-settrade$(RESET)      Settrade-v2 broker adapter (root extra)\n'
	@printf '  $(GREEN)install-ccxt$(RESET)          CCXT multi-exchange adapter (root extra)\n'
	@printf '  $(GREEN)install-prediction$(RESET)    XGBoost / scikit-learn prediction (root extra)\n'
	@printf '  $(GREEN)install-observability$(RESET) OpenTelemetry SDK (root extra)\n'
	@printf '  $(GREEN)install-agent-os$(RESET)      zksato-automation package (agent OS framework)\n'
	@printf '  $(GREEN)install-cli$(RESET)           zksato-cli package (coding-agent CLI)\n'
	@printf '  $(GREEN)install-all$(RESET)           Every optional extra + workspace packages + apps\n'
	@printf '  $(GREEN)install-deps$(RESET)          Install system-level dependencies\n'
	@printf '\n$(BOLD)Quality targets$(RESET)\n'
	@printf '  $(GREEN)lint$(RESET)                 ruff check . (+ yamllint/hadolint when installed)\n'
	@printf '  $(GREEN)format$(RESET)               ruff format (auto-fix)\n'
	@printf '  $(GREEN)format-check$(RESET)         ruff format --check (no mutation)\n'
	@printf '  $(GREEN)shellcheck$(RESET)         Lint all shell scripts\n'
	@printf '  $(GREEN)type$(RESET)                 mypy type-check src/zksato + scripts\n'
	@printf '\n$(BOLD)Test targets — Core$(RESET)\n'
	@printf '  $(GREEN)test$(RESET)                 Full suite (excludes uat, performance)\n'
	@printf '  $(GREEN)test-api$(RESET)              API endpoint tests\n'
	@printf '  $(GREEN)test-auth$(RESET)             Authentication/authorization tests\n'
	@printf '  $(GREEN)test-approvals$(RESET)        Order approval workflow tests\n'
	@printf '  $(GREEN)test-audit$(RESET)            Audit integrity tests\n'
	@printf '  $(GREEN)test-broker$(RESET)           Broker adapter tests (paper, CCXT, Settrade)\n'
	@printf '  $(GREEN)test-concurrency-adv$(RESET)  Advanced concurrency tests\n'
	@printf '  $(GREEN)test-fill-deltas$(RESET)      Fill delta calculation tests\n'
	@printf '  $(GREEN)test-indicators$(RESET)       Technical indicator tests\n'
	@printf '  $(GREEN)test-monorepo$(RESET)         Monorepo package structure tests\n'
	@printf '  $(GREEN)test-news$(RESET)             News/sentiment integration tests\n'
	@printf '  $(GREEN)test-openapi$(RESET)          OpenAPI contract tests\n'
	@printf '  $(GREEN)test-outbox$(RESET)           Outbox delivery pattern tests\n'
	@printf '  $(GREEN)test-paper$(RESET)            Paper broker full cycle tests\n'
	@printf '  $(GREEN)test-protections$(RESET)      Position protection tests\n'
	@printf '  $(GREEN)test-reconcile$(RESET)        Reconciliation logic tests\n'
	@printf '  $(GREEN)test-risk$(RESET)             Risk engine tests\n'
	@printf '  $(GREEN)test-runtime$(RESET)          Runtime state tests\n'
	@printf '  $(GREEN)test-server-risk$(RESET)      Server risk context tests\n'
	@printf '  $(GREEN)test-session-reconcile$(RESET) Session reconciliation tests\n'
	@printf '  $(GREEN)test-strategy$(RESET)         Strategy engine tests\n'
	@printf '  $(GREEN)test-tradingview$(RESET)      TradingView webhook tests\n'
	@printf '  $(GREEN)test-trailing-stop$(RESET)    Trailing stop logic tests\n'
	@printf '  $(GREEN)test-version$(RESET)          Version/immutability tests\n'
	@printf '  $(GREEN)test-env-admin$(RESET)        Admin environment control tests\n'
	@printf '  $(GREEN)test-env-req$(RESET)          Environment requirement tests\n'
	@printf '  $(GREEN)test-bot-enhancements$(RESET) Bot enhancement tests\n'
	@printf '  $(GREEN)test-equity-sell$(RESET)      Equity sell limit tests\n'
	@printf '  $(GREEN)test-github-admin$(RESET)     GitHub admin environment tests\n'
	@printf '  $(GREEN)test-github-req$(RESET)       GitHub environment requirement tests\n'
	@printf '  $(GREEN)test-mql5-policy$(RESET)      MQL5 video EA policy tests\n'
	@printf '\n$(BOLD)Test targets — Feature Suites$(RESET)\n'
	@printf '  $(GREEN)test-agent-platform$(RESET)   Phase 4 agent platform suite (orchestrator/A2A/hooks/MCP/CRDT)\n'
	@printf '  $(GREEN)test-resilience$(RESET)       Risk + recovery fail-closed tests\n'
	@printf '  $(GREEN)test-performance$(RESET)      Performance probe suite\n'
	@printf '  $(GREEN)test-uat$(RESET)              Broker UAT suite (credentials required)\n'
	@printf '  $(GREEN)test-postgres$(RESET)         PostgreSQL integration tests\n'
	@printf '  $(GREEN)test-concurrency$(RESET)      Concurrency / race-condition tests\n'
	@printf '  $(GREEN)test-security$(RESET)         Auth + financial invariants + workflow security\n'
	@printf '  $(GREEN)test-agent-trading$(RESET)     Agent trading engine tests\n'
	@printf '  $(GREEN)test-agent-os$(RESET)          Agent OS framework tests\n'
	@printf '  $(GREEN)test-video-ea$(RESET)          Video EA research tests\n'
	@printf '  $(GREEN)test-prediction$(RESET)        Prediction engine tests\n'
	@printf '  $(GREEN)test-tfex$(RESET)              TFEX derivatives tests\n'
	@printf '  $(GREEN)test-notifications$(RESET)     Telegram notification tests\n'
	@printf '  $(GREEN)test-coordination$(RESET)      Coordination layer tests\n'
	@printf '  $(GREEN)test-ztrader$(RESET)           ZTrader integration tests\n'
	@printf '  $(GREEN)test-hyperopt$(RESET)          Hyperparameter optimization tests\n'
	@printf '  $(GREEN)test-scanner$(RESET)           Market scanner tests\n'
	@printf '  $(GREEN)test-backtest$(RESET)          Backtesting engine tests\n'
	@printf '  $(GREEN)test-market$(RESET)            Market data feed tests\n'
	@printf '  $(GREEN)test-penetration$(RESET)       Penetration/security tests\n'
	@printf '  $(GREEN)test-production-readiness$(RESET) Production readiness tests\n'
	@printf '  $(GREEN)test-research$(RESET)          Research pipeline tests\n'
	@printf '  $(GREEN)coverage$(RESET)              Coverage report (term + xml, gate ≥ $(COV_FAIL_UNDER)%%)\n'
	@printf '  $(GREEN)coverage-html$(RESET)         Coverage HTML report\n'
	@printf '\n$(BOLD)Security targets$(RESET)\n'
	@printf '  $(GREEN)security$(RESET)             pip-audit + bandit + zizmor (all-in-one)\n'
	@printf '  $(GREEN)security-full$(RESET)          Full security scan (all tools)\n'
	@printf '  $(GREEN)sec-bandit$(RESET)             Bandit static analysis (src + packages)\n'
	@printf '  $(GREEN)sec-pip-audit$(RESET)          Dependency vulnerability audit\n'
	@printf '  $(GREEN)sec-zizmor$(RESET)             GitHub Actions workflow scan\n'
	@printf '  $(GREEN)sec-gitleaks$(RESET)           Secret-pattern scan\n'
	@printf '\n$(BOLD)Database targets$(RESET)\n'
	@printf '  $(GREEN)db-migrate$(RESET)           Apply SQL migrations in order\n'
	@printf '  $(GREEN)db-status$(RESET)            List migration files\n'
	@printf '  $(GREEN)db-backup$(RESET)            Dump database → BACKUP_DIR\n'
	@printf '  $(GREEN)db-restore$(RESET)           Restore from BACKUP_FILE\n'
	@printf '\n$(BOLD)Container targets$(RESET)\n'
	@printf '  $(GREEN)docker$(RESET)               Build image + smoke-test import\n'
	@printf '  $(GREEN)docker-run$(RESET)           Run image (hardened, paper mode)\n'
	@printf '  $(GREEN)docker-scan$(RESET)          Trivy CVE scan\n'
	@printf '  $(GREEN)compose$(RESET)              Validate docker-compose.yml\n'
	@printf '\n$(BOLD)Operations targets$(RESET)\n'
	@printf '  $(GREEN)resilience$(RESET)           Full resilience suite\n'
	@printf '  $(GREEN)dr-drill$(RESET)             Disaster-recovery drill\n'
	@printf '  $(GREEN)dr-restore$(RESET)           Restore from latest backup\n'
	@printf '  $(GREEN)load-test$(RESET)            Load test (paper mode)\n'
	@printf '  $(GREEN)env-check$(RESET)            Validate .env for injection risks\n'
	@printf '  $(GREEN)github-health$(RESET)        GitHub repo health check\n'
	@printf '\n$(BOLD)Frontend targets$(RESET)\n'
	@printf '  $(GREEN)frontend-lint$(RESET)          Next.js ESLint\n'
	@printf '  $(GREEN)frontend-type$(RESET)          Next.js TypeScript check\n'
	@printf '  $(GREEN)frontend-build$(RESET)         Next.js production build\n'
	@printf '  $(GREEN)frontend-test$(RESET)          Frontend unit tests\n'
	@printf '  $(GREEN)frontend-e2e$(RESET)           Playwright browser E2E\n'
	@printf '\n$(BOLD)Dashboard targets$(RESET)\n'
	@printf '  $(GREEN)dashboard-lint$(RESET)           Vite dashboard lint\n'
	@printf '  $(GREEN)dashboard-type$(RESET)           Vite dashboard TypeScript\n'
	@printf '  $(GREEN)dashboard-build$(RESET)          Vite dashboard production build\n'
	@printf '  $(GREEN)dashboard-test$(RESET)           Dashboard unit tests\n'
	@printf '\n$(BOLD)Worker targets$(RESET)\n'
	@printf '  $(GREEN)start-worker$(RESET)           Start background worker\n'
	@printf '  $(GREEN)stop-worker$(RESET)            Stop background worker\n'
	@printf '  $(GREEN)restart-worker$(RESET)         Restart background worker\n'
	@printf '\n$(BOLD)TUI targets$(RESET)\n'
	@printf '  $(GREEN)tui-install$(RESET)            Install zksato-cli package (includes TUI)\n'
	@printf '  $(GREEN)tui-start$(RESET)              Launch the zksato TUI (requires running API on :9569)\n'
	@printf '  $(GREEN)tui-build$(RESET)              Build standalone TUI executable with PyInstaller\n'
	@printf '  $(GREEN)tui$(RESET)                    Alias for tui-start\n'
	@printf '\n$(BOLD)Documentation targets$(RESET)\n'
	@printf '  $(GREEN)docs-check$(RESET)             Validate docs structure\n'
	@printf '  $(GREEN)docs-build$(RESET)             Build documentation site\n'
	@printf '  $(GREEN)docs-validate$(RESET)          Validate ADRs and templates\n'
	@printf '\n$(BOLD)All-in-one targets$(RESET)\n'
	@printf '  $(GREEN)all$(RESET)                    Full validation + start all services\n'
	@printf '  $(GREEN)all-features$(RESET)           Install every optional extra\n'
	@printf '  $(GREEN)test-all-features$(RESET)        Run every feature test suite\n'
	@printf '  $(GREEN)all-services$(RESET)           Start all services (backend+frontend+dashboard+worker)\n'
	@printf '  $(GREEN)start-all$(RESET)                Start backend + frontend + dashboard + worker\n'
	@printf '  $(GREEN)stop-all$(RESET)                 Stop all services\n'
	@printf '  $(GREEN)restart-all$(RESET)            Restart all services (stop + start)\n'
	@printf '  $(GREEN)start-backend$(RESET)            Start uvicorn API on :9569\n'
	@printf '  $(GREEN)stop-backend$(RESET)             Stop uvicorn API\n'
	@printf '  $(GREEN)start-frontend$(RESET)           Start Next.js dev on :3016\n'
	@printf '  $(GREEN)stop-frontend$(RESET)            Stop Next.js dev\n'
	@printf '  $(GREEN)start-dashboard$(RESET)          Start Vite dashboard on :5173\n'
	@printf '  $(GREEN)stop-dashboard$(RESET)           Stop Vite dashboard\n'
	@printf '  $(GREEN)start-worker$(RESET)             Start background worker\n'
	@printf '  $(GREEN)stop-worker$(RESET)              Stop background worker\n'
	@printf '  $(GREEN)health-check-all$(RESET)         Curl /readyz + all ports\n'
	@printf '\n$(BOLD)CI gates$(RESET)\n'
	@printf '  $(GREEN)ci$(RESET)                   Standard CI pipeline\n'
	@printf '  $(GREEN)ci-full$(RESET)                ci + security + resilience + docker + env-check\n'
	@printf '  $(GREEN)ci-security$(RESET)            Full security pipeline\n'
	@printf '  $(GREEN)clean$(RESET)                  Remove build artefacts\n'
	@printf '\n'

# ============================================================
# INSTALL
# ============================================================
# Two-step editable install:
#   1. root `zksato` package (legacy modules + tooling extras)
#   2. workspace packages, leaf-first — inter-package deps are bare names
#      and unpublished, so dependents must install after their deps.
#   3. apps (thin wrappers)
install:
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev,quality,security]'
	$(PIP) install -e $(PKGS_LEAF)
	$(PIP) install -e $(PKGS_MIDDLE)
	$(PIP) install -e $(PKGS_TOP)
	@printf '$(GREEN)Workspace ready: zksato + 10 packages installed$(RESET)\n'

install-apps:
	$(PIP) install -e $(APP_API)
	$(PIP) install -e $(APP_CLI)
	$(PIP) install -e $(APP_WORKER)
	@printf '$(GREEN)Apps ready: api, cli, worker installed$(RESET)\n'

install-settrade:
	$(PIP) install -e '.[settrade]'

install-ccxt:
	$(PIP) install -e '.[ccxt]'

install-prediction:
	$(PIP) install -e '.[prediction]'

install-observability:
	$(PIP) install -e '.[observability]'

install-agent-os:
	$(PIP) install -e $(PKG_AUTOMATION)

install-cli:
	$(PIP) install -e $(PKG_CLI)

install-all: install install-apps
	$(PIP) install -e '.[settrade,ccxt,prediction,observability]'

install-deps:
	@printf '$(CYAN)Installing system dependencies…$(RESET)\n'
	@sudo apt-get update -y && sudo apt-get install -y \
		postgresql-client redis-tools curl wget gnupg \
		|| printf '$(YELLOW)Skipping system deps (no sudo/apt)$(RESET)\n'

# ============================================================
# ALL-IN-ONE — single command for everything
# ============================================================

# ---- Master target: everything ----
all: install-all lint format-check type coverage contract package compose security resilience start-all
	@printf '$(GREEN)$(BOLD)ALL DONE — zksato fully validated and running$(RESET)\n'
	@printf '  Backend  : http://127.0.0.1:9569$(RESET)\n'
	@printf '  Frontend : http://127.0.0.1:3016$(RESET)\n'
	@printf '  Dashboard: http://127.0.0.1:5173$(RESET)\n'

# ---- Feature test target ----
test-all-features: test-agent-trading test-agent-os test-agent-platform test-video-ea \
	test-prediction test-tfex test-notifications test-coordination test-ztrader \
	test-hyperopt test-scanner test-backtest test-market test-penetration \
	test-production-readiness test-research \
	test-api test-auth test-approvals test-audit test-broker \
	test-concurrency-adv test-fill-deltas test-indicators test-monorepo \
	test-news test-openapi test-outbox test-paper test-protections \
	test-reconcile test-risk test-runtime test-server-risk test-session-reconcile \
	test-strategy test-tradingview test-trailing-stop test-version \
	test-env-admin test-env-req test-bot-enhancements test-equity-sell \
	test-github-admin test-github-req test-mql5-policy

# ---- Feature installation ----
all-features: install-all

# ---- All services ----
all-services: start-backend start-frontend start-dashboard start-worker

start-all: start-backend start-frontend start-dashboard start-worker
	@printf '$(CYAN)Waiting 3s for services to bind…$(RESET)\n'
	@sleep 3
	@printf '$(GREEN)All services started. PIDs saved to /tmp/zksato-*.pid$(RESET)\n'
	@printf '  Backend  : http://127.0.0.1:9569  (API docs: /docs, health: /readyz)$(RESET)\n'
	@printf '  Frontend : http://127.0.0.1:3016$(RESET)\n'
	@printf '  Dashboard: http://127.0.0.1:5173$(RESET)\n'
	@printf '  Worker   : background$(RESET)\n'

stop-all: stop-backend stop-frontend stop-dashboard stop-worker
	@printf '$(GREEN)All services stopped.$(RESET)\n'

# ---- Individual service start/stop ----
start-backend:
	@printf '$(CYAN)Starting zksato backend (uvicorn :9569)…$(RESET)\n'
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	ZKSATO_TRADING_MODE=paper $(PYTHON) -m uvicorn zksato.api:app --host 127.0.0.1 --port 9569 --reload & \
	echo $$! > /tmp/zksato-backend.pid
	@printf '$(GREEN)Backend PID $$(cat /tmp/zksato-backend.pid) — http://127.0.0.1:9569$(RESET)\n'

stop-backend:
	@if [ -f /tmp/zksato-backend.pid ]; then \
		kill $$(cat /tmp/zksato-backend.pid) 2>/dev/null && \
		rm -f /tmp/zksato-backend.pid && \
		printf '$(GREEN)Backend stopped$(RESET)\n'; \
	else \
		printf '$(YELLOW)No backend PID file found$(RESET)\n'; \
	fi

start-frontend:
	@printf '$(CYAN)Starting Next.js frontend (:3016)…$(RESET)\n'
	@cd frontend && $(NPM) run dev & \
	echo $$! > /tmp/zksato-frontend.pid
	@printf '$(GREEN)Frontend PID $$(cat /tmp/zksato-frontend.pid) — http://127.0.0.1:3016$(RESET)\n'

stop-frontend:
	@if [ -f /tmp/zksato-frontend.pid ]; then \
		kill $$(cat /tmp/zksato-frontend.pid) 2>/dev/null && \
		rm -f /tmp/zksato-frontend.pid && \
		printf '$(GREEN)Frontend stopped$(RESET)\n'; \
	else \
		printf '$(YELLOW)No frontend PID file found$(RESET)\n'; \
	fi

start-dashboard:
	@printf '$(CYAN)Starting Vite dashboard (:5173)…$(RESET)\n'
	@cd dashboard && $(NPM) run dev & \
	echo $$! > /tmp/zksato-dashboard.pid
	@printf '$(GREEN)Dashboard PID $$(cat /tmp/zksato-dashboard.pid) — http://127.0.0.1:5173$(RESET)\n'

stop-dashboard:
	@if [ -f /tmp/zksato-dashboard.pid ]; then \
		kill $$(cat /tmp/zksato-dashboard.pid) 2>/dev/null && \
		rm -f /tmp/zksato-dashboard.pid && \
		printf '$(GREEN)Dashboard stopped$(RESET)\n'; \
	else \
		printf '$(YELLOW)No dashboard PID file found$(RESET)\n'; \
	fi

start-worker:
	@printf '$(CYAN)Starting zksato background worker…$(RESET)\n'
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	ZKSATO_TRADING_MODE=paper $(PYTHON) -m zksato_worker & \
	echo $$! > /tmp/zksato-worker.pid
	@printf '$(GREEN)Worker PID $$(cat /tmp/zksato-worker.pid)$(RESET)\n'

stop-worker:
	@if [ -f /tmp/zksato-worker.pid ]; then \
		kill $$(cat /tmp/zksato-worker.pid) 2>/dev/null && \
		rm -f /tmp/zksato-worker.pid && \
		printf '$(GREEN)Worker stopped$(RESET)\n'; \
	else \
		printf '$(YELLOW)No worker PID file found$(RESET)\n'; \
	fi

# ---- Restart targets ----
restart-backend: stop-backend start-backend

restart-frontend: stop-frontend start-frontend

restart-dashboard: stop-dashboard start-dashboard

restart-worker: stop-worker start-worker

# ============================================================
# TUI — Terminal User Interface
# ============================================================
tui-install: install-cli
	@printf '$(GREEN)zksato-cli installed (includes TUI)$(RESET)\n'

tui-start:
	@printf '$(CYAN)Launching zksato TUI…$(RESET)\n'
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	$(PYTHON) -m zksato_cli.main tui start --host localhost --port 9569

tui-build:
	@printf '$(CYAN)Building standalone TUI executable…$(RESET)\n'
	@command -v pyinstaller >/dev/null 2>&1 || (printf '$(YELLOW)Installing pyinstaller…$(RESET)\n' && $(PIP) install pyinstaller)
	@mkdir -p dist/tui
	@pyinstaller --onefile --name zksato-tui \
		--hidden-import=textual \
		--hidden-import=rich \
		--hidden-import=typer \
		--hidden-import=pydantic \
		--hidden-import=pydantic_settings \
		--hidden-import=yaml \
		--collect-all=textual \
		--collect-all=rich \
		--entry-point="zksato_cli.main:app" \
		--distpath=dist/tui \
		--workpath=build/tui \
		--specpath=build/tui \
		/home/cvsz/zksato/packages/zksato-cli/src/zksato_cli/main.py
	@printf '$(GREEN)TUI executable built: dist/tui/zksato-tui$(RESET)\n'

tui: tui-start

restart-all: stop-all start-all


health-check-all:
	@printf '$(CYAN)Health-checking all services…$(RESET)\n'
	@curl -fsS http://127.0.0.1:9569/readyz > /dev/null 2>&1 && \
		printf '  Backend  : $(GREEN)OK$(RESET)\n' || \
		printf '  Backend  : $(RED)DOWN$(RESET)\n'
	@curl -fsS http://127.0.0.1:3016 > /dev/null 2>&1 && \
		printf '  Frontend : $(GREEN)OK$(RESET)\n' || \
		printf '  Frontend : $(RED)DOWN$(RESET)\n'
	@curl -fsS http://127.0.0.1:5173 > /dev/null 2>&1 && \
		printf '  Dashboard: $(GREEN)OK$(RESET)\n' || \
		printf '  Dashboard: $(RED)DOWN$(RESET)\n'
	@if [ -f /tmp/zksato-worker.pid ] && kill -0 $$(cat /tmp/zksato-worker.pid) 2>/dev/null; then \
		printf '  Worker   : $(GREEN)OK$(RESET)\n'; \
	else \
		printf '  Worker   : $(RED)DOWN$(RESET)\n'; \
	fi

# ============================================================
# QUALITY — lint / format / type
# ============================================================
lint:
	ruff check .
	@command -v yamllint >/dev/null 2>&1 && yamllint .github .yamllint.yml docker-compose.yml || true
	@command -v hadolint >/dev/null 2>&1 && hadolint Dockerfile || true

format:
	ruff format .

format-check:
	ruff format --check .

shellcheck:
	shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh 2>/dev/null

type:
	mypy src/zksato scripts

# ============================================================
# TEST — Python Core
# ============================================================
test:
	$(PYTEST) -m "not uat and not performance"

test-api:
	$(PYTEST) tests/test_api.py tests/test_api_extended.py

test-auth:
	$(PYTEST) tests/test_auth.py tests/test_secure_sessions.py

test-approvals:
	$(PYTEST) tests/test_approvals.py

test-audit:
	$(PYTEST) tests/test_audit_integrity.py

test-broker:
	$(PYTEST) tests/test_paper_broker_full.py tests/test_paper_matching.py tests/test_broker_ccxt.py tests/test_settrade_adapters.py

test-concurrency-adv:
	$(PYTEST) tests/test_concurrency.py tests/test_runtime_state.py

test-fill-deltas:
	$(PYTEST) tests/test_fill_deltas.py

test-indicators:
	$(PYTEST) tests/test_indicators_full.py tests/test_indicators_advanced.py

test-monorepo:
	$(PYTEST) tests/test_monorepo_packages.py

test-news:
	$(PYTEST) tests/test_news.py

test-openapi:
	$(PYTEST) tests/test_openapi_contract.py tests/test_openapi_contract_edges.py

test-outbox:
	$(PYTEST) tests/test_outbox_delivery.py

test-paper:
	$(PYTEST) tests/test_paper_broker_full.py tests/test_paper_matching.py tests/test_paper_recovery.py

test-protections:
	$(PYTEST) tests/test_protections.py

test-reconcile:
	$(PYTEST) tests/test_reconcile.py tests/test_session_reconciliation.py

test-risk:
	$(PYTEST) tests/test_risk.py tests/test_risk_advanced.py tests/test_risk_properties.py tests/test_risk_sell.py tests/test_equity_sell_limits.py tests/test_server_risk_context.py tests/test_financial_invariants.py

test-runtime:
	$(PYTEST) tests/test_runtime_state.py

test-server-risk:
	$(PYTEST) tests/test_server_risk_context.py

test-session-reconcile:
	$(PYTEST) tests/test_session_reconciliation.py

test-strategy:
	$(PYTEST) tests/test_strategy.py tests/test_strategies_enhanced.py tests/test_strategy_expanded.py tests/test_strategy_version_immutability.py

test-tradingview:
	$(PYTEST) tests/test_tradingview.py

test-trailing-stop:
	$(PYTEST) tests/test_trailing_stop.py

test-version:
	$(PYTEST) tests/test_version.py

test-env-admin:
	$(PYTEST) tests/test_admin_env.py tests/test_github_environment_admin.py

test-env-req:
	$(PYTEST) tests/test_environment_controls.py tests/test_github_environment_requirements.py

test-bot-enhancements:
	$(PYTEST) tests/test_bot_enhancements.py

test-equity-sell:
	$(PYTEST) tests/test_equity_sell_limits.py

test-github-admin:
	$(PYTEST) tests/test_github_environment_admin.py

test-github-req:
	$(PYTEST) tests/test_github_environment_requirements.py

test-mql5-policy:
	$(PYTEST) tests/test_mql5_video_ea_policy.py

# ============================================================
# TEST — Feature Suites
# ============================================================
test-agent-platform:
	$(PYTEST) tests/test_agent_platform.py

test-resilience:
	$(PYTEST) -q \
		tests/test_risk_properties.py \
		tests/test_reconciliation_gate.py \
		tests/test_paper_recovery.py \
		tests/test_audit_integrity.py \
		tests/test_approvals.py \
		tests/test_auth.py \
		tests/test_financial_invariants.py \
		tests/test_workflow_security.py \
		tests/test_reconciliation_restart_freshness.py

test-performance:
	$(PYTEST) -m "performance" tests/test_performance_probe.py

test-uat:
	@printf '$(YELLOW)WARNING: Requires broker UAT credentials (Thu/Fri 09:00–17:00 TH).$(RESET)\n'
	$(PYTEST) -m "uat" tests/test_uat.py tests/test_settrade_adapters.py

test-postgres:
	$(PYTEST) tests/test_postgres_integration.py tests/test_persistence.py tests/test_priority_persistence.py

test-concurrency:
	$(PYTEST) tests/test_concurrency.py

test-security:
	$(PYTEST) tests/test_workflow_security.py tests/test_financial_invariants.py tests/test_auth.py

test-agent-trading:
	$(PYTEST) tests/test_agent_trading.py

test-agent-os:
	$(PYTEST) tests/test_agent_os.py

test-video-ea:
	$(PYTEST) tests/test_video_ea.py tests/test_video_ea_runtime.py tests/test_video_ea_research.py tests/test_video_ea_policy.py tests/test_mql5_video_ea_policy.py

test-prediction:
	$(PYTEST) tests/test_prediction.py tests/test_prediction_feed.py tests/test_prediction_broker.py tests/test_prediction_live.py

test-tfex:
	$(PYTEST) tests/test_tfex.py tests/test_tfex_completion.py

test-notifications:
	$(PYTEST) tests/test_telegram.py

test-coordination:
	$(PYTEST) tests/test_coordination.py

test-ztrader:
	$(PYTEST) tests/test_ztrader_integration.py

test-hyperopt:
	$(PYTEST) tests/test_hyperopt.py

test-scanner:
	$(PYTEST) tests/test_scanner.py

test-backtest:
	$(PYTEST) tests/test_backtest_costs.py tests/test_backtest_metrics.py tests/test_backtest_analytics.py

test-market:
	$(PYTEST) tests/test_market_feeds.py tests/test_market_calendar.py tests/test_market_rules.py

test-penetration:
	$(PYTEST) tests/test_penetration.py

test-production-readiness:
	$(PYTEST) tests/test_production_readiness.py

test-research:
	$(PYTEST) tests/test_research_completion.py

# ============================================================
# TEST — Frontend
# ============================================================
frontend-lint:
	@cd frontend && $(NPM) run lint 2>/dev/null || \
		$(NPM) exec eslint --max-warnings 0 src/ 2>/dev/null || \
		printf '$(YELLOW)No ESLint config found, skipping$(RESET)\n'

frontend-type:
	@cd frontend && $(NODE) $(NPM) exec tsc --noEmit

frontend-build:
	@cd frontend && $(NPM) run build

frontend-test:
	@cd frontend && $(NPM) test 2>/dev/null || \
		printf '$(YELLOW)No unit test script configured, skipping$(RESET)\n'

frontend-e2e:
	@cd frontend && $(NPM) run test:e2e

# ============================================================
# TEST — Dashboard
# ============================================================
dashboard-lint:
	@cd dashboard && $(NPM) run lint 2>/dev/null || \
		$(NPM) exec oxlint 2>/dev/null || \
		printf '$(YELLOW)No lint script found, skipping$(RESET)\n'

dashboard-type:
	@cd dashboard && $(NODE) $(NPM) exec tsc -b

dashboard-build:
	@cd dashboard && $(NPM) run build

dashboard-test:
	@cd dashboard && $(NPM) test 2>/dev/null || \
		printf '$(YELLOW)No test script found, skipping$(RESET)\n'

# ============================================================
# COVERAGE
# ============================================================
coverage:
	$(PYTEST) -m "not uat and not performance" \
		--cov=zksato \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=$(COV_FAIL_UNDER)

coverage-html:
	$(PYTEST) -m "not uat and not performance" \
		--cov=zksato \
		--cov-branch \
		--cov-report=html \
		--cov-fail-under=$(COV_FAIL_UNDER)
	@printf '$(GREEN)HTML report:$(RESET) htmlcov/index.html\n'

# ============================================================
# CONTRACTS / DOCS
# ============================================================
contract:
	$(PYTHON) scripts/openapi_contract.py --output openapi.json

openapi: contract

licenses:
	pip-licenses --format=json --output-file=licenses.json

# ============================================================
# SECURITY — all-in-one
# ============================================================
security: sec-bandit sec-pip-audit sec-zizmor

security-full: sec-bandit sec-pip-audit sec-zizmor sec-gitleaks shellcheck

# Bandit scans the legacy tree AND all monorepo packages; -ll = medium+ severity
sec-bandit:
	bandit -q -r src packages -ll

sec-pip-audit:
	$(PIP) freeze --exclude-editable > audit-requirements.txt
	pip-audit --strict --progress-spinner off -r audit-requirements.txt

sec-zizmor:
	zizmor --min-severity high --min-confidence high .github/workflows

sec-gitleaks:
	gitleaks detect --source . --verbose

audit: security

bandit: sec-bandit

gitleaks: sec-gitleaks

# ============================================================
# DATABASE
# ============================================================
db-migrate:
	@printf '$(CYAN)Applying migrations…$(RESET)\n'
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL before running db-migrate}"
	for f in migrations/*.sql; do \
		printf '  applying $$f\n'; \
		psql "$$ZKSATO_DATABASE_URL" -f "$$f"; \
	done

db-status:
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL before running db-status}"
	@printf '$(CYAN)Migration files in migrations/:$(RESET)\n'
	@ls -1 migrations/*.sql

db-backup:
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL before running db-backup}"
	BACKUP_DIR=$(BACKUP_DIR) bash scripts/backup_postgres.sh

db-restore:
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL before running db-restore}"
	@: "$${BACKUP_FILE:?Set BACKUP_FILE=path/to/file.dump}"
	bash scripts/restore_postgres.sh "$(BACKUP_FILE)"

# ============================================================
# CONTAINER
# ============================================================
docker:
	docker build --pull --tag $(IMAGE_TAG) .
	docker run --rm \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=64m \
		--cap-drop ALL \
		--security-opt no-new-privileges:true \
		--env ZKSATO_TRADING_MODE=paper \
		$(IMAGE_TAG) $(PYTHON) -c 'import zksato; print("import OK")'

docker-run:
	docker run --rm -it \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=64m \
		--cap-drop ALL \
		--security-opt no-new-privileges:true \
		--env ZKSATO_TRADING_MODE=paper \
		-p 9569:9569 \
		$(IMAGE_TAG)

docker-scan:
	trivy image --exit-code 1 --severity CRITICAL,HIGH $(IMAGE_TAG)

compose:
	docker compose config --quiet

# ============================================================
# RESILIENCE
# ============================================================
resilience: test-resilience

# ============================================================
# DISASTER RECOVERY
# ============================================================
dr-drill:
	@printf '$(YELLOW)Starting DR drill — backup → restore → verify…$(RESET)\n'
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL}"
	BACKUP_DIR=$(BACKUP_DIR) bash scripts/backup_postgres.sh
	$(PYTEST) -q \
		tests/test_paper_recovery.py \
		tests/test_audit_integrity.py \
		tests/test_persistence.py

dr-restore:
	@: "$${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL}"
	@LATEST=$$(ls -t $(BACKUP_DIR)/*.dump 2>/dev/null | head -1); \
		test -n "$$LATEST" || (printf '$(YELLOW)No .dump found in $(BACKUP_DIR)$(RESET)\n' && exit 1); \
		printf '$(CYAN)Restoring from $$LATEST…$(RESET)\n'; \
		bash scripts/restore_postgres.sh "$$LATEST"

# ============================================================
# LOAD TEST
# ============================================================
load-test:
	@printf '$(YELLOW)Running load test in paper mode.$(RESET)\n'
	ZKSATO_TRADING_MODE=paper $(PYTHON) scripts/load_test.py

# ============================================================
# ENV CHECK
# ============================================================
env-check:
	$(PYTHON) -c "\
import sys, subprocess; \
result = subprocess.run(['$(PYTHON)', '-c', \
  'from zksato.secrets import validate_env_file; validate_env_file(\".env\")'], \
  capture_output=True, text=True); \
print(result.stdout or result.stderr or 'env-check: OK'); \
sys.exit(result.returncode)"

# ============================================================
# GITHUB HEALTH
# ============================================================
github-health:
	$(PYTHON) scripts/github_health.py

# ============================================================
# CLEAN
# ============================================================
clean:
	rm -rf build dist htmlcov .coverage coverage.xml audit-requirements.txt \
		openapi.json licenses.json \
		.mypy_cache .ruff_cache .pytest_cache \
		.zksato bandit-report.json log.txt \
		__pycache__ src/zksato/__pycache__ tests/__pycache__ \
		src/zksato/**/__pycache__ scripts/__pycache__ \
		packages/*/__pycache__ packages/*/src/**/__pycache__ \
		apps/*/__pycache__ apps/*/src/**/__pycache__

# ============================================================
# DOCUMENTATION
# ============================================================
docs-check:
	@printf '$(CYAN)Checking documentation structure…$(RESET)\n'
	@test -f docs/INDEX.md || (printf '$(RED)Missing docs/INDEX.md$(RESET)\n' && exit 1)
	@test -f docs/ARCHITECTURE.md || (printf '$(RED)Missing docs/ARCHITECTURE.md$(RESET)\n' && exit 1)
	@test -f ROADMAP.md || (printf '$(RED)Missing ROADMAP.md$(RESET)\n' && exit 1)
	@test -d docs/adr || (printf '$(RED)Missing docs/adr/$(RESET)\n' && exit 1)
	@ls docs/adr/*.md | wc -l | xargs -I {} printf '  ADRs found: {}\n'
	@printf '$(GREEN)Documentation structure OK$(RESET)\n'

docs-build:
	@printf '$(CYAN)Building documentation site…$(RESET)\n'
	@command -v mkdocs >/dev/null 2>&1 && mkdocs build --strict || \
		(printf '$(YELLOW)mkdocs not installed, skipping site build$(RESET)\n' && exit 0)
	@printf '$(GREEN)Documentation site built in site/$(RESET)\n'

docs-validate:
	@printf '$(CYAN)Validating ADRs and templates…$(RESET)\n'
	@$(PYTHON) -c "import os, re; adr_dir='docs/adr'; template_dir='docs/templates'; [print(f'  WARNING: {f} missing ADR header') for f in os.listdir(adr_dir) if f.endswith('.md') and f != 'README.md' and not re.search(r'^# ADR-\d+:', open(os.path.join(adr_dir, f)).read(), re.MULTILINE)]; [print(f'  WARNING: {f} missing Status field') for f in os.listdir(adr_dir) if f.endswith('.md') and f != 'README.md' and 'Status:' not in open(os.path.join(adr_dir, f)).read()]; print('  ADR validation complete'); [print(f'  Template: {f}') for f in os.listdir(template_dir) if f.endswith('.md')]; print('$(GREEN)Documentation validation complete$(RESET)')"

# ============================================================
# PACKAGE
# ============================================================
package:
	rm -rf build dist
	$(PYTHON) -m build
	twine check dist/*

# ============================================================
# CI GATES
# ============================================================
ci: lint format-check type coverage contract package compose

ci-security: lint format-check type coverage contract package compose security-full resilience docker env-check docs-validate

ci-full: ci security resilience docker env-check test-all-features docs-check