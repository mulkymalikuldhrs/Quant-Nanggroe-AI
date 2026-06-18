#!/bin/bash
# ============================================================================
# HERMES QUANT OS - Main Control Script
# ============================================================================
# Usage: ./hermes.sh [start|stop|restart|status|logs|watchdog|health|install]
#
# Features:
#   - On-boot auto-start via systemd or Termux:Boot
#   - Auto-restart on crash via watchdog daemon
#   - Health monitoring via keeper (cron)
#   - Telegram alerts on status changes
# ============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/hermes.pid"
WATCHDOG_PID="$BASE_DIR/watchdog.pid"
LOG_DIR="$BASE_DIR/logs"
HEALTH_FILE="$BASE_DIR/.hermes/health.json"
CONFIG_ENV="$BASE_DIR/config/.env"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[HERMES]${NC} $1"; }
warn()  { echo -e "${YELLOW}[HERMES]${NC} $1"; }
error() { echo -e "${RED}[HERMES]${NC} $1"; }
info()  { echo -e "${BLUE}[HERMES]${NC} $1"; }

# ============================================================================
# START - Launches watchdog (which starts and monitors Hermes)
# ============================================================================

start() {
    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        warn "Hermes is already running (PID $(cat $PID_FILE))"
        return 0
    fi

    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        warn "Watchdog is already running (PID $(cat $WATCHDOG_PID))"
        return 0
    fi

    log "${BOLD}Starting Hermes Quant OS...${NC}"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BASE_DIR/.hermes"

    # Load env
    if [ -f "$CONFIG_ENV" ]; then
        set -a
        source "$CONFIG_ENV"
        set +a
    fi

    # Start watchdog (which will start and monitor Hermes)
    log "Starting Watchdog (Always-On Mode)..."
    cd "$BASE_DIR/src"
    nohup python3 watchdog.py > "$LOG_DIR/watchdog_stdout.log" 2>&1 &
    WDOG_PID=$!
    echo "$WDOG_PID" > "$WATCHDOG_PID"

    sleep 3

    # Verify watchdog started
    if kill -0 "$WDOG_PID" 2>/dev/null; then
        log "${GREEN}${BOLD}Watchdog RUNNING - Hermes Quant OS is Always-On!${NC}"
        log "  Watchdog PID: $WDOG_PID"
        log "  Check Interval: 10s"
        log "  Max Restarts/Hour: 10"
        log "  Backoff: 5s → 120s (exponential)"
        log ""
        log "To view logs:"
        log "  tail -f $LOG_DIR/hermes_quant_$(date +%Y%m%d).log"
        log ""
        log "To stop:"
        log "  ./hermes.sh stop"
    else
        error "Watchdog failed to start! Check logs: $LOG_DIR/watchdog_stdout.log"
        # Fallback: start Hermes directly
        warn "Falling back to direct Hermes start..."
        nohup python3 hermes_quant.py > "$LOG_DIR/stdout.log" 2>&1 &
        H_PID=$!
        echo "$H_PID" > "$PID_FILE"
        log "Hermes started directly (PID: $H_PID) - no watchdog protection"
    fi
}

# ============================================================================
# STOP - Graceful shutdown
# ============================================================================

stop() {
    log "Stopping Hermes Quant OS..."

    # Stop watchdog first (so it doesn't restart Hermes)
    if [ -f "$WATCHDOG_PID" ]; then
        WPID=$(cat "$WATCHDOG_PID")
        if kill -0 "$WPID" 2>/dev/null; then
            log "Stopping watchdog (PID $WPID)..."
            kill "$WPID" 2>/dev/null || true
            sleep 2
            if kill -0 "$WPID" 2>/dev/null; then
                kill -9 "$WPID" 2>/dev/null || true
            fi
        fi
        rm -f "$WATCHDOG_PID"
    fi

    # Kill any remaining watchdog processes
    pkill -f "watchdog.py" 2>/dev/null || true
    sleep 1

    # Stop Hermes
    if [ -f "$PID_FILE" ]; then
        HPID=$(cat "$PID_FILE")
        if kill -0 "$HPID" 2>/dev/null; then
            log "Stopping Hermes (PID $HPID)..."
            kill "$HPID" 2>/dev/null || true
            sleep 3

            if kill -0 "$HPID" 2>/dev/null; then
                warn "Force killing Hermes..."
                kill -9 "$HPID" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Kill any remaining Hermes processes
    pkill -f "hermes_quant.py" 2>/dev/null || true

    log "${GREEN}Hermes Quant OS stopped.${NC}"
}

# ============================================================================
# STATUS - Show system status
# ============================================================================

status() {
    echo ""
    log "${BOLD}${CYAN}═══ HERMES QUANT OS STATUS ═══${NC}"
    echo ""

    # Check Hermes
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        log "${GREEN}Hermes: RUNNING (PID $(cat $PID_FILE))${NC}"
    else
        warn "Hermes: NOT RUNNING"
    fi

    # Check Watchdog
    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        log "${GREEN}Watchdog: RUNNING (PID $(cat $WATCHDOG_PID))${NC}"
    else
        warn "Watchdog: NOT RUNNING"
    fi

    # Health file
    if [ -f "$HEALTH_FILE" ]; then
        echo ""
        info "Health Status:"
        python3 -c "import json; d=json.load(open('$HEALTH_FILE')); print(json.dumps(d, indent=2))" 2>/dev/null || echo "  Could not read health file"
    fi

    # Resource usage
    echo ""
    info "Resource Usage:"
    ps aux | grep -E "(hermes_quant|watchdog)" | grep -v grep || echo "  No processes found"

    # Disk usage
    echo ""
    info "Disk:"
    du -sh "$BASE_DIR" 2>/dev/null || echo "  Unknown"
    du -sh "$LOG_DIR" 2>/dev/null || echo "  Logs: Unknown"

    echo ""
}

