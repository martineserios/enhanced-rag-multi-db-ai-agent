# GlabitAI Agent - Development Makefile
# Medical AI Agent for Obesity Treatment

.PHONY: help install dev test lint format clean run health

# Default target
help: ## Show this help message
	@echo "GlabitAI Agent - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install with dev dependencies
	uv sync --dev

run: ## Start the FastAPI server
	uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-prod: ## Start server in production mode
	uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

test: ## Run all tests
	uv run pytest

test-cov: ## Run tests with coverage report
	uv run pytest --cov=app --cov-report=html --cov-report=xml --cov-fail-under=90

test-quick: ## Run tests without coverage
	uv run pytest -x --tb=short

lint: ## Run code linting
	uv run ruff check .

format: ## Format code
	uv run ruff format .

lint-fix: ## Fix linting issues automatically
	uv run ruff check --fix .

health: ## Check API health
	@echo "Checking API health..."
	@curl -s http://127.0.0.1:8000/api/v1/chat/health | jq '.' || echo "Server not running or jq not installed"

clean: ## Clean cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage

setup: ## Initial project setup
	uv venv
	make dev
	@echo "Setup complete! Run 'make run' to start the server"

# Medical testing commands
test-medical: ## Run medical-specific tests
	uv run pytest -m medical

test-api: ## Test API endpoints
	uv run pytest tests/test_api_chat.py -v

test-llm: ## Test LLM providers
	uv run pytest tests/test_llm_factory.py tests/test_llm_providers.py -v

# Development helpers
logs: ## View recent logs
	tail -f server.log 2>/dev/null || echo "No server.log file found"

deps: ## Show dependency tree
	uv tree

info: ## Show project info
	@echo "Project: GlabitAI Medical Agent"
	@echo "Python version: $$(uv run python --version)"
	@echo "Package count: $$(uv tree | wc -l)"
	@echo "Test coverage: Run 'make test-cov' to see coverage"