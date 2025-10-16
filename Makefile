.PHONY: setup lint type test run app api demo clean help

help:
	@echo "PhantomScan Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  setup    - Install dependencies and pre-commit hooks"
	@echo "  lint     - Run ruff linter"
	@echo "  type     - Run mypy type checker"
	@echo "  test     - Run pytest with coverage"
	@echo "  run      - Execute radar run-all (fetch, score, feed)"
	@echo "  app      - Launch Streamlit web app"
	@echo "  api      - Launch FastAPI service"
	@echo "  demo     - Run pipeline in offline mode and launch app"
	@echo "  clean    - Remove cache and build artifacts"

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

demo:
	RADAR_OFFLINE=1 radar run-all
	streamlit run webapp/app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/ .coverage
