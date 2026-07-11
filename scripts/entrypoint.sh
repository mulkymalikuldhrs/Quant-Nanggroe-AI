#!/bin/bash
# =============================================================
# Quant-Nanggroe-AI — Docker Entrypoint
# Runs Alembic migrations before starting the application.
# =============================================================
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Quant-Nanggroe-AI — Container Starting               ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── Run Alembic Migrations ──────────────────────────────────
echo "📦 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed! Exiting."
    exit 1
fi

# ── Execute the container command ───────────────────────────
echo "🚀 Starting application: $*"
exec "$@"
