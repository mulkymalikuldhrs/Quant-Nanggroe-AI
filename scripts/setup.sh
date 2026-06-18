#!/usr/bin/env bash
# =============================================================================
# AI MultiColony Ecosystem — Setup Script
# Version 3.0.0
# =============================================================================
# This script checks prerequisites, creates a Python virtual environment,
# installs all Python and Node.js dependencies, and copies .env.example to .env.
#
# Usage:
#   bash scripts/setup.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ---------------------------------------------------------------------------
# Determine project root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  AI MultiColony Ecosystem v3.0.0 — Setup Wizard${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Check Python 3.11+
# ---------------------------------------------------------------------------
info "Checking Python installation..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PYTHON_MAJOR" -gt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; }; then
        success "Python $PYTHON_VERSION found (>= 3.11)"
    else
        fail "Python $PYTHON_VERSION found, but Python >= 3.11 is required. Please upgrade."
    fi
else
    fail "Python 3 not found. Please install Python 3.11 or later."
fi

# ---------------------------------------------------------------------------
# 2. Check Node 22+
# ---------------------------------------------------------------------------
info "Checking Node.js installation..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -ge 22 ]; then
        success "Node.js $(node -v) found (>= 22)"
    else
        fail "Node.js $(node -v) found, but Node >= 22 is required. Please upgrade."
    fi
else
    fail "Node.js not found. Please install Node.js 22 or later."
fi

# ---------------------------------------------------------------------------
# 3. Check npm
# ---------------------------------------------------------------------------
info "Checking npm installation..."
if command -v npm &>/dev/null; then
    success "npm $(npm -v) found"
else
    fail "npm not found. Please install npm."
fi

# ---------------------------------------------------------------------------
# 4. Create Python virtual environment
# ---------------------------------------------------------------------------
VENV_DIR="$PROJECT_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
    info "Virtual environment already exists at $VENV_DIR"
else
    info "Creating Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created"
fi

# Activate venv for the rest of the script
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# 5. Install Python dependencies
# ---------------------------------------------------------------------------
info "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel 2>/dev/null || warn "pip upgrade had warnings"

info "Installing core Python dependencies (pyproject.toml)..."
pip install -e ".[dev]" 2>/dev/null && success "Core dependencies installed" || warn "Some core dependencies may have issues"

info "Installing additional Python dependencies (requirements.txt)..."
pip install -r requirements.txt 2>/dev/null && success "requirements.txt installed" || warn "Some requirements.txt packages may have issues"

info "Installing Hermes Quant dependencies..."
pip install -r packages/hermes-quant/requirements.txt 2>/dev/null && success "Hermes Quant dependencies installed" || warn "Some Hermes Quant packages skipped"

info "Installing Deer Flow backend dependencies..."
if [ -f "packages/deer-flow/backend/pyproject.toml" ]; then
    cd packages/deer-flow/backend && pip install -e ".[dev]" 2>/dev/null && success "Deer Flow backend installed" || warn "Some Deer Flow backend packages skipped"
    cd "$PROJECT_ROOT"
fi

# ---------------------------------------------------------------------------
# 6. Install Node.js dependencies for all workspaces
# ---------------------------------------------------------------------------
info "Installing Node.js workspace dependencies..."
npm install 2>/dev/null && success "Node.js workspaces installed" || warn "Some npm packages may have issues"

# Install Crucix dependencies explicitly (it may not be in workspaces for all setups)
info "Ensuring Crucix dependencies are installed..."
cd packages/crucix && npm install 2>/dev/null && success "Crucix dependencies installed" || warn "Crucix npm install had warnings"
cd "$PROJECT_ROOT"

# Deer Flow frontend uses pnpm
info "Installing Deer Flow Frontend dependencies (pnpm)..."
if command -v pnpm &>/dev/null; then
    cd packages/deer-flow/frontend && pnpm install 2>/dev/null && success "Deer Flow frontend installed" || warn "Deer Flow frontend pnpm install had warnings"
    cd "$PROJECT_ROOT"
else
    warn "pnpm not found. Install it: npm install -g pnpm"
    warn "Skipping Deer Flow frontend install. Run: cd packages/deer-flow/frontend && pnpm install"
fi

# ---------------------------------------------------------------------------
# 7. Copy .env.example to .env
# ---------------------------------------------------------------------------
if [ -f "$PROJECT_ROOT/.env" ]; then
    info ".env file already exists — not overwriting"
else
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        success "Copied .env.example to .env (edit it with your API keys!)"
    else
        warn ".env.example not found — skip .env creation"
    fi
fi

# ---------------------------------------------------------------------------
# 8. Create data directories
# ---------------------------------------------------------------------------
info "Creating data directories..."
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/data/chroma"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/packages/hermes-quant/data"
mkdir -p "$PROJECT_ROOT/packages/hermes-quant/logs"
success "Data directories created"

# ---------------------------------------------------------------------------
# 9. Verify core imports
# ---------------------------------------------------------------------------
info "Verifying core Python module imports..."
python3 -c "
try:
    from ai_multicolony.core import BaseAgent, EventBus, ToolRegistry
    from ai_multicolony.memory import MemoryManager
    from ai_multicolony.colony import ColonyManager
    print('Core modules: OK')
except ImportError as e:
    print(f'Warning: Some core modules could not be imported: {e}')
" 2>/dev/null || warn "Some core modules could not be imported (may need additional setup)"

# ---------------------------------------------------------------------------
# Success!
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  Setup Complete! AI MultiColony Ecosystem v3.0.0${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "  Next steps:"
echo ""
echo -e "  ${CYAN}1.${NC} Edit ${YELLOW}.env${NC} with your API keys and configuration"
echo -e "  ${CYAN}2.${NC} Start the API server:"
echo -e "     ${YELLOW}make dev-api${NC}        (FastAPI on http://localhost:8000)"
echo ""
echo -e "  ${CYAN}3.${NC} Start the Web dashboard:"
echo -e "     ${YELLOW}make dev-web${NC}        (Next.js on http://localhost:3000)"
echo ""
echo -e "  ${CYAN}4.${NC} Start Crucix OSINT:"
echo -e "     ${YELLOW}make dev-crucix${NC}     (Express on http://localhost:3117)"
echo ""
echo -e "  ${CYAN}5.${NC} Or start everything at once:"
echo -e "     ${YELLOW}make dev${NC}            (All services)"
echo ""
echo -e "  ${CYAN}6.${NC} Or use Docker Compose:"
echo -e "     ${YELLOW}make docker-up${NC}      (Full stack with Postgres + Redis + Nginx)"
echo ""
echo -e "  Run ${YELLOW}make help${NC} to see all available commands."
echo ""
