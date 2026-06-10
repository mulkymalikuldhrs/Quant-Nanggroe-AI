"""Market data API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    OHLCVRequest,
    OHLCVResponse,
    PriceResponse,
    MarketRegimeRequest,
    MarketRegimeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str) -> PriceResponse:
    """Get latest price for a symbol.

    Args:
        symbol: Trading symbol (e.g., AAPL, BTC-USD).

    Returns:
        PriceResponse with current price data.
    """
    # Placeholder — would connect to market data provider
    return PriceResponse(symbol=symbol, price=None)


@router.post("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(request: OHLCVRequest) -> OHLCVResponse:
    """Get OHLCV candlestick data for a symbol.

    Args:
        request: OHLCVRequest with symbol, timeframe, and limit.

    Returns:
        OHLCVResponse with candlestick data.
    """
    # Placeholder — would connect to market data provider
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
    """Get current pressure analysis for a symbol.

    Returns the latest pressure normalization result if available.

    Args:
        symbol: Trading symbol.

    Returns:
        Dict with pressure analysis data.
    """
    return {"symbol": symbol, "buy_pressure": 0.0, "sell_pressure": 0.0, "verdict": "NEUTRAL"}
