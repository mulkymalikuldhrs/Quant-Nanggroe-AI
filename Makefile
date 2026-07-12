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

test-cov: ## Run tests with coverage
	$(POETRY) run pytest tests/ -v --tb=short --cov=quant_nanggroe --cov-report=term-missing --cov-report=html

test-quick: ## Quick tests (skip slow integration)
	$(POETRY) run pytest tests/ -v --tb=short -m "not slow" -q

test-api: ## API tests only
	$(POETRY) run pytest tests/test_api/ -v --tb=short

test-risk: ## Risk engine tests
	$(POETRY) run pytest tests/test_engine/test_risk.py tests/test_risk/ -v --tb=short

test-regression: ## Full regression
	$(POETRY) run pytest tests/ --tb=long -x --timeout=600

# ── Lint ──────────────────────────────────────────────────────────────
lint: ## Run lint checks (ruff)
	$(POETRY) run ruff check quant_nanggroe/ tests/

lint-fix: ## Auto-fix lint issues
	$(POETRY) run ruff check --fix quant_nanggroe/ tests/

format: ## Format with ruff
	$(POETRY) run ruff format quant_nanggroe/ tests/

typecheck: ## Static type checking
	$(POETRY) run mypy quant_nanggroe/ --ignore-missing-imports

# ── Security ──────────────────────────────────────────────────────────
security: ## Security audit
	$(POETRY) run bandit -r quant_nanggroe/ -c pyproject.toml
	$(POETRY) run safety check

# ── Build ─────────────────────────────────────────────────────────────
build: ## Build package
	$(POETRY) build

build-docs: ## Build documentation
	$(POETRY) run mkdocs build --clean

# ── Run ───────────────────────────────────────────────────────────────
run: ## Run the API server (dev)
	$(POETRY) run uvicorn quant_nanggroe.api.app:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run the API server (production)
	$(POETRY) run uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port 8000 --workers 4

run-dashboard: ## Run the dashboard (Next.js)
	cd dashboard && npm run dev

# ── Docker ────────────────────────────────────────────────────────────
docker-up: ## Start all containers
	$(DOCKER_COMPOSE) up -d --build

docker-down: ## Stop all containers
	$(DOCKER_COMPOSE) down

docker-logs: ## Tail logs
	$(DOCKER_COMPOSE) logs -f

docker-build: ## Build without running
	$(DOCKER_COMPOSE) build

# ── Database ──────────────────────────────────────────────────────────
db-upgrade: ## Run Alembic migrations
	$(POETRY) run alembic upgrade head

db-downgrade: ## Rollback last migration
	$(POETRY) run alembic downgrade -1

db-migrate: ## Auto-generate migration
	$(POETRY) run alembic autogenerate -m "$(message)"

# ── Git ───────────────────────────────────────────────────────────────
precommit: ## Run all pre-commit hooks
	$(POETRY) run pre-commit run --all-files

# ── Clean ─────────────────────────────────────────────────────────────
clean: ## Clean caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage

# ── CI ────────────────────────────────────────────────────────────────
ci: lint test-cov build ## Full CI pipeline
