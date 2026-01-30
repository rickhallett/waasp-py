# WAASP Makefile - Sandcastle Standard
.PHONY: all build install clean test lint fmt dev up down logs migrate help

# Configuration
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin
APP := waasp.app:create_app

# Colors for output
GREEN := \033[0;32m
NC := \033[0m # No Color

all: help

# ─────────────────────────────────────────────────────────────────────────────
# Development Setup
# ─────────────────────────────────────────────────────────────────────────────

$(VENV)/bin/activate:
	uv venv $(VENV)
	$(BIN)/pip install -e ".[dev]"

install: $(VENV)/bin/activate ## Install dependencies
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

dev: install ## Start development server (local, no Docker)
	$(BIN)/flask --app $(APP) run --debug --reload

# ─────────────────────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────────────────────

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d
	@echo "$(GREEN)✓ Services started. API at http://localhost:8000$(NC)"

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

shell: ## Open shell in web container
	docker compose exec web bash

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

migrate: ## Run database migrations
	docker compose exec web flask --app $(APP) db upgrade

migrate-new: ## Create new migration
	@read -p "Migration message: " msg; \
	docker compose exec web flask --app $(APP) db migrate -m "$$msg"

db-shell: ## Open database shell
	docker compose exec db psql -U waasp waasp

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

test: ## Run all tests
	$(BIN)/pytest tests/ -v --cov=waasp --cov-report=term-missing

test-unit: ## Run unit tests only
	$(BIN)/pytest tests/unit/ -v

test-integration: ## Run integration tests only
	$(BIN)/pytest tests/integration/ -v

test-docker: ## Run tests in Docker
	docker compose exec web pytest tests/ -v

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────

lint: ## Run linters
	$(BIN)/ruff check src/ tests/
	$(BIN)/mypy src/

fmt: ## Format code
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --fix src/ tests/

check: lint test ## Run all checks (lint + test)

# ─────────────────────────────────────────────────────────────────────────────
# Celery
# ─────────────────────────────────────────────────────────────────────────────

worker: ## Start Celery worker (local)
	$(BIN)/celery -A waasp.tasks worker --loglevel=info

beat: ## Start Celery beat (local)
	$(BIN)/celery -A waasp.tasks beat --loglevel=info

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

clean: ## Clean build artifacts
	rm -rf $(VENV) .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-docker: ## Clean Docker volumes
	docker compose down -v
	docker system prune -f

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

help: ## Show this help
	@echo "WAASP - Security whitelist for agentic AI"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
