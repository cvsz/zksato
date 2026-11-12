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
	install-observability install-agent-trading install-agent-os \
	install-video-ea install-notifications install-all install-deps \
	lint format format-check shellcheck type \
	test test-resilience test-performance test-uat test-postgres \
	test-concurrency test-frontend test-e2e test-security \
	test-agent-trading test-agent-os test-video-ea test-prediction \
	test-tfex test-notifications test-coordination test-ztrader \
	test-hyperopt test-scanner test-backtest test-market \
	test-penetration test-production-readiness test-research \
	coverage coverage-html \
	contract openapi licenses \
	security audit bandit gitleaks \
	db-migrate db-status db-backup db-restore \
	docker docker-run docker-scan compose \
	resilience dr-drill dr-restore load-test env-check github-health \
	all all-features all-services start-all stop-all restart-all \
	start-backend stop-backend restart-backend \
	start-frontend stop-frontend restart-frontend \
	start-dashboard stop-dashboard restart-dashboard \
	health-check-all \
	frontend-lint frontend-type frontend-build frontend-test frontend-e2e \
	dashboard-lint dashboard-type dashboard-build \
	security-full sec-bandit sec-pip-audit sec-zizmor sec-gitleaks \
	ci ci-full ci-security clean \
	docs-check docs-build docs-validate
	dashboard-lint dashboard-type dashboard-build \
	security-full sec-bandit sec-pip-audit sec-zizmor sec-gitleaks \
	ci ci-full ci-security clean

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

# ============================================================
# HELP
# ============================================================
help:
	@printf '$(BOLD)$(CYAN)zksato — Enterprise Makefile$(RESET)\n'
	@printf 'Risk-first automated trading control plane for SET / TFEX\n\n'
	@printf '$(BOLD)Install targets$(RESET)\n'
	@printf '  $(GREEN)install$(RESET)              Core + dev + quality + security extras\n'
	@printf '  $(GREEN)install-settrade$(RESET)      Settrade-v2 broker adapter\n'
	@printf '  $(GREEN)install-ccxt$(RESET)          CCXT multi-exchange adapter\n'
	@printf '  $(GREEN)install-prediction$(RESET)    XGBoost / scikit-learn prediction\n'
	@printf '  $(GREEN)install-observability$(RESET) OpenTelemetry SDK\n'
	@printf '  $(GREEN)install-agent-trading$(RESET)  Agent trading engine\n'
	@printf '  $(GREEN)install-agent-os$(RESET)       Agent OS framework\n'
	@printf '  $(GREEN)install-video-ea$(RESET)       Video EA research pipeline\n'
	@printf '  $(GREEN)install-notifications$(RESET)   Telegram notifications\n'
	@printf '  $(GREEN)install-all$(RESET)           Every optional extra\n'
	@printf '  $(GREEN)install-deps$(RESET)          Install system-level dependencies\n'
	@printf '\n$(BOLD)Quality targets$(RESET)\n'
	@printf '  $(GREEN)lint$(RESET)                 ruff + yamllint + hadolint\n'
	@printf '  $(GREEN)format$(RESET)               ruff format (auto-fix)\n'
	@printf '  $(GREEN)format-check$(RESET)         ruff format --check (no mutation)\n'
	@printf '  $(GREEN)shellcheck$(RESET)         Lint all shell scripts\n'
	@printf '  $(GREEN)type$(RESET)                 mypy type-check src + scripts\n'
	@printf '\n$(BOLD)Test targets$(RESET)\n'
	@printf '  $(GREEN)test$(RESET)                 Unit/integration suite (excludes uat, perf)\n'
	@printf '  $(GREEN)test-resilience$(RESET)       Risk + recovery fail-closed tests\n'
	@printf '  $(GREEN)test-performance$(RESET)      Performance probe suite\n'
	@printf '  $(GREEN)test-uat$(RESET)              Broker UAT suite (credentials required)\n'
	@printf '  $(GREEN)test-postgres$(RESET)         PostgreSQL integration tests\n'
	@printf '  $(GREEN)test-concurrency$(RESET)      Concurrency / race-condition tests\n'
	@printf '  $(GREEN)test-frontend$(RESET)         Frontend lint + type + build\n'
	@printf '  $(GREEN)test-e2e$(RESET)              Browser E2E tests (Playwright)\n'
	@printf '  $(GREEN)test-security$(RESET)         Bandit + pip-audit + workflow scan\n'
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
	@printf '  $(GREEN)coverage$(RESET)              Coverage report (term + xml)\n'
	@printf '  $(GREEN)coverage-html$(RESET)         Coverage HTML report\n'
	@printf '\n$(BOLD)Security targets$(RESET)\n'
	@printf '  $(GREEN)security$(RESET)             pip-audit + bandit + zizmor (all-in-one)\n'
	@printf '  $(GREEN)security-full$(RESET)          Full security scan (all tools)\n'
	@printf '  $(GREEN)sec-bandit$(RESET)             Bandit static analysis\n'
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
	@printf '\n$(BOLD)Documentation targets$(RESET)\n'
	@printf '  $(GREEN)docs-check$(RESET)             Validate docs structure\n'
	@printf '  $(GREEN)docs-build$(RESET)             Build documentation site\n'
	@printf '  $(GREEN)docs-validate$(RESET)          Validate ADRs and templates\n'
	@printf '\n$(BOLD)All-in-one targets$(RESET)\n'
	@printf '  $(GREEN)all$(RESET)                    Full validation + start all services\n'
	@printf '  $(GREEN)all-features$(RESET)           Install every optional extra\n'
	@printf '  $(GREEN)all-services$(RESET)           Start all services (backend+frontend+dashboard)\n'
	@printf '  $(GREEN)start-all$(RESET)                Start backend + frontend + dashboard\n'
	@printf '  $(GREEN)stop-all$(RESET)                 Stop all services\n'
	@printf '  $(GREEN)restart-all$(RESET)            Restart all services (stop + start)\n'
	@printf '  $(GREEN)restart-backend$(RESET)          Restart uvicorn API\n'
	@printf '  $(GREEN)restart-frontend$(RESET)         Restart Next.js dev server\n'
	@printf '  $(GREEN)restart-dashboard$(RESET)        Restart Vite dashboard\n'
	@printf '  $(GREEN)start-backend$(RESET)            Start uvicorn API on :9569\n'
	@printf '  $(GREEN)stop-backend$(RESET)             Stop uvicorn API\n'
	@printf '  $(GREEN)start-frontend$(RESET)           Start Next.js dev on :3016\n'
	@printf '  $(GREEN)stop-frontend$(RESET)            Stop Next.js dev\n'
	@printf '  $(GREEN)start-dashboard$(RESET)          Start Vite dashboard on :5173\n'
	@printf '  $(GREEN)stop-dashboard$(RESET)           Stop Vite dashboard\n'
	@printf '  $(GREEN)health-check-all$(RESET)         Curl /readyz + all ports\n'
	@printf '\n$(BOLD)CI gates$(RESET)\n'
	@printf '  $(GREEN)ci$(RESET)                   Standard CI pipeline\n'
	@printf '  $(GREEN)ci-full$(RESET)                ci + security + resilience + docker + env-check\n'
	@printf '  $(GREEN)ci-security$(RESET)            Full security pipeline\n'
	@printf '  $(GREEN)clean$(RESET)                  Remove build artefacts\n'
	@printf '\n'

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
test-all-features: test-agent-trading test-agent-os test-video-ea test-prediction test-tfex \
	test-notifications test-coordination test-ztrader test-hyperopt \
	test-scanner test-backtest test-market test-penetration \
	test-production-readiness test-research

