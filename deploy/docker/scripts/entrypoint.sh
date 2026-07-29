#!/bin/bash
# =============================================================================
# Quant-Nanggroe-AI — Docker Entrypoint
# =============================================================================
set -e

echo "[QNA] Starting Quant Nanggroe AI..."

# Verify required env vars
if [[ -z "${QNAI_JWT_SECRET}" ]]; then
    echo "[QNA] ERROR: QNAI_JWT_SECRET is not set"
    echo "[QNA] Set QNAI_JWT_SECRET in your .env or docker-compose environment"
    exit 1
fi

# Start the API server
echo "[QNA] Starting API server on port ${PORT:-8000}"
exec python qna.py api
