"""Market data API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

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
    """Get overall market sentiment from Fear & Greed + macro weather."""
    try:
        import requests
        fg_resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        fg_data = fg_resp.json()
        fgi = int(fg_data["data"][0]["value"])
    except Exception:
        fgi = None

    from quant_nanggroe.engine.causal.weather_matrix import MacroWeatherEngine
    weather = MacroWeatherEngine()
    weather_regime = weather.to_dict().get("current_regime", "UNKNOWN")

    return {
        "overall": "bullish" if fgi and fgi > 60 else "bearish" if fgi and fgi < 40 else "neutral",
        "fear_greed_index": fgi,
        "macro_weather": weather_regime,
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    }


def _get_exchange_manager(http_request: Request):
    """Retrieve the singleton ExchangeManager from services."""
    from quant_nanggroe.services import get_exchange_manager
    return get_exchange_manager(http_request.app)


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
    """Market pressure analysis via VolumeDelta / CVD strategy on real OHLCV data."""
    try:
        from quant_nanggroe.engine.strategies.volume_delta import VolumeDeltaStrategy
        from quant_nanggroe.types.market import TimeFrame as TF

        em = _get_exchange_manager(http_request)
        candles = await em.get_ohlcv(symbol=symbol, timeframe=TF.D1, limit=60)

        if not candles or len(candles) < 20:
            return {
                "symbol": symbol,
                "buy_pressure": 0.5,
                "sell_pressure": 0.5,
                "verdict": "INSUFFICIENT_DATA",
                "status": "no_data",
                "timestamp": datetime.now().isoformat(),
            }

        import pandas as pd
        df = pd.DataFrame([
            {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in candles
        ])

        strategy = VolumeDeltaStrategy()
        signal = strategy.generate_signal(df, symbol=symbol)

        # Extract pressure from the signal
        buy_pressure = float(signal.confidence) if hasattr(signal, "confidence") else 0.5
        sell_pressure = 1.0 - buy_pressure
        action = signal.action.value if hasattr(signal, "action") else "hold"
        verdict = "BUY" if "buy" in action.lower() else "SELL" if "sell" in action.lower() else "NEUTRAL"

        return {
            "symbol": symbol,
            "buy_pressure": round(buy_pressure, 4),
            "sell_pressure": round(sell_pressure, 4),
            "verdict": verdict,
            "confidence": round(float(getattr(signal, "confidence", 0.5)), 4),
            "status": "live",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        logger.exception("market_pressure_failed symbol=%s", symbol)
        return {
            "symbol": symbol,
            "buy_pressure": 0.5,
            "sell_pressure": 0.5,
            "verdict": "ERROR",
            "status": "error",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/signals")
async def get_signals() -> dict[str, Any]:
    """Market signals from the autonomous pipeline's last run result."""
    try:
        from quant_nanggroe.engine.agentic.autonomous import get_autonomous_pipeline
        pipeline = get_autonomous_pipeline()
        last = pipeline._last_result
        signals = []
        if last is not None and last.success:
            signals.append({
                "symbol": last.symbol,
                "signal": last.signal,
                "confidence": last.confidence,
                "reason": last.reason,
                "timestamp": last.timestamp,
            })
        return {"signals": signals, "status": "ok"}
    except Exception as e:
        return {"signals": [], "status": "ok", "error": str(e)}


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    http_request: Request,
    timeframe: str = Query("1d", description="Candle timeframe: 1m,5m,15m,30m,1h,4h,1d,1w,1M"),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Candlestick data for charting — real OHLCV via ExchangeManager, MT5 fallback.

    Fail-closed: raises 503 when no live source returns data (never mock data).
    """
    from quant_nanggroe.types.market import TimeFrame as TF

    tf_map = {
        "1m": TF.M1, "5m": TF.M5, "15m": TF.M15, "30m": TF.M30,
        "1h": TF.H1, "4h": TF.H4, "1d": TF.D1, "1w": TF.W1, "1M": TF.MO1,
    }
    tf = tf_map.get(timeframe, TF.D1)

    def _serialize(candles: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for c in candles or []:
            ts = c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else str(c.timestamp)
            out.append({
                "time": ts,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(getattr(c, "volume", 0.0) or 0.0),
            })
        return out

    try:
        em = _get_exchange_manager(http_request)
        candles = await em.get_ohlcv(symbol=symbol, timeframe=tf, limit=limit)
        data = _serialize(candles)
        if data:
            return data
        logger.warning("candles_empty symbol=%s timeframe=%s via ExchangeManager", symbol, timeframe)
    except Exception as exc:
        logger.warning("candles_exchange_failed symbol=%s error=%s", symbol, exc)

    try:
        from quant_nanggroe.exchange.base import ExchangeConfig
        from quant_nanggroe.exchange.mt5_broker import MT5Broker

        config = ExchangeConfig(exchange_id="mt5")
        broker = MT5Broker(config)
        await broker.connect()
        try:
            ohlcv = await broker.get_ohlcv(symbol, limit=limit)
        finally:
            await broker.disconnect()
        data = _serialize(ohlcv)
        if data:
            return data
    except ImportError:
        raise HTTPException(status_code=503, detail=f"Candles unavailable for {symbol}: MetaTrader5 not installed")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("candles_mt5_failed symbol=%s error=%s", symbol, exc)

    raise HTTPException(
        status_code=503,
        detail=f"Candles unavailable for {symbol}: all live sources failed",
    )


@router.get("/mt5/{symbol}")
async def mt5_market_data(symbol: str) -> dict[str, Any]:
    """Live market data from MT5 terminal — price, OHLCV, orderbook."""
    try:
        from quant_nanggroe.exchange.base import ExchangeConfig
        from quant_nanggroe.exchange.mt5_broker import MT5Broker

        config = ExchangeConfig(exchange_id="mt5")
        broker = MT5Broker(config)
        await broker.connect()

        ticker = await broker.get_ticker(symbol)
        ohlcv = await broker.get_ohlcv(symbol, limit=5)
        ob = await broker.get_orderbook(symbol)
        await broker.disconnect()

        return {
            "symbol": symbol,
            "price": ticker.price,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "candles": [{"t": c.timestamp.isoformat(), "o": c.open, "h": c.high, "l": c.low, "c": c.close, "v": c.volume} for c in ohlcv],
            "bids": [[p.price, p.size] for p in ob.bids[:5]],
            "asks": [[p.price, p.size] for p in ob.asks[:5]],
            "source": "mt5",
        }
    except ImportError:
        return {"error": "MetaTrader5 not installed", "source": "mt5"}
    except Exception as e:
        return {"error": str(e), "source": "mt5"}
