"""Backtest walk-forward gate — prevents execution if strategy fails validation.

Provides:
- check_gate() — Runs backtest_pipeline.py via subprocess; parses pass/fail
  from stdout and GATE_FILE (gate_status.json). Gate must pass within 24h cache
  window before live execution is allowed.

Related sections in hedge_fund.py: lines 6286-6299
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    check_gate,
    GATE_FILE,
    _QNA_DIR,
    log,
)
