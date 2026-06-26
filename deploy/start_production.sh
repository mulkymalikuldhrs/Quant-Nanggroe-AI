#!/usr/bin/env bash
# =============================================================================
# Agentic AI System - Production Startup Script
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# =============================================================================
# 1. Load environment
# =============================================================================
if [ -f .env ]; then
    log_info "Loading .env file..."
    set -a
    source .env
    set +a
else
    log_warn "No .env file found. Using defaults and environment variables."
fi

# =============================================================================
# 2. Check required env vars
# =============================================================================
MISSING=0

if [ -z "${SECRET_KEY:-}" ]; then
    log_warn "SECRET_KEY not set - a random key will be generated (sessions reset on restart)"
    log_warn "  Set SECRET_KEY for production: python -c \"import secrets; print(secrets.token_hex(32))\""
fi

if [ -z "${FLASK_ENV:-}" ]; then
    export FLASK_ENV=production
fi

if [ "${FLASK_ENV}" = "production" ] && [ -z "${SECRET_KEY:-}" ]; then
    log_error "SECRET_KEY MUST be set when FLASK_ENV=production"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    log_error "Required environment variables missing. Exiting."
    exit 1
fi

# =============================================================================
# 3. Create required directories
# =============================================================================
log_info "Ensuring required directories exist..."
mkdir -p data logs reports projects

# =============================================================================
# 4. Install dependencies
# =============================================================================
if [ ! -f ".deps_installed" ]; then
    log_info "Installing Python dependencies..."
    pip install --quiet -r requirements.txt 2>/dev/null || \
        pip install --break-system-packages --quiet -r requirements.txt

    # Ensure production server packages
    pip install --quiet gunicorn gevent gevent-websocket 2>/dev/null || \
        pip install --break-system-packages --quiet gunicorn gevent gevent-websocket

    touch .deps_installed
    log_info "Dependencies installed."
else
    log_info "Dependencies already installed (remove .deps_installed to force reinstall)."
fi

# =============================================================================
# 5. Configuration
# =============================================================================
HOST="${WEB_INTERFACE_HOST:-0.0.0.0}"
PORT="${WEB_INTERFACE_PORT:-5000}"
WORKERS="${GUNICORN_WORKERS:-1}"
WORKER_CLASS="geventwebsocket.gunicorn.workers.GeventWebSocketWorker"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-30}"
PIDFILE="logs/gunicorn.pid"
LOGLEVEL="${GUNICORN_LOGLEVEL:-info}"

# =============================================================================
# 6. Signal handling
# =============================================================================
cleanup() {
    log_info "Received shutdown signal, stopping gracefully..."
    if [ -f "$PIDFILE" ]; then
        kill -QUIT "$(cat "$PIDFILE")" 2>/dev/null || true
        rm -f "$PIDFILE"
    fi
    log_info "Shutdown complete."
    exit 0
}

trap cleanup SIGINT SIGTERM

# =============================================================================
# 7. Pre-flight check
# =============================================================================
log_info "Running pre-flight check..."
python -c "
import sys
sys.path.insert(0, '.')
try:
    import core
    import connectors
    import agents
    from web_interface.app import app
    print('  Import chain: OK')
except Exception as e:
    print(f'  Import chain FAILED: {e}')
    sys.exit(1)
" || {
    log_error "Pre-flight check failed. See errors above."
    exit 1
}

# =============================================================================
# 8. Start gunicorn
# =============================================================================
log_info "Starting Agentic AI System..."
log_info "  Host: $HOST"
log_info "  Port: $PORT"
log_info "  Workers: $WORKERS"
log_info "  Worker class: $WORKER_CLASS"
log_info "  Dashboard: http://localhost:$PORT"
echo ""

exec gunicorn \
    --worker-class "$WORKER_CLASS" \
    --workers "$WORKERS" \
    --bind "$HOST:$PORT" \
    --timeout "$TIMEOUT" \
    --graceful-timeout "$GRACEFUL_TIMEOUT" \
    --pid "$PIDFILE" \
    --access-logfile - \
    --error-logfile - \
    --log-level "$LOGLEVEL" \
    "web_interface.app:app"
