# ╔══════════════════════════════════════════════════════════════════════╗
# ║      Quant-Nanggroe-AI  —  Multi-stage Docker Build                ║
# ║      uv-based install  |  python:3.12-slim                         ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies and uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# Copy dependency metadata first (layer cache)
COPY pyproject.toml uv.lock ./

# Install runtime dependencies only (no dev)
RUN uv sync --no-dev --no-install-project

# ── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Set PATH to include venv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source (NOT config/ — credentials come from env vars at runtime)
COPY quant_nanggroe/ ./quant_nanggroe/
COPY data/         ./data/
COPY qna.py        ./qna.py

# Expose API port
EXPOSE 8000

# Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start the API server
CMD ["python", "qna.py", "api"]
