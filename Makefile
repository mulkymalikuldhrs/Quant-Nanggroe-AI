PYTHON ?= python3

.PHONY: test lint clean

test:
	$(PYTHON) -m pytest \
		--ignore=tests/test_agents/test_geopolitics.py \
		--ignore=tests/test_nvidia_nim \
		-q --tb=short

lint:
	$(PYTHON) -m ruff check .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
