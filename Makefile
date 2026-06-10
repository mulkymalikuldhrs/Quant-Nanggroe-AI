# ╔══════════════════════════════════════════════════════════════════════╗
# ║              Quant-Nanggroe-AI  —  Makefile                         ║
# ║     Agentic Trading Intelligence OS  ·  Build · Test · Run          ║
# ╚══════════════════════════════════════════════════════════════════════╝

.PHONY: help install dev test lint format typecheck build run clean docker-up docker-down

# ── Defaults ──────────────────────────────────────────────────────────
PYTHON      ?= python3
POETRY      ?= poetry
DOCKER      ?= docker
DOCKER_COMPOSE ?= docker compose

# ── Help ──────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Install ───────────────────────────────────────────────────────────
install: ## Install production dependencies
	$(POETRY) install --only main

dev: ## Install all dependencies (including dev)
	$(POETRY) install --with dev
	$(POETRY) run pre-commit install

# ── Test ──────────────────────────────────────────────────────────────
test: ## Run all tests
	$(POETRY) run pytest tests/ -v --tb=short

test-engine: ## Run engine tests only
	$(POETRY) run pytest tests/test_engine/ -v -m engine

test-agents: ## Run agent tests only
	$(POETRY) run pytest tests/test_agents/ -v -m agents

test-cov: ## Run tests with coverage
	$(POETRY) run pytest tests/ --cov=quant_nanggroe_ai --cov-report=term-missing --cov-report=html

test-slow: ## Run slow tests
	$(POETRY) run pytest tests/ -v -m slow

# ── Code Quality ──────────────────────────────────────────────────────
lint: ## Run linter (ruff)
	$(POETRY) run ruff check src/ tests/

format: ## Auto-format code
	$(POETRY) run ruff format src/ tests/
	$(POETRY) run ruff check --fix src/ tests/

typecheck: ## Run mypy type checking
	$(POETRY) run mypy src/quant_nanggroe_ai/

security: ## Run bandit security scan
	$(POETRY) run bandit -r src/quant_nanggroe_ai/ -ll

check: lint typecheck test ## Run all checks (lint + typecheck + test)

# ── Database ──────────────────────────────────────────────────────────
db-push: ## Push schema to database
	$(POETRY) run alembic -c alembic.ini upgrade head

db-migrate: ## Create a new migration
	$(POETRY) run alembic -c alembic.ini revision --autogenerate -m "$(msg)"

db-rollback: ## Rollback last migration
	$(POETRY) run alembic -c alembic.ini downgrade -1

# ── Run ───────────────────────────────────────────────────────────────
run: ## Start the API server
	$(POETRY) run uvicorn quant_nanggroe_ai.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

run-worker: ## Start the background worker
	$(POETRY) run python -m quant_nanggroe_ai.worker

# ── Docker ────────────────────────────────────────────────────────────
docker-build: ## Build Docker images
	$(DOCKER_COMPOSE) build

docker-up: ## Start all services
	$(DOCKER_COMPOSE) up -d

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down

docker-logs: ## Follow logs
	$(DOCKER_COMPOSE) logs -f api

docker-dev: ## Start dev stack (with hot reload)
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

# ── Clean ─────────────────────────────────────────────────────────────
clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage .mypy_cache dist *.egg-info

# ── CI (simulated locally) ───────────────────────────────────────────
ci: format lint typecheck security test ## Full CI pipeline locally
