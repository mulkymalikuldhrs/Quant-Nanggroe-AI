FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Application code
COPY quant_nanggroe/ ./quant_nanggroe/
COPY tests/ ./tests/

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "from quant_nanggroe.config import get_settings; get_settings()" || exit 1

# Default entry point
ENTRYPOINT ["python", "-m", "quant_nanggroe.cli"]