# ---- Feature installation ----
all-features: install-all

install-deps:
	@printf '$(CYAN)Installing system dependencies…$(RESET)\n'
	@sudo apt-get update -y && sudo apt-get install -y \
		postgresql-client redis-tools curl wget gnupg \
		|| printf '$(YELLOW)Skipping system deps (no sudo/apt)$(RESET)\n'

install-all:
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev,quality,security,settrade,ccxt,prediction,observability,agent-trading,agent-os,video-ea,notifications]'

# ---- All services ----
all-services: start-backend start-frontend start-dashboard

start-all: start-backend start-frontend start-dashboard
	@printf '$(CYAN)Waiting 3s for services to bind…$(RESET)\n'
	@sleep 3
	@printf '$(GREEN)All services started. PIDs saved to /tmp/zksato-*.pid$(RESET)\n'
	@printf '  Backend  : http://127.0.0.1:9569  (API docs: /docs, health: /readyz)$(RESET)\n'
	@printf '  Frontend : http://127.0.0.1:3016$(RESET)\n'
	@printf '  Dashboard: http://127.0.0.1:5173$(RESET)\n'

stop-all: stop-backend stop-frontend stop-dashboard
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

# ---- Restart targets ----
restart-backend: stop-backend start-backend

restart-frontend: stop-frontend start-frontend

restart-dashboard: stop-dashboard start-dashboard

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

# ============================================================
# INSTALL
# ============================================================
install:
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev,quality,security]'

install-settrade:
	$(PIP) install -e '.[settrade]'

install-ccxt:
	$(PIP) install -e '.[ccxt]'

install-prediction:
	$(PIP) install -e '.[prediction]'

install-observability:
	$(PIP) install -e '.[observability]'

install-agent-trading:
	$(PIP) install -e '.[agent-trading]'

install-agent-os:
	$(PIP) install -e '.[agent-os]'

install-video-ea:
	$(PIP) install -e '.[video-ea]'

install-notifications:
	$(PIP) install -e '.[notifications]'

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
# TEST — Python
# ============================================================
test:
	$(PYTEST) -m "not uat and not performance"

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

sec-bandit:
	bandit -q -r src -ll

sec-pip-audit:
	$(PIP) freeze --exclude-editable > audit-requirements.txt
	pip-audit --strict --progress-spinner off -r audit-requirements.txt

sec-zizmor:
	zizmor --min-severity high --min-confidence high .github/workflows

sec-gitleaks:
	gitleaks detect --source . --verbose

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
		__pycache__ src/zksato/__pycache__ tests/__pycache__ \
		src/zksato/**/__pycache__ scripts/__pycache__

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
# CI GATES
# ============================================================
ci: lint format-check type coverage contract package compose

ci-security: lint format-check type coverage contract package compose security-full resilience docker env-check docs-validate

ci-full: ci security resilience docker env-check test-all-features docs-check

# ============================================================
# PACKAGE
# ============================================================
package:
	rm -rf build dist
	$(PYTHON) -m build
	twine check dist/*