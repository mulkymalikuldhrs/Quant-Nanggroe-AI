#!/bin/bash
set -e

echo "=== Quant Nanggroe AI — Entrypoint ==="

# Run database migrations
echo "Running Alembic migrations..."
alembic -c /app/quant_nanggroe/database/alembic.ini upgrade head

# Start the application
echo "Starting application: $@"
exec "$@"
