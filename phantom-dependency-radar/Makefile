.PHONY: setup lint type test run app api demo clean help

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup:  ## Install project + dev deps + pre-commit hooks
	pip install -e ".[dev]"
	pre-commit install

lint:  ## Run linting (ruff + black check)
	ruff check .
	black --check .

type:  ## Run type checking (mypy)
	mypy radar webapp api

test:  ## Run tests with coverage
	pytest --cov=radar --cov=webapp --cov=api --cov-report=term-missing

run:  ## Run the complete radar pipeline (fetch->score->feed)
	radar run-all

app:  ## Launch Streamlit app
	streamlit run webapp/app.py

api:  ## Launch FastAPI service
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

demo:  ## Run pipeline and open app to today's feed
	radar run-all
	@echo "Opening Streamlit app..."
	streamlit run webapp/app.py

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	rm -rf build dist *.egg-info

format:  ## Format code (black + ruff --fix)
	ruff check --fix .
	black .

docker-build:  ## Build Docker images
	docker build -t phantom-radar-app -f Dockerfile.app .
	docker build -t phantom-radar-worker -f Dockerfile.worker .

docker-up:  ## Start docker-compose stack
	docker-compose up -d

docker-down:  ## Stop docker-compose stack
	docker-compose down