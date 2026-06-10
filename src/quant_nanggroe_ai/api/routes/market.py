"""
Market Data Routes — OHLCV, prices, regime detection
======================================================
Uses shared MarketStateEngine singleton from app.state so that
regime history and state persist across requests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Request

from quant_nanggroe_ai.api.schemas import (
    OHLCVResponse,
    OHLCVCandle,
    PriceResponse,
    MarketRegimeRequest,
    MarketRegimeResponse,
)
from quant_nanggroe_ai.services import get_market_engine

logger = structlog.get_logger(__name__)

router = APIRouter()

# In-memory price cache (production would use database / real data feed)
_price_cache: dict[str, dict[str, Any]] = {}
_ohlcv_cache: dict[str, list[dict[str, Any]]] = {}


# ══════════════════════════════════════════════════════════════════════
# OHLCV Data
# ══════════════════════════════════════════════════════════════════════

@router.get("/ohlcv/{symbol}", response_model=OHLCVResponse)
async def get_ohlcv(symbol: str, timeframe: str = "1d", limit: int = 100) -> OHLCVResponse:
    """
    Get OHLCV data for a symbol.

    Returns historical candle data. In production, this queries the
    database or external data provider. Returns cached data or empty
    list if no data is available.
    """
    symbol = symbol.upper()

    # Try to serve from cache
    cache_key = f"{symbol}_{timeframe}"
    cached = _ohlcv_cache.get(cache_key, [])

    candles = [
        OHLCVCandle(
            timestamp=datetime.fromisoformat(c["timestamp"]),
            open=c["open"],
            high=c["high"],
            low=c["low"],
            close=c["close"],
            volume=c["volume"],
        )
        for c in cached[-limit:]
    ]

    # If no cached data, try fetching from market data tool
    if not candles:
        try:
            from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

            tool = MarketDataTool()
            raw_data = tool.get_ohlcv(symbol, timeframe)

            if raw_data:
                candles = [
                    OHLCVCandle(
                        timestamp=datetime.fromisoformat(c.get("timestamp", datetime.now().isoformat())),
                        open=c.get("open", 0.0),
                        high=c.get("high", 0.0),
                        low=c.get("low", 0.0),
                        close=c.get("close", 0.0),
                        volume=c.get("volume", 0.0),
                    )
                    for c in raw_data[-limit:]
                ]
        except Exception as exc:
            logger.warning("ohlcv_fetch_failed", symbol=symbol, error=str(exc))

    return OHLCVResponse(
        symbol=symbol,
        timeframe=timeframe,
        data=candles,
        count=len(candles),
    )


# ══════════════════════════════════════════════════════════════════════
# Latest Price
# ══════════════════════════════════════════════════════════════════════

@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_latest_price(symbol: str) -> PriceResponse:
    """
    Get the latest price for a symbol.

    Tries the market data tool first, then falls back to cached price.
    """
    symbol = symbol.upper()

    # Try market data tool
    try:
        from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

        tool = MarketDataTool()
        price = tool.get_current_price(symbol)

        if price is not None:
            _price_cache[symbol] = {"price": price, "timestamp": datetime.now().isoformat()}
            return PriceResponse(symbol=symbol, price=price)
    except Exception as exc:
        logger.warning("price_fetch_failed", symbol=symbol, error=str(exc))

    # Fallback to cache
    cached = _price_cache.get(symbol)
    if cached:
        return PriceResponse(
            symbol=symbol,
            price=cached["price"],
            timestamp=datetime.fromisoformat(cached["timestamp"]),
        )

    return PriceResponse(symbol=symbol, price=None)


# ══════════════════════════════════════════════════════════════════════
# Market Regime Detection
# ══════════════════════════════════════════════════════════════════════

@router.post("/regime/{symbol}", response_model=MarketRegimeResponse)
async def detect_market_regime(
    request: Request,
    symbol: str,
    body: MarketRegimeRequest | None = None,
) -> MarketRegimeResponse:
    """
    Detect current market regime for a symbol.

    Uses the shared MarketStateEngine instance so that regime history
    is maintained across requests. Accepts optional technical indicator
    inputs; if not provided, attempts to compute them from available data.
    """
    engine = get_market_engine(request.app)
    symbol = symbol.upper()

    # Use provided inputs or defaults
    if body is None:
        body = MarketRegimeRequest(symbol=symbol)

    # If no explicit inputs provided, try to compute from market data
    if body.adx == 20.0 and body.rsi == 50.0 and body.atr_pct == 1.0:
        try:
            from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool

            tech_tool = TechnicalAnalysisTool()
            tech_analysis = tech_tool.analyze(symbol, "1d")

            result = engine.detect_regime(
                symbol=symbol,
                price_change_5d=tech_analysis.get("price_change_5d", 0.0),
                price_change_1d=tech_analysis.get("price_change_1d", 0.0),
                adx=tech_analysis.get("adx", 20.0),
                rsi=tech_analysis.get("rsi_14", 50.0),
                atr_pct=tech_analysis.get("atr_pct", 1.0),
                volume_ratio=tech_analysis.get("volume_ratio", 1.0),
                ema_trend=tech_analysis.get("ema_trend", "neutral"),
            )
        except Exception as exc:
            logger.warning("regime_auto_detect_failed", symbol=symbol, error=str(exc))
            result = engine.detect_regime(symbol=symbol)
    else:
        result = engine.detect_regime(
            symbol=symbol,
            price_change_5d=body.price_change_5d,
            price_change_1d=body.price_change_1d,
            adx=body.adx,
            rsi=body.rsi,
            atr_pct=body.atr_pct,
            volume_ratio=body.volume_ratio,
            ema_trend=body.ema_trend,
        )

    logger.info(
        "regime_detected",
        symbol=symbol,
        regime=result.regime.value,
        trade_allowed=result.trade_allowed,
    )

    return MarketRegimeResponse(
        symbol=result.symbol,
        regime=result.regime.value,
        base_regime=result.base_regime.value,
        volatility=result.volatility.value,
        liquidity=result.liquidity.value,
        no_trade_reasons=result.no_trade_reasons,
        trade_allowed=result.trade_allowed,
        inputs=result.inputs,
        timestamp=result.timestamp,
    )


@router.get("/regime/{symbol}")
async def get_market_regime(request: Request, symbol: str):
    """
    Get the most recently detected market regime for a symbol.

    Returns cached regime from the shared MarketStateEngine.
    """
    engine = get_market_engine(request.app)
    symbol = symbol.upper()

    # Check if we have a recent regime for this symbol
    recent = None
    for entry in reversed(engine.regime_history):
        if entry.symbol == symbol:
            recent = entry
            break

    if recent:
        return MarketRegimeResponse(
            symbol=recent.symbol,
            regime=recent.regime.value,
            base_regime=recent.base_regime.value,
            volatility=recent.volatility.value,
            liquidity=recent.liquidity.value,
            no_trade_reasons=recent.no_trade_reasons,
            trade_allowed=recent.trade_allowed,
            inputs=recent.inputs,
            timestamp=recent.timestamp,
        ).model_dump()

    # No cached regime — detect fresh
    result = engine.detect_regime(symbol=symbol)
    return MarketRegimeResponse(
        symbol=result.symbol,
        regime=result.regime.value,
        base_regime=result.base_regime.value,
        volatility=result.volatility.value,
        liquidity=result.liquidity.value,
        no_trade_reasons=result.no_trade_reasons,
        trade_allowed=result.trade_allowed,
        inputs=result.inputs,
        timestamp=result.timestamp,
    ).model_dump()


# ══════════════════════════════════════════════════════════════════════
# Technical Analysis
# ══════════════════════════════════════════════════════════════════════

@router.get("/analysis/{symbol}")
async def get_technical_analysis(symbol: str, timeframe: str = "1d"):
    """
    Get full technical analysis for a symbol.

    Runs the MathEngine indicator suite and returns all computed indicators.
    """
    symbol = symbol.upper()

    try:
        from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool

        tool = TechnicalAnalysisTool()
        analysis = tool.analyze(symbol, timeframe)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        logger.error("technical_analysis_failed", symbol=symbol, error=str(exc))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


# ══════════════════════════════════════════════════════════════════════
# Multi-Symbol Regime Scan
# ══════════════════════════════════════════════════════════════════════

@router.get("/scan")
async def scan_market_regimes(request: Request, symbols: str = "EURUSD,GBPUSD,XAUUSD"):
    """
    Scan multiple symbols for their current market regimes.

    Args:
        symbols: Comma-separated list of symbols.

    Returns:
        Dict mapping each symbol to its regime detection result.
    """
    engine = get_market_engine(request.app)
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    results = {}
    for sym in symbol_list:
        result = engine.detect_regime(symbol=sym)
        results[sym] = {
            "regime": result.regime.value,
            "trade_allowed": result.trade_allowed,
            "volatility": result.volatility.value,
        }

    return {
        "symbols": results,
        "timestamp": datetime.now().isoformat(),
    }
