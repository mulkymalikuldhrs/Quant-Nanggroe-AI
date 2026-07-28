#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
QNA_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
unset PYTHONPATH
export QNAI_ALPACA_PAPER=true

if [ -z "${QNAI_ALPACA_API_KEY:-}" ] || [ -z "${QNAI_ALPACA_API_SECRET:-}" ]; then
  echo "ERROR: QNAI_ALPACA_API_KEY and QNAI_ALPACA_API_SECRET must be set"
  echo ""
  echo "  export QNAI_ALPACA_API_KEY='your_key_here'"
  echo "  export QNAI_ALPACA_API_SECRET='your_secret_here'"
  echo ""
  echo "Get API keys from: https://alpaca.markets/docs/trading/paper-trading/"
  exit 1
fi

python3 -c "import alpaca" 2>/dev/null || pip install alpaca-py

cd "${QNA_HOME}"
exec python3 -m uvicorn quant_nanggroe.api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
