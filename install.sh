#!/usr/bin/env bash
set -e

echo "═══ Quant-Nanggroe-AI Installer ═══"

# Install Python deps
pip install -q fastapi uvicorn[standard] python-dotenv pyyaml numpy pandas

# Install Node deps
cd dashboard && npm install --silent

echo "Installation complete."