# ═══════════════════════════════════════════════════════════════════════════════
# Multi-stage Dockerfile for Quant-Nanggroe-AI
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy source AND pyproject.toml BEFORE install (fixes the missing-source bug)
COPY pyproject.toml ./
COPY quant_nanggroe/ ./quant_nanggroe/
COPY tests/ ./tests/

# Install into a clean prefix so we can copy only installed packages later
RUN pip install --no-cache-dir --prefix=/install -e ".[dev]"

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime-only system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (already installed, but keep for healthcheck & entrypoint)
COPY --from=builder /build/quant_nanggroe/ ./quant_nanggroe/
COPY --from=builder /build/pyproject.toml ./

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "from quant_nanggroe.config import get_settings; get_settings()" || exit 1

# Default entry point
ENTRYPOINT ["python", "-m", "quant_nanggroe.cli"]
