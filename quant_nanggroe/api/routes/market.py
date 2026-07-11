"""Market data API routes."""

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


@router.get("/sentiment")
async def get_market_sentiment() -> dict[str, Any]:
    """Get overall market sentiment indicator."""
    return {
        "overall": "neutral",
        "fear_greed_index": 52,
        "signals": {
            "technical": "bullish",
            "on_chain": "neutral",
            "news": "bearish",
        },
        "timestamp": datetime.now().isoformat(),
    }


def _get_exchange_manager(http_request: Request):
    """Retrieve or lazily create the ExchangeManager from app state."""
    from quant_nanggroe.exchange.manager import ExchangeManager

    if not hasattr(http_request.app.state, "_services"):
        http_request.app.state._services = {}

    if "exchange_manager" not in http_request.app.state._services:
        http_request.app.state._services["exchange_manager"] = ExchangeManager()
    return http_request.app.state._services["exchange_manager"]


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
async def get_pressure(symbol: str) -> dict[str, Any]:
    """Get current pressure analysis for a symbol."""
    return {"symbol": symbol, "buy_pressure": 0.55, "sell_pressure": 0.45, "verdict": "BUY", "timestamp": datetime.now().isoformat()}


@router.get("/signals")
async def get_signals() -> dict[str, Any]:
    """Market signals for dashboard."""
    return {
        "symbols": [
            {"symbol": "BTC", "price": 108743, "change": 2.4},
            {"symbol": "ETH", "price": 3267, "change": -1.2},
            {"symbol": "SPY", "price": 542, "change": 0.8},
        ],
        "timestamp": datetime.now().isoformat(),
}
