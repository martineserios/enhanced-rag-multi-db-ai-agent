# Makefile for Multi-DB RAG AI Agent
# This Makefile provides commands to manage the entire application infrastructure
# including development, testing, deployment, and maintenance tasks.

# Variables
DOCKER_COMPOSE = docker-compose -f docker-compose.yml
PYTHON = python3
VENV = venv
BACKEND_DIR = backend
FRONTEND_DIR = frontend

# Colors for better output readability
CYAN = \033[0;36m
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Help target
help:
	@echo "${CYAN}Available commands:${NC}"
	@echo "${GREEN}Development:${NC}"
	@echo "  make setup          - Set up development environment (create venv, install deps)"
	@echo "  make dev-backend    - Run backend in development mode"
	@echo "  make dev-frontend   - Run frontend in development mode"
	@echo "  make dev           - Run both frontend and backend in development mode"
	@echo "${GREEN}Docker Operations:${NC}"
	@echo "  make build         - Build all Docker images"
	@echo "  make build SERVICE - Build a specific service (e.g., make build frontend)"
	@echo "  make up            - Start all services in detached mode"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - Show logs for all services"
	@echo "  make logs SERVICE  - Show logs for a specific service"
	@echo "  make restart       - Restart all services"
	@echo "  make restart SERVICE - Restart a specific service (e.g., make restart backend)"
	@echo "  make ps            - List running containers"
	@echo "${GREEN}Database Management:${NC}"
	@echo "  make db-init       - Initialize all databases"
	@echo "  make db-backup     - Create backup of all databases"
	@echo "  make db-restore    - Restore databases from backup"
	@echo "${GREEN}Testing:${NC}"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo "  make lint          - Run linting checks"
	@echo "${GREEN}Maintenance:${NC}"
	@echo "  make clean         - Remove temporary files and caches"
	@echo "  make prune         - Remove unused Docker resources"
	@echo "  make shell-backend - Open shell in backend container"
	@echo "  make shell-frontend - Open shell in frontend container"

# Development environment setup
setup:
	@echo "${CYAN}Setting up development environment...${NC}"
	@echo "${YELLOW}Installing uv...${NC}"
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "${YELLOW}Creating virtual environment...${NC}"
	uv venv $(VENV)
	@echo "${YELLOW}Installing backend dependencies...${NC}"
	. $(VENV)/bin/activate && cd $(BACKEND_DIR) && \
		uv pip install -e ".[viz,dev,test]"
	@echo "${YELLOW}Installing frontend dependencies...${NC}"
	. $(VENV)/bin/activate && cd $(FRONTEND_DIR) && uv pip install -e .
	@echo "${GREEN}Setup complete!${NC}"

# Development servers
dev-backend:
	@echo "${CYAN}Starting backend development server...${NC}"
	. $(VENV)/bin/activate && cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "${CYAN}Starting frontend development server...${NC}"
	. $(VENV)/bin/activate && cd $(FRONTEND_DIR) && streamlit run app.py

dev: dev-backend dev-frontend

# Helper function to check service health
check-services:
	@echo "\n${CYAN}Checking service status...${NC}"
	@echo "${YELLOW}Checking container status...${NC}"
	@if ! $(DOCKER_COMPOSE) ps | grep -q "Up"; then \
		echo "${RED}Error: Some containers are not running properly${NC}"; \
		echo "${YELLOW}Container status:${NC}"; \
		$(DOCKER_COMPOSE) ps; \
		exit 1; \
	fi
	@echo "${GREEN}All containers are running${NC}"
	@echo "\n${YELLOW}Checking database services...${NC}"
	@for service in redis mongodb postgres neo4j chroma; do \
		if ! $(DOCKER_COMPOSE) ps | grep -q "$$service.*Up"; then \
			echo "${RED}Warning: $$service is not running properly${NC}"; \
		else \
			echo "${GREEN}✓ $$service is running${NC}"; \
		fi; \
	done
	@echo "\n${YELLOW}Checking application services...${NC}"
	@if ! curl -s -f http://localhost:8000/health > /dev/null; then \
		echo "${RED}Warning: Backend API is not responding yet${NC}"; \
		echo "${YELLOW}You may need to wait a bit longer for the backend to initialize${NC}"; \
	else \
		echo "${GREEN}✓ Backend API is responding${NC}"; \
	fi
	@if ! curl -s -f http://localhost:8501 > /dev/null; then \
		echo "${RED}Warning: Frontend is not responding yet${NC}"; \
		echo "${YELLOW}You may need to wait a bit longer for the frontend to initialize${NC}"; \
		echo "${YELLOW}If the frontend doesn't start, try:${NC}"; \
		echo "1. make down"; \
		echo "2. docker-compose rm -f frontend"; \
		echo "3. make up"; \
	else \
		echo "${GREEN}✓ Frontend is responding${NC}"; \
	fi
	@echo "\n${GREEN}Service URLs:${NC}"
	@echo "Frontend: http://localhost:8501"
	@echo "Backend API: http://localhost:8000"
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "\n${YELLOW}Database Ports:${NC}"
	@echo "  - Redis: 6379"
	@echo "  - MongoDB: 27017"
	@echo "  - PostgreSQL: 5432"
	@echo "  - Neo4j: 7474 (HTTP), 7687 (Bolt)"
	@echo "  - ChromaDB: 8000"
	@echo "\n${YELLOW}If you encounter any issues:${NC}"
	@echo "1. Check container logs: make logs"
	@echo "2. Restart specific service: docker-compose restart <service-name>"
	@echo "3. Full restart: make restart"

# Docker operations
build:
	@if [ "$(filter-out $@,$(MAKECMDGOALS))" != "" ]; then \
		SERVICE="$(filter-out $@,$(MAKECMDGOALS))"; \
		echo "${CYAN}Building $$SERVICE image...${NC}"; \
		$(DOCKER_COMPOSE) build --no-cache $$SERVICE; \
		echo "\n${GREEN}$$SERVICE build complete!${NC}"; \
		echo "${YELLOW}Next steps:${NC}"; \
		echo "1. Run 'make up' to start all services"; \
		echo "2. Or run 'docker-compose up -d $$SERVICE' to start just $$SERVICE"; \
		echo "3. Run 'make check-services' to verify service status"; \
	else \
		echo "${CYAN}Building all Docker images...${NC}"; \
		echo "${YELLOW}Cleaning up old images...${NC}"; \
		docker system prune -f; \
		echo "${YELLOW}Building images...${NC}"; \
		$(DOCKER_COMPOSE) build --no-cache; \
		echo "\n${GREEN}Build complete!${NC}"; \
		echo "${YELLOW}Next steps:${NC}"; \
		echo "1. Run 'make up' to start the services"; \
		echo "2. Run 'make check-services' to verify all services are running"; \
		echo "3. Access the application at http://localhost:8501"; \
	fi

restart:
	@if [ "$(filter-out $@,$(MAKECMDGOALS))" != "" ]; then \
		SERVICE="$(filter-out $@,$(MAKECMDGOALS))"; \
		echo "${CYAN}Restarting $$SERVICE service...${NC}"; \
		echo "${YELLOW}Stopping $$SERVICE...${NC}"; \
		$(DOCKER_COMPOSE) stop $$SERVICE; \
		$(DOCKER_COMPOSE) rm -f $$SERVICE; \
		echo "${YELLOW}Starting $$SERVICE again...${NC}"; \
		$(DOCKER_COMPOSE) up -d $$SERVICE; \
		echo "\n${GREEN}$$SERVICE restart initiated!${NC}"; \
		echo "${YELLOW}Waiting for $$SERVICE to initialize...${NC}"; \
		sleep 5; \
		if [ "$$SERVICE" = "frontend" ]; then \
			echo "${YELLOW}Checking frontend status...${NC}"; \
			curl -s -f http://localhost:8501/_stcore/health > /dev/null && \
			echo "${GREEN}Frontend is responding${NC}" || \
			echo "${RED}Frontend is not responding yet${NC}"; \
		elif [ "$$SERVICE" = "backend" ]; then \
			echo "${YELLOW}Checking backend status...${NC}"; \
			curl -s -f http://localhost:8000/health > /dev/null && \
			echo "${GREEN}Backend is responding${NC}" || \
			echo "${RED}Backend is not responding yet${NC}"; \
		fi; \
	else \
		echo "${CYAN}Restarting all services...${NC}"; \
		echo "${YELLOW}Stopping all services...${NC}"; \
		$(DOCKER_COMPOSE) down; \
		echo "${YELLOW}Removing any stale containers...${NC}"; \
		$(DOCKER_COMPOSE) rm -f; \
		echo "${YELLOW}Starting services again...${NC}"; \
		sleep 2; \
		if ! $(DOCKER_COMPOSE) up -d; then \
			echo "${RED}Error: Failed to restart services${NC}"; \
			echo "${YELLOW}Please check the logs: make logs${NC}"; \
			exit 1; \
		fi; \
		echo "\n${GREEN}Services restart initiated!${NC}"; \
		echo "${YELLOW}Waiting for services to initialize...${NC}"; \
		sleep 15; \
		$(MAKE) check-services; \
	fi

# This allows passing arguments to the build and restart targets
%:
	@:

# Update logs target to support individual services
logs:
	@if [ "$(filter-out $@,$(MAKECMDGOALS))" != "" ]; then \
		SERVICE="$(filter-out $@,$(MAKECMDGOALS))"; \
		echo "${CYAN}Showing logs for $$SERVICE service (press Ctrl+C to exit)...${NC}"; \
		$(DOCKER_COMPOSE) logs -f $$SERVICE; \
	else \
		echo "${CYAN}Showing logs for all services (press Ctrl+C to exit)...${NC}"; \
		$(DOCKER_COMPOSE) logs -f; \
	fi

up:
	@echo "${CYAN}Starting all services in detached mode...${NC}"
	@echo "${YELLOW}Note: This may take a few minutes on first run${NC}"
	@if ! $(DOCKER_COMPOSE) up -d; then \
		echo "${RED}Error: Failed to start services${NC}"; \
		echo "${YELLOW}Trying to clean up and restart...${NC}"; \
		$(DOCKER_COMPOSE) down; \
		sleep 2; \
		if ! $(DOCKER_COMPOSE) up -d; then \
			echo "${RED}Error: Still unable to start services${NC}"; \
			echo "${YELLOW}Please check the logs: make logs${NC}"; \
			exit 1; \
		fi; \
	fi
	@echo "\n${GREEN}Initial container startup complete!${NC}"
	@echo "${YELLOW}Waiting for services to initialize (this may take a while)...${NC}"
	@sleep 15
	@echo "${YELLOW}Checking service status...${NC}"
	@$(MAKE) check-services

down:
	@echo "${CYAN}Stopping all services...${NC}"
	$(DOCKER_COMPOSE) down
	@echo "\n${GREEN}All services stopped successfully!${NC}"
	@echo "${YELLOW}Note:${NC} All data in ephemeral volumes has been removed"
	@echo "Run 'make up' to start the services again"

ps:
	@echo "${CYAN}Listing running containers...${NC}"
	$(DOCKER_COMPOSE) ps

# Database management
db-init:
	@echo "${CYAN}Initializing all databases...${NC}"
	@echo "${YELLOW}This will reset all databases to their initial state!${NC}"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	$(DOCKER_COMPOSE) exec backend python scripts/init_db.py
	@echo "\n${GREEN}Database initialization complete!${NC}"
	@echo "${YELLOW}Database Status:${NC}"
	@echo "- MongoDB: Ready for episodic memory storage"
	@echo "- Redis: Ready for short-term memory"
	@echo "- ChromaDB: Ready for semantic memory/vector storage"
	@echo "- Neo4j: Ready for procedural memory"
	@echo "- PostgreSQL: Ready for relational data"

db-backup:
	@echo "${CYAN}Creating database backups...${NC}"
	@mkdir -p backups
	@echo "${YELLOW}Backing up MongoDB...${NC}"
	$(DOCKER_COMPOSE) exec -T mongodb mongodump --archive > backups/mongodb_backup.archive
	@echo "${YELLOW}Backing up PostgreSQL...${NC}"
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U postgres > backups/postgres_backup.sql
	@echo "${YELLOW}Backing up Neo4j...${NC}"
	$(DOCKER_COMPOSE) exec -T neo4j neo4j-admin database dump neo4j > backups/neo4j_backup.dump
	@echo "\n${GREEN}Backups created successfully!${NC}"
	@echo "${YELLOW}Backup files:${NC}"
	@ls -lh backups/
	@echo "\n${YELLOW}Note:${NC} Store these backups in a safe location"

db-restore:
	@echo "${CYAN}Restoring databases from backups...${NC}"
	@if [ ! -d "backups" ]; then \
		echo "${RED}No backups directory found!${NC}"; \
		exit 1; \
	fi
	@echo "${YELLOW}This will overwrite all current database data!${NC}"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@echo "${YELLOW}Restoring MongoDB...${NC}"
	$(DOCKER_COMPOSE) exec -T mongodb mongorestore --archive < backups/mongodb_backup.archive
	@echo "${YELLOW}Restoring PostgreSQL...${NC}"
	$(DOCKER_COMPOSE) exec -T postgres psql -U postgres < backups/postgres_backup.sql
	@echo "${YELLOW}Restoring Neo4j...${NC}"
	$(DOCKER_COMPOSE) exec -T neo4j neo4j-admin database load neo4j from backups/neo4j_backup.dump
	@echo "\n${GREEN}Database restoration complete!${NC}"
	@echo "${YELLOW}Verifying database status...${NC}"
	@$(MAKE) check-services

# Testing
test:
	@echo "${CYAN}Running all tests...${NC}"
	@echo "${YELLOW}Running backend tests...${NC}"
	$(DOCKER_COMPOSE) exec backend pytest
	@echo "\n${YELLOW}Running frontend tests...${NC}"
	$(DOCKER_COMPOSE) exec frontend pytest
	@echo "\n${GREEN}All tests completed!${NC}"
	@echo "${YELLOW}Test coverage reports:${NC}"
	@echo "- Backend: Check backend/coverage/index.html"
	@echo "- Frontend: Check frontend/coverage/index.html"

test-backend:
	@echo "${CYAN}Running backend tests...${NC}"
	$(DOCKER_COMPOSE) exec backend pytest

test-frontend:
	@echo "${CYAN}Running frontend tests...${NC}"
	$(DOCKER_COMPOSE) exec frontend pytest

lint:
	@echo "${CYAN}Running linting checks...${NC}"
	@echo "${YELLOW}Checking backend code...${NC}"
	$(DOCKER_COMPOSE) exec backend flake8 app tests
	$(DOCKER_COMPOSE) exec backend black --check app tests
	@echo "\n${YELLOW}Checking frontend code...${NC}"
	$(DOCKER_COMPOSE) exec frontend flake8 .
	$(DOCKER_COMPOSE) exec frontend black --check .
	@echo "\n${GREEN}Linting complete!${NC}"
	@echo "${YELLOW}Code style status:${NC}"
	@echo "- Backend: PEP 8 and Black formatting verified"
	@echo "- Frontend: PEP 8 and Black formatting verified"

# Maintenance
clean:
	@echo "${CYAN}Cleaning temporary files and caches...${NC}"
	@echo "${YELLOW}Removing Python cache files...${NC}"
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -delete
	find . -type f -name "*.pyc" -delete
	@echo "${YELLOW}Cleaning Docker build cache...${NC}"
	docker builder prune -f
	@echo "\n${GREEN}Clean complete!${NC}"
	@echo "${YELLOW}Cleaned items:${NC}"
	@echo "- Python cache files"
	@echo "- Test cache"
	@echo "- Coverage reports"
	@echo "- Docker build cache"

prune:
	@echo "${CYAN}Pruning unused Docker resources...${NC}"
	@echo "${YELLOW}This will remove:${NC}"
	@echo "- All stopped containers"
	@echo "- All unused networks"
	@echo "- All dangling images"
	@echo "- All build cache"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	docker system prune -f
	@echo "\n${GREEN}Docker system pruned successfully!${NC}"
	@echo "${YELLOW}Current Docker status:${NC}"
	docker system df

shell-backend:
	@echo "${CYAN}Opening a shell in the backend container...${NC}"
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-frontend:
	@echo "${CYAN}Opening a shell in the frontend container...${NC}"
	$(DOCKER_COMPOSE) exec frontend /bin/bash

# New development commands
dev-shell:
	@echo "${CYAN}Opening development shell in backend container...${NC}"
	$(DOCKER_COMPOSE) exec backend /bin/bash

dev-logs:
	@echo "${CYAN}Showing development logs (press Ctrl+C to exit)...${NC}"
	$(DOCKER_COMPOSE) logs -f backend frontend

dev-test:
	@echo "${CYAN}Running tests in development mode...${NC}"
	$(DOCKER_COMPOSE) exec backend pytest -v --cov=app --cov-report=term-missing

dev-lint:
	@echo "${CYAN}Running linting in development mode...${NC}"
	$(DOCKER_COMPOSE) exec backend black --check app tests && \
	$(DOCKER_COMPOSE) exec backend flake8 app tests && \
	$(DOCKER_COMPOSE) exec backend mypy app

dev-clean:
	@echo "${CYAN}Cleaning development environment...${NC}"
	@echo "${YELLOW}Removing Python cache files...${NC}"
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -delete
	find . -type f -name "*.pyc" -delete
	@echo "${YELLOW}Cleaning uv cache...${NC}"
	uv cache clean
	@echo "${YELLOW}Cleaning Docker environment...${NC}"
	docker system prune -f
	@echo "${YELLOW}Removing virtual environment...${NC}"
	rm -rf $(VENV)
	@echo "\n${GREEN}Clean complete!${NC}"
	@echo "${YELLOW}Run 'make setup' to recreate the development environment${NC}"

.PHONY: help setup dev-backend dev-frontend dev build up down logs restart ps \
        db-init db-backup db-restore test test-backend test-frontend lint \
        clean prune shell-backend shell-frontend check-services \
        dev-shell dev-logs dev-test dev-lint dev-clean