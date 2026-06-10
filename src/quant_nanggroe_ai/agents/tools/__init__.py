"""
Agent Tools Package — Unified Tool Interface for Quant-Nanggroe-AI
===================================================================
All agent-facing tools are exported from this package.

Tools:
    MarketDataTool        — OHLCV data, current prices, batch fetch
    TechnicalAnalysisTool — Full indicator suite, SMC, trend, S/R
    SentimentTool         — News sentiment, event classification
    ExecutionTool         — Order routing, paper/live trading
    BacktestTool          — Strategy backtesting and results

Example::

    from quant_nanggroe_ai.agents.tools import (
        MarketDataTool,
        TechnicalAnalysisTool,
        SentimentTool,
        ExecutionTool,
        BacktestTool,
    )

    # Initialize with shared market data source
    mdt = MarketDataTool(cache_ttl=60)
    tat = TechnicalAnalysisTool(market_data_tool=mdt)
    st  = SentimentTool()
    et  = ExecutionTool(market_data_tool=mdt)
    bt  = BacktestTool(market_data_tool=mdt)
"""

from quant_nanggroe_ai.agents.tools.execution import ExecutionTool
from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool
from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool

# BacktestTool depends on backtest engine which may have unmet dependencies
try:
    from quant_nanggroe_ai.agents.tools.backtest import BacktestTool
except ImportError:
    BacktestTool = None  # type: ignore[assignment,misc]

__all__ = [
    "BacktestTool",
    "ExecutionTool",
    "MarketDataTool",
    "SentimentTool",
    "TechnicalAnalysisTool",
]
