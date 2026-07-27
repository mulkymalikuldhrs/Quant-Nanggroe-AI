"""ML Signal Generator API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from ._data import signals_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


class GenerateSignalRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str


@router.get("/list")
async def list_signals() -> dict[str, Any]:
    return {
        "items": signals_list(),
        "count": 4,
        "module": "signals",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/active")
async def active_signals() -> dict[str, Any]:
    active = [s for s in signals_list() if s["direction"] != "neutral"]
    return {"items": active, "count": len(active)}


@router.post("/generate")
async def generate_signal(body: GenerateSignalRequest) -> dict[str, Any]:
    """Generate a real signal from a strategy using live market data."""
    try:
        # Load strategy
        from quant_nanggroe.engine.strategies import create_strategy
        strategy = create_strategy(body.strategy)
        
        # Load live data via yfinance
        import yfinance as yf
        ticker_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
            "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X",
            "NZDUSD": "NZDUSD=X",
        }
        symbol = ticker_map.get(body.symbol, body.symbol)
        df = yf.Ticker(symbol).history(period="6mo")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        
        if len(df) < 50:
            return {"strategy": body.strategy, "symbol": body.symbol, "signal": "hold", "confidence": 0.0, "reason": "insufficient data"}
        
        # Generate signal
        result = strategy.generate_signal(df)
        
        signal_type = "hold"
        confidence = 0.0
        if result is not None:
            if hasattr(result, 'signal_type'):
                signal_type = result.signal_type.value
                confidence = getattr(result, 'confidence', 0.5)
            elif isinstance(result, pd.Series) and len(result) > 0:
                last = result.iloc[-1]
                if last > 0: signal_type = "buy"
                elif last < 0: signal_type = "sell"
                confidence = abs(last)
        
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
async def batch_generate_signals(symbols: list[str] = None) -> dict[str, Any]:
    """Generate signals for all KEEP strategies across multiple symbols."""
    if not symbols:
        symbols = ["BTC-USD", "ETH-USD", "EURUSD=X", "USDJPY=X", "AUDUSD=X"]
    
    # Load backtest results to get KEEP strategies
    import os
    results_path = os.path.join("D:", os.sep, "repositories", "Quant-Nanggroe-AI-worktree", "backtest_all_results.md")
    keep_strategies = []
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("|") and "KEEP" in line:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 2:
                        keep_strategies.append(parts[0].strip())
    
    # Generate signals
    all_signals = []
    import yfinance as yf
    ticker_map = {
        "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X",
        "NZDUSD": "NZDUSD=X",
    }
    
    # Cache data per symbol
    data_cache = {}
    for sym in symbols:
        yf_sym = ticker_map.get(sym, sym)
        try:
            df = yf.Ticker(yf_sym).history(period="6mo")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            data_cache[sym] = df
        except Exception:
            continue
    
    from quant_nanggroe.engine.strategy.strategies import create_strategy
    for strat_name in keep_strategies[:20]:  # Top 20 KEEP strategies
        for sym, df in data_cache.items():
            if len(df) < 50:
                continue
            try:
                strategy = create_strategy(strat_name)
                result = strategy.generate_signal(df)
                signal_type = "hold"
                confidence = 0.0
                if result is not None:
                    if hasattr(result, 'signal_type'):
                        signal_type = result.signal_type.value
                        confidence = getattr(result, 'confidence', 0.5)
                    elif isinstance(result, pd.Series) and len(result) > 0:
                        last = result.iloc[-1]
                        if last > 0: signal_type = "buy"
                        elif last < 0: signal_type = "sell"
                        confidence = abs(last)
                if signal_type != "hold":
                    all_signals.append({
                        "strategy": strat_name,
                        "symbol": sym,
                        "signal": signal_type,
                        "confidence": round(confidence, 3),
                    })
            except Exception:
                continue
    
    return {
        "signals": all_signals,
        "total": len(all_signals),
        "buy_count": sum(1 for s in all_signals if s["signal"] == "buy"),
        "sell_count": sum(1 for s in all_signals if s["signal"] == "sell"),
        "symbols_scanned": len(data_cache),
        "strategies_scanned": len(keep_strategies[:20]),
        "generated": datetime.now(timezone.utc).isoformat(),
    }
