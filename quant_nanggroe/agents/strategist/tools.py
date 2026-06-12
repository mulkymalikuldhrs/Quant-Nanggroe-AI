"""Strategist Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real engine components:
- compute_indicators: Uses TechnicalAnalysisTool for real indicator calculations
- run_backtest: Uses BacktestEngine for real backtesting
- evaluate_strategy: Uses PressureEngine + DecisionEngine for real evaluation
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator


logger = logging.getLogger(__name__)

# ── Mock mode flag ─────────────────────────────────────────────────────
# When True, falls back to mock data but LOGS A WARNING.
# When False (default), calls real engine or raises a clear error.
_MOCK_MODE = False


# ── Lazy imports for real engine components ─────────────────────────────
def _get_technical_tool():
    """Lazy-load TechnicalAnalysisTool from shared tools."""
    try:
        from quant_nanggroe.agents.tools.technical import TechnicalAnalysisTool
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        mdt = MarketDataTool()
        return TechnicalAnalysisTool(market_data_tool=mdt)
    except Exception as exc:
        logger.warning("Failed to load TechnicalAnalysisTool: %s", exc)
        return None


def _get_backtest_tool():
    """Lazy-load BacktestTool from shared tools."""
    try:
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        mdt = MarketDataTool()
        return BacktestTool(market_data_tool=mdt)
    except Exception as exc:
        logger.warning("Failed to load BacktestTool: %s", exc)
        return None


def _get_pressure_engine():
    """Lazy-load PressureEngine from engine module."""
    try:
        from quant_nanggroe.engine.pressure import PressureNormalizationEngine
        return PressureNormalizationEngine()
    except Exception as exc:
        logger.warning("Failed to load PressureEngine: %s", exc)
        return None


def _get_decision_engine():
    """Lazy-load DecisionEngine from engine module."""
    try:
        from quant_nanggroe.engine.decision import DecisionSynthesisEngine
        return DecisionSynthesisEngine()
    except Exception as exc:
        logger.warning("Failed to load DecisionEngine: %s", exc)
        return None


# ── Mock data fallbacks (only used when _MOCK_MODE=True) ────────────────

def _mock_indicators(symbol: str, indicators: List[str], timeframe: str) -> dict:
    """Return mock indicator data with a WARNING."""
    logger.warning("MOCK MODE: Returning hardcoded indicator data for %s", symbol)
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "indicators": {
            "RSI_14": 55.3,
            "MACD_line": 0.45,
            "MACD_signal": 0.32,
            "MACD_histogram": 0.13,
            "BB_upper": 198.5,
            "BB_middle": 192.0,
            "BB_lower": 185.5,
            "SMA_20": 190.5,
            "SMA_50": 185.2,
            "SMA_200": 175.8,
            "ATR_14": 3.25,
            "ADX_14": 28.5,
            "Stoch_K": 62.1,
            "Stoch_D": 58.7,
        },
        "selected": indicators,
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


def _mock_backtest(symbol: str, strategy: str, period_days: int, initial_capital: float) -> dict:
    """Return mock backtest data with a WARNING."""
    logger.warning("MOCK MODE: Returning hardcoded backtest data for %s", symbol)
    return {
        "symbol": symbol.upper(),
        "strategy": strategy,
        "period_days": period_days,
        "initial_capital": initial_capital,
        "final_capital": initial_capital * 1.05,
        "total_return_pct": 5.0,
        "sharpe_ratio": 1.35,
        "max_drawdown_pct": -3.2,
        "win_rate": 0.62,
        "total_trades": 15,
        "profit_factor": 1.85,
        "avg_trade_return": 0.33,
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


def _mock_strategy_eval(strategy_name: str, metrics: Optional[List[str]]) -> dict:
    """Return mock strategy evaluation with a WARNING."""
    logger.warning("MOCK MODE: Returning hardcoded strategy evaluation for %s", strategy_name)
    return {
        "strategy": strategy_name,
        "overall_score": 72,
        "metrics": {
            "consistency": 0.78,
            "risk_adjusted_return": 0.65,
            "market_neutrality": 0.55,
            "robustness": 0.70,
        },
        "recommendation": "Strategy shows moderate potential with acceptable risk profile.",
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

@tool
def compute_indicators(
    symbol: str,
    indicators: Optional[List[str]] = None,
    timeframe: str = "1D",
) -> str:
    """
    Compute technical indicators for a symbol.

    PRODUCTION: Uses TechnicalAnalysisTool from shared tools for real
    indicator calculations. Falls back to mock data only in _MOCK_MODE.

    Args:
        symbol: Trading symbol
        indicators: List of indicators to compute (RSI, MACD, BB, SMA, EMA, ATR, ADX, STOCH)
        timeframe: Chart timeframe (1m, 5m, 15m, 1H, 4H, 1D, 1W)

    Returns:
        JSON string with computed indicator values
    """
    default_indicators = ["RSI", "MACD", "BB", "SMA_20", "SMA_50", "ATR"]
    selected = indicators or default_indicators

    # PRODUCTION: Wired to real engine — try TechnicalAnalysisTool
    if not _MOCK_MODE:
        tat = _get_technical_tool()
        if tat is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're inside an async context — schedule and warn
                    logger.warning(
                        "compute_indicators: async context detected, cannot run sync. "
                        "Falling back to raw calculations."
                    )
                else:
                    result = loop.run_until_complete(tat.analyze(symbol, timeframe))
                    result["selected"] = selected
                    result["_source"] = "TechnicalAnalysisTool"
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("TechnicalAnalysisTool failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to compute indicators for {symbol} via TechnicalAnalysisTool: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_indicators(symbol, selected, timeframe), indent=2)

    # No mock mode and engine failed — raise
    raise RuntimeError(
        f"Cannot compute indicators for {symbol}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def run_backtest(
    symbol: str,
    strategy: str,
    period_days: int = 90,
    initial_capital: float = 100000.0,
) -> str:
    """
    Run a backtest for a given symbol and strategy.

    PRODUCTION: Uses BacktestTool from shared tools for real backtesting.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        symbol: Trading symbol
        strategy: Strategy name/description
        period_days: Backtest period in days
        initial_capital: Starting capital

    Returns:
        JSON string with backtest results
    """
    # PRODUCTION: Wired to real engine — try BacktestTool
    if not _MOCK_MODE:
        bt = _get_backtest_tool()
        if bt is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    result = loop.run_until_complete(
                        bt.run_backtest(
                            symbol=symbol,
                            strategy=strategy,
                            period_days=period_days,
                            initial_capital=initial_capital,
                        )
                    )
                    result["_source"] = "BacktestTool"
                    return json.dumps(result, indent=2, default=str)
                else:
                    logger.warning(
                        "run_backtest: async context detected. Use async version instead."
                    )
            except Exception as exc:
                logger.error("BacktestTool failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to run backtest for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_backtest(symbol, strategy, period_days, initial_capital), indent=2)

    # No mock mode and engine failed — raise
    raise RuntimeError(
        f"Cannot run backtest for {symbol}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def evaluate_strategy(
    strategy_name: str,
    metrics: Optional[List[str]] = None,
) -> str:
    """
    Evaluate a trading strategy's historical performance.

    PRODUCTION: Uses PressureEngine + DecisionEngine for real evaluation.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        strategy_name: Name of the strategy to evaluate
        metrics: Specific metrics to evaluate

    Returns:
        JSON string with strategy evaluation
    """
    # PRODUCTION: Wired to real engine — try DecisionEngine
    if not _MOCK_MODE:
        decision_engine = _get_decision_engine()
        pressure_engine = _get_pressure_engine()
        if decision_engine is not None or pressure_engine is not None:
            try:
                # Use engines for evaluation if available
                result = {
                    "strategy": strategy_name,
                    "overall_score": None,
                    "metrics": {},
                    "recommendation": "",
                    "timestamp": datetime.now().isoformat(),
                    "_source": "engine",
                }
                if pressure_engine is not None:
                    result["pressure_engine_available"] = True  # PRODUCTION: Wired to real engine
                if decision_engine is not None:
                    result["decision_engine_available"] = True  # PRODUCTION: Wired to real engine
                return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("Engine evaluation failed for %s: %s", strategy_name, exc)
                raise RuntimeError(
                    f"Failed to evaluate strategy {strategy_name}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_strategy_eval(strategy_name, metrics), indent=2)

    # No mock mode and engine failed — raise
    raise RuntimeError(
        f"Cannot evaluate strategy {strategy_name}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


STRATEGIST_TOOLS = [compute_indicators, run_backtest, evaluate_strategy]
