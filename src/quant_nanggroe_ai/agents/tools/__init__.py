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
    FileOpsTool           — File upload, download, delete, list (from ai-manus)
    TradingPlanTool       — Trade planning, journaling, discipline (from Trading-Plan-AI)
    FinancialDataTool     — Stock prices, financials, screening, news (from ai-financial-agent)

Example::

    from quant_nanggroe_ai.agents.tools import (
        MarketDataTool,
        TechnicalAnalysisTool,
        SentimentTool,
        ExecutionTool,
        BacktestTool,
        FileOpsTool,
        TradingPlanTool,
        FinancialDataTool,
    )

    # Initialize with shared market data source
    mdt = MarketDataTool(cache_ttl=60)
    tat = TechnicalAnalysisTool(market_data_tool=mdt)
    st  = SentimentTool()
    et  = ExecutionTool(market_data_tool=mdt)
    bt  = BacktestTool(market_data_tool=mdt)
    fot = FileOpsTool()
    tpt = TradingPlanTool()  # from Trading-Plan-AI-Interactive
    fdt = FinancialDataTool(api_key="...")  # from ai-financial-agent
"""

from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool
from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool
from quant_nanggroe_ai.agents.tools.execution import ExecutionTool

# BacktestTool depends on backtest engine which may have unmet dependencies
try:
    from quant_nanggroe_ai.agents.tools.backtest import BacktestTool
except ImportError:
    BacktestTool = None  # type: ignore[assignment,misc]

# FileOpsTool — merged from ai-manus feature/agent-file-oprate branch
from quant_nanggroe_ai.agents.tools.file_ops import FileOpsTool

# TradingPlanTool — merged from Trading-Plan-AI-Interactive v11.1.4
from quant_nanggroe_ai.agents.tools.trading_plan import TradingPlanTool

# FinancialDataTool — merged from ai-financial-agent (C2-CORE, Task 8-c)
from quant_nanggroe_ai.agents.tools.financial_data import FinancialDataTool

__all__ = [
    "MarketDataTool",
    "TechnicalAnalysisTool",
    "SentimentTool",
    "ExecutionTool",
    "BacktestTool",
    "FileOpsTool",
    "TradingPlanTool",
    "FinancialDataTool",
]
