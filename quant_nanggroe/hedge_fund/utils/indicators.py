"""Technical analysis indicators.

Provides:
- calc_atr() — Average True Range for a given symbol/period/timeframe.
  Used by execute() for dynamic stop-loss / take-profit distance calculation.

Related sections in hedge_fund.py: lines 85-94
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import calc_atr
