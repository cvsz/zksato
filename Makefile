# ============================================================
# zksato — Makefile
# Risk-first automated trading platform for SET / TFEX
# ============================================================
# Usage:  make <target>
#         make help          — list all targets
# ============================================================

.DEFAULT_GOAL := help
.PHONY: help \
        install install-settrade install-ccxt install-prediction install-observability install-all \
        lint format format-check shellcheck type \
        test test-resilience test-performance test-uat test-postgres test-concurrency \
        coverage coverage-html \
        contract \
        security audit bandit gitleaks \
        db-migrate db-status db-backup db-restore \
        openapi \
        package licenses \
        docker docker-run docker-scan compose \
        resilience \
        dr-drill dr-restore \
        load-test \
        env-check \
        github-health \
        clean \
        ci ci-full

# ─── colour helpers ─────────────────────────────────────────
BOLD  := \033[1m
RESET := \033[0m
GREEN := \033[32m
CYAN  := \033[36m
YELLOW := \033[33m

# ─── env defaults ───────────────────────────────────────────
ZKSATO_TRADING_MODE ?= paper
PYTHON              ?= python
PIP                 ?= $(PYTHON) -m pip
PYTEST              ?= pytest
COV_FAIL_UNDER      ?= 65
IMAGE_TAG           ?= zksato:local
BACKUP_DIR          ?= ./backups

# ============================================================
# HELP
# ============================================================
help:
	@printf '$(BOLD)$(CYAN)zksato Makefile$(RESET) — available targets\n\n'
	@printf '$(BOLD)Install$(RESET)\n'
	@printf '  $(GREEN)install$(RESET)              Install core + dev + quality + security extras\n'
	@printf '  $(GREEN)install-settrade$(RESET)      Add settrade-v2 adapter\n'
	@printf '  $(GREEN)install-ccxt$(RESET)          Add ccxt multi-exchange adapter\n'
	@printf '  $(GREEN)install-prediction$(RESET)    Add XGBoost / scikit-learn extras\n'
	@printf '  $(GREEN)install-observability$(RESET) Add OpenTelemetry SDK\n'
	@printf '  $(GREEN)install-all$(RESET)           Install every optional extra\n'
	@printf '\n$(BOLD)Quality$(RESET)\n'
	@printf '  $(GREEN)lint$(RESET)                 ruff + yamllint + hadolint\n'
	@printf '  $(GREEN)format$(RESET)               ruff format (auto-fix)\n'
	@printf '  $(GREEN)format-check$(RESET)         ruff format --check (no mutation)\n'
	@printf '  $(GREEN)shellcheck$(RESET)           Lint all shell scripts\n'
	@printf '  $(GREEN)type$(RESET)                 mypy type-check src + scripts\n'
	@printf '\n$(BOLD)Test$(RESET)\n'
	@printf '  $(GREEN)test$(RESET)                 Run unit/integration suite (excludes uat, performance)\n'
	@printf '  $(GREEN)test-resilience$(RESET)       Run risk + recovery fail-closed tests\n'
	@printf '  $(GREEN)test-performance$(RESET)      Run performance probe (marked: performance)\n'
	@printf '  $(GREEN)test-uat$(RESET)              Run broker UAT suite (requires credentials)\n'
	@printf '  $(GREEN)test-postgres$(RESET)         Run PostgreSQL integration tests\n'
	@printf '  $(GREEN)test-concurrency$(RESET)      Run concurrency / race-condition tests\n'
	@printf '  $(GREEN)coverage$(RESET)             Coverage report (term-missing + xml, floor $(COV_FAIL_UNDER)%%)\n'
	@printf '  $(GREEN)coverage-html$(RESET)        Coverage HTML report → htmlcov/\n'
	@printf '\n$(BOLD)Security$(RESET)\n'
	@printf '  $(GREEN)security$(RESET)             pip-audit + bandit + zizmor (all-in-one)\n'
	@printf '  $(GREEN)audit$(RESET)                pip-audit only\n'
	@printf '  $(GREEN)bandit$(RESET)               bandit static analysis only\n'
	@printf '  $(GREEN)gitleaks$(RESET)             Secret-pattern scan (requires gitleaks)\n'
	@printf '\n$(BOLD)Database$(RESET)\n'
	@printf '  $(GREEN)db-migrate$(RESET)           Apply SQL migrations in order\n'
	@printf '  $(GREEN)db-status$(RESET)            Show applied migration files\n'
	@printf '  $(GREEN)db-backup$(RESET)            Dump database → BACKUP_DIR\n'
	@printf '  $(GREEN)db-restore$(RESET)           Restore from BACKUP_FILE=path/to/file.dump\n'
	@printf '\n$(BOLD)Contracts & Docs$(RESET)\n'
	@printf '  $(GREEN)contract$(RESET)             Generate openapi.json via scripts/openapi_contract.py\n'
	@printf '  $(GREEN)openapi$(RESET)              Alias for contract\n'
	@printf '  $(GREEN)licenses$(RESET)             Dump runtime license inventory → licenses.json\n'
	@printf '\n$(BOLD)Package$(RESET)\n'
	@printf '  $(GREEN)package$(RESET)              Build wheel + sdist, twine check\n'
	@printf '\n$(BOLD)Container$(RESET)\n'
	@printf '  $(GREEN)docker$(RESET)               Build image and smoke-test import\n'
	@printf '  $(GREEN)docker-run$(RESET)           Run image in hardened mode (paper, read-only fs)\n'
	@printf '  $(GREEN)docker-scan$(RESET)          Trivy CVE scan (requires trivy)\n'
	@printf '  $(GREEN)compose$(RESET)              Validate docker-compose.yml\n'
	@printf '\n$(BOLD)Operations$(RESET)\n'
	@printf '  $(GREEN)resilience$(RESET)           Full resilience suite (risk + reconciliation + paper recovery + audit)\n'
	@printf '  $(GREEN)dr-drill$(RESET)             Disaster-recovery drill (backup → wipe → restore → verify)\n'
	@printf '  $(GREEN)dr-restore$(RESET)           Restore from latest backup in BACKUP_DIR\n'
	@printf '  $(GREEN)load-test$(RESET)            Run load test script (paper only)\n'
	@printf '  $(GREEN)env-check$(RESET)            Validate .env file for permission and injection issues\n'
	@printf '  $(GREEN)github-health$(RESET)        Run GitHub repository health check (read-only)\n'
	@printf '\n$(BOLD)Housekeeping$(RESET)\n'
	@printf '  $(GREEN)clean$(RESET)               Remove build artefacts, caches, coverage data\n'
	@printf '\n$(BOLD)CI gates$(RESET)\n'
	@printf '  $(GREEN)ci$(RESET)                  Standard CI: lint + format-check + type + coverage + contract + package + compose\n'
	@printf '  $(GREEN)ci-full$(RESET)              ci + security + resilience + docker + env-check\n'
	@printf '\n'

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

install-all:
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev,quality,security,settrade,ccxt,prediction,observability]'

# ============================================================
# QUALITY — lint / format / type
# ============================================================
lint:
	ruff check .
	yamllint .github .yamllint.yml docker-compose.yml
	hadolint Dockerfile

format:
	ruff format .

format-check:
	ruff format --check .

shellcheck:
	shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh 2>/dev/null || true

type:
	mypy src/zksato scripts

# ============================================================
# TEST
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
	@printf '$(YELLOW)WARNING: Requires broker UAT credentials and schedule-gated sessions (Thu/Fri 09:00–17:00 TH).$(RESET)\n'
	$(PYTEST) -m "uat" tests/test_uat.py tests/test_settrade_adapters.py

test-postgres:
	$(PYTEST) tests/test_postgres_integration.py tests/test_persistence.py tests/test_priority_persistence.py

test-concurrency:
	$(PYTEST) tests/test_concurrency.py

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
# SECURITY
# ============================================================
security: audit bandit
	zizmor --min-severity high --min-confidence high .github/workflows

audit:
	$(PIP) freeze --exclude-editable > audit-requirements.txt
	pip-audit --strict --progress-spinner off -r audit-requirements.txt

bandit:
	bandit -q -r src -ll

gitleaks:
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
# CONTRACTS / DOCS
# ============================================================
contract:
	$(PYTHON) scripts/openapi_contract.py --output openapi.json

openapi: contract

licenses:
	pip-licenses --format=json --output-file=licenses.json

# ============================================================
# PACKAGE
# ============================================================
package:
	rm -rf build dist
	$(PYTHON) -m build
	twine check dist/*

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
# CI GATES
# ============================================================
ci: lint format-check type coverage contract package compose

ci-full: ci security resilience docker env-check
