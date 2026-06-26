#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║      Quant-Nanggroe-AI  —  Multi-Target Deployment Script          ║
# ║      Supports: E2B Sandbox, VPS (Ubuntu/Debian), Docker            ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="quant-nanggroe-ai"
VERSION="${VERSION:-1.0.0}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8000/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"
LOG_FILE="/tmp/qna-deploy-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Helpers ────────────────────────────────────────────────────────────
log()    { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
err()    { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2; }
success(){ echo -e "${GREEN}[OK]${NC} $*" | tee -a "$LOG_FILE"; }
die()    { err "$*"; exit 1; }

check_deps() {
    local deps=("$@")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            die "Required dependency not found: $dep"
        fi
    done
}

wait_for_health() {
    local url="$1"
    local timeout="${2:-$HEALTH_TIMEOUT}"
    local elapsed=0
    log "Waiting for health check at $url (timeout: ${timeout}s)..."
    while [ $elapsed -lt "$timeout" ]; do
        if curl -sf "$url" &>/dev/null; then
            success "Health check passed after ${elapsed}s"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    err "Health check failed after ${timeout}s"
    return 1
}

# ── E2B Deployment ─────────────────────────────────────────────────────
deploy_e2b() {
    log "═══ Deploying to E2B Sandbox ═══"
    check_deps "e2b" "docker"

    log "Building E2B sandbox image..."
    e2b build --template "$SCRIPT_DIR/e2b.toml" 2>&1 | tee -a "$LOG_FILE"

    log "Deploying sandbox..."
    local SANDBOX_ID
    SANDBOX_ID=$(e2b sandbox start --template "$PROJECT_NAME" 2>&1)
    if [ $? -eq 0 ]; then
        success "E2B sandbox deployed: $SANDBOX_ID"
        log "Sandbox URL: https://$SANDBOX_ID.e2b.app"
        log "Health endpoint: https://$SANDBOX_ID.e2b.app/health"
    else
        die "E2B deployment failed"
    fi
}

# ── VPS Deployment (Ubuntu/Debian) ─────────────────────────────────────
deploy_vps() {
    log "═══ Deploying to VPS (Ubuntu/Debian) ═══"
    check_deps "docker" "docker-compose" "curl"

    local VPS_HOST="${VPS_HOST:-localhost}"
    local VPS_USER="${VPS_USER:-deploy}"
    local DEPLOY_DIR="${DEPLOY_DIR:-/opt/${PROJECT_NAME}}"

    if [ "$VPS_HOST" != "localhost" ] && [ "$VPS_HOST" != "127.0.0.1" ]; then
        log "Setting up remote VPS: ${VPS_USER}@${VPS_HOST}..."
        ssh "$VPS_USER@$VPS_HOST" "sudo mkdir -p $DEPLOY_DIR && sudo chown $VPS_USER:$VPS_USER $DEPLOY_DIR"

        log "Syncing project files..."
        rsync -avz --delete \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='__pycache__' \
            --exclude='.env' \
            --exclude='data' \
            "$SCRIPT_DIR/" "$VPS_USER@$VPS_HOST:$DEPLOY_DIR/"

        log "Running deployment on remote VPS..."
        ssh "$VPS_USER@$VPS_HOST" "cd $DEPLOY_DIR && bash deploy.sh --docker"
    else
        log "Deploying locally to $DEPLOY_DIR..."
        sudo mkdir -p "$DEPLOY_DIR"
        sudo cp -r "$SCRIPT_DIR/." "$DEPLOY_DIR/"
        cd "$DEPLOY_DIR"

        # Install system dependencies
        log "Installing system dependencies..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            curl \
            postgresql-client \
            redis-tools \
            build-essential \
            python3.12 \
            python3.12-venv \
            python3-pip \
            nginx \
            certbot \
            python3-certbot-nginx \
            ufw \
            fail2ban \
            unattended-upgrades 2>&1 | tee -a "$LOG_FILE"

        # Create virtual environment
        log "Setting up Python environment..."
        python3.12 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Create systemd service
        log "Creating systemd service..."
        sudo tee /etc/systemd/system/${PROJECT_NAME}.service > /dev/null <<EOF
[Unit]
Description=Quant Nanggroe AI Trading System
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=$USER
WorkingDirectory=$DEPLOY_DIR
Environment=PATH=$DEPLOY_DIR/venv/bin:/usr/bin
ExecStart=$DEPLOY_DIR/venv/bin/python -m uvicorn quant_nanggroe_ai.api.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable "$PROJECT_NAME"
        sudo systemctl start "$PROJECT_NAME"
        success "VPS deployment complete"
    fi
}

# ── Docker Deployment ──────────────────────────────────────────────────
deploy_docker() {
    log "═══ Deploying with Docker Compose ═══"
    check_deps "docker" "docker-compose"

    log "Building Docker images..."
    docker-compose build --no-cache 2>&1 | tee -a "$LOG_FILE"

    log "Stopping existing containers..."
    docker-compose down --remove-orphans 2>/dev/null || true

    log "Starting all services..."
    docker-compose up -d 2>&1 | tee -a "$LOG_FILE"

    log "Waiting for services to become healthy..."
    sleep 10

    # Check API health
    if wait_for_health "http://localhost:8000/health" 60; then
        success "Docker deployment complete"
        log "Services running:"
        docker-compose ps
    else
        warn "Deployment may need more time to stabilize"
        docker-compose logs --tail=50
    fi
}

# ── Health Check ───────────────────────────────────────────────────────
health_check() {
    log "═══ Running Health Checks ═══"
    local all_ok=true

    # API Health
    log "Checking API health..."
    if curl -sf "$HEALTH_ENDPOINT" &>/dev/null; then
        success "API: healthy"
    else
        warn "API: unhealthy or unreachable"
        all_ok=false
    fi

    # Readiness
    log "Checking readiness probe..."
    if curl -sf "http://localhost:8000/ready" &>/dev/null; then
        success "Readiness: ready"
    else
        warn "Readiness: not ready"
        all_ok=false
    fi

    # Liveness
    log "Checking liveness probe..."
    if curl -sf "http://localhost:8000/live" &>/dev/null; then
        success "Liveness: alive"
    else
        warn "Liveness: not alive"
        all_ok=false
    fi

    # PostgreSQL (if running)
    if command -v pg_isready &>/dev/null; then
        if pg_isready -h localhost -p 5432 &>/dev/null; then
            success "PostgreSQL: accepting connections"
        else
            warn "PostgreSQL: not reachable"
        fi
    fi

    # Redis (if running)
    if command -v redis-cli &>/dev/null; then
        if redis-cli ping &>/dev/null; then
            success "Redis: responding"
        else
            warn "Redis: not responding"
        fi
    fi

    if [ "$all_ok" = false ]; then
        warn "Some health checks failed — review logs"
        return 1
    fi
    success "All health checks passed"
}

# ── Usage ──────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
    e2b         Deploy to E2B sandbox
    vps         Deploy to VPS (Ubuntu/Debian)
    docker      Deploy with Docker Compose
    health      Run health checks
    all         Deploy all targets (E2B + Docker)
    help        Show this help message

Environment Variables:
    VERSION             Release version (default: 1.0.0)
    VPS_HOST            VPS hostname for remote deploy
    VPS_USER            SSH user for VPS
    DEPLOY_DIR          Deployment directory on VPS
    HEALTH_ENDPOINT     Health check URL
    HEALTH_TIMEOUT      Health check timeout in seconds

Examples:
    $0 docker                    # Deploy locally with Docker
    $0 vps                       # Deploy to VPS (local)
    VPS_HOST=10.0.0.1 $0 vps     # Deploy to remote VPS
    $0 health                    # Run health checks
    $0 all                       # Deploy everything
EOF
}

# ── Main ───────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-help}"
    log "Quant Nanggroe AI — Deployment Script v$VERSION"
    log "Log file: $LOG_FILE"

    case "$cmd" in
        e2b)     deploy_e2b ;;
        vps)     deploy_vps ;;
        docker)  deploy_docker ;;
        health)  health_check ;;
        all)
            deploy_docker
            health_check
            ;;
        help|--help|-h) usage ;;
        *)       die "Unknown command: $cmd. Run '$0 help' for usage." ;;
    esac
}

main "$@"
