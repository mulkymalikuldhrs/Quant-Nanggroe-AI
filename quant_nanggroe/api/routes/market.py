"""Market data API routes.

Wired to ExchangeManager for real price/OHLCV data and
MarketRegimeDetector for sentiment and pressure analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    MarketRegimeRequest,
    MarketRegimeResponse,
    OHLCVCandle,
    OHLCVRequest,
    OHLCVResponse,
    PriceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared Helpers ─────────────────────────────────────────────────────────


def _get_exchange_manager(http_request: Request):
    """Retrieve or lazily create the ExchangeManager from app state."""
    from quant_nanggroe.exchange.manager import ExchangeManager

    if not hasattr(http_request.app.state, "_services"):
        http_request.app.state._services = {}

    if "exchange_manager" not in http_request.app.state._services:
        http_request.app.state._services["exchange_manager"] = ExchangeManager()
    return http_request.app.state._services["exchange_manager"]


_WATCHLIST = ["BTC", "ETH", "SOL", "SPY", "QQQ"]


async def _try_fetch_price(em, symbol: str) -> float | None:
    """Try to fetch a price, returning None on failure."""
    try:
        ticker = await em.get_ticker(symbol)
        return ticker.last_price
    except Exception:
        return None


async def _try_detect_regime(em, symbol: str) -> dict[str, Any] | None:
    """Try to detect regime for a symbol using ExchangeManager + MarketStateEngine."""
    try:
        candles = await em.get_ohlcv(symbol, limit=50)
        if len(candles) < 10:
            return None
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        from quant_nanggroe.engine.market_state import MarketStateEngine

        engine = MarketStateEngine()
        result = engine.detect(closes=closes, volumes=volumes, symbol=symbol)
        return {
            "regime": result.regime.value if result.regime else "unknown",
            "confidence": getattr(result, "confidence", 0.0),
            "indicators": getattr(result, "indicators", {}),
        }
    except Exception:
        return None


# ── Routes ─────────────────────────────────────────────────────────────────


@router.get("/sentiment")
async def get_market_sentiment(http_request: Request) -> dict[str, Any]:
    """Get overall market sentiment indicator.

    Fetches real prices and regime across a watchlist,
    then computes a composite sentiment score.
    Falls back to a reasoned estimate if exchange not connected.
    """
    em = _get_exchange_manager(http_request)

    # Collect prices and regimes across the watchlist
    signals: dict[str, dict] = {}
    bullish_count = 0
    bearish_count = 0
    total_checked = 0

    for symbol in _WATCHLIST:
        price = await _try_fetch_price(em, symbol)
        regime = await _try_detect_regime(em, symbol)
        if regime:
            total_checked += 1
            r = regime["regime"]
            if r in ("trending_up", "recovery"):
                bullish_count += 1
            elif r in ("trending_down", "crisis"):
                bearish_count += 1
            signals[symbol] = {
                "price": price,
                "regime": r,
                "confidence": regime["confidence"],
            }
        elif price is not None:
            total_checked += 1
            signals[symbol] = {"price": price, "regime": "unknown"}

    # Composite sentiment
    if total_checked > 0:
        net = (bullish_count - bearish_count) / total_checked
        if net > 0.3:
            overall = "bullish"
        elif net < -0.3:
            overall = "bearish"
        else:
            overall = "neutral"
        fear_greed = int(50 + net * 30)  # map [-1,1] to [20,80]
        fear_greed = max(10, min(90, fear_greed))
    else:
        overall = "neutral"
        fear_greed = 50
        signals = {}

    return {
        "overall": overall,
        "fear_greed_index": fear_greed,
        "signals": signals,
        "symbols_analyzed": total_checked,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str, http_request: Request) -> PriceResponse:
    """Get latest price for a symbol.

    Fetches the current ticker from the best available exchange via the
    ExchangeManager failover chain.

    Args:
        symbol: Trading symbol (e.g., AAPL, BTC-USD).
        http_request: HTTP request for accessing app state.

    Returns:
        PriceResponse with current price data.
    """
    try:
        em = _get_exchange_manager(http_request)
        ticker = await em.get_ticker(symbol)
        return PriceResponse(
            symbol=symbol,
            price=ticker.last_price,
            timestamp=ticker.timestamp,
        )
    except Exception as exc:
        logger.warning("get_price_failed symbol=%s error=%s", symbol, exc)
        return PriceResponse(symbol=symbol, price=None)


@router.post("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(request: OHLCVRequest, http_request: Request) -> OHLCVResponse:
    """Get OHLCV candlestick data for a symbol.

    Fetches OHLCV data from the best available exchange via the
    ExchangeManager failover chain and converts the internal OHLCV
    model to the API response schema.

    Args:
        request: OHLCVRequest with symbol, timeframe, and limit.
        http_request: HTTP request for accessing app state.

    Returns:
        OHLCVResponse with candlestick data.
    """
    try:
        from quant_nanggroe.types.market import TimeFrame as TF

        em = _get_exchange_manager(http_request)

        # Map the string timeframe to the internal TimeFrame enum
        tf_map = {
            "1m": TF.M1, "5m": TF.M5, "15m": TF.M15, "30m": TF.M30,
            "1h": TF.H1, "4h": TF.H4, "1d": TF.D1, "1w": TF.W1, "1M": TF.MO1,
        }
        timeframe = tf_map.get(request.timeframe, TF.D1)

        candles = await em.get_ohlcv(
            symbol=request.symbol,
            timeframe=timeframe,
            limit=request.limit,
        )

        data = [
            OHLCVCandle(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in candles
        ]

        return OHLCVResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            data=data,
            count=len(data),
        )
    except Exception as exc:
        logger.warning("get_ohlcv_failed symbol=%s error=%s", request.symbol, exc)
        return OHLCVResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            data=[],
            count=0,
        )


@router.post("/regime", response_model=MarketRegimeResponse)
async def detect_regime(request: MarketRegimeRequest) -> MarketRegimeResponse:
    """Detect market regime for a symbol.

    Uses the MarketStateEngine to classify the current market regime
    based on ADX, RSI, price change, volume, and ATR.

    Args:
        request: MarketRegimeRequest with market indicators.

    Returns:
        MarketRegimeResponse with regime classification.
    """
    from quant_nanggroe.engine.market_state import MarketStateEngine

    engine = MarketStateEngine()
    result = engine.detect_regime(
        symbol=request.symbol,
        price_change_5d=request.price_change_5d,
        price_change_1d=request.price_change_1d,
        adx=request.adx,
        rsi=request.rsi,
        atr_pct=request.atr_pct,
        volume_ratio=request.volume_ratio,
        ema_trend=request.ema_trend,
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


@router.get("/pressure/{symbol}")
async def get_pressure(symbol: str, http_request: Request) -> dict[str, Any]:
    """Get current pressure analysis for a symbol.

    Uses ExchangeManager price data + MarketStateEngine regime
    to compute buy/sell pressure ratio.
    """
    em = _get_exchange_manager(http_request)
    regime = await _try_detect_regime(em, symbol)
    price = await _try_fetch_price(em, symbol)

    if regime:
        r = regime["regime"]
        confidence = regime.get("confidence", 0.5)
        if r == "trending_up":
            buy_pressure = 0.5 + confidence * 0.4
            sell_pressure = 1.0 - buy_pressure
            verdict = "BUY"
        elif r == "trending_down":
            sell_pressure = 0.5 + confidence * 0.4
            buy_pressure = 1.0 - sell_pressure
            verdict = "SELL"
        elif r == "crisis":
            buy_pressure = 0.2
            sell_pressure = 0.8
            verdict = "STRONG_SELL"
        elif r == "recovery":
            buy_pressure = 0.65
            sell_pressure = 0.35
            verdict = "BUY"
        else:
            buy_pressure = 0.5
            sell_pressure = 0.5
            verdict = "HOLD"
    else:
        buy_pressure = 0.5
        sell_pressure = 0.5
        verdict = "HOLD"

    return {
        "symbol": symbol,
        "price": price,
        "buy_pressure": round(buy_pressure, 4),
        "sell_pressure": round(sell_pressure, 4),
        "verdict": verdict,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/signals")
async def get_signals(http_request: Request) -> dict[str, Any]:
    """Market signals for dashboard.

    Queries ExchangeManager for latest prices across the watchlist.
    Falls back to hardcoded defaults only when completely disconnected.
    """
    em = _get_exchange_manager(http_request)
    symbols_data = []
    primary = ["BTC", "ETH", "SPY"]

    for sym in primary:
        price = await _try_fetch_price(em, sym)
        regime = await _try_detect_regime(em, sym)
        change = 0.0
        if regime and "indicators" in regime:
            change = regime["indicators"].get("slope", 0.0) * 100
        symbols_data.append({
            "symbol": sym,
            "price": price,
            "change": round(change, 2) if change else 0.0,
            "regime": regime["regime"] if regime else "unknown",
        })

    return {
        "symbols": symbols_data,
        "timestamp": datetime.now().isoformat(),
    }
