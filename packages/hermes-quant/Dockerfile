# ── Hermes Quant OS Dockerfile ──────────────────────────────────────
# Python 3.12 slim image for the Hermes Quant trading service
# Owner: Mulky Malikul Dhaher
# ────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

LABEL maintainer="Mulky Malikul Dhaher"
LABEL description="Hermes Quant OS - Autonomous Multi-Agent Trading & Research Infrastructure"
LABEL version="1.0"

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (minimal for slim image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire package
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config

# Default environment variables (override at runtime)
ENV LOG_DIR=/app/logs
ENV DATA_DIR=/app/data
ENV MAX_RESTART_ATTEMPTS=0
ENV RESTART_DELAY=5

# Expose no ports by default (Telegram polling mode)
# If adding API/WebSocket later, expose here

# Health check - verify the main script is importable
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from tools.math_engine import MathEngine; print('OK')" || exit 1

# Run the main Hermes Quant OS agent
CMD ["python", "src/hermes_quant.py"]
