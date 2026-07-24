"""Shared utilities: config, MT5 connection, data fetching, indicators."""

from quant_nanggroe.hedge_fund.utils.config import (
    _HF_DIR, _QNA_DIR, _DATA_DIR,
    SRC, LOG_FILE, VOTE_LOG, PAPER_LOG, GATE_FILE, TERMINAL,
    CREDS, MT5_AVAILABLE, PAPER_TRADE, log,
)
from quant_nanggroe.hedge_fund.utils.connection import connect, ensure_terminal
from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5
from quant_nanggroe.hedge_fund.utils.indicators import calc_atr

__all__ = [
    "_HF_DIR", "_QNA_DIR", "_DATA_DIR",
    "SRC", "LOG_FILE", "VOTE_LOG", "PAPER_LOG", "GATE_FILE", "TERMINAL",
    "CREDS", "MT5_AVAILABLE", "PAPER_TRADE", "log",
    "connect", "ensure_terminal",
    "get_historical_mt5", "calc_atr",
]
