# ╔══════════════════════════════════════════════════════════════════════╗
# ║        Quant-Nanggroe-AI  —  Multi-stage Production Dockerfile      ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── Stage 1: Builder ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml ./

# Install dependencies (no dev, no root project)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi || \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings \
    sqlalchemy alembic asyncpg redis numpy pandas scipy scikit-learn \
    langgraph langchain-core httpx orjson rich click structlog tenacity psutil

# ── Stage 2: Production ──────────────────────────────────────────────
FROM python:3.12-slim AS production

# Metadata
LABEL maintainer="Quant-Nanggroe-AI Team"
LABEL description="Agentic Trading Intelligence OS"
LABEL version="1.0.0"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r qna \
    && useradd -r -g qna -d /app -s /sbin/nologin qna

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=qna:qna quant_nanggroe/ ./quant_nanggroe/
COPY --chown=qna:qna deploy/docker/scripts/entrypoint.sh ./entrypoint.sh

# Environment
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run as non-root user
USER qna

# Entrypoint runs migrations then starts the app
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden for worker service)
CMD ["uvicorn", "quant_nanggroe.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
