"""
QNA RISK LEVELS — ATR + Structure based SL/TP + trailing
========================================================
Problem (user 2026-08-02):
  - SL/TP hardcoded to ±0.5%/±1% (arbitrary, not strategy/volatility aware)
  - Most trades have NO sl/tp because fixed % is below broker trade_stops_level
    (BTCUSD.vx=2976pts) -> broker rejects -> trade fills naked or fails
  - Trailing SL is fixed 0.5% behind entry (no ATR/structure)

Fix:
  - compute_atr(candles, period=14) -> Average True Range
  - strategy_sl_tp(symbol, side, entry, atr, structure) -> SL/TP distance in price
    respecting broker trade_stops_level minimum
  - trailing_sl_atr(side, entry, current, atr, activation_r) -> ATR-based trail

REAL-ONLY: pure math, no external calls.
"""
from typing import List, Dict, Optional


def compute_atr(candles: List[Dict], period: int = 14) -> float:
    """Average True Range from OHLC candles. Returns 0.0 if insufficient data."""
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i].get("high", candles[i].get("close", 0))
        l = candles[i].get("low", candles[i].get("close", 0))
        c_prev = candles[i - 1].get("close", candles[i].get("close", 0))
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return sum(trs[-period:]) / period


def _find_structure_swing(candles: List[Dict], side: str) -> Optional[float]:
    """Find nearest swing high/low as structure level.
    For buy: recent swing low (support). For sell: recent swing high (resistance).
    Returns price level or None if not determinable.
    """
    if len(candles) < 20:
        return None
    highs = [c.get("high", c.get("close", 0)) for c in candles[-20:]]
    lows = [c.get("low", c.get("close", 0)) for c in candles[-20:]]
    if side == "buy":
        return min(lows)  # nearest support
    else:
        return max(highs)  # nearest resistance


def strategy_sl_tp(symbol: str, side: str, entry: float, atr: float,
                   candles: List[Dict], min_stop_points: float = 0.0,
                   point_size: float = 0.00001) -> Dict[str, float]:
    """Compute SL/TP distance from ATR + structure, clamped to broker min stop.

    SL = max(structure swing, entry - atr*2)  for buy
    TP = entry + atr*3                      for buy (3:2 R:R)
    Clamped so SL distance >= min_stop_points * point_size (broker trade_stops_level).

    Returns {sl, tp, sl_dist, tp_dist} in price terms.
    """
    if atr <= 0:
        atr = entry * 0.005  # fallback 0.5% if ATR unavailable

    swing = _find_structure_swing(candles, side)
    if side == "buy":
        # SL below structure swing, but at least 2*ATR below entry
        struct_sl = swing if swing else entry - atr * 2
        sl = min(struct_sl, entry - atr * 1.5)
        sl = min(sl, entry - atr * 1.0)  # never closer than 1 ATR
        tp = entry + atr * 3.0
    else:
        struct_sl = swing if swing else entry + atr * 2
        sl = max(struct_sl, entry + atr * 1.5)
        sl = max(sl, entry + atr * 1.0)
        tp = entry - atr * 3.0

    # Clamp SL to broker minimum stop distance
    min_dist = min_stop_points * point_size
    if min_dist > 0:
        if side == "buy":
            sl_dist = entry - sl
            if sl_dist < min_dist:
                sl = entry - min_dist
            tp_dist = tp - entry
            if tp_dist < min_dist * 1.5:  # keep R:R >= 1.5
                tp = entry + min_dist * 1.5
        else:
            sl_dist = sl - entry
            if sl_dist < min_dist:
                sl = entry + min_dist
            tp_dist = entry - tp
            if tp_dist < min_dist * 1.5:
                tp = entry - min_dist * 1.5

    return {"sl": round(sl, 5), "tp": round(tp, 5),
            "sl_dist": abs(entry - sl), "tp_dist": abs(tp - entry)}


def trailing_sl_atr(side: str, entry: float, current: float, current_sl: float,
                    atr: float, activation_r: float = 1.0) -> float:
    """ATR-based trailing stop. Activates after `activation_r` R of profit.

    Trail distance = 2 * ATR behind current price (structure-aware: only moves
    in favor of position). For buy: new_sl = max(current - 2*ATR, current_sl).
    """
    if atr <= 0:
        atr = entry * 0.005
    trail_dist = 2.0 * atr
    if side == "buy":
        # R multiple from entry
        risk = entry - current_sl if current_sl > 0 else entry * 0.005
        r_mult = (current - entry) / risk if risk > 0 else 0
        if r_mult < activation_r:
            return current_sl  # not activated yet
        new_sl = current - trail_dist
        return max(new_sl, current_sl)  # only move up
    else:
        risk = current_sl - entry if current_sl > 0 else entry * 0.005
        r_mult = (entry - current) / risk if risk > 0 else 0
        if r_mult < activation_r:
            return current_sl
        new_sl = current + trail_dist
        return min(new_sl, current_sl)  # only move down


def breakeven_sl(side: str, entry: float, current: float, current_sl: float,
                 activation_r: float = 1.0, buffer_atr: float = 0.0) -> float:
    """G11: Move SL to breakeven after `activation_r` R of profit.

    Once price is `activation_r` R beyond entry, SL snaps to entry (+ small
    buffer in ATR units) so the trade can never return a loss. Only moves in
    favor; returns current_sl unchanged if not activated.
    """
    if current_sl is None or current_sl <= 0:
        return current_sl
    risk = abs(entry - current_sl)
    if risk <= 0:
        return current_sl
    if side == "buy":
        r_mult = (current - entry) / risk
        if r_mult < activation_r:
            return current_sl
        new_sl = entry + buffer_atr  # buffer ≥ 0 → slightly above entry
        return max(new_sl, current_sl)  # never move SL down
    else:
        r_mult = (entry - current) / risk
        if r_mult < activation_r:
            return current_sl
        new_sl = entry - buffer_atr
        return min(new_sl, current_sl)  # never move SL up


def trailing_sl_structure(side: str, entry: float, current: float, current_sl: float,
                          highs: list, lows: list, lookback: int = 20,
                          activation_r: float = 1.0) -> float:
    """G11: Structure-based trailing stop using SMC swing points.

    Tracks the MOST RECENT swing low (for buy) / swing high (for sell) within
    the last `lookback` candles that is still on the profitable side of price.
    SL trails just beyond that swing — the classic SMC 'invalidate on break of
    structure' behavior: if price breaks the swing, the thesis is invalid.

    Only moves in favor of the position. Returns current_sl unchanged when:
      - not activated (below activation_r R)
      - no valid swing found in lookback
      - proposed level is worse than current_sl
    """
    if current_sl is None or current_sl <= 0:
        return current_sl
    risk = abs(entry - current_sl)
    if risk <= 0:
        return current_sl
    if side == "buy":
        r_mult = (current - entry) / risk
        if r_mult < activation_r:
            return current_sl
        # most recent swing low still below current price (profit side)
        for lvl in reversed(lows[-lookback:]):
            if lvl and lvl > 0 and lvl < current:
                new_sl = lvl
                return max(new_sl, current_sl)  # only move up
        return current_sl
    else:
        r_mult = (entry - current) / risk
        if r_mult < activation_r:
            return current_sl
        # most recent swing high still above current price (profit side)
        for lvl in reversed(highs[-lookback:]):
            if lvl and lvl > 0 and lvl > current:
                new_sl = lvl
                return min(new_sl, current_sl)  # only move down
        return current_sl
