"""
Agent Tools Package — Unified Tool Interface for Quant Nanggroe AI
===================================================================
All agent-facing tools are exported from this package.

Core Tools:
    MarketDataTool        — OHLCV data, current prices, batch fetch
    TechnicalAnalysisTool — Full indicator suite, SMC, trend, S/R
    SentimentTool         — News sentiment, event classification
    ExecutionTool         — Order routing, paper/live trading
    BacktestTool          — Strategy backtesting and results

Advanced Tools (NEW):
    FlowTool              — Whale flow & COT positioning analysis
    GeopoliticalTool      — Geopolitical risk analysis (WorldOrder, GrandChessboard, PrisonersOfGeography)
    IntermarketTool       — Cross-market correlation & sector rotation
    ScreenerTool          — 12-component screening engine
    CompetitionTool       — Agent competition, leaderboard & A/B testing
    ForecastTool          — Multi-day market forecast synthesis
    EmotionalTool         — Emotional intelligence & gamified discipline
    SkillTool             — Skill system, DCF valuation & marketplace

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
    analyze_flow          — Whale flow & COT positioning analysis
    analyze_geopolitical  — Geopolitical risk analysis
    analyze_intermarket   — Intermarket correlation analysis
    screen_symbol         — 12-component screening
    get_leaderboard       — Agent competition leaderboard
    forecast_symbol       — Multi-timeframe market forecast
    check_emotional_state — Emotional state & discipline check
    run_dcf_valuation     — DCF valuation analysis

Example::

    from quant_nanggroe.agents.tools import (
        MarketDataTool,
        TechnicalAnalysisTool,
        SentimentTool,
        ExecutionTool,
        BacktestTool,
        FlowTool,
        GeopoliticalTool,
        IntermarketTool,
        ScreenerTool,
        CompetitionTool,
        ForecastTool,
        EmotionalTool,
        SkillTool,
    )

    # Initialize with shared market data source
    mdt = MarketDataTool(cache_ttl=60)
    tat = TechnicalAnalysisTool(market_data_tool=mdt)
    st  = SentimentTool()
    et  = ExecutionTool(market_data_tool=mdt)
    bt  = BacktestTool(market_data_tool=mdt)
"""

from quant_nanggroe.agents.tools.execution import (
    ExecutionTool,
    cancel_order,
    execute_order,
    get_account_summary,
    get_open_orders,
    get_order_status,
)
from quant_nanggroe.agents.tools.market_data import (
    MarketDataTool,
    get_current_price,
    get_multiple_prices,
    get_ohlcv,
)
from quant_nanggroe.agents.tools.sentiment import (
    SentimentTool,
    analyze_sentiment,
)
from quant_nanggroe.agents.tools.technical import (
    TechnicalAnalysisTool,
    analyze_technical,
)

# BacktestTool depends on backtest engine which may have unmet dependencies
try:
    from quant_nanggroe.agents.tools.backtest import (
        BacktestTool,
        get_backtest_results,
        list_backtests,
        run_backtest,
    )
except ImportError:
    BacktestTool = None  # type: ignore[assignment,misc]
    run_backtest = None  # type: ignore[assignment,misc]
    get_backtest_results = None  # type: ignore[assignment,misc]
    list_backtests = None  # type: ignore[assignment,misc]

# New advanced tools
from quant_nanggroe.agents.tools.competition_tool import (
    CompetitionTool,
    get_leaderboard,
)
from quant_nanggroe.agents.tools.emotional_tool import (
    EmotionalTool,
    check_emotional_state,
)
from quant_nanggroe.agents.tools.flow_tool import (
    FlowTool,
    analyze_flow,
)
from quant_nanggroe.agents.tools.forecast_tool import (
    ForecastTool,
    forecast_symbol,
)
from quant_nanggroe.agents.tools.geopolitical_tool import (
    GeopoliticalTool,
    analyze_geopolitical,
)
from quant_nanggroe.agents.tools.intermarket_tool import (
    IntermarketTool,
    analyze_intermarket,
)
from quant_nanggroe.agents.tools.screener_tool import (
    ScreenerTool,
    screen_symbol,
)
from quant_nanggroe.agents.tools.skill_tool import (
    SkillTool,
    run_dcf_valuation,
)

__all__ = [
    # Core class-based tools
    "MarketDataTool",
    "TechnicalAnalysisTool",
    "SentimentTool",
    "ExecutionTool",
    "BacktestTool",
    # Advanced class-based tools
    "FlowTool",
    "GeopoliticalTool",
    "IntermarketTool",
    "ScreenerTool",
    "CompetitionTool",
    "ForecastTool",
    "EmotionalTool",
    "SkillTool",
    # Core LangChain @tool functions
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
    # Advanced LangChain @tool functions
    "analyze_flow",
    "analyze_geopolitical",
    "analyze_intermarket",
    "screen_symbol",
    "get_leaderboard",
    "forecast_symbol",
    "check_emotional_state",
    "run_dcf_valuation",
]
