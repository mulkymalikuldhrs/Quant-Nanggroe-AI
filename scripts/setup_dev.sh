#!/bin/bash
# =============================================================
# Quant-Nanggroe-AI — Development Environment Setup
# =============================================================
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Quant-Nanggroe-AI — Dev Environment Setup             ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [[ "$(echo "$PYTHON_VERSION >= 3.12" | bc -l)" -ne 1 ]]; then
    echo "❌ Python 3.12+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "✅ Poetry $(poetry --version)"

# Install dependencies
echo "📦 Installing Python dependencies..."
poetry install --with dev,test --no-interaction || pip install -e ".[dev,test]" || pip install -e .

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "🪝 Installing pre-commit hooks..."
    pre-commit install || true
fi

# Copy .env if not exists
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Edit .env with your API keys!"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                        ║"
echo "║                                                          ║"
echo "║   Run the API:      make run-api                         ║"
echo "║   Run tests:        make test                            ║"
echo "║   Docker full stack: make docker-up                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
