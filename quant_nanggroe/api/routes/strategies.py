"""API routes for strategy management, selection, and backtesting."""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from quant_nanggroe.engine.strategy.strategies import (
    list_strategies,
    create_strategy,
)

# Metadata with REAL backtest results — verified 2026-07-14.
# Sources: QNAI standalone backtest (BTC-USD, EURUSD) + TradingView MCP (10 symbols, 2y daily).
_STRATEGY_META = {
    "mean_reversion": {
        "description": "Mean reversion on close price",
        "category": "statistical", "asset_classes": ["forex", "crypto"], "timeframes": ["1h", "4h", "1d"],
        "backtest": {"btc_return": -90.94, "btc_sharpe": -4.0, "eur_return": -31.48, "eur_sharpe": -4.37, "verdict": "ELIMINATE", "reason": "Negative on both symbols, high frequency losses"},
    },
    "momentum": {
        "description": "Price momentum over N bars",
        "category": "trend", "asset_classes": ["crypto", "equity"], "timeframes": ["4h", "1d"],
        "backtest": {"btc_return": 80.74, "btc_sharpe": 0.80, "eur_return": 9.89, "eur_sharpe": 1.12, "verdict": "KEEP", "reason": "Positive both symbols, high R:R (4.75 BTC)"},
    },
    "pairs_trading": {
        "description": "Statistical pairs arbitrage",
        "category": "statistical", "asset_classes": ["equity", "forex"], "timeframes": ["1d"],
        "backtest": {"btc_return": -10.99, "btc_sharpe": -0.74, "eur_return": 1.73, "eur_sharpe": 0.88, "verdict": "MARGINAL", "reason": "Mixed — weak on crypto, marginal on forex"},
    },
    "trend_follow": {
        "description": "Trend following with moving averages",
        "category": "trend", "asset_classes": ["forex", "crypto", "commodity"], "timeframes": ["4h", "1d"],
        "backtest": {"verdict": "KEEP", "reason": "Core trend strategy, EMA Cross positive on 7/10 TradingView symbols"},
    },
    "smc_strategy": {
        "description": "Smart Money Concepts — order blocks, FVG, liquidity",
        "category": "price_action", "asset_classes": ["forex", "crypto"], "timeframes": ["15m", "1h", "4h"],
        "backtest": {"btc_return": 173.23, "btc_sharpe": 1.21, "eur_return": 46.68, "eur_sharpe": 3.45, "verdict": "KEEP", "reason": "Strong on both crypto and forex, Sharpe 3.45 on EURUSD"},
    },
    "ict_strategy": {
        "description": "Inner Circle Trader — OB, FVG, liquidity sweeps",
        "category": "price_action", "asset_classes": ["forex", "crypto"], "timeframes": ["15m", "1h"],
        "backtest": {"btc_return": 45.46, "btc_sharpe": 1.20, "eur_return": 0, "eur_sharpe": 0, "verdict": "KEEP", "reason": "Solid on BTC (66.7% WR), no signals on range-bound EURUSD"},
    },
    "cot_strategy": {
        "description": "Commitment of Traders positioning",
        "category": "fundamental", "asset_classes": ["forex", "commodity"], "timeframes": ["1d", "1w"],
        "backtest": {"btc_return": -34.88, "btc_sharpe": -1.25, "eur_return": 0, "eur_sharpe": 0, "verdict": "ELIMINATE", "reason": "Negative Sharpe on BTC, no data on EURUSD"},
    },
    "fundamental_strategy": {
        "description": "Fundamental analysis — earnings, macro",
        "category": "fundamental", "asset_classes": ["equity"], "timeframes": ["1d", "1w"],
        "backtest": {"btc_return": 1365.64, "btc_sharpe": 2.78, "eur_return": 55.02, "eur_sharpe": 3.27, "verdict": "KEEP", "reason": "Massive returns both symbols, but likely overfitting — needs walk-forward"},
    },
    "market_making": {
        "description": "Spread capture / liquidity provision",
        "category": "market_microstructure", "asset_classes": ["crypto"], "timeframes": ["1m", "5m"],
        "backtest": {"btc_return": -90.94, "btc_sharpe": -4.0, "eur_return": -31.48, "eur_sharpe": -4.37, "verdict": "ELIMINATE", "reason": "Identical to mean_reversion — likely same signal logic"},
    },
    "regime_based": {
        "description": "Adaptive strategy based on market regime detection",
        "category": "adaptive", "asset_classes": ["forex", "crypto", "equity"], "timeframes": ["1h", "4h", "1d"],
        "backtest": {"btc_return": 1880.68, "btc_sharpe": 4.53, "eur_return": 0, "eur_sharpe": 0, "verdict": "KEEP", "reason": "Highest Sharpe on BTC (4.53), needs walk-forward validation"},
    },
    "statistical_arbitrage": {
        "description": "Mean-revert spread between correlated assets",
        "category": "statistical", "asset_classes": ["equity", "crypto"], "timeframes": ["1h", "4h"],
        "backtest": {"btc_return": 6.54, "btc_sharpe": 0.25, "eur_return": -3.03, "eur_sharpe": -0.54, "verdict": "MARGINAL", "reason": "Weak positive on BTC, negative on EURUSD"},
    },
    "supply_demand_strategy": {
        "description": "Supply/demand zone identification and trading",
        "category": "price_action", "asset_classes": ["forex", "crypto"], "timeframes": ["1h", "4h"],
        "backtest": {"btc_return": -38.61, "btc_sharpe": -0.54, "eur_return": 3.93, "eur_sharpe": 0.55, "verdict": "ELIMINATE", "reason": "Deep loss on BTC, marginal on EURUSD"},
    },
    "support_resistance_strategy": {
        "description": "S/R level breakout and bounce",
        "category": "price_action", "asset_classes": ["forex", "crypto", "equity"], "timeframes": ["4h", "1d"],
        "backtest": {"btc_return": -23.92, "btc_sharpe": -0.41, "eur_return": 5.93, "eur_sharpe": 0.63, "verdict": "ELIMINATE", "reason": "Negative on BTC, marginal on EURUSD"},
    },
    "volatility_arbitrage": {
        "description": "Vol expansion/contraction arbitrage",
        "category": "volatility", "asset_classes": ["crypto", "equity"], "timeframes": ["1h", "4h"],
        "backtest": {"btc_return": 24.26, "btc_sharpe": 0.47, "eur_return": -8.06, "eur_sharpe": -1.18, "verdict": "MARGINAL", "reason": "Works on BTC vol, fails on EURUSD"},
    },
    "wyckoff_strategy": {
        "description": "Wyckoff accumulation/distribution phases",
        "category": "price_action", "asset_classes": ["equity", "crypto"], "timeframes": ["4h", "1d"],
        "backtest": {"btc_return": 0, "btc_sharpe": 0, "eur_return": 0, "eur_sharpe": 0, "verdict": "SKIP", "reason": "0 trades on both symbols — pattern thresholds too strict"},
    },
    "crypto_specific": {
        "description": "Crypto-specific signals — funding, OI, on-chain",
        "category": "crypto", "asset_classes": ["crypto"], "timeframes": ["1h", "4h"],
        "backtest": {"verdict": "UNTESTED", "reason": "Needs on-chain data not available in Yahoo Finance"},
    },
}


