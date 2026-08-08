.PHONY: install lint format-check type test coverage package licenses security docker compose ci

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check .
	yamllint .github .yamllint.yml docker-compose.yml

format-check:
	ruff format --check .

type:
	mypy src/zksato scripts

test:
	pytest -m "not uat and not performance"

coverage:
	pytest -m "not uat and not performance" --cov=zksato --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=65

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
	zizmor .github/workflows

docker:
	docker build --pull --tag zksato:local .

compose:
	docker compose config --quiet

ci: lint format-check type coverage package compose
