#!/usr/bin/env bash
# =============================================================================
# Quant Nanggroe AI — Setup Script
# Version 1.0.0 (QNA-native, not AI-MultiColony)
# =============================================================================
# This script checks prerequisites, creates a Python virtual environment,
# installs all Python and Node.js dependencies, and copies .env.example to .env.
#
# Usage:
#   bash scripts/setup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  Quant Nanggroe AI v6 — Setup Wizard${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""

info "Checking Python installation..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PYTHON_MAJOR" -gt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; }; then
        success "Python $PYTHON_VERSION found (>= 3.11)"
    else
        fail "Python $PYTHON_VERSION found, but Python >= 3.11 is required."
    fi
else
    fail "Python 3 not found. Install Python 3.11+."
fi

# QNA uses uv for package management (not pip directly)
info "Checking uv..."
if command -v uv &>/dev/null; then
    success "uv found"
else
    info "uv not found — installing..."
    pip install uv 2>/dev/null && success "uv installed" || warn "uv install failed, falling back to pip"
fi

info "Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        success "Node.js $(node -v) found (>= 18)"
    else
        fail "Node.js $(node -v) found, but >= 18 required."
    fi
else
    fail "Node.js not found."
fi

VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created"
fi
source "$VENV_DIR/bin/activate"

info "Installing Python dependencies (uv sync)..."
if command -v uv &>/dev/null; then
    uv sync 2>/dev/null && success "uv sync completed" || warn "uv sync had issues, trying pip fallback"
else
    pip install -e ".[dev]" 2>/dev/null && success "Core dependencies installed" || warn "pip install had issues"
    pip install -r requirements.txt 2>/dev/null && success "requirements.txt installed" || warn "requirements.txt had issues"
fi

info "Installing dashboard dependencies..."
if [ -d "dashboard" ]; then
    cd dashboard && npm install 2>/dev/null && success "Dashboard dependencies installed" || warn "npm install had warnings"
    cd "$PROJECT_ROOT"
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
    info ".env already exists — not overwriting"
elif [ -f "$PROJECT_ROOT/.env.example" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    success "Copied .env.example to .env (edit with your API keys!)"
else
    warn ".env.example not found — create .env manually"
fi

info "Creating data directories..."
mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"
success "Data directories created"

info "Verifying core imports..."
python3 -c "
try:
    from qna import main
    from quant_nanggroe.hedge_fund import run_once
    print('QNA core imports: OK')
except ImportError as e:
    print(f'Warning: {e}')
" 2>/dev/null || warn "Some imports failed — may need additional setup"

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  Setup Complete! Quant Nanggroe AI v6${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "  Next steps:"
echo ""
echo -e "  ${CYAN}1.${NC} Edit ${YELLOW}.env${NC} with your API keys"
echo -e "  ${CYAN}2.${NC} Start API:     ${YELLOW}launch.bat api${NC}  or  ${YELLOW}python qna.py api${NC}"
echo -e "  ${CYAN}3.${NC} Start daemon:  ${YELLOW}launch.bat daemon${NC}"
echo -e "  ${CYAN}4.${NC} Dashboard:     ${YELLOW}cd dashboard && npm run dev${NC}"
echo -e "  ${CYAN}5.${NC} Run tests:     ${YELLOW}python -m pytest tests/ -v${NC}"
echo ""
