#!/usr/bin/env bash
set -euo pipefail

QNA_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$QNA_ROOT"

echo "═══ Quant-Nanggroe-AI Installer ═══"
echo "Root: $QNA_ROOT"

# ── Python virtual environment ──────────────────────────────────────
if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)  ACTIVATE=".venv/Scripts/activate" ;;
    *)                     ACTIVATE=".venv/bin/activate" ;;
esac

# shellcheck disable=SC1090
source "$ACTIVATE"

echo "Python: $(which python3)"
echo "Pip:    $(pip --version 2>/dev/null | head -1)"

# ── Install Python dependencies ─────────────────────────────────────
echo "Installing Python dependencies from pyproject.toml..."
pip install --quiet --upgrade pip setuptools wheel 2>&1 | tail -1 || true
pip install -e ".[dev]" 2>&1 | tail -3
echo "Python deps: installed $(pip list --format=columns 2>/dev/null | wc -l) packages"

# ── Install optional extras (best-effort) ───────────────────────────
EXTRA_GROUPS="ml alpaca polygon data memory quant"
for group in $EXTRA_GROUPS; do
    echo "  Trying [${group}] extras..."
    pip install -e ".[${group}]" --quiet 2>&1 | tail -1 || echo "  [${group}] skipped"
done

# ── Dashboard (Node.js) ────────────────────────────────────────────
if [ -f dashboard/package.json ]; then
    echo "Installing Dashboard dependencies..."
    cd dashboard
    npm install --silent 2>&1 | tail -1
    cd "$QNA_ROOT"
else
    echo "Dashboard directory not found — skipping"
fi

# ── Verify key imports ──────────────────────────────────────────────
echo "Verifying installation..."
python3 -c "import quant_nanggroe; print('quant_nanggroe:', quant_nanggroe.__version__)" 2>/dev/null && \
    echo "  OK" || echo "  WARNING: import failed (may need missing deps)"

# ── Done ────────────────────────────────────────────────────────────
echo ""
echo "═══ Installation complete ═══"
echo "  Virtual env: $QNA_ROOT/.venv"
echo "  Activate:    source $ACTIVATE"
echo "  Run daemon:  bash qna-paper.sh"
echo "  Run tests:   make test"