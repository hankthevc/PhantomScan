.PHONY: setup lint type test run app api demo demo-npm demo-api demo-ui demo-clean clean help

# ==== Demo orchestration =================================================
PY ?= python3
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
API_BASE ?= http://$(API_HOST):$(API_PORT)

help:
	@echo "PhantomScan Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Install dependencies and pre-commit hooks"
	@echo "  lint        - Run ruff linter"
	@echo "  type        - Run mypy type checker"
	@echo "  test        - Run pytest with coverage"
	@echo "  run         - Execute radar run-all (fetch, score, feed)"
	@echo "  app         - Launch Streamlit web app"
	@echo "  api         - Launch FastAPI service"
	@echo "  demo        - Run PyPI demo casefile (requires API running)"
	@echo "  demo-npm    - Run npm demo casefile (requires API running)"
	@echo "  demo-api    - Launch FastAPI for demo use"
	@echo "  demo-ui     - Launch Streamlit for demo use"
	@echo "  demo-clean  - Remove demo output files"
	@echo "  clean       - Remove cache and build artifacts"

setup:
	pip install -e .[dev]
	pre-commit install

lint:
	ruff check radar/ webapp/ api/ tests/
	black --check radar/ webapp/ api/ tests/

type:
	mypy radar/ webapp/ api/

test:
	pytest

run:
	radar run-all

app:
	streamlit run webapp/app.py

api:
	uvicorn api.main:app --reload --port 8000

# Demo targets for recruiter/stakeholder presentations
demo:
	$(PY) scripts/demo_runner.py examples/casefiles/pypi_basics.json --api-base $(API_BASE)

demo-npm:
	$(PY) scripts/demo_runner.py examples/casefiles/npm_basics.json --api-base $(API_BASE)

demo-api:
	uvicorn api.main:app --host $(API_HOST) --port $(API_PORT)

demo-ui:
	streamlit run webapp/app.py

demo-clean:
	rm -rf dist/demo

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/ .coverage