def get_strategy_metadata(name: str) -> dict:
    """Get metadata for a strategy by name."""
    meta = _STRATEGY_META.get(name, None)
    if meta:
        return meta
    # Dynamic category from module name — ponytail: no import needed
    cat = "unclassified"
    if any(x in name for x in ["fibonacci", "retracement", "extension", "fan", "arc"]): cat = "fibonacci"
    elif any(x in name for x in ["pattern", "hammer", "engulfing", "star", "crows", "soldiers", "harami", "piercing", "dark_cloud", "doji"]): cat = "candlestick"
    elif any(x in name for x in ["adx", "cci", "mfi", "obv", "williams", "stochastic", "ichimoku", "parabolic", "aroon", "vortex", "dmi", "kaufman", "t3_", "hull_", "dema_", "tema_", "trix_", "elder", "pivot", "camarilla", "woodie"]): cat = "technical"
    elif any(x in name for x in ["regime", "kmeans", "kalman", "linear_reg", "polynomial", "bayesian", "adaptive_", "multi_indicator", "particle"]): cat = "ml"
    elif any(x in name for x in ["garch", "ewma_vol", "squeeze", "atr_break", "volatility", "vix_", "vol_surface"]): cat = "volatility"
    elif any(x in name for x in ["commodity", "gold_inf", "yield", "dxy_", "em_carry", "funding", "on_chain", "sentiment", "put_call", "dark_pool"]): cat = "macro"
    elif any(x in name for x in ["pairs", "stat_arb", "cointegration"]): cat = "statistical"
    elif any(x in name for x in ["momentum", "value_factor", "quality", "size_factor"]): cat = "factor"
    elif any(x in name for x in ["kelly", "risk_parity", "monte_carlo"]): cat = "risk"
    elif any(x in name for x in ["hurst", "half_life", "entropy", "pca_", "rsi_div", "choppiness", "relative_vigor"]): cat = "statistical"
    elif any(x in name for x in ["carry_trade", "trend_following_cta", "mean_reversion_stat"]): cat = "trend"
    elif any(x in name for x in ["options_straddle", "macro_rates", "macro_fx"]): cat = "macro"
    return {"description": name.replace("_", " ").title(), "category": cat, "asset_classes": [], "timeframes": []}
from quant_nanggroe.engine.strategy.strategy_selector import (
    StrategySelector,
    AdaptiveStrategyEngine,
)

router = APIRouter()


class StrategyToggle(BaseModel):
    name: str
    enabled: bool
    params: Optional[Dict] = None


class BacktestRequest(BaseModel):
    strategy_name: str
    params: Optional[Dict] = None
    symbol: str = "BTC"
    days: int = 365


# In-memory strategy config (toggles, params)
_strategy_config: Dict[str, StrategyToggle] = {}


