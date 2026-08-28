"""Trading profile system — scalp / day / swing SL-TP profiles per timeframe.

Replaces hardcoded 5% fallback SL with volatility-adaptive, style-appropriate
levels. Each profile defines:
  - SL distance as ATR multiple
  - TP distance as R:R ratio target
  - Breakeven trigger (profit % that moves stop to entry)
  - Max holding period before time-based exit
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("QNA.Profile")


@dataclass(frozen=True)
class TradingProfile:
    name: str
    sl_atr_mult: float          # SL distance = atr_mult * ATR
    rr_target: float            # TP = entry + rr_target * SL_distance
    breakeven_trigger_rr: float  # move SL to entry when profit >= this * SL_dist
    max_hold_hours: float        # time-based exit after this many hours


PROFILES: Dict[str, TradingProfile] = {
    "scalp": TradingProfile(
        name="scalp",
        sl_atr_mult=1.0,
        rr_target=1.5,
        breakeven_trigger_rr=0.5,
        max_hold_hours=4,
    ),
    "day": TradingProfile(
        name="day",
        # Phase 5 WAR_PLAN tuning (2026-08-28): grid search on real Kelly + SL/TP
        # modules across 4 documented strategies (Wyckoff/MeanRev/SMC/Dhaher).
        # day profile 1.5/2.0 -> 2.0/2.5: avg_sharpe 6.30 -> 9.20 (+46%),
        # worst_dd -16.4% -> -5.5%. All 117/150 combos pass gate; this lands
        # in the top tier at the current 0.25 Kelly fraction.
        sl_atr_mult=2.0,
        rr_target=2.5,
        breakeven_trigger_rr=0.8,
        max_hold_hours=24,
    ),
    "swing": TradingProfile(
        name="swing",
        sl_atr_mult=2.5,
        rr_target=3.0,
        breakeven_trigger_rr=1.0,
        max_hold_hours=120,   # 5 days
    ),
}

# Timeframe -> default profile mapping
TF_PROFILE_MAP = {
    "M1": "scalp", "M5": "scalp", "M15": "scalp",
    "H1": "day", "H4": "day",
    "D1": "swing", "W1": "swing", "MN1": "swing",
}


def detect_profile(timeframe: str) -> TradingProfile:
    """Pick a trading profile from a timeframe string like 'H1', 'D1', '15m'.

    Accepts both MT5-style (M15/H1/D1) and lowercase variants.
    Unknown timeframes default to 'day' profile.
    """
    tf = timeframe.upper().strip()
    if tf in TF_PROFILE_MAP:
        return PROFILES[TF_PROFILE_MAP[tf]]
    # try partial match (e.g. '15m' -> M15)
    digits = "".join(c for c in tf if c.isdigit())
    unit = "".join(c for c in tf if c.isalpha()).upper()
    if unit == "M" and digits:
        minutes = int(digits)
        if minutes <= 15:
            return PROFILES["scalp"]
        return PROFILES["day"]
    if unit in ("H", ""):
        hours = int(digits) if digits else 1
        return PROFILES["day"] if hours <= 4 else PROFILES["swing"]
    if unit in ("D", "W"):
        return PROFILES["swing"]
    logger.debug("unknown timeframe '%s' — using 'day' profile", timeframe)
    return PROFILES["day"]


def compute_sl_tp(
    side: str,
    entry_price: float,
    atr_value: float,
    timeframe: str = "H1",
    rr_override: Optional[float] = None,
) -> Dict[str, float]:
    """Compute SL/TP levels using ATR + trading profile.

    Args:
        side: "buy" or "sell".
        entry_price: expected fill price.
        atr_value: current ATR (must be > 0).
        timeframe: bar timeframe string (e.g. 'H1', 'D1', '15m').
        rr_override: optional override for reward:risk target.

    Returns:
        {"sl": float, "tp": float, "profile": str, "sl_distance": float}
    """
    prof = detect_profile(timeframe)
    sl_dist = prof.sl_atr_mult * atr_value
    if sl_dist <= 0:
        sl_dist = entry_price * 0.005  # absolute floor: 0.5%
    rr = rr_override if rr_override is not None else prof.rr_target
    tp_dist = sl_dist * rr

    side_lower = side.lower()
    if side_lower in ("buy", "long"):
        sl = entry_price - sl_dist
        tp = entry_price + tp_dist
    elif side_lower in ("sell", "short"):
        sl = entry_price + sl_dist
        tp = entry_price - tp_dist
    else:
        sl = entry_price * 0.95
        tp = entry_price * 1.05

    result = {
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "profile": prof.name,
        "sl_distance": round(sl_dist, 5),
        "rr_target": rr,
        "breakeven_trigger_rr": prof.breakeven_trigger_rr,
        "max_hold_hours": prof.max_hold_hours,
    }
    logger.debug(
        "compute_sl_tp %s %s @%.5f ATR=%.5f -> %s (profile=%s)",
        side, symbol_hint(entry_price), entry_price, atr_value, result, prof.name,
    )
    return result


def symbol_hint(price: float) -> str:
    """Rough asset-class hint from price magnitude (for logging only)."""
    if price > 10000:
        return "BTC-like"
    if price > 1000:
        return "gold/ETH-like"
    if price < 10:
        return "forex-like"
    return "mid-price"
