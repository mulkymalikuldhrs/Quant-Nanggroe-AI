"""
Quant Nanggroe — Hedge Fund v3 Module
======================================
Single-source-of-truth re-exports from the monolith hedge_fund.py.

NOTE: The pkg was partially refactored into utils/signals/risk/execution/
portfolio submodules, but those stubs were never completed — the real
working code lives in hedge_fund.py. To keep `qna.py hedge-fund` working
we re-export directly from the monolith. The stub submodules remain on
disk but are intentionally NOT imported here (they raise ImportError).
Legacy mtf.py / multipair.py are excluded (they import E:/trading deps
and numpy C-extensions that are not required by the core run_once path).
"""

from quant_nanggroe.hedge_fund.hedge_fund import (  # noqa: F401
    # utils
    connect,
    ensure_terminal,
    get_historical_mt5,
    calc_atr,
    MT5_AVAILABLE,
    PAPER_TRADE,
    log,
    CREDS,
    # core providers / signals
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
    # risk
    check_gate,
    # execution
    trail_sl,
    execute,
    # portfolio / main
    run_once,
)

__all__ = [
    "connect", "ensure_terminal", "get_historical_mt5", "calc_atr",
    "MT5_AVAILABLE", "PAPER_TRADE", "log", "CREDS",
    "aggregate", "ALL_PROVIDERS", "CORE_PROVIDERS",
    "signal_sma", "signal_wyckoff", "signal_aihf", "signal_hidden",
    "signal_tradingagents", "signal_aitrader", "signal_langalpha",
    "signal_aimarketmaker", "signal_kronos", "signal_pyportfolioopt",
    "check_gate",
    "trail_sl", "execute",
    "run_once",
]
