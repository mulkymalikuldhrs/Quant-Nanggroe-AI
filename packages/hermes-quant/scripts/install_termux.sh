#!/bin/bash
# ============================================================================
# HERMES QUANT OS - Android/Termux Installation Script
# ============================================================================
# This script installs Hermes Quant OS on Android via Termux
# 
# Prerequisites:
#   - Termux from F-Droid (NOT Play Store)
#   - Termux:Boot plugin (for on-boot auto-start)
#   - Internet connection
#
# Usage:
#   chmod +x install_termux.sh
#   ./install_termux.sh
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   HERMES QUANT OS - Termux Installer            ║"
echo "║   Autonomous Multi-Agent Trading System          ║"
echo "║   Owner: Mulky Malikul Dhaher                    ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect base directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/hermes-quant"

echo -e "${YELLOW}Installation directory: $INSTALL_DIR${NC}"
echo ""

# ============================================================================
# Step 1: Update Termux packages
# ============================================================================

echo -e "${BOLD}${GREEN}[1/8] Updating Termux packages...${NC}"
pkg update -y 2>/dev/null || apt-get update -y 2>/dev/null || true
pkg upgrade -y 2>/dev/null || apt-get upgrade -y 2>/dev/null || true

# ============================================================================
# Step 2: Install dependencies
# ============================================================================

echo -e "${BOLD}${GREEN}[2/8] Installing dependencies...${NC}"

# Python and pip
pkg install python -y 2>/dev/null || apt-get install python3 -y 2>/dev/null || true

# Essential tools
pkg install git curl wget nano -y 2>/dev/null || true

# Python packages
echo -e "${BLUE}Installing Python packages...${NC}"
pip install --upgrade pip 2>/dev/null || true
pip install aiohttp python-dotenv yfinance 2>/dev/null || pip3 install aiohttp python-dotenv yfinance 2>/dev/null || true

echo -e "${GREEN}Dependencies installed.${NC}"

# ============================================================================
# Step 3: Copy project files
# ============================================================================

echo -e "${BOLD}${GREEN}[3/8] Installing Hermes Quant OS...${NC}"

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy all files from script directory
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR"/.* "$INSTALL_DIR/" 2>/dev/null || true
fi

echo -e "${GREEN}Files copied to $INSTALL_DIR${NC}"

# ============================================================================
# Step 4: Set permissions
# ============================================================================

echo -e "${BOLD}${GREEN}[4/8] Setting permissions...${NC}"
chmod +x "$INSTALL_DIR/hermes.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/"*.py 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR/src/"*.py 2>/dev/null || true
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/.hermes/memories"
echo -e "${GREEN}Permissions set.${NC}"

# ============================================================================
# Step 5: Configure environment
# ============================================================================

echo -e "${BOLD}${GREEN}[5/8] Configuring environment...${NC}"

# Update .env paths for Termux
if [ -f "$INSTALL_DIR/config/.env" ]; then
    # Update paths
    sed -i "s|/workspace/hermes_quant|$INSTALL_DIR|g" "$INSTALL_DIR/config/.env" 2>/dev/null || true
fi

echo -e "${GREEN}Environment configured.${NC}"

# ============================================================================
# Step 6: Setup Termux:Boot (on-boot auto-start)
# ============================================================================

echo -e "${BOLD}${GREEN}[6/8] Setting up on-boot auto-start...${NC}"

BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"

cat > "$BOOT_DIR/hermes-quant.sh" << BOOTSCRIPT
#!/data/data/com.termux/files/usr/bin/bash
# Hermes Quant OS - Auto-start on Android boot
# Triggered by Termux:Boot plugin

# Wait for network connectivity
echo "[HERMES] Waiting for network..." >> $INSTALL_DIR/logs/boot.log
sleep 15

# Verify network
until ping -c 1 api.telegram.org > /dev/null 2>&1; do
    echo "[HERMES] Network not ready, waiting..." >> $INSTALL_DIR/logs/boot.log
    sleep 5
done

echo "[HERMES] Network ready! Starting Hermes Quant OS..." >> $INSTALL_DIR/logs/boot.log

# Start Hermes via control script
cd $INSTALL_DIR
bash hermes.sh start >> $INSTALL_DIR/logs/boot.log 2>&1

echo "[HERMES] Boot sequence complete." >> $INSTALL_DIR/logs/boot.log
BOOTSCRIPT

chmod +x "$BOOT_DIR/hermes-quant.sh"
echo -e "${GREEN}Termux:Boot configured!${NC}"
echo -e "${YELLOW}Note: Install Termux:Boot from F-Droid for on-boot to work.${NC}"

# ============================================================================
# Step 7: Setup cron health monitoring
# ============================================================================

echo -e "${BOLD}${GREEN}[7/8] Setting up health monitoring...${NC}"

# Install cron if not available
pkg install cronie -y 2>/dev/null || true

# Add keeper to crontab (every minute)
CRON_ENTRY="*/1 * * * * cd $INSTALL_DIR && python3 scripts/keeper.py >> $INSTALL_DIR/logs/keeper_cron.log 2>&1"
REBOOT_ENTRY="@reboot sleep 30 && cd $INSTALL_DIR && bash hermes.sh start >> $INSTALL_DIR/logs/boot.log 2>&1"

# Install crontab
(crontab -l 2>/dev/null | grep -v "hermes"; echo "$CRON_ENTRY"; echo "$REBOOT_ENTRY") | crontab - 2>/dev/null || true

# Start crond
crond 2>/dev/null || true

echo -e "${GREEN}Health monitoring configured (every 1 minute).${NC}"

# ============================================================================
# Step 8: Start Hermes
# ============================================================================

echo -e "${BOLD}${GREEN}[8/8] Starting Hermes Quant OS...${NC}"

cd "$INSTALL_DIR"
bash hermes.sh start

# ============================================================================
# Done!
# ============================================================================

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗"
echo "║   HERMES QUANT OS INSTALLED SUCCESSFULLY!       ║"
echo "╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Quick Commands:${NC}"
echo "  Start:     cd $INSTALL_DIR && bash hermes.sh start"
echo "  Stop:      cd $INSTALL_DIR && bash hermes.sh stop"
echo "  Status:    cd $INSTALL_DIR && bash hermes.sh status"
echo "  Logs:      cd $INSTALL_DIR && bash hermes.sh logs"
echo "  Restart:   cd $INSTALL_DIR && bash hermes.sh restart"
echo ""
echo -e "${CYAN}On-Boot:${NC}  Enabled (Termux:Boot)"
echo -e "${CYAN}Watchdog: ${GREEN}Active (auto-restart on crash)${NC}"
echo -e "${CYAN}Keeper:   ${GREEN}Active (health check every minute)${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  - Install Termux:Boot from F-Droid for on-boot"
echo "  - Disable battery optimization for Termux"
echo "  - Lock Termux in notification to prevent Android kill"
echo ""
echo -e "${GREEN}Hermes Quant OS is ETERNAL.${NC}"
