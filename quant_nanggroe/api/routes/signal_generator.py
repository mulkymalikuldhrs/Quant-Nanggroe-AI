"""ML Signal Generator API routes — wired to real StrategyRegistry + signal engine."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


class GenerateSignalRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str = "1d"


def _generate_real_signals(symbol: str = "BTC-USD", max_signals: int = 20) -> list[dict[str, Any]]:
    """Generate real signals from StrategyRegistry strategies."""
    signals: list[dict[str, Any]] = []
    try:
        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
        all_names = StrategyRegistry.list_strategies()
        if not all_names:
            return signals

        # Fetch data once
        import yfinance as yf
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        }
        yf_sym = ticker_map.get(symbol, symbol)
        df = yf.Ticker(yf_sym).history(period="6mo")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        if len(df) < 50:
            return signals

        for strat_name in all_names[:50]:  # Cap to avoid excessive computation
            try:
                strategy = StrategyRegistry.create(strat_name)
                if strategy is None:
                    continue
                result = strategy.generate_signal(df)
                if result is None:
                    continue

                signal_type = "hold"
                confidence = 0.0
                if hasattr(result, "signal_type"):
                    signal_type = result.signal_type.value if hasattr(result.signal_type, "value") else str(result.signal_type)
                    confidence = float(getattr(result, "confidence", 0.0))
                elif hasattr(result, "direction"):
                    d = result.direction
                    signal_type = d.value if hasattr(d, "value") else str(d)
                    confidence = float(getattr(result, "confidence", 0.0))

                if signal_type in ("buy", "sell") and confidence > 0.1:
                    signals.append({
                        "strategy": strat_name,
                        "symbol": symbol,
                        "signal": signal_type,
                        "confidence": round(confidence, 3),
                        "generated": datetime.now(timezone.utc).isoformat(),
                    })
                    if len(signals) >= max_signals:
                        break
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Real signal generation failed: %s", exc)
    return signals


@router.get("/list")
async def list_signals(
    symbol: str = Query("BTC-USD", description="Symbol to scan"),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Generate real signals from registered strategies."""
    signals = _generate_real_signals(symbol, max_signals=limit)
    return {
        "items": signals,
        "count": len(signals),
        "symbol": symbol,
        "module": "signals",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/active")
async def active_signals(
    symbol: str = Query("BTC-USD", description="Symbol to scan"),
) -> dict[str, Any]:
    """Get active (non-hold) signals from real strategies."""
    signals = _generate_real_signals(symbol, max_signals=50)
    active = [s for s in signals if s["signal"] != "hold"]
    return {"items": active, "count": len(active)}


@router.post("/generate")
async def generate_signal(body: GenerateSignalRequest) -> dict[str, Any]:
    """Generate a real signal from a specific strategy using live market data."""
    try:
        from quant_nanggroe.engine.strategies import create_strategy
        strategy = create_strategy(body.strategy)

        import yfinance as yf
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
            "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X",
            "NZDUSD": "NZDUSD=X",
        }
        yf_sym = ticker_map.get(body.symbol, body.symbol)
        df = yf.Ticker(yf_sym).history(period="6mo")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 50:
            return {"strategy": body.strategy, "symbol": body.symbol, "signal": "hold", "confidence": 0.0, "reason": "insufficient data"}

        result = strategy.generate_signal(df)

        signal_type = "hold"
        confidence = 0.0
        if result is not None:
            if hasattr(result, "signal_type"):
                signal_type = result.signal_type.value if hasattr(result.signal_type, "value") else str(result.signal_type)
                confidence = float(getattr(result, "confidence", 0.5))
            elif hasattr(result, "direction"):
                d = result.direction
                signal_type = d.value if hasattr(d, "value") else str(d)
                confidence = float(getattr(result, "confidence", 0.5))
            elif isinstance(result, pd.Series) and len(result) > 0:
                last = result.iloc[-1]
                if last > 0:
                    signal_type = "buy"
                elif last < 0:
                    signal_type = "sell"
                confidence = abs(float(last))

        return {
            "strategy": body.strategy,
            "symbol": body.symbol,
            "timeframe": body.timeframe,
            "signal": signal_type,
            "confidence": round(confidence, 3),
            "generated": datetime.now(timezone.utc).isoformat(),
            "data_bars": len(df),
        }
    except Exception as e:
        return {
            "strategy": body.strategy,
            "symbol": body.symbol,
            "signal": "error",
            "confidence": 0.0,
            "error": str(e),
            "generated": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/batch-generate")
async def batch_generate_signals(
    symbols: Optional[list[str]] = None,
    max_strategies: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Generate signals for all strategies across multiple symbols."""
    if not symbols:
        symbols = ["BTC-USD", "ETH-USD", "EURUSD=X", "USDJPY=X", "AUDUSD=X"]

    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    all_names = StrategyRegistry.list_strategies()[:max_strategies]

    import yfinance as yf
    ticker_map = {
        "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X",
        "NZDUSD": "NZDUSD=X",
    }

    data_cache: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        yf_sym = ticker_map.get(sym, sym)
        try:
            df = yf.Ticker(yf_sym).history(period="6mo")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            if len(df) >= 50:
                data_cache[sym] = df
        except Exception:
            continue

    all_signals: list[dict[str, Any]] = []
    for strat_name in all_names:
        try:
            strategy = StrategyRegistry.create(strat_name)
            if strategy is None:
                continue
            for sym, df in data_cache.items():
                try:
                    result = strategy.generate_signal(df)
                    if result is None:
                        continue
                    signal_type = "hold"
                    confidence = 0.0
                    if hasattr(result, "signal_type"):
                        signal_type = result.signal_type.value if hasattr(result.signal_type, "value") else str(result.signal_type)
                        confidence = float(getattr(result, "confidence", 0.5))
                    elif hasattr(result, "direction"):
                        d = result.direction
                        signal_type = d.value if hasattr(d, "value") else str(d)
                        confidence = float(getattr(result, "confidence", 0.5))
                    if signal_type in ("buy", "sell"):
                        all_signals.append({
                            "strategy": strat_name,
                            "symbol": sym,
                            "signal": signal_type,
                            "confidence": round(confidence, 3),
                        })
                except Exception:
                    continue
        except Exception:
            continue

    return {
        "signals": all_signals,
        "total": len(all_signals),
        "buy_count": sum(1 for s in all_signals if s["signal"] == "buy"),
        "sell_count": sum(1 for s in all_signals if s["signal"] == "sell"),
        "symbols_scanned": len(data_cache),
        "strategies_scanned": len(all_names),
        "generated": datetime.now(timezone.utc).isoformat(),
    }
