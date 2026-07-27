"""Regime Strategy Filter - Filter Strategies by Regime Compatibility."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RM = {
    "trending_up": [("momentum",0.9),("trend",0.9),("trend_following_cta",0.85),("aroon",0.8),("parabolic_sar",0.8),("hull_ma",0.75),("mean_reversion",0.2)],
    "trending_down": [("momentum",0.9),("trend",0.85),("trend_following_cta",0.8),("hull_ma",0.75),("parabolic_sar",0.7),("mean_reversion",0.3)],
    "bull_trend": [("momentum",0.95),("trend",0.9),("trend_following_cta",0.85),("aroon",0.8),("parabolic_sar",0.8),("mean_reversion",0.2)],
    "bear_trend": [("momentum",0.85),("trend",0.8),("trend_following_cta",0.75),("mean_reversion",0.3)],
    "ranging": [("mean_reversion",0.9),("bollinger",0.85),("bollinger_squeeze",0.85),("rsi",0.8),("stochastic",0.75),("pairs_trading",0.8),("momentum",0.3),("trend",0.2)],
    "sideways": [("mean_reversion",0.85),("bollinger",0.8),("bollinger_squeeze",0.8),("rsi",0.75),("momentum",0.2),("trend",0.15)],
    "high_volatility": [("volatility",0.9),("bollinger_squeeze",0.8),("entropy",0.8),("garch",0.85),("kalman",0.75),("mean_reversion",0.6),("momentum",0.4)],
    "volatile": [("volatility",0.9),("bollinger_squeeze",0.8),("entropy",0.8),("garch",0.85),("kalman",0.75),("mean_reversion",0.6)],
    "low_volatility": [("momentum",0.85),("trend",0.85),("trend_following_cta",0.8),("aroon",0.75),("hull_ma",0.7),("mean_reversion",0.6)],
    "crisis": [("mean_reversion",0.7),("bollinger",0.65),("momentum_crash_filter",0.8),("volatility",0.5),("momentum",0.15),("trend",0.1)],
    "recovery": [("momentum",0.8),("trend",0.8),("aroon",0.75),("mean_reversion",0.4)],
    "unknown": [("momentum",0.5),("trend",0.5),("mean_reversion",0.5),("bollinger",0.5),("volatility",0.4)],
}

def _cls(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["momentum","trend","aroon","parabolic","hull","dual_ma","adx","dmi","trix"]): return "trend"
    if any(k in n for k in ["mean_reversion","bollinger","rsi","stochastic","pairs","fibonacci","pivot"]): return "mean_reversion"
    if any(k in n for k in ["vol","entropy","kalman","garch","hurst"]): return "volatility"
    if any(k in n for k in ["engulfing","doji","hammer","pattern","candle","star","piercing","harami","dark_cloud"]): return "pattern"
    if any(k in n for k in ["carry","funding","crypto","gold","dxy","vix","yield","options"]): return "specialty"
    return "default"

class RegimeStrategyFilter:
    def __init__(self, min_compatibility: float = 0.35): self.min_compatibility = min_compatibility
    def filter_strategies(self, strategy_names: list[str], regime: str, min_compat: Optional[float] = None) -> list[tuple[str, float]]:
        th = min_compat if min_compat is not None else self.min_compatibility
        rm = _RM.get(regime.lower(), _RM["unknown"])
        types = {n: _cls(n) for n in strategy_names}
        res = []
        for n in strategy_names:
            st = types[n]; c = 0.5
            for stype, sc in rm:
                if stype in st or st in stype or stype == st: c = sc; break
            if c >= th: res.append((n, c))
        res.sort(key=lambda x: -x[1])
        logger.info("RegimeFilter: %d/%d compatible with %s", len(res), len(strategy_names), regime)
        return res
    def get_compatibility(self, strategy_name: str, regime: str) -> float:
        st = _cls(strategy_name)
        for stype, sc in _RM.get(regime.lower(), _RM["unknown"]):
            if stype in st or st in stype or stype == st: return sc
        return 0.3
    def get_best_strategies(self, regime: str, top_n: int = 5) -> list[str]:
        return [s[0] for s in sorted(_RM.get(regime.lower(), _RM["unknown"]), key=lambda x: -x[1])[:top_n]]

__all__ = ["RegimeStrategyFilter"]
