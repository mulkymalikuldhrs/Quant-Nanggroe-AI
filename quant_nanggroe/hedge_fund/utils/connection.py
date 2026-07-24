"""MT5 terminal connection and initialization utilities.

Provides:
- connect() — Initialize MT5 with timeout guard
- ensure_terminal() — Kill existing terminal, restart with credentials
- _MT5Mock — Mock class for paper trading when MT5 is unavailable

Related sections in hedge_fund.py: lines 26-44 (mock), 70-83 (connect/ensure_terminal)
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    connect, ensure_terminal, mt5, MT5_AVAILABLE,
)
