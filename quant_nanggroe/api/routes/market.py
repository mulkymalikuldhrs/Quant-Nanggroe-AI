"""Market data API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from quant_nanggroe.api.schemas import (
    OHLCVCandle,
    OHLCVRequest,
    OHLCVResponse,
    PriceResponse,
    MarketRegimeRequest,
    MarketRegimeResponse,
)
from quant_nanggroe.security.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


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
async def get_pressure(symbol: str, http_request: Request) -> dict[str, Any]:
    """Get current pressure analysis for a symbol.

    Computes real buy/sell pressure from the order book by summing
    bid and ask volumes, then normalising to a 0-1 scale. Falls back
    to the PressureNormalizationEngine's last cached result when the
    order book is unavailable.

    Args:
        symbol: Trading symbol.
        http_request: HTTP request for accessing app state.

    Returns:
        Dict with pressure analysis data.
    """
    try:
        em = _get_exchange_manager(http_request)
        orderbook = await em.get_orderbook(symbol, limit=20)

        # Compute raw buy/sell volume from the order book
        bid_volume = sum(level.quantity for level in orderbook.bids)
        ask_volume = sum(level.quantity for level in orderbook.asks)
        total_volume = bid_volume + ask_volume

        if total_volume > 0:
            buy_pressure = round(bid_volume / total_volume, 4)
            sell_pressure = round(ask_volume / total_volume, 4)
        else:
            buy_pressure = 0.0
            sell_pressure = 0.0

        if buy_pressure > 0.70:
            verdict = "STRONG_BUY"
        elif buy_pressure > 0.55:
            verdict = "BUY"
        elif sell_pressure > 0.70:
            verdict = "STRONG_SELL"
        elif sell_pressure > 0.55:
            verdict = "SELL"
        else:
            verdict = "NEUTRAL"

        return {
            "symbol": symbol,
            "buy_pressure": buy_pressure,
            "sell_pressure": sell_pressure,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "spread": orderbook.spread,
            "mid_price": orderbook.mid_price,
            "verdict": verdict,
            "timestamp": orderbook.timestamp.isoformat(),
        }
    except Exception as exc:
        logger.warning("get_pressure_failed symbol=%s error=%s", symbol, exc)

        # Fall back to the cached PressureNormalizationEngine result
        try:
            from quant_nanggroe.engine.pressure import PressureNormalizationEngine

            if not hasattr(http_request.app.state, "_services"):
                http_request.app.state._services = {}
            if "pressure_engine" not in http_request.app.state._services:
                http_request.app.state._services["pressure_engine"] = PressureNormalizationEngine()
            pe = http_request.app.state._services["pressure_engine"]
            cached = pe.get_pressure()
            if cached is not None:
                return {
                    "symbol": symbol,
                    "buy_pressure": cached.buy_pressure,
                    "sell_pressure": cached.sell_pressure,
                    "verdict": cached.verdict,
                    "source": "cached_pressure_engine",
                }
        except Exception:
            logger.exception("unhandled_error")
            pass

        return {"symbol": symbol, "buy_pressure": 0.0, "sell_pressure": 0.0, "verdict": "NEUTRAL"}
