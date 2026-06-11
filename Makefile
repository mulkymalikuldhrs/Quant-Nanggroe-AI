.PHONY: install dev test lint format typecheck build docker clean

PYTHON ?= python3
PIP ?= pip3

install:
	$(PIP) install -e ".[dev]"

dev: install
	$(PIP) install -e ".[dev]"
	@echo "Development environment ready."

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ --cov=quant_nanggroe --cov-report=term-missing --cov-report=html

test-engine:
	pytest tests/test_engine/ -v

test-agents:
	pytest tests/test_agents/ -v

test-data:
	pytest tests/test_data/ -v

lint:
	ruff check quant_nanggroe/ tests/

format:
	ruff format quant_nanggroe/ tests/

format-check:
	ruff format --check quant_nanggroe/ tests/

typecheck:
	mypy quant_nanggroe/ --ignore-missing-imports --no-strict-optional

build:
	$(PIP) install build
	$(PYTHON) -m build

docker:
	docker build -f docker/Dockerfile -t quant-nanggroe-ai:latest .

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

all: lint typecheck test

help:
	@echo "Quant Nanggroe AI - Makefile Commands"
	@echo "====================================="
	@echo "install      - Install package in development mode"
	@echo "dev          - Set up development environment"
	@echo "test         - Run all tests"
	@echo "test-cov     - Run tests with coverage report"
	@echo "test-engine  - Run engine tests only"
	@echo "test-agents  - Run agent tests only"
	@echo "lint         - Run ruff linter"
	@echo "format       - Format code with ruff"
	@echo "typecheck    - Run mypy type checking"
	@echo "build        - Build distribution package"
	@echo "docker       - Build Docker image"
	@echo "docker-up    - Start Docker Compose services"
	@echo "docker-down  - Stop Docker Compose services"
	@echo "clean        - Remove build artifacts"
	@echo "all          - Run lint + typecheck + test"