@router.get("/list")
async def list_all_strategies():
    """List all registered strategies with metadata and backtest results."""
    import os
    
    # Load backtest results from file
    bt_results = {}
    results_path = os.path.join("D:", os.sep, "repositories", "Quant-Nanggroe-AI-worktree", "backtest_all_results.md")
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("|") and not line.startswith("|--") and not line.startswith("| Strategy"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 10:
                        name = parts[0].strip()
                        try:
                            bt_results[name] = {
                                "btc_return": float(parts[1].replace("%", "")),
                                "btc_sharpe": float(parts[2]),
                                "btc_wr": float(parts[3].replace("%", "")),
                                "btc_trades": int(parts[5]),
                                "eur_return": float(parts[6].replace("%", "")),
                                "eur_sharpe": float(parts[7]),
                                "verdict": parts[9].replace("\u2705", "").replace("\u274c", "").replace("\u26a0\ufe0f", "").replace("\u23ed\ufe0f", "").strip(),
                            }
                        except (ValueError, IndexError):
                            continue
    
    names = list_strategies()
    result = []
    for name in names:
        meta = get_strategy_metadata(name)
        config = _strategy_config.get(
            name, StrategyToggle(name=name, enabled=True)
        )
        # Merge backtest results (from file or hardcoded metadata)
        bt = meta.get("backtest", {})
        if name in bt_results:
            bt = bt_results[name]
        elif not bt:
            bt = {"verdict": "UNTESTED"}
        
        result.append({
            "name": name,
            "description": meta.get("description", ""),
            "category": meta.get("category", ""),
            "asset_classes": meta.get("asset_classes", []),
            "timeframes": meta.get("timeframes", []),
            "enabled": config.enabled if hasattr(config, 'enabled') else True,
            "backtest": bt,
        })
    return {"strategies": result, "total": len(result)}


@router.post("/{name}/toggle")
async def toggle_strategy(name: str, toggle: StrategyToggle):
    """Enable or disable a strategy."""
    valid = list_strategies()
    if name not in valid:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    _strategy_config[name] = toggle
    return {"name": name, "enabled": toggle.enabled, "params": toggle.params or {}}


@router.get("/backtest-results")
async def get_backtest_results():
    """Read live backtest results from backtest_all_results.md."""
    import os
    results_path = os.path.join("D:", os.sep, "repositories", "Quant-Nanggroe-AI-worktree", "backtest_all_results.md")
    if not os.path.exists(results_path):
        return {"strategies": [], "summary": {}}
    
    with open(results_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    strategies = []
    for line in content.split("\n"):
        if not line.startswith("|") or line.startswith("|--") or line.startswith("| Strategy"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 10:
            continue
        try:
            strategies.append({
                "name": parts[0].strip(),
                "btc_return": float(parts[1].replace("%", "")),
                "btc_sharpe": float(parts[2]),
                "btc_wr": float(parts[3].replace("%", "")),
                "btc_trades": int(parts[5]),
                "eur_return": float(parts[6].replace("%", "")),
                "eur_sharpe": float(parts[7]),
                "verdict": parts[9].replace("\u2705", "").replace("\u274c", "").replace("\u26a0\ufe0f", "").replace("\u23ed\ufe0f", "").strip(),
            })
        except (ValueError, IndexError):
            continue
    
    keep = sum(1 for s in strategies if s["verdict"] == "KEEP")
    eliminate = sum(1 for s in strategies if s["verdict"] == "ELIMINATE")
    marginal = sum(1 for s in strategies if s["verdict"] == "MARGINAL")
    
    return {
        "strategies": strategies,
        "summary": {"total": len(strategies), "keep": keep, "eliminate": eliminate, "marginal": marginal},
    }


@router.get("/{name}")
async def get_strategy_detail(name: str):
    """Get detailed info about a specific strategy."""
    valid = list_strategies()
    if name not in valid:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    meta = get_strategy_metadata(name)
    config = _strategy_config.get(name, StrategyToggle(name=name, enabled=True))
    strategy = create_strategy(name)
    return {
        "name": name,
        "description": meta.get("description", ""),
        "category": meta.get("category", ""),
        "asset_classes": meta.get("asset_classes", []),
        "timeframes": meta.get("timeframes", []),
        "enabled": config.enabled,
        "warmup_period": strategy.warmup_period(),
        "required_columns": strategy.required_columns(),
        "params": strategy.params,
    }


@router.get("/selector/strategies")
async def get_selected_strategies(regime: str = "ranging", top_n: int = 3):
    """Get top N strategies for a given market regime."""
    selector = StrategySelector(top_n=top_n)
    selected = selector.select(regime)
    return {
        "regime": regime,
        "selected": [{"name": n, "score": s} for n, s in selected],
    }


@router.get("/toggles")
async def get_all_toggles():
    """Get all strategy toggle states."""
    return {
        name: {
            "enabled": cfg.enabled,
            "params": cfg.params or {},
        }
        for name, cfg in _strategy_config.items()
    }



