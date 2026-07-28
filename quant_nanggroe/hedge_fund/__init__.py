"""
Quant Nanggroe — Hedge Fund v3 Module
======================================
Re-exports from submodules: utils/, signals/, risk/, execution/, portfolio/.
Legacy mtf.py / multipair.py are excluded (they import E:/trading deps
and numpy C-extensions that are not required by the core run_once path).
"""

from quant_nanggroe.hedge_fund.execution import (  # noqa: F401
    execute,
    kelly_lot_size,
    trail_sl,
)
from quant_nanggroe.hedge_fund.portfolio import (  # noqa: F401
    run_once,
)
from quant_nanggroe.hedge_fund.risk import (  # noqa: F401
    risk_guard_approve,
)
from quant_nanggroe.hedge_fund.signals import (  # noqa: F401
    ALL_PROVIDERS,
    CORE_PROVIDERS,
    aggregate,
    signal_aihf,
    signal_aimarketmaker,
    signal_aitrader,
    signal_hidden,
    signal_kronos,
    signal_langalpha,
    signal_pyportfolioopt,
    signal_sma,
    signal_tradingagents,
    signal_wyckoff,
)
from quant_nanggroe.hedge_fund.utils import (  # noqa: F401
    CREDS,
    MT5_AVAILABLE,
    PAPER_TRADE,
    calc_atr,
    connect,
    ensure_terminal,
    get_historical_mt5,
    log,
)

__all__ = [
    "connect", "ensure_terminal", "get_historical_mt5", "calc_atr",
    "MT5_AVAILABLE", "PAPER_TRADE", "log", "CREDS",
    "aggregate", "ALL_PROVIDERS", "CORE_PROVIDERS",
    "signal_sma", "signal_wyckoff", "signal_aihf", "signal_hidden",
    "signal_tradingagents", "signal_aitrader", "signal_langalpha",
    "signal_aimarketmaker", "signal_kronos", "signal_pyportfolioopt",
    "risk_guard_approve",
    "trail_sl", "execute", "kelly_lot_size",
    "run_once",
]
