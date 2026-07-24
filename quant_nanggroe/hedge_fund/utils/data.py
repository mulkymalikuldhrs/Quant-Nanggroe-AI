"""Historical market data fetching with mock fallback.

Provides:
- get_historical_mt5() — Fetch OHLCV from MT5; falls back to synthetic mock data
  in paper trading mode. Used by every signal provider for technical analysis.

Related sections in hedge_fund.py: lines 289-335
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import get_historical_mt5
