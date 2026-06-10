"""
Agent Tools Package — Unified Tool Interface for Quant Nanggroe AI
===================================================================
All agent-facing tools are exported from this package.

Tools:
    MarketDataTool        — OHLCV data, current prices, batch fetch
    TechnicalAnalysisTool — Full indicator suite, SMC, trend, S/R
    SentimentTool         — News sentiment, event classification
    ExecutionTool         — Order routing, paper/live trading
    BacktestTool          — Strategy backtesting and results

LangChain @tool functions:
    get_ohlcv             — Fetch OHLCV candle data
    get_current_price     — Get latest price for a symbol
    get_multiple_prices   — Batch price fetch
    analyze_technical     — Full technical analysis
    analyze_sentiment     — News sentiment analysis
    execute_order         — Place a trade order
    cancel_order          — Cancel an existing order
    get_order_status      — Query order status
    run_backtest          — Run a strategy backtest
    get_backtest_results  — Retrieve stored backtest results

Example::

    from quant_nanggroe.agents.tools import (
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

from quant_nanggroe.agents.tools.market_data import (
    MarketDataTool,
    get_ohlcv,
    get_current_price,
    get_multiple_prices,
)
from quant_nanggroe.agents.tools.technical import (
    TechnicalAnalysisTool,
    analyze_technical,
)
from quant_nanggroe.agents.tools.sentiment import (
    SentimentTool,
    analyze_sentiment,
)
from quant_nanggroe.agents.tools.execution import (
    ExecutionTool,
    execute_order,
    cancel_order,
    get_order_status,
    get_open_orders,
    get_account_summary,
)

# BacktestTool depends on backtest engine which may have unmet dependencies
try:
    from quant_nanggroe.agents.tools.backtest import (
        BacktestTool,
        run_backtest,
        get_backtest_results,
        list_backtests,
    )
except ImportError:
    BacktestTool = None  # type: ignore[assignment,misc]
    run_backtest = None  # type: ignore[assignment,misc]
    get_backtest_results = None  # type: ignore[assignment,misc]
    list_backtests = None  # type: ignore[assignment,misc]

__all__ = [
    # Class-based tools
    "MarketDataTool",
    "TechnicalAnalysisTool",
    "SentimentTool",
    "ExecutionTool",
    "BacktestTool",
    # LangChain @tool functions
    "get_ohlcv",
    "get_current_price",
    "get_multiple_prices",
    "analyze_technical",
    "analyze_sentiment",
    "execute_order",
    "cancel_order",
    "get_order_status",
    "get_open_orders",
    "get_account_summary",
    "run_backtest",
    "get_backtest_results",
    "list_backtests",
]
