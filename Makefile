.PHONY: install lint format format-check type test coverage contract package licenses security docker compose resilience ci

install:
	python -m pip install -e '.[dev,quality,security]'

lint:
	ruff check .
	yamllint .github .yamllint.yml docker-compose.yml
	hadolint Dockerfile

format:
	ruff format .

format-check:
	ruff format --check .

type:
	mypy src/zksato scripts

test:
	pytest -m "not uat and not performance"

coverage:
	pytest -m "not uat and not performance" --cov=zksato --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=65

contract:
	python scripts/openapi_contract.py --output openapi.json

package:
	rm -rf build dist
	python -m build
	twine check dist/*

licenses:
	pip-licenses --format=json --output-file=licenses.json

security:
	python -m pip freeze --exclude-editable > audit-requirements.txt
	pip-audit --strict --progress-spinner off -r audit-requirements.txt
	bandit -q -r src -ll
	zizmor --min-severity high --min-confidence high .github/workflows

docker:
	docker build --pull --tag zksato:local .
	docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges:true zksato:local python -c 'import zksato'

compose:
	docker compose config --quiet

resilience:
	pytest -q tests/test_risk_properties.py tests/test_reconciliation_gate.py tests/test_paper_recovery.py tests/test_audit_integrity.py tests/test_approvals.py tests/test_auth.py

ci: lint format-check type coverage contract package compose
