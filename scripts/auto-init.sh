#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "=== Auto-Init: QNA Environment Setup ==="

# 1. Create required directories
echo "--- Creating required directories ---"
mkdir -p paper_state data/cached_ohlcv docs/auto/graphs docs/auto/api docs/auto/audit docs/auto/review logs

# 2. Check Python version
echo "--- Python version check ---"
python3 --version 2>&1 || { echo "❌ Python3 required"; exit 1; }

# 3. Install dependencies
if command -v pip3 &>/dev/null; then
    echo "--- Installing/updating dependencies ---"
    pip3 install -e ".[dev]" 2>&1 | tail -5 || echo "⚠️ Partial install — some optional deps may be missing"
fi

# 4. Set up git hooks if .git exists
if [ -d .git ]; then
    echo "--- Setting up git hooks ---"
    if [ -f .pre-commit-config.yaml ]; then
        pre-commit install 2>/dev/null || echo "⚠️ pre-commit not installed, skipping hooks"
    fi
fi

# 5. Register the auto scripts as executable
echo "--- Making scripts executable ---"
chmod +x "$REPO/scripts/auto-"*.sh 2>/dev/null && echo "✅ Scripts registered"

# 6. Create symlink for `qnai` CLI (if on PATH)
echo "--- Setting up qnai CLI ---"
if [ -f "$REPO/scripts/qnai" ]; then
    chmod +x "$REPO/scripts/qnai"
    echo "✅ qnai CLI ready at scripts/qnai"
fi

# 7. Initialize paper_state dir
echo "--- Paper state dir initialized ---"
touch paper_state/.gitkeep

# 8. Verify import
echo "--- Verifying core import ---"
if python3 -c "import sys; sys.path.insert(0, '.'); from quant_nanggroe import QNA_VERSION; print(f'QNA v{QNA_VERSION} — import OK')" 2>&1; then
    echo "✅ Core import verified"
else
    echo "⚠️ Core import failed — may need pip install -e ."
fi

echo ""
echo "=== Auto-Init Complete ==="
echo ""
echo "Quick start:"
echo "  bash scripts/auto-init.sh     # This script"
echo "  bash scripts/auto-audit.sh    # Run all audits"
echo "  bash scripts/auto-docs.sh     # Generate API docs"
echo "  bash scripts/auto-graphify.sh # Generate dependency graphs"
echo "  bash qna-paper.sh             # Start paper trading"
