"""
Quant Nanggroe — Hedge Fund v3 Module
======================================
Multi-provider weighted voting aggregator with MT5/paper execution.

Adapted from E:/trading/hedge_fund.py for QNA integration.

Refactored module structure (Mon Jul 24 2026):
  utils/         — config, connection, data, indicators
  signals/       — core providers, qna_strategies, registry, aggregator
  risk/          — gate, guard
  execution/     — orders (trail_sl, execute)
  portfolio/     — main orchestration (run_once)

Usage:
    from quant_nanggroe.hedge_fund import run_once, aggregate, ALL_PROVIDERS
    result = run_once("EURUSD")
"""

from quant_nanggroe.hedge_fund.utils import (
    connect,
    ensure_terminal,
    get_historical_mt5,
    calc_atr,
    MT5_AVAILABLE,
    PAPER_TRADE,
    log,
)
from quant_nanggroe.hedge_fund.signals import (
    aggregate,
    ALL_PROVIDERS,
    CORE_PROVIDERS,
    signal_sma,
    signal_wyckoff,
    signal_aihf,
    signal_hidden,
    signal_tradingagents,
    signal_aitrader,
    signal_langalpha,
    signal_aimarketmaker,
    signal_kronos,
    signal_pyportfolioopt,
)
from quant_nanggroe.hedge_fund.risk import check_gate
from quant_nanggroe.hedge_fund.execution import trail_sl, execute
from quant_nanggroe.hedge_fund.portfolio import run_once

# Legacy re-exports (from monolith era — kept for backward compatibility)
from quant_nanggroe.hedge_fund.mtf import run_mtf_cycle, execute_mtf
from quant_nanggroe.hedge_fund.multipair import run_multipair_cycle

__all__ = [
    # utils
    "connect", "ensure_terminal", "get_historical_mt5", "calc_atr",
    "MT5_AVAILABLE", "PAPER_TRADE", "log",
    # signals
    "aggregate", "ALL_PROVIDERS", "CORE_PROVIDERS",
    "signal_sma", "signal_wyckoff", "signal_aihf", "signal_hidden",
    "signal_tradingagents", "signal_aitrader", "signal_langalpha",
    "signal_aimarketmaker", "signal_kronos", "signal_pyportfolioopt",
    # risk
    "check_gate",
    # execution
    "trail_sl", "execute",
    # portfolio / main
    "run_once",
    # legacy (mtf, multipair)
    "run_mtf_cycle", "execute_mtf", "run_multipair_cycle",
]
