#!/bin/bash
# ============================================================
# Agentic AI System - Web Interface Startup Script
# Made with love by Mulky Malikul Dhaher in Indonesia
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================================"
echo "  Agentic AI System - Web Interface"
echo "  Autonomous Multi-Agent Intelligence Platform"
echo "  Made with love by Mulky Malikul Dhaher in Indonesia"
echo "========================================================"
echo -e "${NC}"

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env if present
if [ -f .env ]; then
    echo -e "${GREEN}Loading .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Set defaults
export WEB_INTERFACE_PORT="${WEB_INTERFACE_PORT:-5000}"
export WEB_INTERFACE_HOST="${WEB_INTERFACE_HOST:-0.0.0.0}"
export FLASK_ENV="${FLASK_ENV:-development}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON=python3

# Check and install dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

# Core dependencies
DEPS=("flask" "flask_socketio")
MISSING=()

for dep in "${DEPS[@]}"; do
    if ! $PYTHON -c "import ${dep}" 2>/dev/null; then
        MISSING+=("$dep")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing dependencies: ${MISSING[*]}${NC}"
    $PYTHON -m pip install "${MISSING[@]}" --quiet
fi

# Ensure data directories exist
echo -e "${YELLOW}Ensuring data directories...${NC}"
mkdir -p data data/backups data/logs data/cache projects ui/generated reports

# Check if port is already in use
if lsof -Pi :$WEB_INTERFACE_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}Error: Port $WEB_INTERFACE_PORT is already in use${NC}"
    echo -e "${YELLOW}Try: lsof -i :$WEB_INTERFACE_PORT to find the process${NC}"
    echo -e "${YELLOW}Or set WEB_INTERFACE_PORT to a different port${NC}"
    exit 1
fi

# Start the web interface
echo -e "${GREEN}Starting Agentic AI System Web Interface...${NC}"
echo -e "${BLUE}  Host: $WEB_INTERFACE_HOST${NC}"
echo -e "${BLUE}  Port: $WEB_INTERFACE_PORT${NC}"
echo -e "${BLUE}  URL:  http://localhost:$WEB_INTERFACE_PORT${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

$PYTHON -m web_interface.app || $PYTHON web_interface/app.py
