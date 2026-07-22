"""
Quant Nanggroe — Hedge Fund v3 Module
======================================
Multi-provider weighted voting aggregator with MT5/paper execution.

Adapted from E:/trading/hedge_fund.py for QNA integration.

Usage:
    from quant_nanggroe.hedge_fund import run_once, aggregate, run_mtf_cycle, run_multipair_cycle
    result = run_once("EURUSD")
"""

from quant_nanggroe.hedge_fund.hedge_fund import (
    ALL_PROVIDERS,
    CORE_PROVIDERS,
    PAPER_TRADE,
    aggregate,
    run_once,
)
from quant_nanggroe.hedge_fund.mtf import run_mtf_cycle, execute_mtf
from quant_nanggroe.hedge_fund.multipair import run_multipair_cycle

__all__ = [
    "run_once",
    "aggregate",
    "run_mtf_cycle",
    "execute_mtf",
    "run_multipair_cycle",
    "ALL_PROVIDERS",
    "CORE_PROVIDERS",
    "PAPER_TRADE",
]
