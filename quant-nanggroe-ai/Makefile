# ===================== BUILD =====================
install:
	poetry install

install-no-dev:
	poetry install --without dev

# ===================== LINT & FORMAT =====================
lint:
	poetry run ruff check quant_nanggroe tests

format:
	poetry run ruff format quant_nanggroe tests

format-check:
	poetry run ruff format --check quant_nanggroe tests

typecheck:
	poetry run mypy quant_nanggroe

# ===================== TEST =====================
test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ -v --cov=quant_nanggroe --cov-report=term-missing --cov-report=html

test-types:
	poetry run pytest tests/test_types/ -v

test-data:
	poetry run pytest tests/test_data/ -v

test-engine:
	poetry run pytest tests/test_engine/ -v

# ===================== DOCKER =====================
docker-build:
	docker build -t quant-nanggroe-ai:latest -f docker/Dockerfile .

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

# ===================== ALL =====================
check: lint format-check typecheck test
	@echo "All checks passed!"

.PHONY: install lint format format-check typecheck test test-cov test-types test-data test-engine docker-build docker-up docker-down check
