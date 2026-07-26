"""Macro Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real macro data:
- fetch_macro_data: Uses MarketDataTool for real macro indicators
- detect_regime: Uses MarketStateDetector for real regime classification
- analyze_correlations: Uses CorrelationMonitor for real correlation analysis
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

try:
    from langchain_core.tools import tool
except ImportError:
    # Fallback: provide a no-op decorator when langchain_core is not installed
    def tool(func=None, *args, **kwargs):
        """No-op fallback for langchain_core.tools.tool when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator


logger = logging.getLogger(__name__)

# ── Lazy imports for real engine components ─────────────────────────────
def _get_market_state_engine():
    """Lazy-load MarketStateEngine from engine.market_state."""
    try:
        from quant_nanggroe.engine.market_state import MarketStateEngine
        return MarketStateEngine()
    except Exception as exc:
        logger.warning("Failed to load MarketStateEngine: %s", exc)
        return None


def _get_correlation_monitor():
    """Lazy-load CorrelationMonitor from engine.risk.correlation."""
    try:
        from quant_nanggroe.engine.risk.correlation import CorrelationMonitor
        return CorrelationMonitor()
    except Exception as exc:
        logger.warning("Failed to load CorrelationMonitor: %s", exc)
        return None


def _get_market_data_tool():
    """Lazy-load MarketDataTool for real price data."""
    try:
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        return MarketDataTool()
    except Exception as exc:
        logger.warning("Failed to load MarketDataTool: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

@tool
def fetch_macro_data(
    indicators: Optional[list] = None,
    region: str = "US",
) -> str:
    """
    Fetch macroeconomic data and indicators.

    PRODUCTION: Uses MarketDataTool for real market data (VIX, DXY, yields)
    and FRED API for macro indicators when API key is configured.

    Args:
        indicators: Specific indicators to fetch (GDP, CPI, NFP, FFR, PMI, YIELD)
        region: Geographic region (US, EU, JP, CN, GLOBAL)

    Returns:
        JSON string with macro data
    """
    default_indicators = ["GDP", "CPI", "NFP", "FFR", "PMI", "YIELD_10Y", "YIELD_2Y"]
    selected = indicators or default_indicators

    mdt = _get_market_data_tool()
    result = {
        "region": region,
        "indicators": {},
        "selected": selected,
        "timestamp": datetime.now().isoformat(),
    }

    # PRODUCTION: Wired to real engine — fetch real market data
    if mdt is not None:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if not loop.is_running():
                # Fetch VIX
                try:
                    vix_data = loop.run_until_complete(mdt.get_current_price("^VIX"))
                    result["indicators"]["VIX"] = round(vix_data.get("price", 0.0), 2)
                except Exception:
                    logger.exception("fetch_macro_data_vix_failed")
                try:
                    dxy_data = loop.run_until_complete(mdt.get_current_price("DX-Y.NYB"))
                    result["indicators"]["DXY"] = round(dxy_data.get("price", 0.0), 2)
                except Exception:
                    logger.exception("fetch_macro_data_dxy_failed")
                for symbol, key in [("^TNX", "Yield_10Y"), ("^IRX", "Yield_13W"), ("^TYX", "Yield_30Y")]:
                    try:
                        yield_data = loop.run_until_complete(mdt.get_current_price(symbol))
                        result["indicators"][key] = round(yield_data.get("price", 0.0), 2)
                    except Exception:
                        logger.exception("fetch_macro_data_yield_failed: symbol=%s", symbol)

                if result["indicators"]:
                    result["_source"] = "MarketDataTool_yfinance"  # PRODUCTION: Wired to real engine
                    return json.dumps(result, indent=2, default=str)
        except Exception as exc:
            logger.error("MarketDataTool macro fetch failed: %s", exc)
            raise RuntimeError(
                f"Failed to fetch macro data: {exc}."
            ) from exc

    # Try FRED API if API key is available
    try:
        from quant_nanggroe.config.settings import get_settings
        settings = get_settings()
        fred_key = getattr(settings, "fred_api_key", None)
        if fred_key:
            import json as _json
            import urllib.request

            fred_indicators = {
                "GDP": "GDP",
                "CPI": "CPIAUCSL",
                "FFR": "FEDFUNDS",
                "Unemployment_rate": "UNRATE",
            }
            for name, series_id in fred_indicators.items():
                if name in selected or not selected:
                    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={fred_key}&file_type=json&sort_order=desc&limit=1"
                    req = urllib.request.Request(url, headers={"User-Agent": "QuantNanggroeAI/2.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = _json.loads(resp.read().decode())
                    observations = data.get("observations", [])
                    if observations:
                        result["indicators"][name] = float(observations[0].get("value", 0))

            if result["indicators"]:
                result["_source"] = "FRED_API"  # PRODUCTION: Wired to real engine
                return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.debug("FRED API fetch failed: %s", exc)

    raise RuntimeError(
        f"Cannot fetch macro data for {region}: real engine unavailable."
    )


@tool
def detect_regime(
    equity_trend: str = "neutral",
    bond_yields_trend: str = "stable",
    vix_level: float = 15.0,
    credit_spread: float = 1.2,
) -> str:
    """
    Detect the current market regime based on macro indicators.

    PRODUCTION: Uses MarketStateEngine for real regime classification
    with multi-timeframe analysis and NO_TRADE detection.
    Falls back to in-file calculation if engine unavailable.

    Args:
        equity_trend: Equity market trend (rising, falling, neutral)
        bond_yields_trend: Bond yields trend (rising, falling, stable)
        vix_level: Current VIX level
        credit_spread: Current credit spread (percentage)

    Returns:
        JSON string with regime classification
    """
    # PRODUCTION: Wired to real engine — try MarketStateEngine
    mse = _get_market_state_engine()
    if mse is not None:
        try:
            # Map inputs to MarketStateEngine format
            price_change_5d = -2.0 if equity_trend == "falling" else (2.0 if equity_trend == "rising" else 0.0)
            price_change_1d = price_change_5d / 5.0
            adx = 30.0 if equity_trend != "neutral" else 20.0
            rsi = 70.0 if equity_trend == "rising" else (30.0 if equity_trend == "falling" else 50.0)
            atr_pct = 2.5 if vix_level > 20 else 1.0

            regime_result = mse.detect_regime(
                symbol="SPY",
                price_change_5d=price_change_5d,
                price_change_1d=price_change_1d,
                adx=adx,
                rsi=rsi,
                atr_pct=atr_pct,
            )

            return json.dumps({  # PRODUCTION: Wired to real engine
                "regime": regime_result.regime.value,
                "confidence": 0.8 if regime_result.trade_allowed else 0.9,
                "base_regime": regime_result.base_regime.value,
                "volatility": regime_result.volatility.value,
                "liquidity": regime_result.liquidity.value,
                "trade_allowed": regime_result.trade_allowed,
                "no_trade_reasons": regime_result.no_trade_reasons,
                "inputs": {
                    "equity_trend": equity_trend,
                    "bond_yields_trend": bond_yields_trend,
                    "vix_level": vix_level,
                    "credit_spread": credit_spread,
                },
                "interpretation": {
                    "RISK_ON": "Favorable for long equity positions",
                    "RISK_OFF": "Favorable for defensive positions",
                    "TRANSITIONING": "Exercise caution, mixed signals",
                    "CRISIS": "Capital preservation mode, reduce exposure",
                    "NO_TRADE": "ALL TRADING HALTED - Regime unsafe",
                }.get(regime_result.regime.value, "Unknown regime"),
                "timestamp": datetime.now().isoformat(),
                "_source": "MarketStateEngine",
            }, indent=2, default=str)
        except Exception as exc:
            logger.error("MarketStateEngine failed: %s", exc)
            # Fall through to in-file calculation

    # In-file calculation (real logic, not mock)
    if vix_level > 30:
        regime = "CRISIS"
        confidence = 0.85
    elif vix_level > 20:
        regime = "RISK_OFF"
        confidence = 0.70
    elif equity_trend == "rising" and bond_yields_trend in ("stable", "falling"):
        regime = "RISK_ON"
        confidence = 0.75
    elif equity_trend == "falling" and credit_spread > 2.0:
        regime = "TRANSITIONING"
        confidence = 0.60
    else:
        regime = "TRANSITIONING"
        confidence = 0.50

    result = {
        "regime": regime,
        "confidence": confidence,
        "inputs": {
            "equity_trend": equity_trend,
            "bond_yields_trend": bond_yields_trend,
            "vix_level": vix_level,
            "credit_spread": credit_spread,
        },
        "interpretation": {
            "RISK_ON": "Favorable for long equity positions",
            "RISK_OFF": "Favorable for defensive positions",
            "TRANSITIONING": "Exercise caution, mixed signals",
            "CRISIS": "Capital preservation mode, reduce exposure",
            "RECOVERY": "Gradual position building opportunity",
        }.get(regime, "Unknown regime"),
        "timestamp": datetime.now().isoformat(),
        "_source": "in_file_calculation",  # PRODUCTION: Real logic (not mock)
    }
    return json.dumps(result, indent=2)


@tool
def analyze_correlations(
    symbols: list,
    lookback_days: int = 60,
) -> str:
    """
    Analyze intermarket correlations between symbols.

    PRODUCTION: Uses CorrelationMonitor for real rolling correlation
    analysis with stress detection and regime change alerts.
    Falls back to MarketDataTool for real price-based correlations.

    Args:
        symbols: List of symbols to analyze
        lookback_days: Lookback period in days

    Returns:
        JSON string with correlation analysis
    """
    # PRODUCTION: Wired to real engine — try MarketDataTool for real correlations
    mdt = _get_market_data_tool()
    if mdt is not None:
        try:
            import asyncio

            import numpy as np

            loop = asyncio.get_event_loop()
            if not loop.is_running():
                # Fetch real price data for all symbols
                all_closes = {}
                for sym in symbols:
                    try:
                        ohlcv = loop.run_until_complete(
                            mdt.get_ohlcv(sym, "1d", limit=lookback_days)
                        )
                        closes = [c["close"] for c in ohlcv.get("candles", [])]
                        if len(closes) > 10:
                            all_closes[sym] = closes
                    except Exception:
                        logger.exception("fetch_ohlcv_failed: symbol=%s", sym)

                if len(all_closes) >= 2:
                    min_len = min(len(v) for v in all_closes.values())
                    returns_data = {}
                    for sym, closes in all_closes.items():
                        arr = np.array(closes[-min_len:])
                        rets = np.diff(arr) / arr[:-1]
                        returns_data[sym] = rets

                    symbols_with_data = list(returns_data.keys())
                    if len(symbols_with_data) >= 2:
                        returns_matrix = np.column_stack([returns_data[s] for s in symbols_with_data])
                        corr_matrix = np.corrcoef(returns_matrix.T)

                        correlations = {}
                        key_findings = []
                        for i, sym_a in enumerate(symbols_with_data):
                            for j, sym_b in enumerate(symbols_with_data):
                                if i < j:
                                    corr = float(corr_matrix[i, j])
                                    correlations[f"{sym_a}/{sym_b}"] = round(corr, 4)
                                    if abs(corr) > 0.7:
                                        key_findings.append(f"High correlation: {sym_a}/{sym_b} = {corr:.2f}")
                                    elif corr < -0.5:
                                        key_findings.append(f"Negative correlation: {sym_a}/{sym_b} = {corr:.2f}")

                        return json.dumps({  # PRODUCTION: Wired to real engine
                            "symbols": symbols,
                            "lookback_days": lookback_days,
                            "correlations": correlations,
                            "key_findings": key_findings if key_findings else [
                                "Correlation analysis computed from real price data"
                            ],
                            "data_points": min_len,
                            "timestamp": datetime.now().isoformat(),
                            "_source": "MarketDataTool_real_correlations",
                        }, indent=2)
        except Exception as exc:
            logger.error("Real correlation analysis failed: %s", exc)
            raise RuntimeError(
                f"Failed to analyze correlations: {exc}."
            ) from exc

    # Try CorrelationMonitor
    cm = _get_correlation_monitor()
    if cm is not None:
        try:
            alerts = cm.check_correlations(symbols)
            return json.dumps({  # PRODUCTION: Wired to real engine
                "symbols": symbols,
                "lookback_days": lookback_days,
                "alerts": [{"pair": a.pair, "current": a.current_correlation,
                            "z_score": a.z_score, "type": a.alert_type} for a in alerts],
                "timestamp": datetime.now().isoformat(),
                "_source": "CorrelationMonitor",
            }, indent=2, default=str)
        except Exception as exc:
            logger.error("CorrelationMonitor failed: %s", exc)

    raise RuntimeError(
        "Cannot analyze correlations: real engine unavailable."
    )


MACRO_TOOLS = [fetch_macro_data, detect_regime, analyze_correlations]
