# GlabitAI Agent - Development Makefile
# Medical AI Agent for Obesity Treatment

.PHONY: help install dev test lint format clean run health backend frontend

# Default target
help: ## Show this help message
	@echo "GlabitAI Agent - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Backend commands (default: operate in backend)
BACKEND_DIR=backend

install: ## Install backend dependencies
	cd $(BACKEND_DIR) && uv sync

dev: ## Install backend with dev dependencies
	cd $(BACKEND_DIR) && uv sync --dev

run: ## Start the FastAPI backend server
	cd $(BACKEND_DIR) && uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-prod: ## Start backend server in production mode
	cd $(BACKEND_DIR) && uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

test: ## Run all backend tests
	cd $(BACKEND_DIR) && uv run pytest

test-cov: ## Run backend tests with coverage report
	cd $(BACKEND_DIR) && uv run pytest --cov=app --cov-report=html --cov-report=xml --cov-fail-under=90

test-quick: ## Run backend tests without coverage
	cd $(BACKEND_DIR) && uv run pytest -x --tb=short

lint: ## Run backend code linting
	cd $(BACKEND_DIR) && uv run ruff check .

format: ## Format backend code
	cd $(BACKEND_DIR) && uv run ruff format .

lint-fix: ## Fix backend linting issues automatically
	cd $(BACKEND_DIR) && uv run ruff check --fix .

health: ## Check backend API health
	@echo "Checking API health..."
	@curl -s http://127.0.0.1:8000/api/v1/chat/health | jq '.' || echo "Server not running or jq not installed"

clean: ## Clean backend cache files
	cd $(BACKEND_DIR) && find . -type d -name __pycache__ -exec rm -rf {} +
	cd $(BACKEND_DIR) && find . -type f -name "*.pyc" -delete
	cd $(BACKEND_DIR) && rm -rf .pytest_cache .ruff_cache htmlcov .coverage

setup: ## Initial backend project setup
	cd $(BACKEND_DIR) && uv venv
	make dev
	@echo "Setup complete! Run 'make run' to start the backend server"

# Medical testing commands

test-medical: ## Run medical-specific backend tests
	cd $(BACKEND_DIR) && uv run pytest -m medical

test-api: ## Test backend API endpoints
	cd $(BACKEND_DIR) && uv run pytest tests/test_api_chat.py -v

test-llm: ## Test backend LLM providers
	cd $(BACKEND_DIR) && uv run pytest tests/test_llm_factory.py tests/test_llm_providers.py -v

# Development helpers
logs: ## View recent backend logs
	cd $(BACKEND_DIR) && tail -f server.log 2>/dev/null || echo "No server.log file found"

deps: ## Show backend dependency tree
	cd $(BACKEND_DIR) && uv tree

info: ## Show backend project info
	@echo "Project: GlabitAI Medical Agent (Backend)"
	@cd $(BACKEND_DIR) && echo "Python version: $$(uv run python --version)"
	@cd $(BACKEND_DIR) && echo "Package count: $$(uv tree | wc -l)"
	@cd $(BACKEND_DIR) && echo "Test coverage: Run 'make test-cov' to see coverage"

# Frontend placeholder (to be implemented)
frontend: ## Placeholder for frontend commands
	@echo "Frontend commands will be added here in the future."
