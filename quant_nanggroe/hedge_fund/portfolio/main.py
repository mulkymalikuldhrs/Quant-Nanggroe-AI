"""Main hedge fund orchestration cycle — ties all modules together.

Provides:
- run_once() — The complete hedge fund cycle:
  1. MT5 connection (or paper mode fallback)
  2. Backtest walk-forward gate check (24h cache)
  3. Symbol selection (target or auto-pick best pair via multi_pair_scanner)
  4. Account info logging
  5. Position management (trailing SL for open positions)
  6. Multi-provider weighted voting (delegates to signals.aggregator)
  7. Risk guard approval (delegates to risk.guard)
  8. Order execution (delegates to execution.orders)

Flow:
    connect() → check_gate() → pick_symbol() → manage_positions()
    → aggregate() → risk_guard_approve() → execute()

Related sections in hedge_fund.py: lines 6301-6461
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    run_once,
    PAPER_TRADE,
    ALL_PROVIDERS,
    GATE_FILE,
    _QNA_DIR,
    log,
    connect,
    ensure_terminal,
    mt5,
    trail_sl,
    aggregate,
    check_gate,
    execute,
    calc_atr,
)