# ============================================================================
# LOGS - Tail log files
# ============================================================================

logs() {
    local log_type="${1:-hermes}"

    case "$log_type" in
        hermes)
            local logf="$LOG_DIR/hermes_quant_$(date +%Y%m%d).log"
            if [ -f "$logf" ]; then
                tail -f "$logf"
            else
                warn "No Hermes log found for today. Checking stdout..."
                tail -f "$LOG_DIR/stdout.log" 2>/dev/null || error "No logs found"
            fi
            ;;
        watchdog)
            tail -f "$LOG_DIR/watchdog_stdout.log" 2>/dev/null || \
            tail -f "$LOG_DIR/watchdog_$(date +%Y%m%d).log" 2>/dev/null || \
            error "No watchdog logs found"
            ;;
        keeper)
            tail -f "$LOG_DIR/keeper_$(date +%Y%m%d).log" 2>/dev/null || \
            error "No keeper logs found"
            ;;
        all)
            tail -f "$LOG_DIR"/*.log 2>/dev/null || error "No logs found"
            ;;
        *)
            echo "Usage: ./hermes.sh logs [hermes|watchdog|keeper|all]"
            ;;
    esac
}

# ============================================================================
# HEALTH - Run health check
# ============================================================================

health() {
    python3 "$BASE_DIR/scripts/keeper.py"
}

# ============================================================================
# RESTART
# ============================================================================

restart() {
    stop
    sleep 3
    start
}

# ============================================================================
# WATCHDOG - Start only the watchdog
# ============================================================================

watchdog_start() {
    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        warn "Watchdog already running (PID $(cat $WATCHDOG_PID))"
        return 0
    fi

    log "Starting watchdog only..."
    mkdir -p "$LOG_DIR"
    cd "$BASE_DIR/src"
    nohup python3 watchdog.py > "$LOG_DIR/watchdog_stdout.log" 2>&1 &
    echo $! > "$WATCHDOG_PID"
    log "Watchdog started (PID $(cat $WATCHDOG_PID))"
}

# ============================================================================
# INSTALL - Setup on-boot and auto-restart
# ============================================================================

install_on_boot() {
    log "${BOLD}Installing Hermes Quant OS as system service...${NC}"
    echo ""

    # Detect environment
    if command -v termux-info &> /dev/null; then
        install_termux_boot
    elif command -v systemctl &> /dev/null; then
        install_systemd
    elif command -v crontab &> /dev/null; then
        install_cron
    else
        error "No supported init system found!"
        error "Supported: systemd, Termux:Boot, cron"
        return 1
    fi
}

install_systemd() {
    log "Installing systemd service..."

    cat > /tmp/hermes-quant.service << EOF
[Unit]
Description=Hermes Quant Operating System - Autonomous Trading
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=$(whoami)
WorkingDirectory=$BASE_DIR
ExecStart=/bin/bash $BASE_DIR/hermes.sh start
ExecStop=/bin/bash $BASE_DIR/hermes.sh stop
ExecReload=/bin/bash $BASE_DIR/hermes.sh restart
PIDFile=$WATCHDOG_PID
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/systemd.log
StandardError=append:$LOG_DIR/systemd.log

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/hermes-quant.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable hermes-quant
    log "${GREEN}Systemd service installed and enabled!${NC}"
    log "Start: sudo systemctl start hermes-quant"
    log "Status: sudo systemctl status hermes-quant"
}

install_termux_boot() {
    log "Installing Termux:Boot service..."

    BOOT_DIR="$HOME/.termux/boot"
    mkdir -p "$BOOT_DIR"

    cat > "$BOOT_DIR/hermes-quant.sh" << EOF
#!/data/data/com.termux/files/usr/bin/bash
# Hermes Quant OS - Auto-start on boot

# Wait for network
sleep 10

# Start Hermes
cd $BASE_DIR
bash hermes.sh start
EOF

    chmod +x "$BOOT_DIR/hermes-quant.sh"
    log "${GREEN}Termux:Boot installed!${NC}"
    log "Install Termux:Boot from F-Droid for auto-start on device boot."
    log "File: $BOOT_DIR/hermes-quant.sh"
}

install_cron() {
    log "Installing cron job for health monitoring..."

    CRON_CMD="*/1 * * * * cd $BASE_DIR && python3 scripts/keeper.py >> $LOG_DIR/keeper_cron.log 2>&1"

    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

    log "${GREEN}Cron job installed!${NC}"
    log "Keeper will check every 1 minute."
    log "View: crontab -l"

    # Also add @reboot for on-boot
    REBOOT_CMD="@reboot sleep 30 && cd $BASE_DIR && bash hermes.sh start >> $LOG_DIR/boot.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "hermes.*start"; echo "$REBOOT_CMD") | crontab -

    log "@reboot also installed for on-boot start."
}

# ============================================================================
# Main
# ============================================================================

case "${1:-start}" in
    start)        start ;;
    stop)         stop ;;
    restart)      restart ;;
    status)       status ;;
    logs)         logs "${2:-hermes}" ;;
    health)       health ;;
    watchdog)     watchdog_start ;;
    install)      install_on_boot ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health|watchdog|install}"
        echo ""
        echo "Commands:"
        echo "  start     - Start Hermes Quant OS (with watchdog)"
        echo "  stop      - Stop Hermes Quant OS"
        echo "  restart   - Restart Hermes Quant OS"
        echo "  status    - Show system status"
        echo "  logs      - Tail logs [hermes|watchdog|keeper|all]"
        echo "  health    - Run health check"
        echo "  watchdog  - Start watchdog only"
        echo "  install   - Install on-boot + auto-restart"
        exit 1
        ;;
esac
