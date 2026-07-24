"""Provider registry — lists of all signal providers used by the aggregator.

Defines:
- CORE_PROVIDERS: Built-in strategies (10 providers: SMA, Wyckoff, AIHF, Hidden,
  TradingAgents, AITrader, LangAlpha, Kronos, AIMM, PyPortfolioOpt)
- QNA_EVOLVED_PROVIDERS: MUE-X auto-generated strategy wrappers (~240 providers)
- ALL_PROVIDERS: Union of both lists

Related sections in hedge_fund.py: lines 5850-6108
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    CORE_PROVIDERS,
    QNA_EVOLVED_PROVIDERS,
    ALL_PROVIDERS,
)
