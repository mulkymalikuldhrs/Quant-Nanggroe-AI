#!/bin/bash
# ============================================================================
# HERMES QUANT OS - Linux Server Installation Script
# ============================================================================
# Installs on Linux server with systemd for on-boot + auto-restart
#
# Usage:
#   chmod +x install_server.sh
#   sudo ./install_server.sh
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:-/opt/hermes-quant}"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo -e "${BOLD}${GREEN}"
echo "HERMES QUANT OS - Server Installer"
echo "Installing to: $INSTALL_DIR"
echo "Service user: $SERVICE_USER"
echo -e "${NC}"

# Install dependencies
echo -e "${BOLD}${GREEN}[1/5] Installing dependencies...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl
pip3 install aiohttp python-dotenv yfinance 2>/dev/null || true

# Copy files
echo -e "${BOLD}${GREEN}[2/5] Installing files...${NC}"
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/hermes.sh"
chmod +x "$INSTALL_DIR/src/"*.py
chmod +x "$INSTALL_DIR/scripts/"*.py
mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/data" "$INSTALL_DIR/.hermes/memories"

# Update paths
sed -i "s|/workspace/hermes_quant|$INSTALL_DIR|g" "$INSTALL_DIR/config/.env" 2>/dev/null || true

# Install systemd service
echo -e "${BOLD}${GREEN}[3/5] Installing systemd service...${NC}"
cat > /etc/systemd/system/hermes-quant.service << EOF
[Unit]
Description=Hermes Quant Operating System
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/bin/bash $INSTALL_DIR/hermes.sh start
ExecStop=/bin/bash $INSTALL_DIR/hermes.sh stop
ExecReload=/bin/bash $INSTALL_DIR/hermes.sh restart
PIDFile=$INSTALL_DIR/watchdog.pid
Restart=on-failure
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/systemd.log
StandardError=append:$INSTALL_DIR/logs/systemd.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hermes-quant

# Install cron health check
echo -e "${BOLD}${GREEN}[4/5] Installing cron keeper...${NC}"
CRON_CMD="*/1 * * * * cd $INSTALL_DIR && python3 scripts/keeper.py >> $INSTALL_DIR/logs/keeper_cron.log 2>&1"
(crontab -u $SERVICE_USER -l 2>/dev/null | grep -v "hermes"; echo "$CRON_CMD") | crontab -u $SERVICE_USER - || true

# Start
echo -e "${BOLD}${GREEN}[5/5] Starting Hermes Quant OS...${NC}"
systemctl start hermes-quant

echo ""
echo -e "${BOLD}${GREEN}HERMES QUANT OS INSTALLED!${NC}"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start hermes-quant"
echo "  Stop:    sudo systemctl stop hermes-quant"
echo "  Status:  sudo systemctl status hermes-quant"
echo "  Logs:    journalctl -u hermes-quant -f"
echo ""
echo "On-boot:  Enabled (systemd)"
echo "Watchdog: Active (auto-restart on crash)"
